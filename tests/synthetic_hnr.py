"""Controlled periodic/noise components; no acoustic HNR oracle from Praat values."""
from functools import lru_cache
import io
import math
import random
import statistics
import struct
import wave

DURATION=6
SEEDS=tuple(range(5000,5020))
SNR_LEVELS=(0,10,20,30,40)


@lru_cache(maxsize=24)
def unit_noise(seed=5000,rate=48000):
    rng=random.Random(seed)
    values=[rng.gauss(0,1) for _ in range(DURATION*rate)]
    rms=math.sqrt(math.fsum(v*v for v in values)/len(values))
    return tuple(v/rms for v in values)


@lru_cache(maxsize=12)
def periodic_values(frequency=200,rate=48000,kind='tone'):
    # Repeat an exact sampled period where possible, avoiding cumulative phase round-off.
    period=rate/frequency
    def sample(i):
        phase=2*math.pi*frequency*((i+.5)/rate)
        if kind=='harmonics': return math.sin(phase)+.5*math.sin(2*phase)+.25*math.sin(3*phase)
        if kind=='weak_fundamental': return .1*math.sin(phase)+math.sin(2*phase)
        if kind=='inharmonic': return math.sin(phase)+.5*math.sin(2*math.pi*317*((i+.5)/rate))
        return math.sin(phase)
    if kind!='inharmonic' and period.is_integer():
        block=[sample(i) for i in range(int(period))]
        return tuple(block[i%len(block)] for i in range(DURATION*rate))
    return tuple(sample(i) for i in range(DURATION*rate))


def make_wav(frequency=200,snr_db=None,seed=5000,gain=1,clipping=False,rate=48000,kind='tone',global_context=False):
    n=DURATION*rate
    if kind in ('silence','noise_only'):
        signal=[0.0]*n
    else:
        signal=[.2*v for v in periodic_values(frequency,rate,kind if kind in ('harmonics','weak_fundamental','inharmonic') else 'tone')]
    power=math.fsum(v*v for v in signal)/n
    if kind=='noise_only':
        noise=[.1*v for v in unit_noise(seed,rate)]
    elif snr_db is not None:
        scale=math.sqrt(power)/10**(snr_db/20)
        noise=[scale*v for v in unit_noise(seed,rate)]
    else:
        noise=[0.0]*n
    # Joint source scaling controls headroom without altering the generated component ratio.
    peak=max((abs(s+z) for s,z in zip(signal,noise)),default=0)
    source_scale=min(1,.4/peak) if peak else 1
    signal=[v*source_scale*gain for v in signal];noise=[v*source_scale*gain for v in noise]
    if kind=='gap':
        for i in range(int(2.5*rate),int(3.5*rate)):signal[i]=0;noise[i]=0
    if kind=='weak_center':
        signal=[v*.05 for v in signal]
        if global_context:
            for i in range(rate):signal[i]*=16
    values=[s+z for s,z in zip(signal,noise)]
    if not clipping and any(abs(v)>1 for v in values):raise ValueError('Unintended clipping')
    encoded=[max(-32768,min(32767,round(v*32767))) for v in values]
    data=io.BytesIO()
    with wave.open(data,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate)
        wav.writeframes(struct.pack('<'+'h'*n,*encoded))
    ps=math.fsum(v*v for v in signal)/n;pn=math.fsum(v*v for v in noise)/n
    generated_snr=10*math.log10(ps/pn) if ps>0 and pn>0 else None
    # Residual relative to quantized known periodic component includes noise and quantization.
    periodic_pcm=[max(-32768,min(32767,round(v*32767))) for v in signal]
    periodic_power=math.fsum((v/32768)**2 for v in periodic_pcm)/n
    residual_power=math.fsum(((v-s)/32768)**2 for v,s in zip(encoded,periodic_pcm))/n
    effective_snr=10*math.log10(periodic_power/residual_power) if periodic_power>0 and residual_power>0 else None
    return data.getvalue(),{'kind':kind,'frequency_hz':None if kind in ('silence','noise_only') else frequency,
                          'rate_hz':rate,'sample_width_bytes':2,'nominal_snr_db':snr_db,'seed':seed,
                          'gain':gain,'clipping_requested':clipping,'joint_source_scale':source_scale,
                          'generated_component_snr_db':generated_snr,'pcm_reference_residual_snr_db':effective_snr}


def fixed_lag_reference(data,frequency=200):
    # Normalized Pearson correlation at the KNOWN true period; no maximizing or Praat input.
    with wave.open(io.BytesIO(data),'rb') as wav:
        rate=wav.getframerate();samples=[v[0]/32768 for v in struct.iter_unpack('<h',wav.readframes(wav.getnframes()))]
    lag=rate/frequency
    if not lag.is_integer():raise ValueError('Reference requires integer-sample period')
    lag=int(lag);width=round(.06*rate)
    correlations=[];values=[]
    for frame in range(300):
        center=1.505+.01*frame
        first=round(center*rate-width/2)
        a=samples[first:first+width];b=samples[first+lag:first+lag+width]
        ma=math.fsum(a)/width;mb=math.fsum(b)/width
        covariance=math.fsum((x-ma)*(y-mb) for x,y in zip(a,b))
        energy_a=math.fsum((x-ma)**2 for x in a);energy_b=math.fsum((y-mb)**2 for y in b)
        r=covariance/math.sqrt(energy_a*energy_b) if energy_a and energy_b else None
        correlations.append(r)
        values.append(10*math.log10(r/(1-r)) if r is not None and 0<r<1 else None)
    valid=[v for v in values if v is not None]
    return {'definition':'Known-lag Pearson correlation, 60 ms segments, 200 Hz integer lag; NOT Praat algorithm',
            'finite_frames':len(valid),'mean_db':statistics.mean(valid) if valid else None,
            'mean_correlation':statistics.mean([v for v in correlations if v is not None]),
            'ideal_stationary_correlation_from_snr':'Ps/(Ps+Pn); not an exact finite-sample Praat reference'}
