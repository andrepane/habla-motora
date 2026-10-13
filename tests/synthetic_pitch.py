"""Deterministic PCM16 signals; no participants, speech corpus or AI voices."""
import io
import math
import random
import struct
import wave

RATE = 44100
DURATION = 6.0


def wav_bytes(kind='tone', frequency=200, rate=RATE):
    rng = random.Random(20261013)
    samples = []
    for i in range(int(DURATION*rate)):
        t = i/rate
        if kind == 'silence':
            y = 0
        elif kind == 'noise':
            y = 0.3*rng.uniform(-1, 1)
        elif kind == 'modulated':
            # Integral of f(t)=200+20*sin(2*pi*2*t); modulation is continuous.
            phase = 2*math.pi*200*t + 10*(1-math.cos(2*math.pi*2*t))
            y = 0.3*math.sin(phase)
        elif kind == 'gap':
            y = 0.3*math.sin(2*math.pi*frequency*t) if t < 2.5 or t >= 3.5 else 0
        elif kind == 'weak_fundamental':
            y = 0.0001*math.sin(2*math.pi*200*t)+0.3*math.sin(2*math.pi*400*t)
        else:
            y = 0.3*math.sin(2*math.pi*frequency*t)
        samples.append(struct.pack('<h', round(y*32767)))
    out = io.BytesIO()
    with wave.open(out, 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(rate)
        wav.writeframes(b''.join(samples))
    return out.getvalue()
