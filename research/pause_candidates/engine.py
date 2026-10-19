"""Deterministic offline candidate proposals, never manual pause classifications."""
import hashlib
import io
import json
import platform
import wave
from pathlib import Path
import numpy as np
from backend.phrase import read_wav, canonical, digest, ROOT


def config(variant):
    if variant not in ('energy', 'multifeature'):
        raise ValueError('Unknown experimental variant')
    raw=(ROOT/f'configs/pause_detector_{variant}_v1.json').read_bytes()
    return json.loads(raw),digest(raw)


def decode(data):
    meta=read_wav(data)
    with wave.open(io.BytesIO(data),'rb') as w: raw=w.readframes(w.getnframes())
    bits=meta['pcm_bits']
    if bits==24:
        b=np.frombuffer(raw,dtype=np.uint8).reshape(-1,3).astype(np.int32)
        x=b[:,0]+(b[:,1]<<8)+(b[:,2]<<16);x=np.where(x>=2**23,x-2**24,x)
    else:x=np.frombuffer(raw,dtype='<i2' if bits==16 else '<i4')
    return x.astype(np.float64)/2**(bits-1),meta


def identity(data,meta,selection,context_id):
    if not isinstance(selection,dict) or set(selection)!={'start_sample','end_sample_exclusive','confirmed'} or selection['confirmed'] is not True:
        raise ValueError('A confirmed 7A selection is required')
    a,b=selection['start_sample'],selection['end_sample_exclusive']
    if type(a) is not int or type(b) is not int or not 0<=a<b<=meta['sample_count']:
        raise ValueError('Invalid integer sample selection')
    if not isinstance(context_id,str) or not context_id:
        raise ValueError('Source context identity is required')
    return dict(file_sha256=digest(data),sample_rate_hz=meta['sample_rate_hz'],selection=selection,source_context_id=context_id)


