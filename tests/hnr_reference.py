"""Controlled native objects and a separate native script, never a frame-mean substitute."""
import json
import os
from pathlib import Path
import tempfile
from backend.praat_runner import _run

HERE=Path(__file__).parent


def query_sound(data,start=1.5,end=4.5):
    with tempfile.TemporaryDirectory() as temp:
        wav=Path(temp)/'input.wav';wav.write_bytes(data)
        raw=_run([os.environ.get('PRAAT_EXECUTABLE','praat'),'--run',str(HERE/'reference_hnr.praat'),str(wav),str(start),str(end)])
    return json.loads(raw)


def query_object(values,start=1.5,end=4.5,x1=2,step=.01):
    with tempfile.TemporaryDirectory() as temp:
        matrix=Path(temp)/'known.Matrix'
        matrix.write_text('File type = "ooTextFile"\nObject class = "Matrix"\n\nxmin = 0\nxmax = 6\n'
                          f'nx = {len(values)}\ndx = {step:.17g}\nx1 = {x1:.17g}\n'
                          'ymin = 1\nymax = 1\nny = 1\ndy = 1\ny1 = 1\nz []:\n    z [1]:\n'+
                          ''.join(f'        z [1] [{i}] = {v:.17g}\n' for i,v in enumerate(values,1)))
        raw=_run([os.environ.get('PRAAT_EXECUTABLE','praat'),'--run',str(HERE/'reference_hnr_object.praat'),
                  str(matrix),str(start),str(end)])
    return json.loads(raw)
