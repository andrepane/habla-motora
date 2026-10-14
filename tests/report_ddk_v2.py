"""Frozen comparison; never tunes parameters against human counts."""
import argparse,json,math,io,wave,os
from concurrent.futures import ProcessPoolExecutor
from collections import deque
from pathlib import Path
from backend import ddk,ddk_v2
from tests.synthetic_ddk import signal

def evaluate(data,reference,tolerance=.02):
    samples,sr,_=ddk.read_wav(data)
    outputs={'v1':ddk.detect(samples,sr,0,len(samples)), 'v2':ddk_v2.detect(samples,sr,0,len(samples))}
    row={}
    for name,d in outputs.items():
        found=[e['time_s'] for e in d['events']]
        # Maximum-cardinality, minimum-total-error ordered matching (not greedy).
        n,m=len(reference),len(found)
        table={(0,0):(0,0,[])}
        for i in range(n+1):
            for j in range(m+1):
                options=[]
                if i: options.append(table[i-1,j])
                if j: options.append(table[i,j-1])
                if i and j and abs(reference[i-1]-found[j-1])<=tolerance:
                    k,e,p=table[i-1,j-1];options.append((k+1,e+abs(reference[i-1]-found[j-1]),p+[(i-1,j-1)]))
                if options:table[i,j]=min(options,key=lambda z:(-z[0],z[1]))
        matched,_,pairs=table[n,m]
        errors=[abs(reference[i]-found[j])*1000 for i,j in pairs]
        row[name]={'count':m,'matched':matched,'extra':m-matched,'missed':n-matched,'max_error_ms':max(errors) if errors else None,'times_s':found}
    return row,outputs

def custom(components,rate,bits,duration=1.5):
    values=[0.0]*round(duration*rate)
    for center,length,amp,freq in components:
        for i in range(max(0,round((center-length/2)*rate)),min(len(values),round((center+length/2)*rate))):
            t=i/rate-center
            values[i]+=amp*(.5+.5*math.cos(2*math.pi*t/length))**2*math.cos(2*math.pi*freq*t)
    scale=2**(bits-1);width=bits//8
    pcm=b''.join(max(-scale,min(scale-1,round(v*(scale-1)))).to_bytes(width,'little',signed=True) for v in values)
    out=io.BytesIO()
    with wave.open(out,'wb') as w:w.setnchannels(1);w.setsampwidth(width);w.setframerate(rate);w.writeframes(pcm)
    return out.getvalue()

def evaluate_summary(data,reference,tolerance):
    return evaluate(data,reference,tolerance)[0]


