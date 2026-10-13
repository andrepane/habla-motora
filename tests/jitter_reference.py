"""Praat calculation on supplied times, with no Sound or pitch tracking."""
import json
import os
from pathlib import Path
import tempfile
from backend.praat_runner import _run


def query_known_times(times,start=1.5,end=4.5):
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'known.PointProcess'
        # Praat text format: xmin, xmax, capacity/count and exact point times.
        path.write_text('File type = "ooTextFile"\nObject class = "PointProcess"\n\n'
                        'xmin = 0\nxmax = 6\nnt = '+str(len(times))+'\nt []:\n'+
                        ''.join(f'    t [{i}] = {t:.17g}\n' for i,t in enumerate(times,1)))
        raw=_run([os.environ.get('PRAAT_EXECUTABLE','praat'),'--run',
                  str(Path(__file__).parent/'reference_jitter.praat'),str(path),str(start),str(end),
                  str(0.8/600),str(1.25/75),'1.3'])
    return json.loads(raw)
