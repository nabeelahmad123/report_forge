import logging

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from app.analysis import InvalidExperimentDataError, compute_metrics, load_experiment_csv
from app.config import settings
from app.models import AnalyzeResponse, FeedResponse, ReportResponse
from app.ratelimit import InMemoryRateLimiter
from app.regwatch import load_snapshot_feed
from app.report import generate_report

logging.basicConfig(
    level=settings.log_level,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
)
logger = logging.getLogger("reportforge")

app = FastAPI(
    title="ReportForge API",
    description="Unsolicited demo project for PFASuiki — electrochemical PFAS degradation "
    "lab report generator. Not affiliated with PFASuiki.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

report_rate_limiter = InMemoryRateLimiter(
    max_requests=settings.report_rate_limit_per_minute, window_seconds=60.0
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(file: UploadFile | None = None, use_demo: bool = False) -> AnalyzeResponse:
    if use_demo:
        if not settings.demo_data_path.exists():
            logger.error("Demo data requested but not found at %s", settings.demo_data_path)
            raise HTTPException(
                status_code=500,
                detail="Demo dataset not found on server — run scripts/generate_demo_data.py",
            )
        raw_bytes = settings.demo_data_path.read_bytes()
        source = "demo"
    elif file is not None:
        raw_bytes = await file.read()
        source = "upload"
    else:
        raise HTTPException(status_code=422, detail="Provide either a CSV file upload or use_demo=true")

    try:
        # CPU-bound (pandas/scipy curve fitting) — run off the event loop so
        # one large upload can't stall every other in-flight request.
        df = await run_in_threadpool(load_experiment_csv, raw_bytes)
        result = await run_in_threadpool(compute_metrics, df, source)
    except InvalidExperimentDataError as exc:
        logger.warning("Rejected invalid experiment data: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    logger.info("Analyzed %d run(s) from source=%s", len(result.runs), source)
    return result


@app.post("/report", response_model=ReportResponse)
async def report(metrics: AnalyzeResponse, request: Request) -> ReportResponse:
    client_key = request.client.host if request.client else "unknown"
    if not report_rate_limiter.allow(client_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded — try again shortly")

    if not metrics.runs:
        raise HTTPException(status_code=422, detail="No runs provided in metrics payload")

    # A real LLM call here runs 45-60s; run it off the event loop so it
    # doesn't stall every other in-flight request (including /health).
    result = await run_in_threadpool(generate_report, metrics)
    logger.info("Generated report (source=%s) for %d run(s)", result.source, len(metrics.runs))
    return result


@app.get("/feed", response_model=FeedResponse)
def feed() -> FeedResponse:
    try:
        result = load_snapshot_feed()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    logger.info("Served RegWatch feed (%d items)", len(result.items))
    return result
