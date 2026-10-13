"""Repeatable observations; criteria are fixed independently of observed native HNR."""
import statistics
from backend.hnr import analyze_hnr
from tests.synthetic_hnr import make_wav,SEEDS,SNR_LEVELS,fixed_lag_reference


def observation(data,metadata):
    result=analyze_hnr(data)
    q=result['quality']
    return {'source':metadata,'hnr_mean_db':result['acoustic']['hnr_mean_db']['value'],
            'total_frames':q['hnr_total_frames'],'valid_frames':q['hnr_valid_frames'],
            'excluded_frames':q['hnr_excluded_frames'],'coverage_percent':q['hnr_coverage_percent']['value'],
            'grid':q['hnr_object_grid'],'amplitude_diagnostics':q['amplitude_diagnostics'],
            'digital_rail_samples_full_file':q['digital_rail_samples_full_file'],
            'warnings':q['technical_warnings'],'provenance':result['provenance']}


def noise_ensemble():
    levels={}
    for snr in SNR_LEVELS:
        runs=[]
        for seed in SEEDS:
            data,metadata=make_wav(snr_db=snr,seed=seed)
            runs.append(observation(data,metadata))
        means=[r['hnr_mean_db'] for r in runs]
        complete=all(v is not None for v in means)
        data,_=make_wav(snr_db=snr,seed=SEEDS[0])
        levels[str(snr)]={'runs':runs,'all_realizations_defined':complete,
                          'mean_hnr_db':statistics.mean(means) if complete else None,
                          'sd_between_realizations_db':statistics.stdev(means) if complete else None,
                          'min_hnr_db':min(means) if complete else None,'max_hnr_db':max(means) if complete else None,
                          'min_coverage_percent':min(r['coverage_percent'] for r in runs),
                          'max_coverage_percent':max(r['coverage_percent'] for r in runs),
                          'known_lag_reference_seed_5000':fixed_lag_reference(data)}
    return levels
