"""Predeclared development candidates; no speaker-dependent auto-tuning."""
BASE = dict(hop_s=.005, floor_hz=50., top_hz=800., candidates=15,
            very_accurate=False, silence=.03, voicing=.45, octave_cost=.01,
            jump_cost=.35, vu_cost=.14, attenuation=.03)
PROFILES = [dict(BASE, id='current_cc', method='raw cross-correlation', floor_hz=75., top_hz=600.),
            dict(BASE, id='wide_cc', method='raw cross-correlation'),
            dict(BASE, id='wide_ac', method='raw autocorrelation')]
for top in (800.,1200.):
    for silence in (.03,.09):
        PROFILES.append(dict(BASE,id=f'filtered_{int(top)}_{int(silence*100):02d}',
                             method='filtered autocorrelation',top_hz=top,silence=silence,
                             voicing=.50,octave_cost=.055))
CONTEXTS = [0., .25]
RANGE_RULES = [dict(id='frames_only',minimum_n=20,minimum_span_s=0.,minimum_span_fraction=0.,minimum_coverage=0.,minimum_bins=0),
               dict(id='temporal',minimum_n=30,minimum_span_s=.5,minimum_span_fraction=.6,minimum_coverage=.3,minimum_bins=3),
               dict(id='distributed',minimum_n=50,minimum_span_s=1.,minimum_span_fraction=.7,minimum_coverage=.5,minimum_bins=4)]
JUMP_LIMITS_S = [.010,.020,.050]
