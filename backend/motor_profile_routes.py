"""Identity and static page only. Never invokes an analysis module."""
import hashlib
import json
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parents[1]
router = APIRouter()


def fingerprint(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def protocol():
    sources = {}
    def spec(kind, schema, checks):
        sources[kind] = dict(schema_version=schema, checks=checks)
    def check(pointer, value, when=None):
        return dict(pointer=pointer, value=value, **({'when': when} if when else {}))
    vocal = []
    for name in ('shimmer', 'hnr'):
        base = f'/modules/{name}/result'
        vocal.extend([check(base+'/provenance/configuration_sha256', fingerprint('configs/experimental_v1.json'), base),
                      check(base+'/provenance/script_sha256', fingerprint(f'praat/{name}_v1.praat'), base),
                      check(base+'/provenance/module_version', name+'_v1', base),
                      check(base+'/provenance/praat_version', '6.4.27', base)])
    for key, script in [('pitch_script_sha256', 'pitch'), ('jitter_script_sha256', 'jitter')]:
        vocal.append(check('/modules/shimmer/result/provenance/'+key, fingerprint(f'praat/{script}_v1.praat'), '/modules/shimmer/result'))
    spec('vowel', 'vowel_analysis_v1', vocal)
    spec('ddk', 'ddk_output_v1', [
        check('/provenance/configuration_sha256', fingerprint('configs/ddk_experimental_v1.json')),
        check('/provenance/detector_sha256', fingerprint('backend/ddk.py')),
        check('/provenance/module_version', 'ddk_v1')])
    spec('phrase', 'phrase_output_v1', [
        check('/provenance/config_sha256', fingerprint('configs/phrase_7a_v1.json')),
        check('/provenance/engine_sha256', fingerprint('backend/phrase.py')),
        check('/protocol_version', 'phrase_7a_v1')])
    spec('pauses', 'phrase_pause_output_v1', [
        check('/provenance/config_sha256', fingerprint('configs/phrase_pause_review_v1.json')),
        check('/provenance/engine_sha256', fingerprint('backend/phrase_pauses.py')),
        check('/protocol_version', 'phrase_pause_review_v1')])
    spec('candidates', 'phrase_candidate_execution_v1', [
        check('/dependencies/config_sha256', fingerprint('configs/pause_detector_energy_v1.json')),
        check('/dependencies/engine_sha256', fingerprint('research/pause_candidates/engine.py')),
        check('/detector_version', 'pause_detector_energy_v1')])
    frozen = json.loads((ROOT/'research/prosody/freeze.json').read_bytes())
    canonical = json.dumps(frozen, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    engine = b''.join((ROOT/p).read_bytes() for p in [
        'backend/phrase_prosody.py', 'research/prosody/engine.py',
        'research/prosody/extract.praat', 'research/prosody/statistics.praat'])
    spec('prosody', 'phrase_prosody_output_v1', [
        check('/dependencies/config_sha256', hashlib.sha256(canonical).hexdigest()),
        check('/dependencies/engine_sha256', hashlib.sha256(engine).hexdigest()),
        check('/protocol_version', 'phrase_prosody_v1'),
        check('/configuration/schema_version', 'phrase_prosody_freeze_v2'),
        check('/configuration/selected_configuration_id', 'filtered_800_03__0')])
    return dict(schema_version='motor_profile_protocol_v1', battery_version='motor_battery_v1', sources=sources,
                projection_version='motor_profile_projection_v1', acoustic_execution=False)


@router.get('/motor-profile-protocol')
def identity():
    return protocol()


@router.get('/profile', include_in_schema=False)
def page():
    return FileResponse(ROOT/'frontend/motor-profile.html')
