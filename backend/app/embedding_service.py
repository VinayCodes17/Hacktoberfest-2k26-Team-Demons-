"""Single CPU encoder, offline weights, bounded inputs and serialized inference."""
import json
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import Field

from app.contracts import Contract
from app.embedding_smoke import validate_vectors
from app.settings import ROOT


class EmbedRequest(Contract):
    text: str = Field(min_length=1, max_length=8000)
    kind: Literal["query", "document"]


class EmbedResponse(Contract):
    vector: list[float]
    revision: str
    dimensions: Literal[768] = 768


def create_app() -> FastAPI:
    manifest = json.loads((ROOT / "backend/embedding-model.json").read_text())
    default = ROOT / "storage/huggingface/models--google--embeddinggemma-2/snapshots" / manifest["revision"]
    snapshot = Path(os.environ.get("EMBEDDING_SNAPSHOT", str(default)))
    lock = threading.Lock()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        import torch
        from sentence_transformers import SentenceTransformer

        if not snapshot.is_dir() or snapshot.name != manifest["revision"]:
            raise ValueError("Pinned embedding snapshot is missing")
        torch.set_num_threads(2)
        model = SentenceTransformer(str(snapshot), device="cpu", local_files_only=True,
                                    trust_remote_code=False,
                                    config_kwargs={"vision_config": None, "audio_config": None},
                                    model_kwargs={"torch_dtype": torch.float32})
        config = model[0].auto_model.config
        if getattr(config, "vision_config", None) is not None or getattr(config, "audio_config", None) is not None:
            raise ValueError("Unused modality encoders remain configured")
        if any("vision_tower" in name or "audio_tower" in name for name, _ in model.named_parameters()):
            raise ValueError("Unused modality encoder parameters loaded")
        if any(p.dtype != torch.float32 or p.device.type != "cpu" for p in model.parameters()):
            raise ValueError("Encoder must use CPU float32")
        for prompt in (manifest["query_prompt"], manifest["document_prompt"]):
            if not model.prompts.get(prompt):
                raise ValueError("Expected query/document prompt is missing")
        vectors = [model.encode("Synthetic startup check", prompt_name=manifest[key], normalize_embeddings=True)
                   for key in ("query_prompt", "document_prompt")]
        validate_vectors(vectors)
        app.state.encoder = model
        yield
        del app.state.encoder

    app = FastAPI(title="HisabhParakh CPU embeddings", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ready", "model_id": manifest["model_id"], "revision": manifest["revision"],
                "dimensions": 768, "device": "cpu", "dtype": "float32", "unused_modalities_loaded": False}

    @app.post("/embed", response_model=EmbedResponse)
    def embed(request: EmbedRequest):
        model = app.state.encoder
        prompt = manifest["query_prompt" if request.kind == "query" else "document_prompt"]
        with lock:
            token_count = len(model.tokenizer.encode(model.prompts[prompt] + request.text))
            if token_count > min(model.max_seq_length, 2048):
                raise HTTPException(status_code=422, detail="Text exceeds the configured token limit")
            vector = model.encode(request.text, prompt_name=prompt, normalize_embeddings=True).tolist()
        validate_vectors([vector, vector])
        return EmbedResponse(vector=vector, revision=manifest["revision"])

    return app
