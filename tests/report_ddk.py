"""Reproducible characterization, no claim of speech validation."""
import json
from backend.ddk import analyze_ddk
from tests.synthetic_ddk import signal


def report():
    baseline=[.25+i/6 for i in range(21)]
    cases=[('clean',{},baseline),('weak',{'amplitudes':(.00001,)},baseline),
           ('transients',{'transients':True},baseline),('noise_sigma_0.003',{'noise':.003},baseline),
           ('noise_sigma_0.03',{'noise':.03},baseline),('noise_sigma_0.15',{'noise':.15},baseline),
           ('clipping',{'clip':True},baseline),('omission',{},baseline[:7]+baseline[8:]),
           ('doublet',{},sorted(baseline+[baseline[4]+.055])),
           ('pause_0.2',{},[t if i<10 else t+.2 for i,t in enumerate(baseline)]),
           ('pause_0.5',{},[t if i<10 else t+.5 for i,t in enumerate(baseline)]),
           ('pause_1',{},[t if i<10 else t+1 for i,t in enumerate(baseline)]),
           ('silence',{},[]),('noise_only',{'noise':.03},[])]
    rows=[]
    for name,kwargs,centers in cases:
        data,_=signal(centers,duration=5,**kwargs)
        r=analyze_ddk(data); detection=r['automatic_original']['detection']; found=detection['events']
        available=set(range(len(found))); errors=[]
        for truth in centers:
            best=min(available,key=lambda j:abs(found[j]['time_s']-truth),default=None)
            if best is not None and abs(found[best]['time_s']-truth)<=.02:
                errors.append(abs(found[best]['time_s']-truth));available.remove(best)
        rows.append({'case':name,'truth_event_count':len(centers),'candidate_count':len(found),
          'matched_20ms':len(errors),'false_positive':len(available),'missed':len(centers)-len(errors),
          'max_matched_error_ms':max(errors)*1000 if errors else None,
          'status':r['status'],'rate':r['automatic_original']['metrics']['event_rate_per_s'],
          'rejections':{reason:sum(c['reason']==reason for c in detection['candidates']) for reason in sorted({c['reason'] for c in detection['candidates'] if c['reason']})},
          'warnings':detection['warnings']})
    return {'schema_version':'ddk_synthetic_report_v1','seed':606,'note':'Noise levels are generator amplitudes, NOT measured or calibrated SNR. Synthetic bursts are NOT speech.', 'cases':rows}

if __name__=='__main__': print(json.dumps(report(),indent=2))
