"""Praat comparator, same candidate contract; not a reference annotation."""
import json
from functools import lru_cache
import os
from pathlib import Path
import subprocess
import tempfile
from backend.phrase import ROOT, canonical, digest
from .engine import decode, identity


@lru_cache(maxsize=4)
def praat_version(executable):
    version=subprocess.run([executable,'--version'],check=True,capture_output=True,text=True,timeout=15).stdout.strip()
    if len(version.split())<2 or version.split()[1]!='6.4.27':raise ValueError('Expected Praat 6.4.27')
    return version


def detect_praat(data,selection,source_context_id,executable=None):
    _,meta=decode(data);source=identity(data,meta,selection,source_context_id)
    raw=(ROOT/'configs/pause_detector_praat_v1.json').read_bytes();c=json.loads(raw)
    script=ROOT/'praat/pause_candidates_comparator.praat'
    provenance=dict(schema_version='pause_candidates_output_v1',detector_version=c['detector_version'],configuration=c,config_sha256=digest(raw),engine_sha256=digest(Path(__file__).read_bytes()+script.read_bytes()),source=source,
        candidate_decisions=[],manual_annotations=[],candidate_manual_links=[],manual_final_result=None,warnings=['PRAAT_COMPARATOR_NOT_REFERENCE_TRUTH'],frame_trace=None)
    run_id=digest(canonical(provenance));provenance['run_id']=run_id
    executable=executable or os.environ.get('PRAAT_EXECUTABLE','praat')
    try:
        version=praat_version(executable)
        with tempfile.TemporaryDirectory(prefix='pause-comparator-') as temp:
            path=Path(temp)/'original.wav';path.write_bytes(data);rate=meta['sample_rate_hz']
            out=subprocess.run([executable,'--run',str(script),str(path),str(selection['start_sample']/rate),str(selection['end_sample_exclusive']/rate)],check=True,capture_output=True,text=True,timeout=15).stdout
        candidates=[]
        for line in out.splitlines():
            p,q=map(float,line.split());a=selection['start_sample']+round(p*rate);b=selection['start_sample']+round(q*rate)
            a=max(selection['start_sample'],a);b=min(selection['end_sample_exclusive'],b)
            if a>=b:raise ValueError('Invalid comparator interval')
            candidates.append(dict(candidate_id=f'{run_id[:16]}-c{len(candidates)+1:04d}',start_sample=a,end_sample_exclusive=b,duration_samples=b-a,duration_s=(b-a)/rate,status='unreviewed',proposal_reasons=['praat_native_intensity_segmentation'],features={'native_intensity_contour':'Praat 6.4.27; no custom reimplementation'},technical_evidence={'native_start_s':p,'native_end_s':q},warnings=['selection_edge'] if a==selection['start_sample'] or b==selection['end_sample_exclusive'] else [],detector_version=c['detector_version'],config_sha256=digest(raw),overlap_group_id=None))
        return {**provenance,'status':'completed','reason':None,'automatic_candidates':candidates,'praat_version':version,'native_output':out}
    except (OSError,subprocess.SubprocessError,ValueError) as exc:
        return {**provenance,'status':'failed','reason':type(exc).__name__,'automatic_candidates':None,'error_detail':str(exc)}
