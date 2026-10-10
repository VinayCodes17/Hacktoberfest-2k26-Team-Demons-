import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, File, Form, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.contracts import load_taxonomy, require_classification_taxonomy
from app.ingestion.persistence import persist_ingestion
from app.ingestion.pipeline import generate_ingestion_report, ingest_workbook
from app.ingestion.profiler import MAX_FILE_SIZE
from app.logging_config import setup_logging
from app.persistence.database import make_engine
from app.persistence.repository import create_job, get_job, get_job_predictions, get_job_progress
from app.readiness import readiness
from app.review_export import export_review_workbook
from app.schemas import ErrorResponse, Health, JobCreate, JobView, Readiness
from app.settings import Settings
from app.worker.worker import WorkerState, run_worker


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    logger = setup_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = make_engine(config.database_path)
        # Start worker
        app.state.worker = WorkerState()
        worker_task = asyncio.create_task(run_worker(app.state.engine, config, state=app.state.worker))
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
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
        result = readiness(request.app.state.engine, config, worker_ready=request.app.state.worker.ready)
        response.status_code = 200 if result.service_ready else 503
        return result

    @app.post("/api/v1/jobs", response_model=JobView)
    def start_job(body: JobCreate, request: Request):
        try:
            require_classification_taxonomy(load_taxonomy(config.taxonomy_path))
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

    @app.get("/api/v1/jobs/{job_id}/export.xlsx")
    def download_results(job_id: str, request: Request):
        try:
            content = export_review_workbook(request.app.state.engine, job_id)
        except LookupError:
            return JSONResponse(status_code=404, content={"message": "Job not found."})
        except ValueError:
            return JSONResponse(
                status_code=409,
                content={"message": "Wait until every row has a saved result before downloading."},
            )
        return Response(
            content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="classification-{job_id}.xlsx"'},
        )

    @app.get("/api/v1/predictions/{prediction_id}/trace")
    def prediction_trace(prediction_id: str, request: Request):
        from app.persistence.repository import get_prediction_trace

        trace = get_prediction_trace(request.app.state.engine, prediction_id)
        if not trace:
            return JSONResponse(
                status_code=404,
                content={
                    "code": "PREDICTION_NOT_FOUND",
                    "message": "No prediction exists with that identifier.",
                },
            )
        return trace

    @app.post("/api/v1/datasets/profile")
    async def profile_dataset(
        request: Request,
        sheet_name: str | None = Form(None),
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

        if not file.filename or not file.filename.lower().endswith(".xlsx"):
            return JSONResponse(status_code=422, content={"message": "Upload an .xlsx workbook."})
        temp_dir = Path(config.database_path).parent / "uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f"{uuid4()}.xlsx"
        persisted = False
        try:
            size = 0
            with temp_path.open("wb") as buffer:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_FILE_SIZE:
                        return JSONResponse(status_code=413, content={"message": "Workbook exceeds 50 MiB."})
                    buffer.write(chunk)
            result = await asyncio.to_thread(
                ingest_workbook, temp_path, sheet_name, user_mapping_overrides=overrides
            )
            report = generate_ingestion_report(result)
            if result.errors or not result.transactions or result.mapping.ambiguous_mappings:
                return JSONResponse(
                    status_code=422,
                    content={
                        "message": " ".join(result.errors + result.mapping.ambiguous_mappings)
                        or "No transaction rows were found in the selected sheet.",
                        "report": report,
                    },
                )
            ids = await asyncio.to_thread(
                persist_ingestion, request.app.state.engine, config, result, temp_path
            )
            persisted = True
            return {
                **report,
                **ids,
                "filename": file.filename,
                "selected_sheet": result.workbook_data.sheet_name,
            }
        finally:
            await file.close()
            if not persisted:
                temp_path.unlink(missing_ok=True)

    return app
