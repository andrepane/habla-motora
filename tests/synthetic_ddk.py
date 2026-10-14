"""Controlled acoustic bursts. NOT speech, syllables, or phonetic labels."""
import io
import math
import random
import wave


def signal(centers=None, rate=48000, bits=16, duration=4, amplitudes=(.35,), noise=0, clip=False, transients=False, seed=606):
    centers = [.25+i/6 for i in range(21)] if centers is None else centers
    values = [0.0]*round(duration*rate)
    for k, center in enumerate(centers):
        for i in range(max(0,round((center-.03)*rate)), min(len(values),round((center+.03)*rate))):
            t=i/rate-center
            envelope=(.5+.5*math.cos(math.pi*t/.03))**2
            values[i]+=amplitudes[k%len(amplitudes)]*envelope*math.cos(2*math.pi*240*t)
        if transients:
            i=round((center-.045)*rate)
            if 0<=i<len(values): values[i]=.9
    rng=random.Random(seed)
    if noise: values=[v+noise*rng.gauss(0,1) for v in values]
    if clip: values=[v*8 for v in values]
    width=bits//8;scale=2**(bits-1)
    pcm=b''.join(max(-scale,min(scale-1,round(v*(scale-1)))).to_bytes(width,'little',signed=True) for v in values)
    out=io.BytesIO()
    with wave.open(out,'wb') as w:
        w.setnchannels(1);w.setsampwidth(width);w.setframerate(rate);w.writeframes(pcm)
    return out.getvalue(), centers
