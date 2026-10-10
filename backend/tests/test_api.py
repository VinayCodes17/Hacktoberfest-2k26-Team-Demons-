import logging

import httpx
import pytest
from fastapi.testclient import TestClient

from app.logging_config import SafeFormatter
from app.main import create_app
from app.persistence.database import make_engine, migrate
from app.settings import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, database_path=tmp_path / "api.db")


@pytest.fixture
def metadata_only_ollama(monkeypatch, settings):
    client_type = httpx.Client

    def handler(request):
        if request.url.path in ("/health", "/readyz"):
            return httpx.Response(503)  # Optional services absent in this fixture.
        assert request.url.path == "/api/tags"  # No inference in readiness.
        return httpx.Response(200, json={"models": [{"name": settings.gemma_runtime_model, "digest": settings.gemma_model_digest}]})

    monkeypatch.setattr("app.readiness.httpx.Client", lambda **kwargs: client_type(**kwargs, transport=httpx.MockTransport(handler)))


def test_liveness_and_unmigrated_readiness(settings, metadata_only_ollama):
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/health").json()["status"] == "ok"
        response = client.get("/api/v1/readiness")
        assert response.status_code == 503
        assert response.json()["service_ready"] is False
        assert response.headers["X-Request-ID"]


def test_readiness_distinguishes_service_from_classification(settings, metadata_only_ollama):
    engine = make_engine(settings.database_path)
    migrate(engine)
    engine.dispose()
    with TestClient(create_app(settings)) as client:
        result = client.get("/api/v1/readiness")
        assert result.status_code == 200
        body = result.json()
        assert body["service_ready"] is True
        assert body["classification_ready"] is False
        checks = {c["name"]: c for c in body["checks"]}
        assert checks["Voucher definitions"]["status"] == "blocked"
        assert checks["Local Gemma"]["status"] == "ready"
        assert checks["Reference memory"]["status"] == "optional"
        assert client.get("/api/v1/jobs/absent").status_code == 404


def test_ollama_outage_does_not_break_readiness(settings, monkeypatch):
    def offline(**kwargs):
        raise httpx.ConnectError("synthetic failure containing PRIVATE")

    monkeypatch.setattr("app.readiness.httpx.Client", offline)
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/readiness")
        assert "PRIVATE" not in response.text
        assert next(c for c in response.json()["checks"] if c["name"] == "Local Gemma")["status"] == "unavailable"


def test_unknown_fields_rejected_without_echo_and_no_jobs_started(settings):
    with TestClient(create_app(settings)) as client:
        request = dict(dataset_id="synthetic", mapping_id="m", harness_id="h", idempotency_key="k")
        result = client.post("/api/v1/jobs", json={**request, "narration": "PRIVATE_FINANCIAL_TEXT"})
        assert result.status_code == 422
        assert "PRIVATE_FINANCIAL_TEXT" not in result.text
        assert client.post("/api/v1/jobs", json=request).status_code == 400


def test_structured_logger_ignores_sensitive_extras_and_unknown_messages():
    record = logging.LogRecord("test", logging.ERROR, "file", 1, "PRIVATE_FINANCIAL_TEXT", (), None)
    record.body = "SECRET_TOKEN"
    record.request_id = "generated-id"
    formatted = SafeFormatter().format(record)
    assert "SECRET" not in formatted and "PRIVATE" not in formatted
    assert "generated-id" in formatted


@pytest.mark.parametrize("revision,expected", [("wrong", "blocked"), ("914f7f89142e33e77833254d9c9b90c3cef7303b", "ready")])
def test_embedding_readiness_requires_pinned_metadata(settings, monkeypatch, revision, expected):
    client_type = httpx.Client

    def handler(request):
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ready", "revision": revision,
                                           "model_id": settings.embedding_model_id, "dimensions": 768,
                                           "device": "cpu", "dtype": "float32", "unused_modalities_loaded": False})
        return httpx.Response(503)

    monkeypatch.setattr("app.readiness.httpx.Client", lambda **kwargs: client_type(**kwargs, transport=httpx.MockTransport(handler)))
    with TestClient(create_app(settings)) as client:
        checks = client.get("/api/v1/readiness").json()["checks"]
        assert next(c for c in checks if c["name"] == "Embeddings")["status"] == expected
