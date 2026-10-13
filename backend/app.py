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
