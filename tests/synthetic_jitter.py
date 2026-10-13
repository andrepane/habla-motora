"""Known pulse timing, independent of Praat's detector."""
import io
import math
import random
import struct
import wave
from decimal import Decimal, localcontext

RATE=44100
DURATION=6.0


def cycle_times(jitter_percent=0,frequency=200,anomaly=None):
    period=1/frequency; epsilon=jitter_percent/200
    times=[0.05]; i=0
    while times[-1]<5.95:
        interval=period*(1+epsilon if i%2 else 1-epsilon)
        if anomaly=='long_period' and i==600: interval*=1.5
        times.append(times[-1]+interval); i+=1
    if anomaly=='lost_pulse': del times[600]
    if anomaly=='added_pulse': times.insert(600,(times[599]+times[600])/2)
    return times



def random_cycle_times(jitter_percent=1,frequency=200):
    rng=random.Random(731)
    deviations=[rng.uniform(-1,1) for _ in range(1300)]
    average=sum(deviations)/len(deviations)
    deviations=[v-average for v in deviations]
    average_difference=sum(abs(b-a) for a,b in zip(deviations,deviations[1:]))/(len(deviations)-1)
    scale=(jitter_percent/100)/average_difference
    times=[.05]
    for v in deviations:
        times.append(times[-1]+(1/frequency)*(1+scale*v))
        if times[-1]>=5.95: break
    return times

def mathematical_reference(times,start=1.5,end=4.5,minimum=0.8/600,maximum=1.25/75,factor=1.3):
    # Test oracle: explicit inequalities on known times, never used by production.
    # Keep outside-window neighbours, matching the documented mean-period context.
    with localcontext() as ctx:
        ctx.prec=40
        ts=[Decimal(str(t)) for t in times]
        periods=[b-a for a,b in zip(ts,ts[1:])]
        low,high,limit=map(lambda v:Decimal(str(v)),(minimum,maximum,factor))
        selected=[i for i in range(len(periods)) if Decimal(str(start))<=ts[i] and ts[i+1]<=Decimal(str(end))]
        def similar(a,b): return max(a/b,b/a)<=limit
        accepted=[]
        for i in selected:
            p=periods[i]
            if not low<=p<=high: continue
            neighbours=[periods[j] for j in (i-1,i+1) if 0<=j<len(periods)]
            if len(neighbours)==2 and all(not similar(p,n) for n in neighbours): continue
            accepted.append(p)
        diffs=[abs(periods[i+1]-periods[i]) for i in selected if i+1 in selected
               and low<=periods[i]<=high and low<=periods[i+1]<=high
               and similar(periods[i],periods[i+1])]
        value=None if not diffs or not accepted else float(100*sum(diffs)/len(diffs)/(sum(accepted)/len(accepted)))
    return {'jitter_local_percent':value,'candidate_periods':len(selected),
            'accepted_periods':len(accepted),'pairs':len(diffs)}


def pulse_wav(times,gain=1,noise_db=None,saturate=False,rate=RATE):
    samples=[0.0]*int(DURATION*rate)
    # Identical fixed Gaussian pulse template at known (possibly fractional-sample) times.
    # Absolute time shift of detected extrema is allowed; variable warping is not.
    sigma=0.0002
    for t in times:
        left=max(0,math.floor((t-4*sigma)*rate));right=min(len(samples),math.ceil((t+4*sigma)*rate)+1)
        for i in range(left,right): samples[i]+=0.3*math.exp(-0.5*((i/rate-t)/sigma)**2)
    if noise_db is not None:
        rng=random.Random(20261013)
        noise=[rng.gauss(0,1) for _ in samples]
        signal_rms=math.sqrt(sum(v*v for v in samples)/len(samples))
        noise_rms=math.sqrt(sum(v*v for v in noise)/len(noise))
        scale=signal_rms/(10**(noise_db/20)*noise_rms)
        samples=[v+n*scale for v,n in zip(samples,noise)]
    out=io.BytesIO()
    with wave.open(out,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate)
        encoded=[]
        for v in samples:
            x=v*gain
            if not saturate and abs(x)>1: raise ValueError('Unintended saturation')
            encoded.append(struct.pack('<h',max(-32768,min(32767,round(x*32767)))))
        wav.writeframes(b''.join(encoded))
    return out.getvalue()


def pulse_matching(known,detected,start=1.5,end=4.5,period=0.005):
    # Pair with full context before counting inside a guarded analysis interval.
    # This prevents a constant acoustic phase shift from manufacturing edge misses.
    truth=list(known); observed=[p['time_s'] for p in detected]
    i=j=0; offsets=[];missing=extra=0
    gate=0.25*period
    inner_start,inner_end=start+period,end-period
    while i<len(truth) and j<len(observed):
        delta=observed[j]-truth[i]
        if abs(delta)<=gate:
            if inner_start<truth[i]<inner_end: offsets.append(delta)
            i+=1;j+=1
        elif delta<0:
            extra+=int(inner_start<observed[j]<inner_end);j+=1
        else:
            missing+=int(inner_start<truth[i]<inner_end);i+=1
    missing+=sum(inner_start<t<inner_end for t in truth[i:])
    extra+=sum(inner_start<t<inner_end for t in observed[j:])
    shift=sorted(offsets)[len(offsets)//2] if offsets else None
    residual=max(abs(v-shift) for v in offsets) if offsets else None
    return {'matched':len(offsets),'missing':missing,'extra':extra,'global_shift_s':shift,
            'max_residual_after_global_shift_s':residual,'matching_gate_s':gate}
