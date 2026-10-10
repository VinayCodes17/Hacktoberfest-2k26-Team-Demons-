import os
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, File, Form, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.ingestion.pipeline import generate_ingestion_report, ingest_workbook
from app.logging_config import setup_logging
from app.persistence.database import make_engine
from app.persistence.repository import get_job, create_job, get_job_progress, get_job_predictions
from app.readiness import readiness
from app.schemas import ErrorResponse, Health, JobCreate, JobView, Readiness
from app.settings import Settings
from app.worker.worker import run_worker
import asyncio


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    logger = setup_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = make_engine(config.database_path)
        # Start worker
        worker_task = asyncio.create_task(run_worker(app.state.engine, config))
        try:
            yield
        finally:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
            app.state.engine.dispose()

    app = FastAPI(
        title="HisabhParakh",
        version="0.1.0",
        lifespan=lifespan,
        responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    )

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        request_id = str(uuid4())
        start = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.error("request_failed", extra={"request_id": request_id, "status": 500})
            response = JSONResponse(
                status_code=500,
                content={"code": "INTERNAL_ERROR", "message": "The request could not be completed."},
            )
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "status": response.status_code,
                "duration_ms": round((perf_counter() - start) * 1000),
            },
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        # Pydantic errors may contain supplied values. Do not echo those values.
        return JSONResponse(
            status_code=422,
            content={"code": "INVALID_REQUEST", "message": "Request fields do not match the API contract."},
        )

    @app.get("/api/v1/health", response_model=Health)
    def health() -> Health:
        return Health()

    @app.get("/api/v1/readiness", response_model=Readiness, responses={503: {"model": Readiness}})
    def ready(request: Request, response: Response) -> Readiness:
        result = readiness(request.app.state.engine, config)
        response.status_code = 200 if result.service_ready else 503
        return result

    @app.post("/api/v1/jobs", response_model=JobView)
    def start_job(body: JobCreate, request: Request) -> JobView:
        try:
            return create_job(request.app.state.engine, body)
        except Exception as e:
            return JSONResponse(status_code=400, content={"code": "BAD_REQUEST", "message": str(e)})

    @app.get("/api/v1/jobs/{job_id}", response_model=JobView, responses={404: {"model": ErrorResponse}})
    def read_job(job_id: str, request: Request):
        job = get_job(request.app.state.engine, job_id)
        if job is None:
            return JSONResponse(
                status_code=404,
                content={"code": "JOB_NOT_FOUND", "message": "No job exists with that identifier."},
            )
        return job

    @app.get("/api/v1/jobs/{job_id}/progress")
    def job_progress(job_id: str, request: Request):
        job = get_job(request.app.state.engine, job_id)
        if job is None:
            return JSONResponse(
                status_code=404,
                content={"code": "JOB_NOT_FOUND", "message": "No job exists with that identifier."},
            )
        return get_job_progress(request.app.state.engine, job_id)

    @app.get("/api/v1/jobs/{job_id}/predictions")
    def job_predictions(job_id: str, request: Request):
        job = get_job(request.app.state.engine, job_id)
        if job is None:
            return JSONResponse(
                status_code=404,
                content={"code": "JOB_NOT_FOUND", "message": "No job exists with that identifier."},
            )
        return get_job_predictions(request.app.state.engine, job_id)

    @app.post("/api/v1/datasets/profile")
    async def profile_dataset(
        file: UploadFile = File(...),
        mapping_overrides: str | None = Form(
            None, description="JSON string of column mapping overrides {source: canonical}"
        ),
    ):
        import json

        overrides = None
        if mapping_overrides:
            try:
                overrides = json.loads(mapping_overrides)
                if not isinstance(overrides, dict):
                    return JSONResponse(
                        status_code=422,
                        content={
                            "code": "INVALID_MAPPING",
                            "message": "mapping_overrides must be a JSON object.",
                        },
                    )
            except json.JSONDecodeError:
                return JSONResponse(
                    status_code=422,
                    content={"code": "INVALID_MAPPING", "message": "mapping_overrides is not valid JSON."},
                )

        temp_dir = Path(config.database_path).parent / "tmp_uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f"{uuid4()}_{file.filename}"
        try:
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            result = ingest_workbook(temp_path, user_mapping_overrides=overrides)
            report = generate_ingestion_report(result)
            return report
        finally:
            if temp_path.exists():
                os.remove(temp_path)

    return app
