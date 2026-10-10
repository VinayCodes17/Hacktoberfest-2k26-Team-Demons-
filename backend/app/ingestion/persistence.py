"""Persist immutable source data and the proposed mapping before job creation."""

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.contracts import load_taxonomy, require_classification_taxonomy
from app.persistence.models import Dataset, HarnessRecord, MappingRecord, SourceRecord
from app.schemas import CanonicalTransaction, FinancialSignal, SourceCell, SourceRow


def persist_ingestion(engine, settings, result, storage_path):
    taxonomy = load_taxonomy(settings.taxonomy_path)
    require_classification_taxonomy(taxonomy)
    dataset_id, mapping_id, harness_id = (str(uuid4()) for _ in range(3))

    def serial(value):
        return json.loads(json.dumps(value, default=str))

    rows = {r.physical_row: r for r in result.workbook_data.rows}
    mapping = {
        "sheet": result.workbook_data.sheet_name,
        "header_row": result.workbook_data.header_row,
        "canonical_to_column": result.mapping.canonical_to_source,
        "first_data_row": min(rows),
        "last_data_row": max(rows),
        "row_unit": "physical_row",
        "blank_rows": "excluded",
    }
    with Session(engine) as session:
        session.add(
            Dataset(
                id=dataset_id,
                source_sha256=result.source_sha256,
                storage_key=str(storage_path),
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        session.flush()
        session.add(MappingRecord(id=mapping_id, dataset_id=dataset_id, revision=1, payload=mapping))
        session.add(
            HarnessRecord(
                id=harness_id,
                payload={
                    "taxonomy": taxonomy.model_dump(),
                    "model_digest": settings.gemma_model_digest,
                    "model": settings.gemma_runtime_model,
                    "num_ctx": settings.gemma_num_ctx,
                    "mode": "ontology_only",
                    "memory_snapshot_id": None,
                    "prompt_version": "direct-v2",
                },
            )
        )
        for t in result.transactions:
            raw = rows[t.physical_row]
            record_id = f"{dataset_id}:{t.physical_row}"
            canonical = CanonicalTransaction(
                id=record_id,
                sources=[
                    SourceRow(
                        dataset_id=dataset_id,
                        sheet=raw.sheet_name,
                        physical_row=raw.physical_row,
                        source_sha256=result.source_sha256,
                        cells=[
                            SourceCell(coordinate=c.coordinate, cell_type=c.cell_type, value=serial(c.value))
                            for c in raw.cells
                        ],
                    )
                ],
                signals=[
                    FinancialSignal(
                        name=s.canonical_name,
                        value=serial(s.value),
                        status="observed" if s.status == "observed" else "unknown",
                        source_paths=[s.source_coordinate],
                    )
                    for s in t.signals
                ],
                missing_paths=t.missing_paths,
                parse_issues=t.parse_issues,
            )
            session.add(
                SourceRecord(
                    id=record_id,
                    dataset_id=dataset_id,
                    sheet=raw.sheet_name,
                    physical_row=raw.physical_row,
                    payload=canonical.model_dump(mode="json"),
                )
            )
        session.commit()
    return {"dataset_id": dataset_id, "mapping_id": mapping_id, "harness_id": harness_id, "mapping": mapping}
