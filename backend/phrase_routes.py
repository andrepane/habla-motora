"""Isolated 7A routes; existing analysis modules/routes remain unchanged."""
import json
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from backend.phrase import CONFIG, ROOT, MAX_BYTES, analyze_phrase

router = APIRouter()

@router.get('/phrase', include_in_schema=False)
def phrase_interface():
    return FileResponse(ROOT / 'frontend/phrase.html')

@router.get('/phrase-protocol')
def phrase_protocol():
    return CONFIG

@router.post('/phrase-analysis')
async def phrase_analysis(file: UploadFile = File(...), context_json: str = Form(...),
                          review_json: str | None = Form(None), expected_file_sha256: str | None = Form(None)):
    try:
        data = await file.read(MAX_BYTES + 1)
    finally:
        await file.close()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, 'Frase admite hasta 4.000.000 bytes.')
    try:
        if len(context_json.encode()) > 20000 or review_json is not None and len(review_json.encode()) > 250000:
            raise ValueError('Contexto o revisión demasiado grande.')
        context = json.loads(context_json)
        review = json.loads(review_json) if review_json is not None else None
        if review_json is not None and not isinstance(review, dict):
            raise ValueError('La revisión debe ser un objeto JSON.')
        return await run_in_threadpool(analyze_phrase, data, context, review, expected_file_sha256)
    except (ValueError, RecursionError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, 'El módulo de frase no pudo completar la solicitud.') from exc
