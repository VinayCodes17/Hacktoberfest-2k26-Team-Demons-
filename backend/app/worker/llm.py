from typing import Any

import httpx

from app.schemas import ModelProposal
from app.settings import Settings


class OllamaAdapterError(Exception):
    pass


def generate_classification(prompt: str, settings: Settings) -> dict[str, Any]:
    """One bounded request; the caller durably reserves its attempt first."""
    try:
        with httpx.Client(timeout=120.0, trust_env=False) as client:
            tags = client.get(f"{settings.ollama_base_url}/api/tags")
            tags.raise_for_status()
            if not any(
                m.get("name") == settings.gemma_runtime_model
                and m.get("digest") == settings.gemma_model_digest
                for m in tags.json().get("models", [])
            ):
                raise OllamaAdapterError("MODEL_DIGEST_MISMATCH")
            response = client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.gemma_runtime_model,
                    "prompt": prompt,
                    "format": ModelProposal.model_json_schema(),
                    "stream": False,
                    "think": False,
                    "options": {"temperature": 0, "num_ctx": settings.gemma_num_ctx, "num_predict": 512},
                },
            )
            response.raise_for_status()
            result = response.json()
            if result.get("done_reason") == "length":
                raise OllamaAdapterError("OUTPUT_TRUNCATED")
            return ModelProposal.model_validate_json(result["response"]).model_dump()
    except OllamaAdapterError:
        raise
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise OllamaAdapterError("MODEL_REQUEST_OR_SCHEMA_ERROR") from exc
