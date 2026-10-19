"""Independent manual 7B.1 API. No automatic candidate detection."""
import json
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from backend.phrase import MAX_BYTES
from backend.phrase_pauses import CONFIG, analyze_pauses

router = APIRouter()

@router.get('/phrase-pause-protocol')
def pause_protocol():
    return CONFIG

@router.post('/phrase-pause-analysis')
async def pause_analysis(file: UploadFile = File(...), context_json: str = Form(...),
                         temporal_json: str = Form(...), review_json: str | None = Form(None),
                         expected_file_sha256: str | None = Form(None)):
    try:
        data = await file.read(MAX_BYTES + 1)
    finally:
        await file.close()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, 'Frase admite hasta 4.000.000 bytes.')
    try:
        if len(context_json.encode()) > 20000 or len(temporal_json.encode()) > 500000 or review_json is not None and len(review_json.encode()) > 250000:
            raise ValueError('Solicitud de revisión demasiado grande.')
        context, temporal = json.loads(context_json), json.loads(temporal_json)
        review = json.loads(review_json) if review_json is not None else None
        if review_json is not None and not isinstance(review, dict):
            raise ValueError('Revisión 7A inválida.')
        return await run_in_threadpool(analyze_pauses, data, context, review, expected_file_sha256, temporal)
    except (ValueError, RecursionError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, 'El módulo de pausas revisadas no pudo completar la solicitud.') from exc
