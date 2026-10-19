"""Offline comparative bank runner. Blocked evaluation requires a frozen development gate."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import gzip
import json
import os
import platform
from pathlib import Path
import time
import numpy as np
from backend.phrase import canonical,digest
from .bank import manifest,generate,manifest_digest
from .engine import detect,config
from .praat_comparator import detect_praat
from .metrics import evaluate


def quant(values):
    a=np.asarray(values,dtype=float)
    return {'n':len(a),'mean':float(a.mean()),'p50':float(np.median(a)),'p95':float(np.percentile(a,95)),'max':float(a.max())} if len(a) else {'n':0,'mean':None,'p50':None,'p95':None,'max':None}


def aggregate(rows):
    result={}
    for name in ['region_metrics','pause_proxy_metrics','region_metrics_iou50']:
        metrics=[r[name] for r in rows if r[name] is not None];tp=sum(m['tp'] for m in metrics);fp=sum(m['fp'] for m in metrics);fn=sum(m['fn'] for m in metrics)
        seconds=sum(r['case']['length_s'] for r in rows if r[name] is not None)
        result[name]=dict(tp=tp,fp=fp,fn=fn,recall=tp/(tp+fn) if tp+fn else None,precision=tp/(tp+fp) if tp+fp else None,
            false_candidates_per_minute=fp/(seconds/60) if seconds else None,
            false_candidates_per_minute_distribution=quant([m['false_candidates_per_minute'] for m in metrics]),
            iou=quant([v for m in metrics for v in m['iou']]),
            start_error_ms=quant([v for m in metrics for v in m['start_error_ms']]),end_error_ms=quant([v for m in metrics for v in m['end_error_ms']]),
            absolute_start_error_ms=quant([abs(v) for m in metrics for v in m['start_error_ms']]),absolute_end_error_ms=quant([abs(v) for m in metrics for v in m['end_error_ms']]),
            fusion_count=sum(m['fusion_count'] for m in metrics),fragmentation_count=sum(m['fragmentation_count'] for m in metrics),omissions=fn)
    result.update(cases=len(rows),statuses={s:sum(r['status']==s for r in rows) for s in ['completed','failed','not_evaluable']},latency_s=quant([r['latency_s'] for r in rows]))
    return result


def evaluate_case(case):
    result=[]
    data,selection,truth=generate(case)
    for variant in ['energy','multifeature','praat']:
        tick=time.perf_counter();response=detect_praat(data,selection,case['case_id']) if variant=='praat' else detect(data,selection,case['case_id'],variant,False)
        elapsed=time.perf_counter()-tick
        candidates=response['automatic_candidates'] or []
        # Include every proposal in review burden, including boundary regions. Never hide them as free exclusions.
        internal=candidates
        metrics=None if response['status']=='failed' else evaluate(internal,truth['region_references'],case['rate'],selection['end_sample_exclusive'])
        pm=None if response['status']=='failed' else evaluate(internal,truth['pause_proxy_references'],case['rate'],selection['end_sample_exclusive'])
        row=dict(case=case,truth=truth,variant=variant,status=response['status'],latency_s=elapsed,edge_candidate_count=sum('selection_edge' in c['warnings'] for c in candidates),
            region_metrics=metrics,pause_proxy_metrics=pm,region_metrics_iou50=None if metrics is None else evaluate(internal,truth['region_references'],case['rate'],selection['end_sample_exclusive'],.5),response=response)
        result.append(row)
    return result


def run(split,destination,gate_path=None,limit=None):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    gate=None
    if split=='blocked':
        if not gate_path:raise ValueError('Blocked evaluation requires a frozen gate')
        raw=Path(gate_path).read_bytes();gate=json.loads(raw)
        if gate['blocked_manifest_sha256']!=manifest_digest(split):raise ValueError('Blocked manifest mismatch')
        for v in ['energy','multifeature']:
            if gate['detector_config_sha256'][v]!=config(v)[1]:raise ValueError('Configuration changed after freeze')
        if gate['detector_config_sha256']['praat']!=digest((Path(__file__).parents[2]/'configs/pause_detector_praat_v1.json').read_bytes()):raise ValueError('Praat configuration changed after freeze')
        if gate['evaluation_code_sha256']!=evaluation_digest():raise ValueError('Evaluation changed after freeze')
        if gate['runtime']!={'numpy':np.__version__,'python':platform.python_version()}:raise ValueError('Runtime changed after freeze')
    code_at_start=evaluation_digest()
    rows=[];started=time.time()
    target=destination/f'{split}-cases.jsonl.gz'
    # Reproducible gzip header; each row contains full candidate provenance, waveform recipe and references.
    cases=list(manifest(split))
    if limit:cases=cases[:limit]
    with target.open('wb') as rawout,gzip.GzipFile(filename='',mode='wb',fileobj=rawout,mtime=0) as out,ThreadPoolExecutor(max_workers=8) as executor:
        for index,case_rows in enumerate(executor.map(evaluate_case,cases)):
            for row in case_rows:
                out.write(canonical(row)+b'\n');rows.append(row)
            if (index+1)%100==0:print(f'{split}: {index+1} WAV / {3*(index+1)} evaluations',flush=True)
    if evaluation_digest()!=code_at_start:raise ValueError('Evaluation code changed during execution')
    groups=defaultdict(list)
    for row in rows:
        c=row['case'];v=row['variant']
        for key in [f'overall/{v}',f'family/{c["family"]}/{v}',f'duration/{c["duration_ms"]}/{v}',f'format/{c["rate"]}-{c["bits"]}/{v}',f'frequency/{c["frequency_hz"]}/{v}',f'condition/{c["family"]}/{c["duration_ms"]}/{c["rate"]}/{c["bits"]}/{c["frequency_hz"]}/{v}']:
            groups[key].append(row)
    summary=dict(split=split,manifest_sha256=manifest_digest(split),evaluation_code_sha256=evaluation_digest(),case_rows_sha256=digest(target.read_bytes()),execution_workers=8,runtime={"numpy":np.__version__,"python":platform.python_version()},wav_cases=len(rows)//3,evaluations=len(rows),elapsed_s=time.time()-started,
        all_proposals_in_false_candidate_load=True,frozen_gate_sha256=digest(Path(gate_path).read_bytes()) if gate_path else None,limited_run=bool(limit),groups={k:aggregate(v) for k,v in groups.items()})
    (destination/f'{split}-summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='groups'}),flush=True)
    return summary


def evaluation_digest():
    root=Path(__file__).parent
    return digest(b''.join((root/p).read_bytes() for p in ['engine.py','metrics.py','bank.py','praat_comparator.py','run_bank.py'])+(root.parents[1]/'praat/pause_candidates_comparator.praat').read_bytes())


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--split',choices=['development','blocked'],required=True);p.add_argument('--output',default='reports/pause_candidates');p.add_argument('--gate');p.add_argument('--limit',type=int)
    a=p.parse_args();run(a.split,a.output,a.gate,a.limit)
