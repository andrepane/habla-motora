"""Orchestration only. Acoustic modules and their output remain unchanged."""
import hashlib
import math
import io
import wave
from backend.shimmer import analyze_shimmer
from backend.hnr import analyze_hnr
from backend.praat_runner import AnalysisError, MAX_BYTES


def analyze_vowel(data, emission_start_s=0.0, emission_end_s=None):
    if not math.isfinite(emission_start_s) or emission_start_s < 0:
        raise ValueError('Invalid emission interval')
    if emission_end_s is not None and (not math.isfinite(emission_end_s) or emission_end_s-emission_start_s < 3):
        raise ValueError('Selected emission must contain at least 3 seconds')
    # Input validation only; duration reported to the user still comes from Praat.
    if not data or len(data) > MAX_BYTES:
        raise ValueError('WAV must contain 1 byte to 10 MiB')
    try:
        with wave.open(io.BytesIO(data), 'rb') as wav:
            if (wav.getnchannels() != 1 or wav.getsampwidth() not in (2, 3, 4)
                    or wav.getframerate() not in (44100, 48000)
                    or wav.getcomptype() != 'NONE' or wav.getnframes() == 0):
                raise ValueError('Expected nonempty mono PCM WAV, 16/24/32-bit, 44100/48000 Hz')
            duration = wav.getnframes() / wav.getframerate()
    except (wave.Error, EOFError) as exc:
        raise ValueError('Invalid PCM WAV') from exc
    end = duration if emission_end_s is None else emission_end_s
    if not 0 <= emission_start_s < end <= duration or end-emission_start_s < 3:
        raise ValueError('Selected emission must contain at least 3 seconds within the WAV')
    # The duration smoke script formats to 12 decimal places. For a selection
    # ending at the WAV boundary, let each unchanged module use its own native
    # duration instead of passing a sample-derived boundary a fraction of a
    # picosecond beyond it. No extra analysis or audio conversion is performed.
    native_file_end = math.isclose(end, duration, rel_tol=0, abs_tol=1e-12)
    effective_end = None if native_file_end else emission_end_s
    modules = {}
    for name, analyze in (('shimmer', analyze_shimmer), ('hnr', analyze_hnr)):
        try:
            result = analyze(data, emission_start_s, effective_end)
            modules[name] = {'status': 'completed', 'result': result, 'error': None}
        except (AnalysisError, ValueError) as exc:
            modules[name] = {'status': 'failed', 'result': None,
                             'error': {'code': 'ANALYSIS_FAILED', 'message': str(exc)}}
        except Exception:
            modules[name] = {'status': 'failed', 'result': None,
                             'error': {'code': 'INTERNAL_MODULE_ERROR',
                                       'message': 'El módulo no pudo completar el análisis.'}}
    successes = [m['result'] for m in modules.values() if m['status'] == 'completed']
    if not successes:
        raise AnalysisError('Both acoustic modules failed')
    expected_hash = hashlib.sha256(data).hexdigest()
    for result in successes:
        if result['provenance']['file_sha256'] != expected_hash:
            raise AnalysisError('WAV hash mismatch; combined result rejected')
    fields = ('configuration_sha256', 'configuration_version', 'protocol_version', 'praat_version')
    first = successes[0]
    for result in successes[1:]:
        if (any(result['provenance'][key] != first['provenance'][key] for key in fields)
                or result['analysis_interval'] != first['analysis_interval']):
            raise AnalysisError('Configuration or analysis interval mismatch; combined result rejected')
    return {'schema_version': 'vowel_analysis_v1',
            'status': 'completed' if len(successes) == 2 else 'partial',
            'input': {'file_sha256': expected_hash, 'emission_start_s': emission_start_s,
                      'emission_end_s': emission_end_s,
                      'effective_emission_end_s': effective_end,
                      'end_selection': 'native_file_end' if native_file_end else 'explicit_limit'},
            'integrity': {'wav_hash_verified': True, 'cross_module_verified': len(successes) == 2},
            'analysis_interval': first['analysis_interval'], 'modules': modules}
