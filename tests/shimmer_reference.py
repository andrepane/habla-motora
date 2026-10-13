"""Native queries on imposed amplitudes and pulses, without acoustic tracking."""
import json
import os
from pathlib import Path
import tempfile
from backend.praat_runner import _run

HERE = Path(__file__).parent


def query_tier(times, amplitudes):
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'known.AmplitudeTier'
        path.write_text('File type = "ooTextFile"\nObject class = "AmplitudeTier"\n\nxmin = 0\nxmax = 6\npoints: size = '+str(len(times))+'\n'+
                        ''.join(f'points [{i}]:\n    number = {t:.17g}\n    value = {a:.17g}\n' for i,(t,a) in enumerate(zip(times,amplitudes),1)))
        raw=_run([os.environ.get('PRAAT_EXECUTABLE','praat'),'--run',str(HERE/'reference_shimmer_tier.praat'),
                  str(path),str(.8/600),str(1.25/75),'1.6'])
    return json.loads(raw)


def query_sound(data, times, start=1.5, end=4.5):
    with tempfile.TemporaryDirectory() as temp:
        wav=Path(temp)/'known.wav';wav.write_bytes(data)
        path=Path(temp)/'known.PointProcess'
        path.write_text('File type = "ooTextFile"\nObject class = "PointProcess"\n\nxmin = 0\nxmax = 6\nnt = '+str(len(times))+'\nt []:\n'+
                        ''.join(f'    t [{i}] = {t:.17g}\n' for i,t in enumerate(times,1)))
        raw=_run([os.environ.get('PRAAT_EXECUTABLE','praat'),'--run',str(HERE/'reference_shimmer_sound.praat'),
                  str(wav),str(path),str(start),str(end),str(.8/600),str(1.25/75),'1.3','1.6'])
    result=json.loads(raw)
    result['shimmer_local_percent']=100*result['shimmer_local_ratio'] if result['shimmer_local_ratio'] is not None else None
    return result
