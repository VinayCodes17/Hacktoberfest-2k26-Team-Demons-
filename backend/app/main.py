from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.logging_config import setup_logging
from app.persistence.database import make_engine
from app.persistence.repository import get_job
from app.readiness import readiness
from app.schemas import ErrorResponse, Health, JobCreate, JobView, Readiness
from app.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    logger = setup_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = make_engine(config.database_path)
        try:
            yield
        finally:
            app.state.engine.dispose()

    app = FastAPI(title="HisabhParakh", version="0.1.0", lifespan=lifespan,
                  responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        request_id = str(uuid4())
        start = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.error("request_failed", extra={"request_id": request_id, "status": 500})
            response = JSONResponse(status_code=500, content={"code": "INTERNAL_ERROR", "message": "The request could not be completed."})
        response.headers["X-Request-ID"] = request_id
        logger.info("request_completed", extra={"request_id": request_id, "status": response.status_code,
                                                "duration_ms": round((perf_counter() - start) * 1000)})
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        # Pydantic errors may contain supplied values. Do not echo those values.
        return JSONResponse(status_code=422, content={"code": "INVALID_REQUEST", "message": "Request fields do not match the API contract."})

    @app.get("/api/v1/health", response_model=Health)
    def health() -> Health:
        return Health()

    @app.get("/api/v1/readiness", response_model=Readiness, responses={503: {"model": Readiness}})
    def ready(request: Request, response: Response) -> Readiness:
        result = readiness(request.app.state.engine, config)
        response.status_code = 200 if result.service_ready else 503
        return result

    @app.post("/api/v1/jobs", response_model=ErrorResponse, status_code=409)
    def start_job(body: JobCreate) -> ErrorResponse:
        # Storage interfaces exist, but no jobs may start before the real worker.
        return ErrorResponse(code="CLASSIFICATION_NOT_READY", message="Workbook mapping and the classification worker are not available yet.")

    @app.get("/api/v1/jobs/{job_id}", response_model=JobView, responses={404: {"model": ErrorResponse}})
    def read_job(job_id: str, request: Request):
        job = get_job(request.app.state.engine, job_id)
        if job is None:
            return JSONResponse(status_code=404, content={"code": "JOB_NOT_FOUND", "message": "No job exists with that identifier."})
        return job

    return app
