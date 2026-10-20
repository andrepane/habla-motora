"""Auditable Praat extraction; selected-only native statistics, never a clinical decision."""
import csv
import io
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
import tempfile
import numpy as np
from backend.phrase import ROOT, analyze_phrase, canonical, digest, read_wav

HERE=Path(__file__).parent
NATIVE_NAMES=['f0_mean_hz','f0_median_hz','f0_sd_hz','f0_sd_st','p10_hz','p90_hz','f0_min_hz','f0_max_hz']


def executable_identity(executable):
    path=shutil.which(executable) or executable
    version=subprocess.run([path,'--version'],check=True,capture_output=True,text=True,timeout=15).stdout.strip()
    if version.split()[1]!='6.4.27':raise ValueError('Praat 6.4.27 required')
    return dict(praat_version=version,binary_sha256=digest(Path(path).read_bytes()),python=platform.python_version(),numpy=np.__version__)


def parse_pitch(raw,a,b,rate):
    lines=raw.splitlines();values=lines[3:]
    xmin,xmax,n,dx,x1,ceiling,maxc=map(float,values[:7]);n=int(n)
    selected=[];blocks=[];pos=7
    for i in range(n):
        begin=pos;intensity=float(values[pos]);nc=int(values[pos+1]);pos+=2
        frequency=float(values[pos]);strength=float(values[pos+1]);pos+=2*nc
        t=x1+i*dx
        if a/rate<=t<b/rate:
            f=frequency if 0<frequency<ceiling else None
            selected.append(dict(frame_index=i+1,time_absolute_s=t,time_relative_s=t-a/rate,
                                 sample_position_float=t*rate,f0_hz=f,defined=f is not None,
                                 undefined_reason=None if f is not None else 'praat_unvoiced_or_unresolved',
                                 intensity=intensity,candidate_strength=strength))
            blocks.extend(values[begin:pos])
    if pos!=len(values):raise ValueError('Unexpected Pitch serialization')
    header=[a/rate,b/rate,len(selected),dx,selected[0]['time_absolute_s'] if selected else 0,ceiling,int(maxc)]
    restricted='\n'.join(lines[:3]+[str(v) for v in header]+blocks)+'\n'
    return selected,restricted,dict(x1_s=x1,dx_s=dx,nx=n,domain_start_s=xmin,domain_end_s=xmax)


def extract_many(data,selection,profiles,contexts=(0.,),executable=None):
    meta=read_wav(data);rate=meta['sample_rate_hz'];a,b=selection['start_sample'],selection['end_sample_exclusive']
    if type(a) is not int or type(b) is not int or not 0<=a<b<=meta['sample_count']:raise ValueError('Invalid sample selection')
    executable=executable or os.environ.get('PRAAT_EXECUTABLE','praat')
    records={}
    with tempfile.TemporaryDirectory(prefix='prosody-') as tmp:
        path=Path(tmp);(path/'input.wav').write_bytes(data)
        jobs=[]
        for p in profiles:
            if p['hop_s']!=.005 or p['candidates']!=15 or p['very_accurate'] or p['attenuation']!=.03 or p['jump_cost']!=.35 or p['vu_cost']!=.14:
                raise ValueError('Unsupported batch parameters; must match explicit Praat script')
            for context in contexts:
                ident=f"{p['id']}__{int(context*1000)}"
                left=max(0,a-round(context*rate))/rate;right=min(meta['sample_count'],b+round(context*rate))/rate
                jobs.append(dict(id=ident,method=p['method'],floor=p['floor_hz'],top=p['top_hz'],silence=p['silence'],voicing=p['voicing'],cost=p['octave_cost'],left=left,right=right))
                records[ident]=dict(profile=p,context_s=context,acoustic_interval={'start_sample':round(left*rate),'end_sample_exclusive':round(right*rate)})
        with (path/'jobs.tsv').open('w') as f:
            writer=csv.DictWriter(f,fieldnames=jobs[0].keys(),delimiter='\t');writer.writeheader();writer.writerows(jobs)
        subprocess.run([executable,'--run',str(HERE/'extract.praat'),str(path/'input.wav'),str(path/'jobs.tsv'),str(path)],check=True,capture_output=True,text=True,timeout=180)
        available=[]
        for ident,r in records.items():
            raw=(path/f'{ident}.Pitch').read_text();frames,restricted,grid=parse_pitch(raw,a,b,rate)
            r.update(frames=frames,grid=grid,original_pitch_sha256=digest(raw.encode()),restricted_pitch_sha256=digest(restricted.encode()),native={k:None for k in NATIVE_NAMES})
            if frames:
                (path/f'{ident}.selected.Pitch').write_text(restricted);available.append(ident)
        (path/'native-jobs.txt').write_text('\n'.join(available)+'\n')
        if available:
            subprocess.run([executable,'--run',str(HERE/'statistics.praat'),str(path/'native-jobs.txt'),str(path)],check=True,capture_output=True,text=True,timeout=90)
        for ident in available:
            tokens=(path/f'{ident}.stats').read_text().strip().split('\t')
            native={k:(None if '--undefined--' in v else float(v)) for k,v in zip(NATIVE_NAMES,tokens,strict=True)}
            if any(v is not None and not np.isfinite(v) for v in native.values()):raise ValueError('Nonfinite native result')
            records[ident]['native']=native
    return records


