"""Selection policy v2: frozen acceptance first, unchanged cost/tie-break second.

Consumes persisted development only. Never runs acoustic extraction or holdout.
The v1 freeze and all v1 results remain immutable historical evidence.
"""
import copy
import json
import tempfile
from pathlib import Path

from backend.phrase import canonical, digest
from reports.prosody.assess import assess

PRIOR_COMMIT = '89d2bb645fcb3d62e9a217e3ecf2357aed096016'


def rank_eligible(ranking, eligible_ids):
    candidates = [r for r in ranking if r['configuration_id'] in eligible_ids]
    if not candidates:
        return None
    best = min(r['score'] for r in candidates)
    tied = [r for r in candidates if r['score'] <= best + .001]
    return min(tied, key=lambda r: (r['median_core_cents'], r['context_s'], r['configuration_id']))


def review(directory='reports/prosody/development', output='reports/prosody/eligibility_v2'):
    source = Path(directory).resolve()
    target = Path(output)
    historical = Path('research/prosody/freeze_v1.json')
    freeze_path = historical if historical.exists() else Path('research/prosody/freeze.json')
    freeze_bytes = freeze_path.read_bytes()
    frozen = json.loads(freeze_bytes)
    meta = json.loads((source / 'manifest.json').read_text())
    if meta['split'] != 'development' or meta['limited'] or meta['cases'] != 450:
        raise ValueError('Complete persisted development only')
    for key, path in [('development_manifest_sha256', source/'manifest.json'),
                      ('development_results_sha256', source/'results.jsonl.gz'),
                      ('assessment_sha256', Path('reports/prosody/assess.py'))]:
        if digest(path.read_bytes()) != frozen[key]:
            raise ValueError(f'Frozen source mismatch: {key}')
    ranking_path = source/'selection.json'
    ranking = json.loads(ranking_path.read_text())['ranking']
    if len(ranking) != 14 or len({r['configuration_id'] for r in ranking}) != 14:
        raise ValueError('Expected all fourteen original candidates')
    cases = {c['case_id']: c for c in json.loads((source/'cases.json').read_text())}
    fundamental = {k for k,c in cases.items() if
                   c['family'] in {'constant', 'duration'} and 55 <= c['frequency'] <= 600}
    target.mkdir(parents=True, exist_ok=True)
    results = []
    # Reuse the exact frozen assessor. Its acceptance.json output is confined to a
    # temporary directory, so no historical report or freeze can be overwritten.
    with tempfile.TemporaryDirectory(prefix='prosody-eligibility-') as tmp:
        temporary = Path(tmp)
        (temporary/'results.jsonl.gz').symlink_to(source/'results.jsonl.gz')
        for candidate in ranking:
            config = copy.deepcopy(frozen)
            config['selected_configuration_id'] = candidate['configuration_id']
            assessment = assess(temporary, config)
            if not assessment['criteria'] or any(v['total'] == 0 for v in assessment['criteria'].values()):
                raise ValueError('Empty acceptance cannot establish eligibility')
            failures = {}
            fundamental_failures = []
            for criterion, result in assessment['criteria'].items():
                if result['all_passed']:
                    continue
                detailed = [dict(f, case=cases[f['case_id']]) for f in result['failures']]
                failures[criterion] = dict(failed=len(detailed), total=result['total'], cases=detailed)
                fundamental_failures.extend(dict(criterion=criterion, **f) for f in detailed
                                            if f['case_id'] in fundamental)
            assessment['failed_criteria_detailed'] = failures
            (target/f"{candidate['configuration_id']}.json").write_bytes(canonical(assessment)+b'\n')
            results.append(dict(configuration_id=candidate['configuration_id'],
                                eligible=assessment['all_passed'], score=candidate['score'],
                                median_core_cents=candidate['median_core_cents'],
                                context_s=candidate['context_s'],
                                failed_criteria={k:dict(failed=v['failed'],total=v['total']) for k,v in failures.items()},
                                fundamental_controls_passed=not fundamental_failures,
                                fundamental_failures=fundamental_failures,
                                failed_families=sorted({f['case']['family'] for v in failures.values() for f in v['cases']})))
            print(candidate['configuration_id'], 'eligible' if assessment['all_passed'] else 'ineligible', flush=True)
    winner = rank_eligible(ranking, {r['configuration_id'] for r in results if r['eligible']})
    decision = dict(schema_version='phrase_prosody_selection_policy_v2',
                    historical_freeze_commit=PRIOR_COMMIT, historical_freeze_sha256=digest(freeze_bytes),
                    reason='v1 ranked cost without the mandatory frozen acceptance eligibility gate',
                    scope='persisted_development_only', blocked_executed=False, human_wav_used=False,
                    acceptance=frozen['acceptance'], range_rule=frozen['range_rule'],
                    jump_limit_s=frozen['jump_limit_s'], historical_context_s=frozen['context_s'],
                    development_results_sha256=frozen['development_results_sha256'],
                    assessment_sha256=frozen['assessment_sha256'], ranking_sha256=digest(ranking_path.read_bytes()),
                    policy_sha256=digest(Path(__file__).read_bytes()),
                    fundamental_description='All frozen checks on in-scope constants 55–600 Hz and duration controls; descriptive subgroup only, never a replacement for full eligibility.',
                    candidates=results, eligible_count=sum(r['eligible'] for r in results),
                    selected_configuration_id=winner['configuration_id'] if winner else None,
                    status='eligible_candidate_requires_versioned_freeze' if winner else 'no_eligible_configuration',
                    prior_decision_status='historical_only_not_approved_for_blocked')
    (target/'decision.json').write_bytes(canonical(decision)+b'\n')
    assert freeze_path.read_bytes() == freeze_bytes
    return decision


