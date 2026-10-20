"""Deterministic acoustic controls, not speech. Split recipes exist before any held-out run."""
import io
import wave
import numpy as np
from backend.phrase import canonical,digest


def recipes():
    rows=[]
    def add(family,**kw):rows.append(dict(family=family,frequency=200.,duration=4.,**kw))
    # Explicit updates avoid hidden tuning of any human sample.
    for f in [45,55,75,100,150,200,300,450,600,750,950]:rows.append(dict(family='constant',frequency=float(f),duration=4.))
    for s in [-2,-1,.5,2]:add('linear_st',slope=s)
    for s in [-20,20]:add('linear_hz',slope=s)
    for at in [.2,.5,.8]:
        for jump in [6.,12.]:add('step',position=at,jump=jump)
    for depth in [2.,6.]:
        for cycles in [1.,3.]:add('sinusoidal',depth=depth,cycles=cycles)
    for gap in [.020,.050,.100,.250,.500,1.]:
        for at in [.2,.5,.8]:add('gap',gap=gap,position=at)
    add('alternating');add('aperiodic_gaps');add('single_island');add('middle_only');add('split_ends')
    for snr in [30.,20.,10.,0.]:
        for f in [100.,450.]:rows.append(dict(family='noise',frequency=f,duration=4.,snr_db=snr))
    for family in ['weak','fade','exterior_loud','exterior_different','edge_rise','edge_fall','missing_fundamental','dominant_second','dominant_third','clipping','severe_clipping','silence','aperiodic']:add(family)
    for d in [2.,8.,12.,20.]:rows.append(dict(family='duration',frequency=200.,duration=d))
    return rows


def manifest(split):
    if split not in ['development','blocked']:raise ValueError('Unknown split')
    for i,recipe in enumerate(recipes()):
        for rate in [44100,48000]:
            for bits in [16,24,32]:
                # Held-out phases/seeds/base-pitch/slope perturbations, same declared families.
                yield dict(recipe,split=split,rate=rate,bits=bits,recipe_index=i,
                           case_id=f'{split}-{i:03d}-{rate}-{bits}',seed=(8100 if split=='development' else 1000000)+i*100+rate+bits,
                           phase=.37 if split=='development' else 1.13)


def trajectory(case,t):
    d=case['duration'];family=case['family'];f=case['frequency']*(1 if case['split']=='development' else 1.037)
    pitch=np.full(np.shape(t),f,dtype=float);voiced=np.ones(np.shape(t),dtype=bool)
    if family=='linear_st':pitch=f*2**(case['slope']*(1 if case['split']=='development' else .93)*(t-d/2)/12)
    if family=='linear_hz':pitch=f+case['slope']*(t-d/2)
    if family=='step':pitch=f*2**(case['jump']*(t>=case['position']*d)/12)
    if family=='sinusoidal':pitch=f*2**(case['depth']*np.sin(2*np.pi*case['cycles']*t/d+case['phase'])/12)
    if family in ['gap','aperiodic_gaps']:
        center=case.get('position',.5)*d;width=case.get('gap',.5);voiced &= np.abs(t-center)>=width/2
    if family=='alternating':voiced &= np.mod(t,.5)<.25
    if family=='single_island':voiced &= (t>=.45*d)&(t<.55*d)
    if family=='middle_only':voiced &= (t>=.3*d)&(t<.7*d)
    if family=='split_ends':voiced &= (t<.1*d)|(t>=.9*d)
    if family=='edge_rise':pitch=f*2**(6*np.clip(t/.12,0,1)/12)
    if family=='edge_fall':pitch=f*2**(-6*np.clip((t-(d-.12))/.12,0,1)/12)
    if family in ['silence','aperiodic']:voiced[:]=False
    return pitch,voiced


def encode(x,rate,bits):
    scale=2**(bits-1);v=np.rint(np.clip(x,-1,1-1/scale)*scale).astype(np.int64)
    if bits==24:raw=np.stack([v&255,(v>>8)&255,(v>>16)&255],axis=1).astype(np.uint8).tobytes()
    else:raw=v.astype('<i2' if bits==16 else '<i4').tobytes()
    b=io.BytesIO()
    with wave.open(b,'wb') as w:w.setparams((1,bits//8,rate,0,'NONE','not compressed'));w.writeframes(raw)
    return b.getvalue()


def generate(case):
    rate=case['rate'];d=case['duration'];pad=round(min(.4,(20-d)/2)*rate);count=round(d*rate)
    t=(np.arange(count)+.5)/rate;f,voiced=trajectory(case,t);phase=case['phase']+2*np.pi*np.cumsum(f)/rate
    family=case['family'];rng=np.random.default_rng(case['seed'])
    x=.2*np.sin(phase)
    if family=='missing_fundamental':x=.002*np.sin(phase)+.1*np.sin(2*phase)+.1*np.sin(3*phase)
    if family=='dominant_second':x=.02*np.sin(phase)+.2*np.sin(2*phase)+.005*np.sin(3*phase)
    if family=='dominant_third':x=.02*np.sin(phase)+.2*np.sin(3*phase)
    if family=='weak':x*=.015
    if family=='fade':x*=np.linspace(1,.001,count)
    if family in ['clipping','severe_clipping']:x*=8 if family=='clipping' else 40
    x[~voiced]=0
    if family in ['aperiodic','aperiodic_gaps']:x[~voiced]=rng.normal(0,.08,np.sum(~voiced))
    if family=='noise':x+=rng.normal(0,.2/np.sqrt(2)*10**(-case['snr_db']/20),count)
    before_f=f[0] if family!='exterior_different' else 400.
    after_f=f[-1] if family!='exterior_different' else 400.
    before=.2*np.sin(phase[0]-2*np.pi*before_f*np.arange(pad,0,-1)/rate)
    after=.2*np.sin(phase[-1]+2*np.pi*after_f*np.arange(1,pad+1)/rate)
    if family in ['exterior_loud','weak']:before*=4;after*=4
    if family=='exterior_loud':x*=.05
    data=encode(np.r_[before,x,after],rate,case['bits'])
    truth=dict(known_nonperiodic=family in ['silence','aperiodic'],global_support_expected=family not in ['single_island','middle_only','split_ends','silence','aperiodic'],
               clipping_samples=int(np.sum(np.abs(x)>=1)),selection_sha256=digest(canonical({'a':pad,'b':pad+count,'rate':rate})))
    return data,dict(start_sample=pad,end_sample_exclusive=pad+count),truth
