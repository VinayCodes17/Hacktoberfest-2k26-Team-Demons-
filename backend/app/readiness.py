import httpx
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.contracts import load_taxonomy, require_classification_taxonomy
from app.persistence.database import schema_ready
from app.schemas import Check, Readiness
from app.settings import Settings


def readiness(engine: Engine, settings: Settings, worker_ready: bool = False) -> Readiness:
    checks: list[Check] = []
    try:
        database_ready = schema_ready(engine)
    except SQLAlchemyError:
        database_ready = False
    checks.append(
        Check(
            name="Database",
            status="ready" if database_ready else "blocked",
            message="Storage is available and up to date."
            if database_ready
            else "Run the database migrations before using the service.",
        )
    )
    try:
        taxonomy = load_taxonomy(settings.taxonomy_path)
        require_classification_taxonomy(taxonomy)
        checks.append(
            Check(
                name="Voucher definitions",
                status="ready",
                message=(
                    f"{len(taxonomy.entries)} voucher definitions approved for {taxonomy.approval_scope}; "
                    f"{len(taxonomy.confusion_boundaries)} confusion boundaries. Unresolved overlaps require review."
                ),
            )
        )
    except (ValueError, OSError) as error:
        messages = {
            "TAXONOMY_MISSING": "No voucher taxonomy is configured.",
            "TAXONOMY_NAMES_UNCONFIRMED": "Category names need organizer confirmation.",
            "TAXONOMY_DEFINITIONS_UNAPPROVED": "Category names are confirmed; definitions and overlap rules still need approval.",
        }
        checks.append(
            Check(
                name="Voucher definitions",
                status="blocked",
                message=messages.get(str(error), "The configured taxonomy could not be validated."),
            )
        )
    try:
        # Metadata only: no model is loaded and no generation budget is consumed.
        with httpx.Client(base_url=settings.ollama_base_url, timeout=2, trust_env=False) as client:
            response = client.get("/api/tags")
            response.raise_for_status()
            models = response.json()["models"]
        match = next((m for m in models if m.get("name") == settings.gemma_runtime_model), None)
        valid = match is not None and match.get("digest") == settings.gemma_model_digest
        checks.append(
            Check(
                name="Local Gemma",
                status="ready" if valid else "blocked",
                message="The pinned Gemma model is installed in Ollama. Generation is not tested by this check."
                if valid
                else "The configured Gemma model or its pinned digest does not match Ollama.",
            )
        )
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
        checks.append(
            Check(
                name="Local Gemma",
                status="unavailable",
                message="Ollama is unavailable. Start the local runtime and check again.",
            )
        )
    try:
        with httpx.Client(base_url=settings.embedding_url, timeout=1, trust_env=False) as client:
            response = client.get("/health")
            response.raise_for_status()
            data = response.json()
        embedding_ready = (
            data.get("status") == "ready"
            and data.get("revision") == settings.embedding_revision
            and data.get("model_id") == settings.embedding_model_id
            and data.get("dimensions") == 768
            and data.get("dtype") == "float32"
            and data.get("device") == "cpu"
            and data.get("unused_modalities_loaded") is False
        )
        checks.append(
            Check(
                name="Embeddings",
                status="ready" if embedding_ready else "blocked",
                message="The pinned CPU encoder passed its startup vector checks."
                if embedding_ready
                else "The embedding service does not match the pinned configuration.",
            )
        )
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        checks.append(
            Check(
                name="Embeddings",
                status="blocked",
                message="The pinned CPU embedding service is not available. Start the embeddings Compose profile after caching the model.",
            )
        )
    try:
        with httpx.Client(base_url=settings.qdrant_url, timeout=1, trust_env=False) as client:
            response = client.get("/readyz")
            response.raise_for_status()
        checks.append(
            Check(
                name="Qdrant",
                status="ready",
                message="The local vector database is available. Approved retrieval collections are not connected yet.",
            )
        )
    except httpx.HTTPError:
        checks.append(
            Check(
                name="Qdrant",
                status="optional",
                message="Qdrant is not connected. Empty reference memory is allowed.",
            )
        )
    checks.extend(
        [
            Check(
                name="Reference memory",
                status="optional",
                message="No approved examples are connected. Empty reference memory is allowed.",
            ),
            Check(
                name="Classification worker",
                status="ready" if worker_ready else "blocked",
                message="Worker is polling persisted jobs. Confirm workbook mapping before classification."
                if worker_ready
                else "Worker is not polling jobs; check database migrations and backend logs.",
            ),
        ]
    )
    return Readiness(
        service_ready=database_ready,
        classification_ready=all(c.status in {"ready", "optional"} for c in checks),
        checks=checks,
    )
