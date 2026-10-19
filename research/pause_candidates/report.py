"""Publish complete split/condition comparisons and adjudicate the frozen gate."""
import argparse
import csv
import gzip
import json
from pathlib import Path
from collections import defaultdict
import numpy as np
from .run_bank import aggregate
from .bank import FAMILIES
from backend.phrase import digest


def read_rows(path):
    with gzip.open(path,'rt') as f:return [json.loads(line) for line in f]


def flat_summary(rows):
    out=[]
    for r in rows:
        c=r['case'];x={**c,'variant':r['variant'],'status':r['status'],'latency_s':r['latency_s'],'edge_candidates':r['edge_candidate_count']}
        for kind in ['region_metrics','pause_proxy_metrics','region_metrics_iou50']:
            m=r[kind]
            if m:
                for k in ['tp','fp','fn','recall','precision','false_candidates_per_minute','fusion_count','fragmentation_count','omissions']:x[f'{kind}.{k}']=m[k]
                for k in ['iou','start_error_ms','end_error_ms']:x[f'{kind}.{k}']=json.dumps(m[k])
        out.append(x)
    return out


def csv_write(path,rows):
    keys=sorted({k for r in rows for k in r})
    opener=gzip.open if str(path).endswith('.gz') else open
    with opener(path,'wt',newline='') as f:
        w=csv.DictWriter(f,keys);w.writeheader();w.writerows(rows)


def eligible(rows,variant,gate):
    subset=[r for r in rows if r['variant']==variant];criteria=gate['technical_criteria'];checks={}
    def metric(filter_fn):return aggregate([r for r in subset if filter_fn(r['case'])])['region_metrics']
    clean=metric(lambda c:c['family']=='clean' and c['duration_ms']>=250)
    noise=metric(lambda c:c['family'] in ['noise_20','noise_30'] and c['duration_ms']>=250)
    close=metric(lambda c:c['family']=='two_close' and c['gap_between_s']>=.05)
    checks['clean_ge250_recall']=clean['recall']==criteria['clean_ge250_recall']
    checks['white_noise_ge20_ge250_recall']=noise['recall'] is not None and noise['recall']>=criteria['white_noise_ge20_ge250_recall']
    for edge in ['start','end']:
        errors=clean[f'absolute_{edge}_error_ms']
        checks[f'clean_{edge}_median']=errors['p50'] is not None and errors['p50']<=criteria['clean_absolute_boundary_median_ms_max']
        checks[f'clean_{edge}_p95']=errors['p95'] is not None and errors['p95']<=criteria['clean_absolute_boundary_p95_ms_max']
    checks['two_close_gap_ge50_fusions']=close['fusion_count']<=criteria['two_close_gap_ge50_fusions_max']
    checks['periodic_negative_control_candidates']=sum(len(r['response']['automatic_candidates'] or []) for r in subset if r['case']['family']=='no_pause')<=criteria['periodic_negative_controls_candidates_max']
    checks['failed_runs']=sum(r['status']=='failed' for r in subset)<=criteria['failed_runs_max']
    burden={}
    for family in FAMILIES:
        observed=aggregate([r for r in subset if r['case']['family']==family])['pause_proxy_metrics']['false_candidates_per_minute_distribution']['p95']
        ceiling=gate['family_burden_caps'][family]['maximum_blocked_p95_false_candidates_per_minute']
        checks[f'burden:{family}']=observed is not None and observed<=ceiling+1e-9
        burden[family]={'observed_p95':observed,'frozen_cap':ceiling}
    return {'eligible':all(checks.values()),'checks':checks,'failed_checks':[k for k,v in checks.items() if not v], 'burden':burden}