def runs(frames,hop,duration=None):
    result=[];start=None
    for i,f in enumerate(frames+[{'defined':True}]):
        if not f['defined'] and start is None:start=i
        if f['defined'] and start is not None:
            left=frames[start]['time_relative_s']-hop/2;right=frames[i-1]['time_relative_s']+hop/2
            if duration is not None:right=min(duration,right)
            result.append(dict(first_frame=start,last_frame=i-1,start_s=max(0,left),end_s=right,duration_s=right-max(0,left),internal=start>0 and i<len(frames)))
            start=None
    return result


def support(frames,duration,rule):
    valid=[f for f in frames if f['defined']];n=len(valid)
    span=valid[-1]['time_relative_s']-valid[0]['time_relative_s'] if n else 0
    occupied=sorted({min(4,int(f['time_relative_s']/duration*5)) for f in valid})
    coverage=n/len(frames) if frames else None
    eligible=(n>=rule['minimum_n'] and span>=rule['minimum_span_s'] and span>=rule['minimum_span_fraction']*duration and coverage is not None and coverage>=rule['minimum_coverage'] and len(occupied)>=rule['minimum_bins'])
    return dict(eligible=eligible,defined_frames=n,span_s=span,span_fraction=span/duration,coverage=coverage,occupied_quintiles=occupied,rule=rule)


