from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from backend.praat_runner import AnalysisError, MAX_BYTES, analyze_wav

app = FastAPI(title="habla-motora: experimental smoke test", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "alive", "note": "Does not establish Praat readiness"}

@app.post("/smoke-test")
async def smoke_test(file: UploadFile = File(...)):
    try:
        data = await file.read(MAX_BYTES + 1)
    finally:
        await file.close()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Maximum WAV size is 10 MiB")
    try:
        return await run_in_threadpool(analyze_wav, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except AnalysisError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/pitch")
async def pitch(file: UploadFile = File(...), emission_start_s: float = Form(0.0),
                emission_end_s: float | None = Form(None)):
    from backend.pitch import analyze_pitch
    try:
        data = await file.read(MAX_BYTES + 1)
    finally:
        await file.close()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Maximum WAV size is 10 MiB")
    try:
        return await run_in_threadpool(analyze_pitch, data, emission_start_s, emission_end_s)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except AnalysisError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/jitter")
async def jitter(file: UploadFile = File(...), emission_start_s: float = Form(0.0),
                emission_end_s: float | None = Form(None)):
    from backend.jitter import analyze_jitter
    try:
        data = await file.read(MAX_BYTES + 1)
    finally:
        await file.close()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Maximum WAV size is 10 MiB")
    try:
        return await run_in_threadpool(analyze_jitter, data, emission_start_s, emission_end_s)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except AnalysisError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/shimmer")
async def shimmer(file: UploadFile = File(...), emission_start_s: float = Form(0.0),
                emission_end_s: float | None = Form(None)):
    from backend.shimmer import analyze_shimmer
    try:
        data = await file.read(MAX_BYTES + 1)
    finally:
        await file.close()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Maximum WAV size is 10 MiB")
    try:
        return await run_in_threadpool(analyze_shimmer, data, emission_start_s, emission_end_s)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except AnalysisError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/hnr")
async def hnr(file: UploadFile = File(...), emission_start_s: float = Form(0.0),
                emission_end_s: float | None = Form(None)):
    from backend.hnr import analyze_hnr
    try:
        data = await file.read(MAX_BYTES + 1)
    finally:
        await file.close()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Maximum WAV size is 10 MiB")
    try:
        return await run_in_threadpool(analyze_hnr, data, emission_start_s, emission_end_s)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except AnalysisError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post('/vowel-analysis')
async def vowel_analysis(file: UploadFile = File(...), emission_start_s: float = Form(0.0),
                         emission_end_s: float | None = Form(None)):
    from backend.vowel import analyze_vowel
    try:
        data = await file.read(MAX_BYTES + 1)
    finally:
        await file.close()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, 'Maximum WAV size is 10 MiB')
    try:
        return await run_in_threadpool(analyze_vowel, data, emission_start_s, emission_end_s)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except AnalysisError as exc:
        raise HTTPException(503, str(exc)) from exc


from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

FRONTEND = Path(__file__).resolve().parents[1] / 'frontend'
app.mount('/static', StaticFiles(directory=FRONTEND), name='static')


@app.get('/', include_in_schema=False)
def interface():
    return FileResponse(FRONTEND / 'index.html')


@app.get('/ddk', include_in_schema=False)
def ddk_interface():
    return FileResponse(FRONTEND / 'ddk.html')


@app.post('/ddk-analysis')
async def ddk_analysis(file: UploadFile = File(...), emission_start_s: float = Form(0.0),
                       emission_end_s: float | None = Form(None), anchor_id: str | None = Form(None),
                       review_json: str | None = Form(None), expected_file_sha256: str | None = Form(None)):
    import json
    from backend.ddk import analyze_ddk, MAX_BYTES as DDK_MAX_BYTES
    try:
        data = await file.read(DDK_MAX_BYTES + 1)
    finally:
        await file.close()
    if len(data) > DDK_MAX_BYTES:
        raise HTTPException(413, 'DDK admite hasta 4.000.000 bytes.')
    try:
        if review_json is not None and len(review_json.encode('utf-8')) > 250000:
            raise ValueError('Revisión demasiado grande.')
        review = json.loads(review_json) if review_json is not None else None
        if review_json is not None and not isinstance(review, dict):
            raise ValueError('Revisión debe ser un objeto JSON.')
        return await run_in_threadpool(analyze_ddk, data, emission_start_s, emission_end_s,
                                       anchor_id, review, expected_file_sha256)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, 'El motor DDK no pudo completar la solicitud.') from exc


# Independent phrase 7A module: no changes to vowel or DDK handlers.
from backend.phrase_routes import router as phrase_router
app.include_router(phrase_router)

# 7B.1 is additive; 7A calculations and existing acoustic handlers stay unchanged.
from backend.phrase_pause_routes import router as phrase_pause_router
app.include_router(phrase_pause_router)

# Optional experimental proposals; manual 7B.1 remains the sole metric source.
from backend.phrase_candidate_routes import router as phrase_candidate_router
app.include_router(phrase_candidate_router)

# 8B only adapts the immutable 8A extractor to the confirmed 7A context.
from backend.phrase_prosody_routes import router as phrase_prosody_router
app.include_router(phrase_prosody_router)
