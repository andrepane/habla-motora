"""8B transport adapter. The frozen 8A module and extraction are untouched."""
import json
from pathlib import Path
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from backend import phrase_prosody as acoustic
from backend.phrase import MAX_BYTES, CONFIG_BYTES, ROOT, canonical, digest
from research.prosody.run import code_hash

router = APIRouter()
INTEGRATION_VERSION = 'phrase_prosody_integration_v1'
FREEZE_SHA256 = '047fac7379b09dfae0f545569e21ec34463ab7227255507ceeba68f8c6b6a24c'
DEPENDENCIES = {'file_sha256', 'context_sha256', 'selection_sha256', 'config_sha256', 'engine_sha256'}


def configuration():
    raw = (acoustic.HERE/'freeze.json').read_bytes()
    if digest(raw) != FREEZE_SHA256:
        raise RuntimeError('Frozen configuration integrity mismatch')
    frozen = json.loads(raw)
    if (frozen['code_sha256'] != code_hash()
            or frozen['module_sha256'] != digest(Path(acoustic.__file__).read_bytes())
            or frozen['assessment_sha256'] != digest((ROOT/'reports/prosody/assess.py').read_bytes())):
        raise RuntimeError('Frozen implementation integrity mismatch')
    return frozen


def protocol_identity():
    frozen = configuration()
    # Identical byte identity used by the frozen source_dependencies helper.
    engine = digest(Path(acoustic.__file__).read_bytes() + b''.join(
        (acoustic.HERE/p).read_bytes() for p in ['engine.py', 'extract.praat', 'statistics.praat']))
    return dict(integration_version=INTEGRATION_VERSION, protocol_version=acoustic.MODULE_VERSION,
                configuration=frozen, freeze_sha256=FREEZE_SHA256,
                config_sha256=digest(canonical(frozen)), engine_sha256=engine,
                phrase_config_sha256=digest(CONFIG_BYTES), expected_praat_version='6.4.27')


def execute(data, context, expected):
    identity = protocol_identity()
    if (not isinstance(expected, dict) or set(expected) != DEPENDENCIES
            or any(not isinstance(v, str) or len(v) != 64 or any(c not in '0123456789abcdef' for c in v)
                   for v in expected.values())):
        raise ValueError('Se requieren los cinco hashes SHA-256 de dependencias.')
    # No configurable acoustic parameters are exposed at this boundary.
    result = acoustic.analyze_prosody(data, context, expected_dependencies=expected,
                                     configuration=identity['configuration'])
    return dict(result, integration_version=INTEGRATION_VERSION, identity=identity,
                gaps=result.get('gaps', []), counts=result.get('counts', dict(total=None, defined=None, undefined=None)),
                reference_st=result.get('reference_st', dict(type='selection_native_median_hz', value_hz=None)),
                runtime=result.get('runtime', dict(praat_version=None, reason='engine_not_executed_or_unavailable')))


@router.get('/phrase-prosody-protocol')
def protocol():
    try:
        return protocol_identity()
    except (OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(503, 'No se puede verificar la identidad congelada de Prosodia.') from exc


@router.post('/phrase-prosody-analysis')
async def analysis(file: UploadFile = File(...), context_json: str = Form(...),
                   expected_dependencies_json: str = Form(...)):
    try:
        data = await file.read(MAX_BYTES + 1)
    finally:
        await file.close()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, 'Frase admite hasta 4.000.000 bytes.')
    try:
        if len(context_json.encode()) > 20000 or len(expected_dependencies_json.encode()) > 2000:
            raise ValueError('Solicitud demasiado grande.')
        return await run_in_threadpool(execute, data, json.loads(context_json), json.loads(expected_dependencies_json))
    except (ValueError, RecursionError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, 'No se pudo verificar o completar Prosodia con la configuración congelada.') from exc
