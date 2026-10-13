"""Known cycle amplitudes and PCM signals; independent test oracles only."""
import io
import math
import random
import struct
import wave
from decimal import Decimal, localcontext

RATE = 44100
DURATION = 6


def source(level=1, random_amplitudes=False, anomaly=None):
    times = [.05 + i/200 for i in range(1181)]
    if random_amplitudes:
        rng = random.Random(20261014)
        d = [rng.uniform(-1, 1) for _ in times]
        mean = sum(d)/len(d)
        d = [v-mean for v in d]
        difference = sum(abs(b-a) for a,b in zip(d,d[1:]))/(len(d)-1)
        scale = level/100/difference
        amplitudes = [1+scale*v for v in d]
    else:
        epsilon = level/200
        amplitudes = [1+(-1 if i%2 == 0 else 1)*epsilon for i in range(len(times))]
    if anomaly == 'lost_pulse':
        del times[600]; del amplitudes[600]
    elif anomaly == 'added_pulse':
        times.insert(600, (times[599]+times[600])/2); amplitudes.insert(600, 1)
    elif anomaly == 'shifted_pulse':
        times[600] += .002
    elif anomaly == 'long_period':
        times = [t + (.0025 if i >= 600 else 0) for i,t in enumerate(times)]
    elif anomaly == 'amplitude_spike':
        amplitudes[600] *= 2
    return times, amplitudes


def wav_from_cycles(times, amplitudes, gain=1, noise_db=None, clipping=False):
    samples = [0.0]*int(DURATION*RATE)
    sigma = .0002
    for t,a in zip(times,amplitudes):
        left = max(0, math.floor((t-4*sigma)*RATE-.5))
        right = min(len(samples), math.ceil((t+4*sigma)*RATE-.5)+1)
        for i in range(left,right):
            sample_time = (i+.5)/RATE
            samples[i] += .3*a*math.exp(-.5*((sample_time-t)/sigma)**2)
    if noise_db is not None:
        rng = random.Random(20261014)
        noise = [rng.gauss(0,1) for _ in samples]
        signal_rms = math.sqrt(sum(v*v for v in samples)/len(samples))
        noise_rms = math.sqrt(sum(v*v for v in noise)/len(noise))
        scale = signal_rms/(10**(noise_db/20)*noise_rms)
        samples = [v+n*scale for v,n in zip(samples,noise)]
    out = io.BytesIO()
    with wave.open(out, 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(RATE)
        encoded = []
        for v in samples:
            value = v*gain
            if not clipping and abs(value)>1:
                raise ValueError('Unintended clipping')
            encoded.append(struct.pack('<h', max(-32768,min(32767,round(value*32767)))))
        wav.writeframes(b''.join(encoded))
    return out.getvalue()


def shimmer_formula(times, amplitudes, minimum=.8/600, maximum=1.25/75, factor=1.6):
    # Only a test oracle, never used by production. Follow exact frozen-engine denominator.
    with localcontext() as context:
        context.prec = 40
        t = [Decimal(str(v)) for v in times]
        a = [Decimal(str(v)) for v in amplitudes]
        low, high, limit = (Decimal(str(v)) for v in (minimum,maximum,factor))
        differences = [abs(a[i]-a[i-1]) for i in range(1,len(a))
                       if low <= t[i]-t[i-1] <= high and max(a[i]/a[i-1],a[i-1]/a[i]) <= limit]
        denominator = sum(a[:-1])/len(a[:-1]) if len(a)>1 else Decimal(0)
        result = float(100*sum(differences)/len(differences)/denominator) if differences and denominator else None
    return {'shimmer_local_percent': result, 'pairs_used': len(differences), 'amplitudes': len(a)}


def source_reference(times, amplitudes, start=1.5, end=4.5):
    inside = [(t,a) for t,a in zip(times,amplitudes) if start <= t <= end]
    points = []
    for i in range(1,len(inside)-1):
        p1,p2 = inside[i][0]-inside[i-1][0],inside[i+1][0]-inside[i][0]
        if .8/600 <= p1 <= 1.25/75 and .8/600 <= p2 <= 1.25/75 and max(p1/p2,p2/p1) <= 1.3:
            points.append(inside[i])
    return shimmer_formula([p[0] for p in points],[p[1] for p in points])


def independently_extract_pcm(data, times, start=1.5, end=4.5):
    # Explicit weighted RMS on decoded PCM samples, with no calls to Praat.
    with wave.open(io.BytesIO(data),'rb') as wav:
        rate = wav.getframerate(); width = wav.getsampwidth()
        raw = wav.readframes(wav.getnframes())
    scale = 1 << (8*width-1)
    values = [int.from_bytes(raw[i:i+width],'little',signed=True)/scale for i in range(0,len(raw),width)]
    inside = [t for t in times if start <= t <= end]
    points = []
    for left,t,right in zip(inside,inside[1:],inside[2:]):
        p1,p2 = t-left,right-t
        if not (.8/600 <= p1 <= 1.25/75 and .8/600 <= p2 <= 1.25/75 and max(p1/p2,p2/p1) <= 1.3):
            continue
        wl,wr = .2*p1,.2*p2
        first=max(0,math.ceil((t-wl)*rate-.5));last=min(len(values)-1,math.floor((t+wr)*rate-.5))
        if last-first+1 < 3: continue
        weighted=[];squares=[]
        for i in range(first,last+1):
            dt=(i+.5)/rate-t
            window=.5+.5*math.cos(math.pi*dt/(wl if dt<0 else wr))
            weighted.append((values[i]*window)**2);squares.append(window**2)
        amplitude=math.sqrt(math.fsum(weighted)/math.fsum(squares))
        if amplitude>0: points.append((t,amplitude))
    result=shimmer_formula([p[0] for p in points],[p[1] for p in points])
    result['points']=[{'time_s':t,'amplitude_rms':a} for t,a in points]
    return result
