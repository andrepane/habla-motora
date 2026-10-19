"""Freeze acceptance from DEVELOPMENT only; no blocked results are read here."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
from backend.phrase import digest
from .bank import FAMILIES,manifest_digest
from .engine import config
from .run_bank import evaluation_digest


def freeze(development_path,output):
    raw=Path(development_path).read_bytes();dev=json.loads(raw)
    if dev['split']!='development' or dev['limited_run'] or dev['wav_cases']!=3264:raise ValueError('Complete development required')
    caps={}
    for family in FAMILIES:
        values={v:dev['groups'][f'family/{family}/{v}']['pause_proxy_metrics']['false_candidates_per_minute_distribution']['p95'] for v in ['energy','multifeature','praat']}
        if any(x is None for x in values.values()):raise ValueError('Missing false-candidate distribution')
        caps[family]={'maximum_blocked_p95_false_candidates_per_minute':min(values.values()),'development_p95_by_variant':values,
            'derivation':'minimum observed development family P95 across all three comparators; no universal burden limit'}
    gate=dict(schema_version='pause_candidate_acceptance_gate_v1',state='frozen_before_blocked',created_utc=datetime.now(timezone.utc).isoformat(),
        runtime=dev['runtime'],development_summary_sha256=digest(raw),development_manifest_sha256=dev['manifest_sha256'],blocked_manifest_sha256=manifest_digest('blocked'),
        evaluation_code_sha256=evaluation_digest(),freeze_code_sha256=digest(Path(__file__).read_bytes()),
        detector_config_sha256={v:config(v)[1] for v in ['energy','multifeature']},
        family_burden_caps=caps,
        technical_criteria={'clean_ge250_recall':1.0,'white_noise_ge20_ge250_recall':.95,'clean_absolute_boundary_median_ms_max':15,'clean_absolute_boundary_p95_ms_max':30,'two_close_gap_ge50_fusions_max':0,'periodic_negative_controls_candidates_max':0,'failed_runs_max':0,'latency_p95_s_max':None},
        latency_note='Concurrent bank timings descriptive only; isolated 20s latency gate remains pending before any UI integration',
        B_incremental_false_candidates_per_minute_max_by_family=2,
        preference_rule='Choose only an eligible engine. If both eligible, B requires >=2 percentage points macro-family region recall gain, <=1pp pause-proxy precision loss, no added fusions and all per-family incremental burden gates. Otherwise prefer A if eligible; if neither eligible choose neither.',
        caution='Synthetic engineering criteria only. Caps may be stringent and do not validate reviewer time savings; no human parameters/results.')
    gate['detector_config_sha256']['praat']=digest((Path(__file__).parents[2]/'configs/pause_detector_praat_v1.json').read_bytes())
    Path(output).write_text(json.dumps(gate,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'gate_sha256':digest(Path(output).read_bytes()),'caps':{k:v['maximum_blocked_p95_false_candidates_per_minute'] for k,v in caps.items()}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--development',required=True);p.add_argument('--output',required=True);a=p.parse_args();freeze(a.development,a.output)