def summarize(record,selection,rate,range_rule,jump_limit_s):
    frames=record['frames'];native=record['native'];duration=(selection['end_sample_exclusive']-selection['start_sample'])/rate
    valid=[f for f in frames if f['defined']];n=len(frames);nv=len(valid);median=native['f0_median_hz']
    for f in frames:f['f0_st']=12*np.log2(f['f0_hz']/median) if f['defined'] and median is not None and median>0 else None
    gaps=runs(frames,record['profile']['hop_s'],duration);rangesupport=support(frames,duration,range_rule)
    warnings=[];transitions=[]
    for p,q in zip(valid,valid[1:]):
        delta=12*np.log2(q['f0_hz']/p['f0_hz']);dt=q['time_absolute_s']-p['time_absolute_s'];missing=q['frame_index']-p['frame_index']-1
        gap=missing*record['profile']['hop_s']
        if abs(delta)>6:
            evidence=dict(from_frame=p['frame_index'],to_frame=q['frame_index'],delta_st=float(delta),direction='up' if delta>0 else 'down',delta_t_s=dt,intermediate_gap=missing>0,gap_duration_s=gap)
            transitions.append(evidence)
            if dt<=jump_limit_s+1e-12:
                warnings.append(dict(code='POSSIBLE_OCTAVE_JUMP' if 11<=abs(delta)<=13 else 'EXTREME_DISCONTINUITY',**evidence))
    def metric(value,method,reason=None):return dict(value=None if value is None else float(value),reason=reason if value is None else None,method=method)
    reason='no_analysis_frames' if not n else 'no_defined_f0' if not nv else 'praat_undefined'
    metrics={k:metric(v,'praat_native',reason) for k,v in native.items()}
    if nv<2:
        for k in ['f0_sd_hz','f0_sd_st']:metrics[k]=metric(None,'praat_native','insufficient_defined_frames')
    raw=native['f0_max_hz']-native['f0_min_hz'] if nv>=2 and native['f0_max_hz'] is not None and native['f0_min_hz'] is not None else None
    metrics['raw_range_hz']=metric(raw,'native_extrema_difference','insufficient_defined_frames')
    q10,q90=native['p10_hz'],native['p90_hz'];ok=rangesupport['eligible'] and q10 is not None and q90 is not None and q10>0
    metrics['robust_range_hz']=metric(q90-q10 if ok else None,'native_hz_quantiles_difference','insufficient_distributional_support')
    metrics['robust_range_st']=metric(12*np.log2(q90/q10) if ok else None,'native_hz_quantiles_log_ratio','insufficient_distributional_support')
    # Quantiles remain raw native evidence; eligibility controls publication as a robust summary.
    for key in ['p10_hz','p90_hz']:
        if not ok:metrics[key]=metric(None,'praat_native','insufficient_distributional_support')
    coverage=nv/n if n else None;times=np.array([f['time_relative_s'] for f in valid]);st=np.array([f['f0_st'] for f in valid],dtype=float)
    internal_max=max([g['duration_s'] for g in gaps if g['internal']],default=0)
    slope_ok=nv>=30 and duration>=1 and coverage>=.5 and times[-1]-times[0]>=.6*duration and sum(times<=.2*duration)>=5 and sum(times>=.8*duration)>=5 and internal_max<=max(.5,.25*duration) and median is not None
    beta=float(np.sum((times-times.mean())*(st-st.mean()))/np.sum((times-times.mean())**2)) if nv>=2 and np.ptp(times)>0 and median is not None else None
    metrics['slope_st_s']=metric(beta if slope_ok else None,'ols_defined_frames_real_time','insufficient_temporal_support')
    metrics['coverage_percent']=metric(100*coverage if coverage is not None else None,'defined_frame_ratio','no_analysis_frames')
    metrics['selection_duration_s']=metric(duration,'sample_indices')
    if coverage is not None and coverage<.5:warnings.append({'code':'LOW_F0_COVERAGE'})
    if gaps:warnings.append({'code':'UNDEFINED_F0_REGIONS','count':len(gaps),'max_internal_s':internal_max})
    if duration<1:warnings.append({'code':'SHORT_SELECTION'})
    if valid:
        if record['profile']['method']=='filtered autocorrelation' and max(f['f0_hz'] for f in valid)>=record['profile']['top_hz']/2:warnings.append({'code':'UPPER_FILTERED_BAND'})
        floor=record['profile']['floor_hz'];top=record['profile']['top_hz']
        if min(f['f0_hz'] for f in valid)<=floor*2**(1/12) or max(f['f0_hz'] for f in valid)>=top/2**(1/12):warnings.append({'code':'F0_NEAR_SEARCH_LIMIT'})
    return dict(reason='no_analysis_frames' if not n else 'no_defined_f0' if not nv else None,status='not_evaluable' if not nv else 'partial' if any(m['value'] is None for m in metrics.values()) else 'completed',metrics=metrics,reference_st={'type':'selection_native_median_hz','value_hz':median},range_support=rangesupport,counts={'total':n,'defined':nv,'undefined':n-nv},gaps=gaps,transitions=transitions,warnings=warnings,
                raw_ols_st_s=beta,frames_sha256=digest(canonical(frames)))


def independent_concordance(record,selection,rate,executable):
    """Reconstruct the chosen-only Pitch grid, preserving undefined cells; no interpolation."""
    frames=record['frames']
    if not frames:return None
    head=[selection['start_sample']/rate,selection['end_sample_exclusive']/rate,len(frames),record['profile']['hop_s'],frames[0]['time_absolute_s'],record['profile']['top_hz'],2]
    lines=['File type = "ooTextFile"','Object class = "Pitch 1"','']+[str(v) for v in head]
    for f in frames:lines.extend(['1','2',str(f['f0_hz'] or 0),'1','0','0'])
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/'oracle.Pitch';p.write_text('\n'.join(lines)+'\n')
        raw=subprocess.run([executable,'--run',str(HERE/'verify.praat'),str(p)],check=True,capture_output=True,text=True,timeout=30).stdout.strip().split('\t')
    values={k:(None if '--undefined--' in v else float(v)) for k,v in zip(NATIVE_NAMES,raw[:8],strict=True)}
    values['total_frames']=int(raw[8]);values['defined_frames']=int(raw[9]);return values
