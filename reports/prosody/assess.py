"""Frozen per-case acceptance. Failing criteria remain failures, no post-held-out tuning."""
import gzip
import json
from pathlib import Path
from collections import defaultdict
from backend.phrase import canonical

CLEAN={'constant','duration','linear_st','linear_hz','sinusoidal','step'}


def assess(directory,freeze):
    p=Path(directory)
    with gzip.open(p/'results.jsonl.gz','rt') as f:rows=[json.loads(l) for l in f]
    selected=[r for r in rows if r['configuration_id']==freeze['selected_configuration_id']]
    a=freeze['acceptance'];checks=defaultdict(list)
    def check(name,ok,r,value):checks[name].append(dict(passed=bool(ok),case_id=r['case']['case_id'],value=value))
    for r in selected:
        c=r['case'];m=r['metrics'];clean=c['family'] in CLEAN and 55<=c['frequency']<=600
        if clean:
            for key,limit in [('core_median_abs_cents',a['clean_core_median_cents']),('core_p95_abs_cents',a['clean_core_p95_cents'])]:
                v=m[key];check(key,v is not None and v<=limit,r,v)
            v=m['core_defined_percent'];check('clean_core_defined_percent',v is not None and v>=a['clean_core_defined_percent'],r,v)
            for q in ['p10','p90']:
                v=m[q+'_abs_error_hz'];truth=m[q+'_truth_hz'];limit=max(a['quantile_max_hz_floor'],a['quantile_relative_tolerance']*truth)
                check(q+'_error',v is not None and v<=limit,r,v)
            # Development rows carry all candidate support rules, while the runner's
            # primary summary uses rules[0]. Assess the frozen publication policy.
            support=r['support_comparison'][freeze['range_rule']['id']]
            v=m['robust_range_abs_error_st'];check('robust_range_error',support['eligible'] and v is not None and v<=a['robust_range_st'],r,v)
            v=m['slope_abs_error_st_s'];limit=max(a['slope_st_s_floor'],a['slope_relative_tolerance']*abs(m['slope_truth_st_s']))
            check('slope_error',m['slope_published'] and v is not None and v<=limit,r,v)
            if c['family'] in ['constant','duration']:check('constant_octave_error',m['octave_error_frames']==0,r,m['octave_error_frames'])
        if c['family'] in ['silence','aperiodic']:
            v=100*m['false_defined_frames']/m['nonperiodic_reference_frames'];check('nonperiodic_false_defined_percent',v<=a['silence_false_defined_percent'],r,v)
        if c['family']=='noise' and c['snr_db']==20:
            v=m['f0_median_abs_cents'];check('noise20_median_cents',v is not None and v<=a['noise20_median_cents'],r,v)
            ref=next(x for x in selected if x['case']['family']=='constant' and x['case']['frequency']==c['frequency'] and x['case']['rate']==c['rate'] and x['case']['bits']==c['bits'])
            loss=ref['metrics']['coverage_percent']-m['coverage_percent'];check('noise20_coverage_loss_pp',loss<=a['noise20_coverage_loss_pp'],r,loss)
        if c['family']=='gap' and c['gap']>=.5:
            v=m['gap_matched_count']/m['gap_reference_count'];check('long_gap_recall',v>=a['long_gap_recall'],r,v)
            for name in ['gap_start_abs_error_s','gap_end_abs_error_s']:
                v=m[name];check(name,v is not None and v<=a['gap_boundary_window_factor']/r['profile']['floor_hz'],r,v)
    result={k:dict(passed=sum(v['passed'] for v in vs),total=len(vs),failures=[v for v in vs if not v['passed']],all_passed=all(v['passed'] for v in vs)) for k,vs in checks.items()}
    report=dict(configuration_id=freeze['selected_configuration_id'],all_passed=all(v['all_passed'] for v in result.values()),criteria=result)
    (p/'acceptance.json').write_bytes(canonical(report));return report

if __name__=='__main__':
    import sys
    freeze=json.loads(Path('research/prosody/freeze.json').read_text());print(json.dumps(assess(sys.argv[1],freeze),indent=2))
