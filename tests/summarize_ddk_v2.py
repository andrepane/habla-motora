"""Summarize frozen per-condition comparison without retuning the detector."""
import argparse,json,gzip
from pathlib import Path


def summarize(report):
    rows=report['rows']
    families={}
    for family in sorted({r['family'] for r in rows}):
        rr=[r for r in rows if r['family']==family]
        block={'conditions':len(rr),'reference_count':sum(r.get('reference_count',len(r['reference_s'] or [])) for r in rr)}
        for version in ['v1','v2']:
            errors=[r[version]['max_error_ms'] for r in rr if r[version]['max_error_ms'] is not None]
            block[version]={'count':sum(r[version]['count'] for r in rr),'extra':sum(r[version]['extra'] for r in rr),'missed':sum(r[version]['missed'] for r in rr),'max_error_ms':max(errors) if errors else None}
        block['conditions_more_extra_v2']=sum(r['v2']['extra']>r['v1']['extra'] for r in rr)
        block['conditions_more_missed_v2']=sum(r['v2']['missed']>r['v1']['missed'] for r in rr)
        families[family]=block
    clean=[r for r in rows if r['family']=='clean']
    char=[r for r in rows if r['family']=='characterization']
    controls=[r for r in rows if r['family'] in ('independent','weak_strong')]
    compound=[r for r in rows if r['family']=='compound']
    gates={
        'clean_all_882_recovered_without_extras_10ms':len(clean)==36 and families['clean']['reference_count']==882 and all(r['v2']['extra']==r['v2']['missed']==0 and r['v2']['max_error_ms']<=10 for r in clean),
        'existing_characterization_no_new_losses_or_extras':len(char)==14 and all(r['v2']['extra']<=r['v1']['extra'] and r['v2']['missed']<=r['v1']['missed'] for r in char),
        'compound_strict_reduction_of_additional_candidates':families['compound']['v2']['extra']<families['compound']['v1']['extra'],
        'compound_no_new_omissions_or_per_condition_extras':len(compound)==2592 and all(r['v2']['extra']<=r['v1']['extra'] and r['v2']['missed']<=r['v1']['missed'] for r in compound),
        'independent_controls_no_new_losses_or_extras':len(controls)==72 and all(r['v2']['extra']<=r['v1']['extra'] and r['v2']['missed']<=r['v1']['missed'] for r in controls),
        'matched_characterization_and_controls_within_20ms':all(r['v2']['max_error_ms'] is None or r['v2']['max_error_ms']<=20 for r in rows),
    }
    regressions=[{'family':r['family'],'parameters':r['parameters'],'v1':r['v1'],'v2':r['v2']} for r in rows if r['v2']['extra']>r['v1']['extra'] or r['v2']['missed']>r['v1']['missed']]
    return {'families':families,'numerical_gates':gates,'all_numerical_gates_pass':all(gates.values()),'regressions':regressions,'characterization_cases':char,'human':report['human']['comparison'] if report.get('human') else None,'note':'Extras are additional candidates; omissions are not automatically proven fusions. Human event-level truth is unavailable. Numerical gates do not constitute clinical validation.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('report');p.add_argument('output');a=p.parse_args()
    raw=gzip.decompress(Path(a.report).read_bytes()).decode() if a.report.endswith('.gz') else Path(a.report).read_text()
    summary=summarize(json.loads(raw));Path(a.output).write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='regressions'},indent=2));print('regressions',len(summary['regressions']))