def runs(mask,centers,a,b,rate,minimum):
    # Time cells at midpoints, not entire overlapping analysis windows. Never bridge gaps.
    edges=np.r_[a, (centers[:-1]+centers[1:]+1)//2,b]
    changes=np.diff(np.r_[False,mask,False].astype(np.int8))
    result=[]
    for i,j in zip(np.flatnonzero(changes==1),np.flatnonzero(changes==-1)):
        p,q=int(edges[i]),int(edges[j])
        if (q-p)*1000>=minimum*rate: result.append((p,q,int(i),int(j)))
    return result


def feature_frames(x,rate,a,b,c,multifeature):
    # Absolute centers calculated separately: no accumulation of rounded hops at 44.1 kHz.
    centers=a+np.rint(np.arange(int(np.ceil((b-a)*1000/(rate*c['hop_ms']))))*rate*c['hop_ms']/1000).astype(np.int64)
    centers=centers[centers<b]
    n=round(rate*c['window_ms']/1000)
    offsets=np.arange(n)-n//2
    idx=centers[:,None]+offsets
    valid=(idx>=0)&(idx<len(x))
    frames=x[np.clip(idx,0,len(x)-1)]
    # No zero padding: replicated samples only in storage; edge features excluded via valid flag.
    full=valid.all(axis=1)
    frames=frames-frames.mean(axis=1,keepdims=True)
    rms=np.sqrt(np.mean(frames**2,axis=1))
    level=20*np.log10(np.maximum(rms,c['epsilon']))
    features=dict(center_sample=centers,level_dbfs=level,window_complete=full)
    if not multifeature:return features
    nfft=1<<(n-1).bit_length()
    power=np.abs(np.fft.rfft(frames*np.hanning(n),n=nfft,axis=1))**2
    freq=np.fft.rfftfreq(nfft,1/rate);mask=(freq>=c['band_hz'][0])&(freq<=c['band_hz'][1])
    power=power[:,mask];total=power.sum(axis=1);good=total>c['epsilon']**2
    normalized=power/np.maximum(total[:,None],c['epsilon']**2)
    flat=np.exp(np.log(normalized+c['epsilon']).mean(axis=1))/(normalized+c['epsilon']).mean(axis=1)
    flux=np.r_[np.nan,.5*np.abs(np.diff(normalized,axis=0)).sum(axis=1)]
    flat[~good]=np.nan;flux[~good]=np.nan
    pn=round(rate*c['periodicity_window_ms']/1000)
    pi=centers[:,None]+np.arange(pn)-pn//2
    pfull=((pi>=0)&(pi<len(x))).all(axis=1)
    pf=x[np.clip(pi,0,len(x)-1)];pf-=pf.mean(axis=1,keepdims=True)
    fftn=1<<(2*pn-1).bit_length()
    corr=np.fft.irfft(np.abs(np.fft.rfft(pf,n=fftn,axis=1))**2,n=fftn,axis=1)
    lo=int(np.ceil(rate/c['periodicity_ceiling_hz']));hi=int(np.floor(rate/c['periodicity_floor_hz']))
    lags=np.arange(lo,hi+1)
    prefix=np.c_[np.zeros(len(pf)),np.cumsum(pf**2,axis=1)]
    denom=np.sqrt(prefix[:,pn-lags]*(prefix[:,pn,None]-prefix[:,lags]))
    p=np.max(np.divide(corr[:,lags],denom,out=np.zeros_like(denom),where=denom>c['epsilon']**2),axis=1)
    p=np.clip(p,0,1);p[(prefix[:,-1]<=c['epsilon']**2)|~pfull]=np.nan
    features.update(periodicity=p,flatness=flat,spectral_flux=flux,periodicity_window_complete=pfull)
    bf=freq[mask]
    for k,(low,high) in enumerate(c['bands_hz']):
        features[f'band_{k}_fraction']=normalized[:,(bf>=low)&(bf<high)].sum(axis=1)
    return features


def finite(v):
    return float(v) if np.isfinite(v) else None


def detect(data,selection,source_context_id,variant='energy',include_frames=True):
    c,ch=config(variant);x,meta=decode(data);source=identity(data,meta,selection,source_context_id)
    a,b=selection['start_sample'],selection['end_sample_exclusive'];rate=meta['sample_rate_hz']
    run_id=digest(canonical(dict(source=source,config_sha256=ch,engine_sha256=digest(Path(__file__).read_bytes()),numpy_version=np.__version__,python_version=platform.python_version())))
    base=dict(schema_version='pause_candidates_output_v1',detector_version=c['detector_version'],configuration=c,
              config_sha256=ch,engine_sha256=digest(Path(__file__).read_bytes()),run_id=run_id,source=source,
              runtime={'numpy':np.__version__,'python':platform.python_version()},warnings=['EXPERIMENTAL_NOT_MANUAL_PAUSES'],
              candidate_decisions=[],manual_annotations=[],candidate_manual_links=[],manual_final_result=None)
    if b-a<round(.08*rate) or not np.any(x[a:b]-np.mean(x[a:b])):
        return {**base,'status':'not_evaluable','reason':'insufficient_acoustic_variation','automatic_candidates':None,'frame_trace':None}
    f=feature_frames(x,rate,a,b,c,variant=='multifeature')
    level=f['level_dbfs'];p20,p90=np.percentile(level[f['window_complete']], [20,90],method='linear') if np.any(f['window_complete']) else (np.nan,np.nan)
    A=((level<=p90-c['energy_primary_drop_db'])|((level<=p20+c['energy_lower_margin_db'])&(level<=p90-c['energy_secondary_drop_db'])))&f['window_complete']
    masks={'A':A}
    if variant=='multifeature':
        masks['B']=(f['periodicity']<c['periodicity_max'])&(f['flatness']>c['flatness_min'])&(f['spectral_flux']<=c['flux_max'])&f['window_complete']
    proposals={}
    for path,mask in masks.items():
        for p,q,i,j in runs(mask,f['center_sample'],a,b,rate,c['minimum_candidate_ms']):
            key=(p,q)
            if key not in proposals:proposals[key]=dict(start_sample=p,end_sample_exclusive=q,frame_start=i,frame_end_exclusive=j,proposal_reasons=[])
            proposals[key]['proposal_reasons'].append('A_energy_depression' if path=='A' else 'B_aperiodic_spectral_stability')
    candidates=[]
    for k,((p,q),v) in enumerate(sorted(proposals.items()),1):
        i,j=v['frame_start'],v['frame_end_exclusive'];warn=[]
        if p-a<=round(c['context_ms']*rate/1000) or b-q<=round(c['context_ms']*rate/1000):warn.append('selection_edge')
        if p90-p20<12:warn.append('low_acoustic_contrast')
        summaries={}
        for key,arr in f.items():
            if key.endswith('complete') or key=='center_sample':continue
            values=arr[i:j];valid=values[np.isfinite(values)]
            summaries[key]={'median':finite(np.median(valid)) if len(valid) else None,'min':finite(np.min(valid)) if len(valid) else None,'max':finite(np.max(valid)) if len(valid) else None}
        if 'periodicity' in f and summaries['periodicity']['max'] is not None and summaries['periodicity']['max']>=.6:warn.append('periodic_low_level_region')
        slope=float(np.polyfit((f['center_sample'][i:j]-p)/rate,level[i:j],1)[0]) if j-i>1 else 0
        if slope<-12:warn.append('intensity_fade')
        if 'B_aperiodic_spectral_stability' in v['proposal_reasons']:warn.append('aperiodic_energy_present_not_breath_classification')
        if np.any(np.abs(x[p:q])>=1-1/2**(meta['pcm_bits']-1)):warn.append('clipping_present')
        context_n=round(c['context_ms']*rate/1000)
        context_evidence={}
        for name,left,right in [('before',max(0,p-context_n),p),('after',q,min(len(x),q+context_n))]:
            samples=x[left:right]
            context_evidence[name]={'start_sample':left,'end_sample_exclusive':right,'level_dbfs':float(20*np.log10(max(float(np.sqrt(np.mean((samples-samples.mean())**2))),c['epsilon']))) if len(samples) else None}
        candidates.append({**v,'candidate_id':f'{run_id[:16]}-c{k:04d}','duration_samples':q-p,'duration_s':(q-p)/rate,
            'status':'unreviewed','features':summaries,'technical_evidence':{'p20_dbfs':float(p20),'p90_dbfs':float(p90),'intensity_slope_db_s':slope,'context':context_evidence},
            'warnings':warn,'detector_version':c['detector_version'],'config_sha256':ch,'overlap_group_id':None})
    group=0;end=-1
    for cand in candidates:
        if cand['start_sample']>=end:group+=1
        cand['overlap_group_id']=f'g{group}';end=max(end,cand['end_sample_exclusive'])
    trace=[{key:(bool(arr[k]) if key.endswith('complete') else int(arr[k]) if key=='center_sample' else finite(arr[k])) for key,arr in f.items()} for k in range(len(level))]
    return {**base,'status':'completed','reason':None,'automatic_candidates':candidates,
            'frame_trace_sha256':digest(canonical(trace)),'frame_trace':trace if include_frames else None,
            'selection_statistics':{'p20_dbfs':float(p20),'p90_dbfs':float(p90)},'frame_count':len(level)}