def persist_revision(decision):
    """Archive exact v1 bytes and explicitly supersede its selection before holdout."""
    if decision['selected_configuration_id'] is None:
        return None
    folder = Path('research/prosody')
    if (folder/'freeze_v2.json').exists():
        raise ValueError('Version 2 already exists; never overwrite a persisted freeze')
    old = (folder/'freeze.json').read_bytes()
    if digest(old) != decision['historical_freeze_sha256']:
        raise ValueError('Active freeze differs from reviewed v1')
    prior = json.loads(old)
    ranking = json.loads(Path('reports/prosody/development/selection.json').read_text())['ranking']
    selected = next(r for r in ranking if r['configuration_id'] == decision['selected_configuration_id'])
    if selected['context_s'] != prior['context_s']:
        raise ValueError('Changing the frozen border strategy is not authorized')
    revised = copy.deepcopy(prior)
    revised.update(schema_version='phrase_prosody_freeze_v2',
                   selected_configuration_id=selected['configuration_id'], profile=selected['profile'],
                   selection_policy='frozen_acceptance_eligibility_then_original_cost_and_tie_break',
                   supersedes_commit=PRIOR_COMMIT, supersedes_freeze_sha256=digest(old),
                   revision_reason=decision['reason'], revision_timing='before_any_blocked_execution',
                   selection_script_sha256=digest(Path(__file__).read_bytes()))
    decision.update(status='revised_freeze_persisted',
                    prior_decision_status='superseded_before_blocked_for_selection_policy_defect',
                    revised_freeze_path='research/prosody/freeze_v2.json')
    decision_path = Path('reports/prosody/eligibility_v2/decision.json')
    decision_path.write_bytes(canonical(decision)+b'\n')
    revised['eligibility_decision_sha256'] = digest(decision_path.read_bytes())
    raw = canonical(revised)+b'\n'
    (folder/'freeze_v1.json').write_bytes(old)
    (folder/'freeze_v2.json').write_bytes(raw)
    (folder/'freeze.json').write_bytes(raw)
    return revised


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    decision = review()
    if args.freeze:
        persist_revision(decision)
    print(json.dumps(decision, indent=2))
