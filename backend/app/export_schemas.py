"""Regenerate tracked schema artifacts; no DB, network or model initialization."""

import inspect
import json
from pathlib import Path

from app import schemas
from app.contracts import Contract
from app.main import create_app
from app.settings import Settings


def main():
    destination = Path(__file__).resolve().parents[2] / "docs" / "contracts"
    destination.mkdir(parents=True, exist_ok=True)
    contracts = {
        name: cls.model_json_schema()
        for name, cls in inspect.getmembers(schemas, inspect.isclass)
        if issubclass(cls, Contract) and cls is not Contract
    }
    for filename, value in (
        ("domain.schema.json", contracts),
        ("openapi.json", create_app(Settings(_env_file=None)).openapi()),
    ):
        (destination / filename).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
