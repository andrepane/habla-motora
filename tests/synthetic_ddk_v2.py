"""One controlled modulated carrier; no speech or phonetic ground truth."""
import io
import math
import wave

# Frozen from seed-606 topology exploration, trial 6. Detector config was never tuned.
BASIN_PARAMETERS={'f1':10,'f2':35,'a':0.293976294813734,'b':0.23678898845010482,
                  'p1':-1.1007566122811516,'p2':2.89699205948264}

def basin_fragmentation_wav():
    p=BASIN_PARAMETERS;rate=48000;pcm=[]
    for i in range(round(1.2*rate)):
        t=i/rate-.6
        envelope=.3*math.exp(-t*t/(2*.09**2))*(1+p['a']*math.cos(2*math.pi*p['f1']*t+p['p1'])+p['b']*math.cos(2*math.pi*p['f2']*t+p['p2']))
        value=round(envelope*math.cos(2*math.pi*240*t)*32767)
        pcm.append(value.to_bytes(2,'little',signed=True))
    out=io.BytesIO()
    with wave.open(out,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(b''.join(pcm))
    return out.getvalue()