def run(human=None):
    rows=[]
    workers=int(os.environ.get('DDK_REPORT_WORKERS','1'))
    pool=ProcessPoolExecutor(max_workers=workers) if workers>1 else None
    pending=deque()
    completed=0
    def finish_one():
        nonlocal completed
        row,future=pending.popleft()
        row.update(future.result())
        completed+=1
        if completed%100==0:print('completed',completed,flush=True)
    def add(family,params,data,refs,tol=.02):
        row={'family':family,'parameters':params,'reference_s':refs}
        rows.append(row)
        if pool:
            pending.append((row,pool.submit(evaluate_summary,data,refs,tol)))
            if len(pending)>=workers*3:finish_one()
        else:row.update(evaluate_summary(data,refs,tol))
    for rhythm in [2,4,6,8,10,12]:
        for sr in [44100,48000]:
            for bits in [16,24,32]:
                centers=[.25+i/rhythm for i in range(int(3.5*rhythm))]
                data,_=signal(centers,rate=sr,bits=bits,amplitudes=(.1,.3,.6))
                add('clean',dict(rhythm=rhythm,rate=sr,bits=bits),data,centers,.01)
    baseline=[.25+i/6 for i in range(21)]
    cases=[('clean',{},baseline),('weak',{'amplitudes':(.00001,)},baseline),('transients',{'transients':True},baseline),('noise_0.003',{'noise':.003},baseline),('noise_0.03',{'noise':.03},baseline),('noise_0.15',{'noise':.15},baseline),('clipping',{'clip':True},baseline),('omission',{},baseline[:7]+baseline[8:]),('doublet',{},sorted(baseline+[baseline[4]+.055])),('pause_0.2',{},[t if i<10 else t+.2 for i,t in enumerate(baseline)]),('pause_0.5',{},[t if i<10 else t+.5 for i,t in enumerate(baseline)]),('pause_1',{},[t if i<10 else t+1 for i,t in enumerate(baseline)]),('silence',{},[]),('noise_only',{'noise':.03},[])]
    for name,kwargs,refs in cases:add('characterization',{'case':name},signal(refs,duration=5,**kwargs)[0],refs)
    for sr in [44100,48000]:
      for bits in [16,24,32]:
       for offset in [0,.0025]:
        for noise in [0,.03]:
         for gap in [.06,.08,.1]:
          for transient in [.002,.005,.01]:
           for length in [.02,.04,.08]:
            for db in [-12,-6,0,6]:
             t=.6+offset
             data=custom([(t-gap,transient,.3*10**(db/20),3000),(t,length,.3,240)],sr,bits)
             # Add deterministic existing noise through decoded PCM, requantized.
             if noise:
                import random
                values,_,_=ddk.read_wav(data);rng=random.Random(606);values=[v+noise*rng.gauss(0,1) for v in values]
                scale=2**(bits-1);width=bits//8;buf=io.BytesIO()
                with wave.open(buf,'wb') as w:w.setnchannels(1);w.setsampwidth(width);w.setframerate(sr);w.writeframes(b''.join(max(-scale,min(scale-1,round(v*(scale-1)))).to_bytes(width,'little',signed=True) for v in values))
                data=buf.getvalue()
             add('compound',dict(rate=sr,bits=bits,offset=offset,noise=noise,gap_ms=gap*1000,transient_ms=transient*1000,length_ms=length*1000,relative_db=db),data,[t])
         for gap in [.06,.08,.1]:
          t=.6+offset
          add('independent',dict(rate=sr,bits=bits,gap_ms=gap*1000,offset=offset),custom([(t-gap,.06,.3,240),(t,.06,.3,240)],sr,bits),[t-gap,t])
          add('internal_double',dict(rate=sr,bits=bits,gap_ms=gap*1000,offset=offset),custom([(t-gap,.16,.3,240),(t,.16,.3,240)],sr,bits),[t-gap,t])
          add('weak_strong',dict(rate=sr,bits=bits,gap_ms=gap*1000,offset=offset),custom([(t-gap,.06,.015,240),(t,.06,.3,240)],sr,bits),[t-gap,t])
         add('isolated_transient',dict(rate=sr,bits=bits,offset=offset),custom([(.6+offset,.005,.3,3000)],sr,bits),[.6+offset])
    while pending:finish_one()
    if pool:pool.shutdown()
    from tests.synthetic_ddk_v2 import basin_fragmentation_wav, BASIN_PARAMETERS
    result,outputs=evaluate(basin_fragmentation_wav(),[])
    rows.append({'family':'basin_fragmentation_wav','parameters':BASIN_PARAMETERS,'reference_s':None,'reference_count':1,**result})
    basin_audit={'v2':outputs['v2'],'alternative_times_s':[c['time_s'] for c in eligible_only_alternative(outputs['v2'])], 'note':'Selected topology fixture from seed-606 exploration, trial 6; not an unbiased performance corpus.'}
    # One generated emitter with two lobes: count reference is one,
    # but no unique temporal maximum is prescribed. Do not fabricate timing truth.
    for row in rows:
        if row['family'] in ('internal_double','basin_fragmentation_wav'):
            row['reference_s']=None
            row['reference_count']=1
            for name in ['v1','v2']:
                n=row[name]['count']
                row[name].update(matched=None,extra=max(0,n-1),missed=max(0,1-n),max_error_ms=None)
    # Controls are repeated inside the compound noise loop; retain unique conditions.
    unique={}
    for row in rows:
        key=(row['family'],json.dumps(row['parameters'],sort_keys=True))
        unique[key]=row
    rows=list(unique.values())
    result={'rows':rows,'human':None,'basin_fragmentation':basin_audit,'internal_double_note':'One composite generated emitter, two overlapping amplitude lobes; count-only reference, no unique timestamp truth.'}
    if human:
        data=Path(human).read_bytes();comparison,outputs=evaluate(data,[])
        result['human']={'comparison':comparison,'v2_audit':outputs['v2'],'known_syllables_exploratory':12,'note':'No event-level human timing reference; extra/missed fields not applicable.'}
        for v in comparison.values():v.pop('extra');v.pop('missed');v.pop('matched')
    return result

def eligible_only_alternative(detection):
    """OFFLINE association comparison, never a production mode or fallback."""
    structures=[s for s in detection['structures'] if s['eligible']]
    if not structures:return []
    limits=ddk_v2.basins(detection['structural_frames'],structures)
    buckets=[[] for s in structures]
    for c in detection['candidates']:
        if c['v1_scale_reason'] not in (None,'minimum_separation'):continue
        buckets[sum(c['time_s']>boundary for boundary in limits)].append(c)
    winners=[]
    for s,members in zip(structures,buckets):
        if members:winners.append(min(members,key=lambda c:(-c['energy_db'],abs(c['time_s']-s['time_s']),c['time_s'])))
    kept=[]
    for c in sorted(winners,key=lambda c:(-c['energy_db'],c['time_s'])):
        if all(abs(c['time_s']-k['time_s'])>=.05 or math.isclose(abs(c['time_s']-k['time_s']),.05,rel_tol=0,abs_tol=1e-12) for k in kept):kept.append(c)
    return sorted(kept,key=lambda c:c['time_s'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--human');p.add_argument('--out',required=True);args=p.parse_args()
    result=run(args.human);Path(args.out).write_text(json.dumps(result,indent=2))
    for family in sorted({r['family'] for r in result['rows']}):
        rr=[r for r in result['rows'] if r['family']==family]
        print(family,len(rr),{v:{'count':sum(r[v]['count'] for r in rr),'extra':sum(r[v]['extra'] for r in rr),'missed':sum(r[v]['missed'] for r in rr),'max_error_ms':max((r[v]['max_error_ms'] for r in rr if r[v]['max_error_ms'] is not None),default=None)} for v in ['v1','v2']},flush=True)
    if result['human']:print('human',result['human']['comparison'],flush=True)
