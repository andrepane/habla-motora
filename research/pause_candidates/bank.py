"""Deterministic constructed signals: no participants and no phonetic truth."""
import io
import json
from pathlib import Path
import wave
import numpy as np
from backend.phrase import canonical, digest

DURATIONS=(100,200,249,250,251,300,500,1000)
FREQUENCIES=(60,100,200,350,500,600,700,800)
FAMILIES=('clean','noise_30','noise_20','noise_10','noise_0','breath','low_amplitude','fade','closure','weak_voice','two_close','brief_event','aperiodic','low_energy_present','no_pause','all_silence','background_only','clipped','stationary_broadband','colored_30','colored_20','colored_10','colored_0','variable_30','variable_20','variable_10','variable_0')
SPLITS={'development':{'seeds':[104729,130363],'phase_s':[0,.0025]},'blocked':{'seeds':[169087,200003],'phase_s':[.00125,.00375]}}


def manifest(split):
    if split not in SPLITS:raise ValueError('Unknown split')
    config=SPLITS[split]
    for family in FAMILIES:
        for di,d in enumerate(DURATIONS):
            frequencies=FREQUENCIES if family=='clean' else (FREQUENCIES[di],)
            for frequency in frequencies:
                for rate in (44100,48000):
                    for bits in (16,24,32):
                        for si,seed in enumerate(config['seeds']):
                            case=dict(split=split,family=family,duration_ms=d,frequency_hz=frequency,rate=rate,bits=bits,seed=seed,phase_s=config['phase_s'][si],length_s=4,
                                      gap_between_s=(.02,.05,.1,.2)[di%4],fade_ms=(50,100,250,500)[di%4],brief_event_ms=(5,10,20,40)[di%4],breath_amplitude=(.02,.06,.12,.2)[di%4],signal_version='constructed_pause_bank_v1')
                            case['case_id']=digest(canonical(case))[:24]
                            yield case


def encode(x,rate,bits):
    maximum=2**(bits-1)-1;values=np.rint(np.clip(x,-1,1)*maximum).astype(np.int64)
    if bits==24:
        unsigned=values&0xffffff
        raw=np.stack([unsigned&255,(unsigned>>8)&255,(unsigned>>16)&255],axis=1).astype(np.uint8).tobytes()
    else:raw=values.astype('<i2' if bits==16 else '<i4').tobytes()
    out=io.BytesIO()
    with wave.open(out,'wb') as w:w.setnchannels(1);w.setsampwidth(bits//8);w.setframerate(rate);w.writeframes(raw)
    return out.getvalue()


def generate(case):
    rate=case['rate'];n=round(case['length_s']*rate);t=np.arange(n)/rate
    # PCG64 explicit; base sinusoid and harmonics represent activity, not human speech.
    rng=np.random.Generator(np.random.PCG64(case['seed']))
    freq=case['frequency_hz'];x=.18*np.sin(2*np.pi*freq*t)+.04*np.sin(4*np.pi*freq*t+.4)
    noise=rng.standard_normal(n);noise/=np.sqrt(np.mean(noise**2))
    a=round((1+case['phase_s'])*rate);b=a+round(case['duration_ms']*rate/1000)
    family=case['family'];regions=[];pause_refs=[]
    if family not in ('low_energy_present','no_pause','all_silence','background_only','stationary_broadband'):
        x[a:b]=0;regions=[dict(start_sample=a,end_sample_exclusive=b,label='constructed_interruption')]
        if family=='closure':regions[0]['label']='closure_proxy'
        elif b-a>=rate//4:pause_refs=regions.copy()
    if family.startswith(('noise_','colored_','variable_')):
        snr=int(family.split('_')[1]);background=noise.copy()
        if family.startswith('colored_'):
            background=np.convolve(background,np.ones(15)/15,mode='same');background/=np.sqrt(np.mean(background**2))
        if family.startswith('variable_'):
            background*=.25+.75*(.5+.5*np.sin(2*np.pi*.7*t));background/=np.sqrt(np.mean(background**2))
        x+=background*(.13/10**(snr/20))
    elif family=='breath':
        breath=np.convolve(noise[a:b],np.ones(9)/9,mode='same');breath/=np.sqrt(np.mean(breath**2));envelope=np.sin(np.linspace(0,np.pi,b-a))**.7
        x[a:b]=case['breath_amplitude']*breath*envelope
    elif family=='low_amplitude':x*=.01
    elif family=='weak_voice':x*=.001
    elif family=='fade':
        width=round(case['fade_ms']*rate/1000);x[a-width:a]*=np.linspace(1,.01,width);x[b:b+width]*=np.linspace(.01,1,width)
    elif family=='closure':x[b:b+round(.005*rate)]+=.6*noise[b:b+round(.005*rate)]
    elif family=='two_close':
        c=b+round(case['gap_between_s']*rate);d=c+(b-a);x[c:d]=0
        regions.append(dict(start_sample=c,end_sample_exclusive=d,label='constructed_interruption'))
        if d-c>=rate//4:pause_refs=regions.copy()
    elif family=='brief_event':
        middle=(a+b)//2;w=round(case['brief_event_ms']*rate/1000);x[middle-w//2:middle+w//2]=.16*np.sin(2*np.pi*freq*t[middle-w//2:middle+w//2])
        # Activity is genuinely present: two reference regions, not one automatically bridged gap.
        regions=[dict(start_sample=a,end_sample_exclusive=middle-w//2,label='constructed_interruption'),dict(start_sample=middle+w//2,end_sample_exclusive=b,label='constructed_interruption')]
        pause_refs=[r for r in regions if r['end_sample_exclusive']-r['start_sample']>=rate//4]
    elif family=='aperiodic':
        x=.10*noise;x[a:b]=0
    elif family=='low_energy_present':
        x[a:b]*=.001 # Production proxy remains present; NOT a reference interruption.
    elif family=='all_silence':x[:]=0
    elif family=='background_only':x=.08*noise
    elif family=='clipped':x=np.clip(x*10,-1,1)
    elif family=='stationary_broadband':
        # Dense inharmonic activity: deliberately unvoiced-like, not a reference pause.
        x=np.zeros(n)
        for hz in (977,1409,1877,2381,3001,3691,4483,5303,6173,7247):x+=.025*np.sin(2*np.pi*hz*t+rng.uniform(0,6.28))
    wav=encode(x,rate,case['bits'])
    selection=dict(start_sample=0,end_sample_exclusive=n,confirmed=True)
    return wav,selection,dict(region_references=regions,pause_proxy_references=pause_refs,
        reference_scope='synthetic construction only; not human manual truth',duration_samples=b-a,
        actual_duration_s=(b-a)/rate,wav_sha256=digest(wav))


def manifest_digest(split):return digest(canonical(list(manifest(split))))
