"""Independent mathematical oracles on declared synthetic trajectories."""
import numpy as np
from .bank import trajectory
from .engine import runs


def quantile(values,p):
    x=np.sort(np.asarray(values));n=len(x)
    if not n:return None
    if n==1:return float(x[0])
    r=n*p+.5;j=int(np.clip(np.floor(r),1,n-1));return float(x[j-1]+(r-j)*(x[j]-x[j-1]))


def percentile(x,p):return float(np.percentile(x,p)) if len(x) else None

def evaluate(case,record,summary):
    frames=record['frames'];t=np.array([f['time_relative_s'] for f in frames]);truth,voiced=trajectory(case,t)
    actual=np.array([f['f0_hz'] if f['defined'] else np.nan for f in frames]);defined=np.isfinite(actual);both=defined&voiced
    cents=1200*np.log2(actual[both]/truth[both]);error=np.abs(cents);ntruth=int(np.sum(voiced));W=3/record['profile']['floor_hz']
    # A priori guard around every known frequency/voicing discontinuity.
    core=voiced.copy();change=np.flatnonzero(np.r_[False,np.diff(voiced.astype(int))!=0])
    if case['family']=='step':change=np.r_[change,np.searchsorted(t,case['position']*case['duration'])]
    for i in change:
        if i<len(t):core &= np.abs(t-t[i])>W
    ce=1200*np.log2(actual[defined&core]/truth[defined&core])
    target10=quantile(truth[voiced],.1);target90=quantile(truth[voiced],.9)
    native=record['native'];q10=native['p10_hz'];q90=native['p90_hz']
    expectedrange=12*np.log2(target90/target10) if target10 is not None else None
    observedrange=12*np.log2(q90/q10) if q10 is not None and q90 is not None and q10>0 else None
    tv=t[voiced];st=12*np.log2(truth[voiced]);expected_slope=float(np.sum((tv-tv.mean())*(st-st.mean()))/np.sum((tv-tv.mean())**2)) if len(tv)>1 else None
    beta=summary['raw_ols_st_s']
    out=dict(f0_median_abs_cents=percentile(error,50),f0_p95_abs_cents=percentile(error,95),core_median_abs_cents=percentile(np.abs(ce),50),core_p95_abs_cents=percentile(np.abs(ce),95),
             voiced_reference_frames=ntruth,defined_on_voiced_frames=int(np.sum(both)),missed_voiced_frames=int(np.sum(voiced&~defined)),false_defined_frames=int(np.sum(~voiced&defined)),nonperiodic_reference_frames=int(np.sum(~voiced)),
             octave_error_frames=int(np.sum(np.abs(error-1200)<=100)),gross_error_frames=int(np.sum(error>600)),compared_frames=int(np.sum(both)),
             coverage_percent=summary['metrics']['coverage_percent']['value'],truth_coverage_percent=100*float(np.mean(voiced)) if len(t) else None,
             core_defined_percent=100*float(np.mean(defined[core])) if np.any(core) else None,
             p10_truth_hz=target10,p90_truth_hz=target90,p10_hz=q10,p90_hz=q90,
             p10_abs_error_hz=abs(q10-target10) if q10 is not None and target10 is not None else None,
             p90_abs_error_hz=abs(q90-target90) if q90 is not None and target90 is not None else None,
             robust_range_truth_st=expectedrange,robust_range_st=observedrange,robust_range_abs_error_st=abs(observedrange-expectedrange) if observedrange is not None and expectedrange is not None else None,
             slope_truth_st_s=expected_slope,slope_st_s=beta,slope_abs_error_st_s=abs(beta-expected_slope) if beta is not None and expected_slope is not None else None,
             range_published=summary['metrics']['robust_range_st']['value'] is not None,slope_published=summary['metrics']['slope_st_s']['value'] is not None,
             gap_mask_iou=float(np.sum(~voiced&~defined)/np.sum(~voiced|~defined)) if np.any(~voiced|~defined) else None,
             gap_count=len(summary['gaps']),truth_gap_count=int(np.sum(np.diff(np.r_[False,~voiced,False].astype(int))==1)))
    truth_frames=[dict(time_relative_s=float(ti),defined=bool(v)) for ti,v in zip(t,voiced)]
    references=runs(truth_frames,record['profile']['hop_s'],case['duration'])
    proposals=summary['gaps'];pairs=[]
    for ref in references:
        overlaps=[max(0,min(ref['end_s'],p['end_s'])-max(ref['start_s'],p['start_s'])) for p in proposals]
        if overlaps and max(overlaps)>0:
            idx=int(np.argmax(overlaps));p=proposals[idx]
            pairs.append((abs(p['start_s']-ref['start_s']),abs(p['end_s']-ref['end_s'])))
    out.update(gap_reference_count=len(references),gap_matched_count=len(pairs),
               gap_start_abs_error_s=percentile([p[0] for p in pairs],50),gap_end_abs_error_s=percentile([p[1] for p in pairs],50))
    for side,mask in [('initial',t<.1),('final',t>=case['duration']-.1)]:
        matched=mask&both;e=np.abs(1200*np.log2(actual[matched]/truth[matched]));v=mask&voiced
        out[f'{side}_edge_median_abs_cents']=percentile(e,50);out[f'{side}_edge_defined_percent']=100*float(np.mean(defined[v])) if np.any(v) else None
        out[f'{side}_edge_grid_support_percent']=100*int(np.sum(mask))*record['profile']['hop_s']/.1
        out[f'{side}_edge_defined_of_nominal_percent']=100*int(np.sum(mask&defined))*record['profile']['hop_s']/.1
    vi=np.flatnonzero(both)
    for side,idx in [('first_five',vi[:5]),('last_five',vi[-5:])]:
        out[f'{side}_median_abs_cents']=percentile(np.abs(1200*np.log2(actual[idx]/truth[idx])),50)
    return out
