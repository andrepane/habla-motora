"""Development acceptance must use the frozen publication policy."""
import gzip
import json
import pytest

from reports.prosody.assess import assess


@pytest.mark.parametrize('eligible', [False, True])
def test_acceptance_uses_selected_support_instead_of_runner_default(tmp_path, eligible):
    metrics = dict(core_median_abs_cents=0., core_p95_abs_cents=0.,
                   core_defined_percent=100., p10_abs_error_hz=0.,
                   p90_abs_error_hz=0., p10_truth_hz=200., p90_truth_hz=200.,
                   robust_range_abs_error_st=0., range_published=not eligible,
                   slope_abs_error_st_s=0., slope_truth_st_s=0.,
                   slope_published=True, octave_error_frames=0)
    row = dict(configuration_id='candidate',
               case=dict(case_id='synthetic', family='constant', frequency=200.),
               metrics=metrics,
               support_comparison={'temporal': {'eligible': eligible}})
    with gzip.open(tmp_path / 'results.jsonl.gz', 'wt') as stream:
        stream.write(json.dumps(row) + '\n')
    acceptance = dict(clean_core_median_cents=20., clean_core_p95_cents=50.,
                      clean_core_defined_percent=98., quantile_max_hz_floor=1.,
                      quantile_relative_tolerance=.02, robust_range_st=.2,
                      slope_st_s_floor=.05, slope_relative_tolerance=.05)
    result = assess(tmp_path, dict(selected_configuration_id='candidate',
                                 range_rule={'id': 'temporal'}, acceptance=acceptance))
    assert result['criteria']['robust_range_error']['all_passed'] is eligible
    assert result['criteria']['core_median_abs_cents']['all_passed']
