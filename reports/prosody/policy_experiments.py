"""Controlled temporal-warning policy comparisons; not phonetic classification truth."""
from pathlib import Path
from backend.phrase import canonical
from research.prosody.profiles import PROFILES,RANGE_RULES,JUMP_LIMITS_S
from research.prosody.engine import summarize

rows=[]
for dt in [.005,.010,.015,.020,.025,.050,.100,.250,.500]:
    for sign in [-1,1]:
        n=round(dt/.005)
        fs=[dict(frame_index=i+1,time_relative_s=i*.005,time_absolute_s=i*.005,sample_position_float=i*240,f0_hz=(200. if i==0 else 200*2**sign if i==n else None),defined=i in [0,n]) for i in range(n+1)]
        native=dict(f0_mean_hz=200.,f0_median_hz=200.,f0_sd_hz=0.,f0_sd_st=0.,p10_hz=200.,p90_hz=200.,f0_min_hz=100.,f0_max_hz=400.)
        for limit in JUMP_LIMITS_S:
            out=summarize(dict(frames=fs,native=native,profile=PROFILES[3]),dict(start_sample=0,end_sample_exclusive=48000),48000,RANGE_RULES[0],limit)
            rows.append(dict(delta_t_s=dt,direction=sign,jump_limit_s=limit,warning=any(w['code']=='POSSIBLE_OCTAVE_JUMP' for w in out['warnings']),evidence=out['transitions'],positive_policy_control=dt in [.005,.010],negative_policy_control=dt>=.025))
Path('reports/prosody/development/temporal_policy.json').write_bytes(canonical(rows))
