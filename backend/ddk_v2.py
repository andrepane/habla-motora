"""Experimental multiscale acoustic support. V1 remains an independent output."""
import copy
import hashlib
import json
import math
from pathlib import Path
from backend import ddk
from backend.ddk import percentile, DetectionError

CONFIG_BYTES = (Path(__file__).resolve().parents[1] / 'configs/ddk_experimental_v2.json').read_bytes()
CONFIG = json.loads(CONFIG_BYTES)

def _scale_detect(samples, rate, a, b, config):
    window = round(rate*config['window_ms']/1000)
    hop = round(rate*config['hop_ms']/1000)
    weights = [0.5-0.5*math.cos(2*math.pi*i/(window-1)) for i in range(window)]
    total = sum(weights)
    frames = []
    for center in range(a, b, hop):
        left = center-window//2
        energy = sum(samples[j]**2*weights[k] for k, j in enumerate(range(left, left+window)) if 0 <= j < len(samples))/total
        frames.append({'frame_index': len(frames), 'time_s': center/rate,
                       'energy_db': max(config['digital_floor_db'], 10*math.log10(max(energy, 1e-12))),
                       'boundary': left < a or left+window > b})
    if not frames:
        raise DetectionError('No hay frames para analizar.')
    vals = [f['energy_db'] for f in frames]
    threshold = max(percentile(vals, config['noise_percentile'])+config['noise_margin_db'],
                    percentile(vals, config['signal_percentile'])-config['signal_margin_db'])
    candidates = []
    i = 0
    while i < len(vals):
        end = i
        while end+1 < len(vals) and vals[end+1] == vals[i]:
            end += 1
        if (i == 0 or vals[i] > vals[i-1]) and (end == len(vals)-1 or vals[end] > vals[end+1]):
            peak = vals[i]
            left = i
            while left > 0 and vals[left-1] <= peak:
                left -= 1
            right = end
            while right+1 < len(vals) and vals[right+1] <= peak:
                right += 1
            dip = min(peak-min(vals[left:i+1]), peak-min(vals[end:right+1]))
            boundary = any(f['boundary'] for f in frames[i:end+1]) or i == 0 or end == len(vals)-1
            reason = ('boundary_incomplete' if boundary else 'below_threshold' if peak < threshold
                      else 'insufficient_dip' if dip < config['minimum_dip_db'] else None)
            candidates.append({'id': f'c{len(candidates)+1}', 'time_s': (frames[i]['time_s']+frames[end]['time_s'])/2,
                               'energy_db': peak, 'dip_db': dip, 'boundary': boundary,
                               'accepted': reason is None, 'reason': reason})
        i = end+1
    kept = []
    for c in sorted((c for c in candidates if c['accepted']), key=lambda c: (-c['energy_db'], c['time_s'])):
        if any(abs(c['time_s']-k['time_s']) < config['minimum_separation_ms']/1000 for k in kept):
            c['accepted'] = False; c['reason'] = 'minimum_separation'
        else:
            kept.append(c)
    events = [{'id': c['id'], 'time_s': c['time_s'], 'label': 'unknown', 'restart': False}
              for c in candidates if c['accepted']]
    return {'frames': frames, 'threshold_db': threshold, 'candidates': candidates, 'events': events,
            'warnings': ['ACOUSTIC_CANDIDATES_NOT_PHONETIC_RECOGNITION'] + (['POSSIBLE_DIGITAL_CLIPPING'] if any(abs(x) >= .999 for x in samples[a:b]) else [])}


def basins(frames, maxima):
    """All structural maxima partition the time axis, including ineligible ones."""
    values = [f['energy_db'] for f in frames]
    times = [f['time_s'] for f in frames]
    limits = []
    for left, right in zip(maxima, maxima[1:]):
        lo = min(range(len(times)), key=lambda i: abs(times[i]-left['time_s']))
        hi = min(range(len(times)), key=lambda i: abs(times[i]-right['time_s']))
        minimum = min(values[lo:hi+1])
        indices = [i for i in range(lo, hi+1) if values[i] == minimum]
        # Disjoint equal minima: choose the first contiguous minimum plateau.
        end = indices[0]
        while end+1 in indices:
            end += 1
        limits.append((times[indices[0]]+times[end])/2)
    return limits


def width_3db(frames, peak):
    times = [f['time_s'] for f in frames]
    vals = [f['energy_db'] for f in frames]
    i = min(range(len(times)), key=lambda j: abs(times[j]-peak['time_s']))
    level = peak['energy_db']-3
    lo = hi = i
    while lo > 0 and vals[lo-1] >= level: lo -= 1
    while hi+1 < len(vals) and vals[hi+1] >= level: hi += 1
    if lo == 0 or hi == len(vals)-1:
        return ddk.measure(reason='incomplete_crossings')
    left = times[lo]-(vals[lo]-level)/(vals[lo]-vals[lo-1])*(times[lo]-times[lo-1])
    right = times[hi]+(vals[hi]-level)/(vals[hi]-vals[hi+1])*(times[hi+1]-times[hi])
    return ddk.measure((right-left)*1000)