def compare(rows,gate):
    bycase=defaultdict(dict)
    for r in rows:bycase[r['case']['case_id']][r['variant']]=r
    deltas=[]
    for key,g in bycase.items():
        if set(g)!={'energy','multifeature','praat'}:raise ValueError('Incomplete paired comparison')
        a,b=g['energy'],g['multifeature'];abounds={(c['start_sample'],c['end_sample_exclusive']) for c in a['response']['automatic_candidates'] or []}
        added=[c for c in b['response']['automatic_candidates'] or [] if (c['start_sample'],c['end_sample_exclusive']) not in abounds]
        row={'case_id':key,'family':a['case']['family'],'duration_ms':a['case']['duration_ms'],'B_added_candidates':len(added)}
        for kind in ['region_metrics','pause_proxy_metrics']:
            for metric in ['tp','fp','fn','fusion_count','fragmentation_count']:
                row[f'delta_{kind}_{metric}']=None if a[kind] is None or b[kind] is None else b[kind][metric]-a[kind][metric]
        row['B_added_candidate_ids']=';'.join(c['candidate_id'] for c in added);deltas.append(row)
    family=[]
    for f in FAMILIES:
        d=[r for r in deltas if r['family']==f];a=aggregate([r for r in rows if r['variant']=='energy' and r['case']['family']==f]);b=aggregate([r for r in rows if r['variant']=='multifeature' and r['case']['family']==f])
        family.append({'family':f,'B_added_candidates':sum(r['B_added_candidates'] for r in d),
            'delta_region_tp':sum(r['delta_region_metrics_tp'] or 0 for r in d),
            'delta_pause_proxy_fp':sum(r['delta_pause_proxy_metrics_fp'] or 0 for r in d),
            'delta_fusions':b['region_metrics']['fusion_count']-a['region_metrics']['fusion_count'],
            'delta_fragmentations':b['region_metrics']['fragmentation_count']-a['region_metrics']['fragmentation_count'],
            'incremental_false_candidates_per_minute':b['pause_proxy_metrics']['false_candidates_per_minute']-a['pause_proxy_metrics']['false_candidates_per_minute']})
    eligibility={v:eligible(rows,v,gate) for v in ['energy','multifeature','praat']}
    macros={}
    overall={v:aggregate([r for r in rows if r['variant']==v]) for v in ['energy','multifeature','praat']}
    for v in ['energy','multifeature','praat']:
        values=[aggregate([r for r in rows if r['variant']==v and r['case']['family']==f])['region_metrics']['recall'] for f in FAMILIES]
        macros[v]=float(np.mean([v for v in values if v is not None]))
    b_gain=macros['multifeature']-macros['energy']
    precision_change=overall['multifeature']['pause_proxy_metrics']['precision']-overall['energy']['pause_proxy_metrics']['precision']
    B_checks={'macro_recall_gain_ge2pp':b_gain>=.02,'precision_loss_le1pp':precision_change>=-.01,
        'no_extra_fusions':overall['multifeature']['region_metrics']['fusion_count']<=overall['energy']['region_metrics']['fusion_count'],
        'incremental_burden_le2_each_family':all(r['incremental_false_candidates_per_minute']<=gate['B_incremental_false_candidates_per_minute_max_by_family']+1e-9 for r in family)}
    eligibility['multifeature']['checks']['incremental_burden_le2_each_family']=B_checks['incremental_burden_le2_each_family']
    if not B_checks['incremental_burden_le2_each_family']:
        eligibility['multifeature']['eligible']=False
        eligibility['multifeature']['failed_checks'].append('incremental_burden_le2_each_family')
    Aok=eligibility['energy']['eligible'];Bok=eligibility['multifeature']['eligible']
    # Comparator is never selected as a production detector.
    choice='multifeature' if Bok and (not Aok or all(B_checks.values())) else 'energy' if Aok else 'neither'
    return dict(choice=choice,scope='blocked synthetic engineering comparison only; no UI activation or human validation',eligibility=eligibility,B_preference_checks=B_checks,macro_family_recall=macros,B_macro_recall_change=b_gain,B_precision_change=precision_change,family_deltas=family,overall=overall),deltas


def publish(folder):
    root=Path(folder);gate=json.loads((root/'frozen-gate.json').read_text());blocked=json.loads((root/'blocked-summary.json').read_text())
    if blocked['frozen_gate_sha256']!=digest((root/'frozen-gate.json').read_bytes()):raise ValueError('Not the frozen gate')
    if blocked['limited_run'] or blocked['wav_cases']!=3264:raise ValueError('Complete blocked results required')
    rows=read_rows(root/'blocked-cases.jsonl.gz');decision,deltas=compare(rows,gate)
    (root/'decision.json').write_text(json.dumps(decision,indent=2,allow_nan=False)+'\n')
    csv_write(root/'blocked-per-case.csv.gz',flat_summary(rows));csv_write(root/'B-delta-per-case.csv.gz',deltas);csv_write(root/'B-delta-per-family.csv',decision['family_deltas'])
    for split in ['development','blocked']:
        summary=json.loads((root/f'{split}-summary.json').read_text());familyrows=[];conditionrows=[]
        for key,g in summary['groups'].items():
            if not key.startswith(('family/','condition/')):continue
            row={'group':key,'cases':g['cases'],'completed':g['statuses']['completed'],'failed':g['statuses']['failed'],'not_evaluable':g['statuses']['not_evaluable'],'latency_s.p50':g['latency_s']['p50'],'latency_s.p95':g['latency_s']['p95']}
            for kind in ['region_metrics','pause_proxy_metrics','region_metrics_iou50']:
                for k,value in g[kind].items():
                    if isinstance(value,dict):
                        for sub,val in value.items():row[f'{kind}.{k}.{sub}']=val
                    else:row[f'{kind}.{k}']=value
            (familyrows if key.startswith('family/') else conditionrows).append(row)
        csv_write(root/f'{split}-per-family.csv',familyrows);csv_write(root/f'{split}-per-condition.csv.gz',conditionrows)
    return decision


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--folder',default='reports/pause_candidates');a=p.parse_args();d=publish(a.folder);print(json.dumps({'choice':d['choice'],'failed_checks':{v:d['eligibility'][v]['failed_checks'] for v in d['eligibility']},'B_checks':d['B_preference_checks']}))
