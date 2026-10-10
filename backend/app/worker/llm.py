import json
from typing import Any

import httpx

from app.settings import Settings


class OllamaAdapterError(Exception):
    pass


def generate_classification(prompt: str, settings: Settings, model_name: str = "gemma2") -> dict[str, Any]:
    """Call Ollama with the given prompt and enforce JSON format."""

    # We pass a JSON schema to Ollama format parameter if supported, or just trust the prompt.
    # Note: Ollama supports `format: "json"` which guarantees a valid JSON object is returned.

    url = f"{settings.ollama_base_url}/api/generate"
    options = {
        "temperature": 0.0,  # Deterministic reasoning
    }
    payload = {
        "model": model_name,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": options,
    }

    from app.worker.cache import InferenceCache
    cache = InferenceCache()
    cached_result = cache.get(model_name, prompt, options)
    if cached_result is not None:
        return cached_result

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            response_text = data.get("response", "{}")

            # Parse the JSON response
            result = json.loads(response_text)
            cache.set(model_name, prompt, options, result)
            return result

    except httpx.RequestError as e:
        raise OllamaAdapterError(f"HTTP error communicating with Ollama: {str(e)}")
    except json.JSONDecodeError as e:
        raise OllamaAdapterError(f"Ollama returned invalid JSON: {str(e)}")
    except Exception as e:
        raise OllamaAdapterError(f"Failed to generate classification: {str(e)}")