def detect(samples, rate, a, b):
    fine = _scale_detect(samples, rate, a, b, {**CONFIG, 'window_ms':20})
    structural = _scale_detect(samples, rate, a, b, {**CONFIG, 'window_ms':40})
    structures = copy.deepcopy(structural['candidates'])
    # Eligibility is evaluated BEFORE 50 ms suppression.
    for s in structures:
        s['scale_original_accepted'] = s.pop('accepted')
        s['scale_original_reason'] = s.pop('reason')
        s['eligibility_reasons'] = []
        if s['boundary']: s['eligibility_reasons'].append('boundary_incomplete')
        if s['energy_db'] < structural['threshold_db']: s['eligibility_reasons'].append('below_threshold')
        if s['dip_db'] < CONFIG['minimum_dip_db']: s['eligibility_reasons'].append('insufficient_dip')
        s['eligible'] = not s['eligibility_reasons']
        s['width_3db_ms'] = width_3db(structural['frames'],s)
        s['background_margin_db'] = s['energy_db']-percentile([f['energy_db'] for f in structural['frames']],10)
    limits = basins(structural['frames'], structures)
    candidates = copy.deepcopy(fine['candidates'])
    for c in candidates:
        c['v1_scale_accepted'] = c['accepted']
        c['v1_scale_reason'] = c['reason']
        c['reasons'] = []
        c['accepted'] = False
        c['width_3db_ms'] = width_3db(fine['frames'], c)
        c['fine_margin_db'] = c['energy_db']-fine['threshold_db']
        c['fine_background_margin_db'] = c['energy_db']-percentile([f['energy_db'] for f in fine['frames']],10)
        index = sum(c['time_s'] > boundary for boundary in limits)
        s = structures[index]
        c['structure_id'] = s['id']
        c['structural_margin_db'] = s['energy_db']-structural['threshold_db']
        c['scale_offset_ms'] = (c['time_s']-s['time_s'])*1000
        c['threshold_sensitive'] = min(abs(c['fine_margin_db']),abs(c['structural_margin_db'])) <= CONFIG['threshold_sensitive_db']
        if c['boundary']: c['reasons'].append('boundary_incomplete')
        if c['energy_db'] < fine['threshold_db']: c['reasons'].append('below_threshold')
        if c['dip_db'] < CONFIG['minimum_dip_db']: c['reasons'].append('insufficient_dip')
        c['reasons'].extend('structural_'+reason for reason in s['eligibility_reasons'])
    for i,s in enumerate(structures):
        s['left_boundary_s'] = a/rate if i==0 else limits[i-1]
        s['right_boundary_s'] = b/rate if i==len(structures)-1 else limits[i]
        members = [c for c in candidates if c['structure_id']==s['id']]
        eligible = [c for c in members if not c['reasons']]
        s['fine_ids'] = [c['id'] for c in members]
        s['representative_id'] = None
        s['multiple_fine_maxima'] = len(eligible)>1
        if not eligible:
            s['selection_reason'] = 'no_eligible_fine_maximum' if s['eligible'] else 'structure_ineligible'
            continue
        winner = min(eligible,key=lambda c:(-c['energy_db'],abs(c['time_s']-s['time_s']),c['time_s']))
        s['representative_id'] = winner['id']
        s['selection_reason'] = None
        winner['accepted'] = True
        for c in eligible:
            c['representative_id'] = winner['id']
            if c is not winner: c['reasons'].append('same_structure_secondary')
    kept = []
    for c in sorted((c for c in candidates if c['accepted']),key=lambda c:(-c['energy_db'],c['time_s'])):
        minimum = CONFIG['minimum_separation_ms']/1000
        conflict = next((k for k in kept
                         if abs(c['time_s']-k['time_s']) < minimum
                         and not math.isclose(abs(c['time_s']-k['time_s']), minimum,
                                              rel_tol=0, abs_tol=1e-12)),None)
        if conflict:
            c['accepted'] = False
            c['reasons'].append('minimum_separation')
            c['suppressed_by_id'] = conflict['id']
        else: kept.append(c)
    for c in candidates: c['reason'] = c['reasons'][0] if c['reasons'] else None
    valleys = []
    for left,right in zip(candidates,candidates[1:]):
        segment = [f for f in fine['frames'] if left['time_s'] <= f['time_s'] <= right['time_s']]
        if not segment: continue
        valley = min(segment,key=lambda f:f['energy_db'])
        valleys.append({'from_id':left['id'],'to_id':right['id'],'time_s':valley['time_s'], 'energy_db':valley['energy_db'], 'left_drop_db':left['energy_db']-valley['energy_db'], 'right_drop_db':right['energy_db']-valley['energy_db']})
    return {'frames':fine['frames'],'structural_frames':structural['frames'], 'threshold_db':fine['threshold_db'],'structural_threshold_db':structural['threshold_db'], 'structures':structures,'basin_limits_s':limits,'candidates':candidates,'valleys':valleys, 'events':[{'id':c['id'],'time_s':c['time_s'],'label':'unknown','restart':False} for c in candidates if c['accepted']], 'warnings':fine['warnings']}


def compare_wav(data, start=0.0, end=None):
    """Independent v1 and v2; no alteration of the existing API or review records."""
    v1 = ddk.analyze_ddk(data,start=start,end=end)
    samples,rate,_ = ddk.read_wav(data)
    a = math.ceil(start*rate)
    b = len(samples) if end is None else min(len(samples), math.ceil(end*rate))
    failure_message = None
    try:
        detection = detect(samples,rate,a,b)
        status = 'completed' if detection['events'] else 'empty'
        measures = ddk.calculate(detection['events'],None,(b-a)/rate)
    except DetectionError as exc:
        failure_message = str(exc)
        detection = None
        status = 'failed'
        measures = {'event_count':ddk.measure(reason='detector_failed'),'event_rate_per_s':ddk.measure(reason='detector_failed')}
    return {'v1':v1,'v2':{'version':CONFIG['version'],'status':status,'failure_reason':'detector_failed' if status=='failed' else None,'failure_message':failure_message,'time_definition':'selected_20ms_energy_maximum','detection':detection,'measures':measures,'human_speech_validation':'pending_6b','config_sha256':hashlib.sha256(CONFIG_BYTES).hexdigest(),'detector_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}}
