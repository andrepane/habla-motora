"""Offline bank runner. Blocked requires a persisted, hash-verified freeze."""
import argparse
import gzip
import json
from pathlib import Path
import subprocess
import time
from collections import defaultdict
import numpy as np
from backend.phrase import canonical,digest
from .bank import manifest,generate
from .profiles import PROFILES,CONTEXTS,RANGE_RULES,JUMP_LIMITS_S
from .engine import extract_many,summarize,executable_identity,independent_concordance,HERE
from .evaluate import evaluate


def code_hash():
    files=[HERE/p for p in ['bank.py','engine.py','evaluate.py','profiles.py','extract.praat','statistics.praat','verify.praat']]
    return digest(b''.join(p.name.encode()+p.read_bytes() for p in files))


def run(split,output,executable,limit=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    cases=list(manifest(split));freeze=None
    if split=='blocked':
        if limit:raise ValueError('Blocked cannot be limited')
        freeze=json.loads((HERE/'freeze.json').read_text())
        if freeze['code_sha256']!=code_hash():raise ValueError('Code changed after freeze')
        if freeze['assessment_sha256']!=digest(Path('reports/prosody/assess.py').read_bytes()):raise ValueError('Acceptance changed after freeze')
        if freeze['module_sha256']!=digest(Path('backend/phrase_prosody.py').read_bytes()):raise ValueError('Module changed after freeze')
        commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        # Exact freeze bytes must exist in HEAD before any blocked signal is generated.
        committed=subprocess.check_output(['git','show','HEAD:research/prosody/freeze.json'])
        if committed!=(HERE/'freeze.json').read_bytes():raise ValueError('Freeze not committed')
        profiles=[freeze['profile']];contexts=[freeze['context_s']];rules=[freeze['range_rule']];limits=[freeze['jump_limit_s']]
    else:profiles=PROFILES;contexts=CONTEXTS;rules=RANGE_RULES;limits=JUMP_LIMITS_S;commit=None
    if limit:cases=cases[:limit]
    meta=dict(schema_version='prosody_bank_v1',split=split,cases=len(cases),limited=limit is not None,manifest_sha256=digest(canonical(cases)),code_sha256=code_hash(),runtime=executable_identity(executable),freeze_commit=commit,freeze_sha256=digest(canonical(freeze)) if freeze else None)
    (output/'manifest.json').write_bytes(canonical(meta));(output/'cases.json').write_bytes(canonical(cases))
    traces=defaultdict(dict);started=time.monotonic()
    with gzip.open(output/'results.jsonl.gz','wt',encoding='utf8') as out:
        for idx,case in enumerate(cases):
            data,selection,truth=generate(case)
            records=extract_many(data,selection,profiles,contexts,executable)
            for ident,record in records.items():
                summary=summarize(record,selection,case['rate'],rules[0],limits[0]);metrics=evaluate(case,record,summary)
                rule_comparison={}
                for rule in rules:
                    from .engine import support
                    sup=support(record['frames'],case['duration'],rule)
                    rule_comparison[rule['id']]={**sup,'expected':truth['global_support_expected']}
                # All jump evidence retained; time limits only control warnings.
                jumps={str(dt):sum(t['delta_t_s']<=dt+1e-12 and 11<=abs(t['delta_st'])<=13 for t in summary['transitions']) for dt in limits}
                concordance=None
                if case['rate']==44100 and case['bits']==16:
                    oracle=independent_concordance(record,selection,case['rate'],executable)
                    differences={k:abs(oracle[k]-record['native'][k]) if oracle[k] is not None and record['native'][k] is not None else None for k in record['native']}
                    concordance=dict(oracle=oracle,differences=differences,passed=all((oracle[k] is None)==(record['native'][k] is None) and (differences[k] is None or differences[k]<=1e-9) for k in record['native']))
                    if not concordance['passed']:raise ValueError('Native concordance failed')
                row=dict(concordance=concordance,case=case,configuration_id=ident,selection=selection,file_sha256=digest(data),truth=truth,metrics=metrics,native=record['native'],summary={k:v for k,v in summary.items() if k!='frames'},support_comparison=rule_comparison,jump_limit_comparison=jumps,profile=record['profile'],context_s=record['context_s'],grid=record['grid'],acoustic_interval=record['acoustic_interval'],original_pitch_sha256=record['original_pitch_sha256'],restricted_pitch_sha256=record['restricted_pitch_sha256'])
                out.write(canonical(row).decode()+'\n')
                # Compact lossless audit: exact exported centres and F0; NaN encodes JSON null only in NPZ.
                traces[ident][case['case_id']]=np.array([[f['time_absolute_s'],f['f0_hz'] if f['defined'] else np.nan] for f in record['frames']],dtype='<f8')
            if (idx+1)%6==0:print(f'{split} {idx+1}/{len(cases)} {time.monotonic()-started:.1f}s',flush=True)
    for ident,arrays in traces.items():np.savez_compressed(output/f'traces-{ident}.npz',**arrays)
    meta['elapsed_s']=time.monotonic()-started;(output/'manifest.json').write_bytes(canonical(meta))
    aggregate(output)


def aggregate(output):
    groups=defaultdict(list)
    with gzip.open(output/'results.jsonl.gz','rt') as f:
        for line in f:
            r=json.loads(line);groups[(r['configuration_id'],r['case']['family'])].append(r)
    result=[]
    for (config,family),rows in sorted(groups.items()):
        fields=rows[0]['metrics'].keys();m={}
        for key in fields:
            values=[float(r['metrics'][key]) for r in rows if r['metrics'][key] is not None]
            m[key]={'median':float(np.median(values)) if values else None,'p95':float(np.percentile(values,95)) if values else None,'sum':float(np.sum(values)) if values else None,'n':len(values)}
        result.append(dict(configuration_id=config,family=family,cases=len(rows),metrics=m))
    (output/'summary.json').write_bytes(canonical(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('split',choices=['development','blocked']);p.add_argument('--output',required=True);p.add_argument('--executable',default='praat');p.add_argument('--limit',type=int);a=p.parse_args();run(a.split,a.output,a.executable,a.limit)
