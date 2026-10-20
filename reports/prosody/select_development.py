"""Predeclared ranking and freeze writer. Consumes development only."""
import gzip
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from backend.phrase import canonical,digest
from research.prosody.run import code_hash
from research.prosody.profiles import JUMP_LIMITS_S


def choose(directory):
    if Path('research/prosody/freeze.json').exists():
        raise ValueError('Historical cost-only selector superseded; use select_eligible_development.py. Never overwrite a freeze with v1 policy.')
    path=Path(directory)
    if json.loads((path/'manifest.json').read_text())['split']!='development':raise ValueError('Development only')
    with gzip.open(path/'results.jsonl.gz','rt') as f:rows=[json.loads(line) for line in f]
    groups=defaultdict(lambda:defaultdict(list))
    for r in rows:
        c=r['case'];m=r['metrics']
        if c['frequency']<55 or c['frequency']>600 or c.get('snr_db',100)<=10:continue
        miss=m['missed_voiced_frames']/m['voiced_reference_frames'] if m['voiced_reference_frames'] else 0
        gross=m['gross_error_frames']/m['compared_frames'] if m['compared_frames'] else 0
        false=m['false_defined_frames']/m['nonperiodic_reference_frames'] if m['nonperiodic_reference_frames'] else 0
        groups[r['configuration_id']][c['family']].append(miss+5*gross+5*false)
    ranking=[]
    for ident,g in groups.items():
        sample=next(r for r in rows if r['configuration_id']==ident)
        errors=[r['metrics']['core_median_abs_cents'] for r in rows if r['configuration_id']==ident and r['metrics']['core_median_abs_cents'] is not None]
        ranking.append(dict(configuration_id=ident,score=float(np.mean([np.mean(v) for v in g.values()])),family_scores={k:float(np.mean(v)) for k,v in g.items()},median_core_cents=float(np.median(errors)),profile=sample['profile'],context_s=sample['context_s']))
    ranking.sort(key=lambda r:(r['score'],r['median_core_cents'],r['context_s'],r['configuration_id']))
    bestscore=ranking[0]['score'];tied=[r for r in ranking if r['score']<=bestscore+.001]
    tied.sort(key=lambda r:(r['median_core_cents'],r['context_s'],r['configuration_id']))
    winner=tied[0];wr=[r for r in rows if r['configuration_id']==winner['configuration_id']]
    rule_scores=[]
    for name in wr[0]['support_comparison']:
        fp=sum(r['support_comparison'][name]['eligible'] and not r['truth']['global_support_expected'] for r in wr)
        tp=sum(r['support_comparison'][name]['eligible'] and r['truth']['global_support_expected'] for r in wr)
        rule_scores.append(dict(id=name,false_publications=fp,true_publications=tp,rule=wr[0]['support_comparison'][name]['rule']))
    rule_scores.sort(key=lambda r:(r['false_publications'],-r['true_publications'],r['id']))
    experiment=json.loads((path/'temporal_policy.json').read_text())
    jump_scores=[]
    for limit in JUMP_LIMITS_S:
        controls=[r for r in experiment if r['jump_limit_s']==limit]
        jump_scores.append(dict(limit_s=limit,true_warnings=sum(r['warning'] and r['positive_policy_control'] for r in controls),false_long_gap_warnings=sum(r['warning'] and r['negative_policy_control'] for r in controls)))
    jump_scores.sort(key=lambda r:(r['false_long_gap_warnings'],-r['true_warnings'],r['limit_s']))
    acceptance=dict(clean_core_median_cents=20.,clean_core_p95_cents=50.,clean_core_defined_percent=98.,constant_octave_error_frames=0,
                    quantile_max_hz_floor=1.,quantile_relative_tolerance=.02,robust_range_st=.2,slope_st_s_floor=.05,slope_relative_tolerance=.05,
                    silence_false_defined_percent=2.,noise20_median_cents=50.,noise20_coverage_loss_pp=10.,long_gap_recall=.95,gap_boundary_window_factor=3.)
    freeze=dict(schema_version='phrase_prosody_freeze_v1',selected_configuration_id=winner['configuration_id'],profile=winner['profile'],context_s=winner['context_s'],
                range_rule=rule_scores[0]['rule'],jump_limit_s=jump_scores[0]['limit_s'],acceptance=acceptance,code_sha256=code_hash(),
                module_sha256=digest(Path('backend/phrase_prosody.py').read_bytes()),assessment_sha256=digest(Path('reports/prosody/assess.py').read_bytes()),development_manifest_sha256=digest((path/'manifest.json').read_bytes()),development_results_sha256=digest((path/'results.jsonl.gz').read_bytes()),
                selection_policy='predeclared_macro_family_cost_then_core_cents_within_0.001',validation='technical_only_human_validity_pending')
    report=dict(ranking=ranking,selected=winner,range_rules=rule_scores,jump_limits=jump_scores)
    (path/'selection.json').write_bytes(canonical(report))
    (Path('research/prosody')/'freeze.json').write_bytes(canonical(freeze)+b'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    import sys
    choose(sys.argv[1])
