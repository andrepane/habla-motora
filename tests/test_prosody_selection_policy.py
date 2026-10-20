from reports.prosody.select_eligible_development import rank_eligible


def candidate(name, score, cents=1., context=0.):
    return dict(configuration_id=name, score=score, median_core_cents=cents, context_s=context)


def test_no_eligible_candidate_has_no_fallback():
    assert rank_eligible([candidate('cheap_but_failed', 0.)], set()) is None


def test_ineligible_cheaper_candidate_cannot_win():
    rows = [candidate('cheap_but_failed', 0.), candidate('accepted', 1.)]
    assert rank_eligible(rows, {'accepted'})['configuration_id'] == 'accepted'


def test_original_cost_tolerance_and_tie_break_are_preserved():
    rows = [candidate('best_cost', 1., 2.), candidate('within_tolerance', 1.0005, 1.),
            candidate('outside_tolerance', 1.002, 0.)]
    assert rank_eligible(rows, {r['configuration_id'] for r in rows})['configuration_id'] == 'within_tolerance'
    rows = [candidate('b', 1., context=.25), candidate('a', 1.), candidate('c', 1.)]
    assert rank_eligible(rows, {'a', 'b', 'c'})['configuration_id'] == 'a'


def test_revision_archives_v1_and_preserves_frozen_rules(tmp_path, monkeypatch):
    import json
    from backend.phrase import canonical, digest
    from reports.prosody.select_eligible_development import persist_revision
    monkeypatch.chdir(tmp_path)
    folder = tmp_path/'research/prosody'
    folder.mkdir(parents=True)
    development = tmp_path/'reports/prosody/development'
    development.mkdir(parents=True)
    (tmp_path/'reports/prosody/eligibility_v2').mkdir()
    old = dict(selected_configuration_id='old', profile={'id':'old'}, context_s=0.,
               acceptance={'fixed_threshold':20.}, range_rule={'id':'distributed'},
               jump_limit_s=.01, code_sha256='unchanged')
    raw = canonical(old)+b'\n'
    (folder/'freeze.json').write_bytes(raw)
    selected = dict(candidate('new', 1.), profile={'id':'new'})
    (development/'selection.json').write_text(json.dumps({'ranking':[selected]}))
    decision = dict(selected_configuration_id='new', historical_freeze_sha256=digest(raw),
                    reason='missing eligibility gate')
    revised = persist_revision(decision)
    assert (folder/'freeze_v1.json').read_bytes() == raw
    assert (folder/'freeze.json').read_bytes() == (folder/'freeze_v2.json').read_bytes()
    for key in ['acceptance','range_rule','jump_limit_s','context_s','code_sha256']:
        assert revised[key] == old[key]
    assert revised['selected_configuration_id'] == 'new'
    assert revised['supersedes_freeze_sha256'] == digest(raw)
    assert revised['eligibility_decision_sha256'] == digest((tmp_path/'reports/prosody/eligibility_v2/decision.json').read_bytes())


def test_no_winner_cannot_create_a_freeze(tmp_path, monkeypatch):
    from reports.prosody.select_eligible_development import persist_revision
    monkeypatch.chdir(tmp_path)
    assert persist_revision({'selected_configuration_id':None}) is None
    assert not list(tmp_path.iterdir())


def test_historical_cost_only_selector_cannot_overwrite_freeze(tmp_path, monkeypatch):
    import pytest
    from reports.prosody.select_development import choose
    monkeypatch.chdir(tmp_path)
    folder = tmp_path/'research/prosody'
    folder.mkdir(parents=True)
    frozen = folder/'freeze.json'
    frozen.write_bytes(b'historical evidence')
    with pytest.raises(ValueError, match='superseded'):
        choose('unused')
    assert frozen.read_bytes() == b'historical evidence'
