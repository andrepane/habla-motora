"""Opt-in adapter for the frozen energy experiment. Never computes manual metrics."""
import json
from pathlib import Path
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from backend.phrase import MAX_BYTES, analyze_phrase, digest
from research.pause_candidates import engine

router = APIRouter()


def propose(data, context, expected):
    source = analyze_phrase(data, context)
    configuration, config_hash = engine.config('energy')
    deps = dict(file_sha256=source['provenance']['file_sha256'],
                context_sha256=source['provenance']['context_sha256'],
                context=source['context'], detector_version='pause_detector_energy_v1',
                config_sha256=config_hash, engine_sha256=digest(Path(engine.__file__).read_bytes()))
    base = dict(schema_version='phrase_candidate_execution_v1', dependencies=deps,
                automatic_candidates=None, detector_version=deps['detector_version'],
                configuration=configuration)
    if not isinstance(expected, dict) or set(expected) != {'file_sha256', 'context_sha256', 'config_sha256', 'engine_sha256'}:
        raise ValueError('Se requieren los cuatro hashes de dependencias.')
    if any(expected[k] != deps[k] for k in expected):
        return {**base, 'status': 'stale', 'reason': 'dependency_mismatch'}
    if not source['context']['selection_confirmed'] or source['context']['selection'] is None:
        raise ValueError('Se requiere una selección 7A confirmada.')
    selection = {**source['context']['selection'], 'confirmed': True}
    try:
        original = engine.detect(data, selection, deps['context_sha256'], variant='energy', include_frames=False)
    except Exception:
        return {**base, 'status': 'failed', 'reason': 'execution_failed'}
    # Preserve the detector response verbatim; provenance is added outside it.
    return {**base, 'status': original['status'], 'reason': original['reason'],
            'automatic_candidates': original['automatic_candidates'], 'original_execution': original}


@router.get('/phrase-candidate-protocol')
def protocol():
    configuration, config_hash = engine.config('energy')
    return dict(detector_version='pause_detector_energy_v1', configuration=configuration,
                config_sha256=config_hash, engine_sha256=digest(Path(engine.__file__).read_bytes()))


@router.post('/phrase-candidates')
async def candidates(file: UploadFile = File(...), context_json: str = Form(...),
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
        return await run_in_threadpool(propose, data, json.loads(context_json), json.loads(expected_dependencies_json))
    except (ValueError, RecursionError) as exc:
        raise HTTPException(422, str(exc)) from exc
