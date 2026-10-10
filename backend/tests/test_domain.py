from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas import CanonicalTransaction, EvaluationRun, FinancialSignal, SourceRow
from app.settings import Settings


def test_decimal_json_and_missing_zero_false_remain_distinct():
    source = SourceRow(dataset_id="fixture", sheet="Synthetic", physical_row=2, source_sha256="0" * 64, cells=[
        {"coordinate": "A2", "cell_type": "n", "value": 0},
        {"coordinate": "B2", "cell_type": "b", "value": False},
        {"coordinate": "C2", "cell_type": "null", "value": None},
        {"coordinate": "D2", "cell_type": "s", "value": ""},
    ])
    record = CanonicalTransaction(id="fixture", sources=[source], amounts={"total": Decimal("0.00"), "tax": None})
    restored = CanonicalTransaction.model_validate_json(record.model_dump_json())
    assert restored.amounts["total"] == Decimal("0.00")
    assert restored.amounts["tax"] is None
    assert '"total":"0.00"' in record.model_dump_json()
    assert type(restored.sources[0].cells[0].value) is int
    assert type(restored.sources[0].cells[1].value) is bool


def test_evidence_and_evaluation_contracts_reject_invalid_inputs():
    with pytest.raises(ValidationError):
        FinancialSignal(name="direction", value="out", status="derived", source_paths=[])
    with pytest.raises(ValidationError):
        EvaluationRun(id="test", manifest_sha256="0" * 64, harness_id="fixture", split="synthetic_fixture", variants=["fixture"], invented_score=1)


@pytest.mark.parametrize("override", [
    {"generation_concurrency": 2}, {"max_model_calls_per_row": 3},
    {"gemma_runtime_model": "other"}, {"embedding_dim": 512},
    {"embedding_revision": "main"}, {"gemma_num_ctx": 128000},
])
def test_configuration_rejects_unsafe_or_unmeasured_settings(override):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **override)


def test_documented_env_template_loads():
    settings = Settings(_env_file=Path(__file__).resolve().parents[2] / ".env.example")
    assert settings.generation_concurrency == 1
    assert settings.max_model_calls_per_row == 2
    assert settings.embedding_dim == 768
