"""Regenerate one recipe, original WAV and full acoustic/candidate trace (offline)."""
import argparse
import json
from pathlib import Path
from .bank import manifest,generate
from .engine import detect
from .praat_comparator import detect_praat

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--split',choices=['development','blocked'],required=True);p.add_argument('--case-id',required=True);p.add_argument('--variant',choices=['energy','multifeature','praat'],required=True);p.add_argument('--output',required=True);a=p.parse_args()
    c=next((c for c in manifest(a.split) if c['case_id']==a.case_id),None)
    if c is None:raise SystemExit('Unknown case ID')
    data,s,t=generate(c);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    response=detect_praat(data,s,c['case_id']) if a.variant=='praat' else detect(data,s,c['case_id'],a.variant,True)
    (out/'original.wav').write_bytes(data);(out/'trace.json').write_text(json.dumps(dict(case=c,truth=t,response=response),indent=2,allow_nan=False)+'\n')
