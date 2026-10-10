"""Recheck saved proposals, preserving previous verification outcomes. No inference."""

import argparse
import json
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts import Taxonomy
from app.persistence.database import make_engine
from app.persistence.models import Job, Prediction, SourceRecord
from app.routing.ontology import OntologyProvider
from app.schemas import CanonicalTransaction, ModelProposal
from app.settings import Settings
from app.verification.verifier import VERIFIER_VERSION, Verifier, meaningful_missing


def reverify(engine, job_id, apply=False):
    counts = Counter()
    with Session(engine) as session:
        if apply:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        job = session.get(Job, job_id)
        if job is None:
            raise ValueError("JOB_NOT_FOUND")
        verifier = Verifier(
            OntologyProvider.from_taxonomy(Taxonomy.model_validate(job.harness_snapshot["taxonomy"]))
        )
        for prediction in session.scalars(select(Prediction).where(Prediction.job_id == job_id)):
            previous = prediction.payload
            if not all(k in previous for k in ModelProposal.model_fields):
                counts["unchanged_error"] += 1
                continue
            proposal = ModelProposal.model_validate({k: previous[k] for k in ModelProposal.model_fields})
            proposal.missing_evidence = meaningful_missing(proposal.missing_evidence)
            source = session.get(SourceRecord, prediction.transaction_id)
            transaction = CanonicalTransaction.model_validate_json(json.dumps(source.payload))
            status, reasons = verifier.verify(proposal, transaction)
            counts[f"{previous['status']} -> {status}"] += 1
            if apply and (
                status != previous["status"]
                or reasons != previous.get("reason_codes")
                or proposal.missing_evidence != previous["missing_evidence"]
            ):
                history = list(previous.get("verification_history", []))
                history.append(
                    {
                        "status": previous["status"],
                        "reason_codes": previous.get("reason_codes", []),
                        "missing_evidence": previous["missing_evidence"],
                        "version": previous.get("verification_version", "legacy"),
                        "rechecked_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                prediction.payload = {
                    **previous,
                    "status": status,
                    "reason_codes": reasons,
                    "missing_evidence": proposal.missing_evidence,
                    "verification_version": VERIFIER_VERSION,
                    "verification_history": history,
                }
        if apply:
            session.commit()
    return dict(counts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", action="append", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    engine = make_engine(Settings().database_path)
    print(json.dumps({job: reverify(engine, job, args.apply) for job in args.job_id}))
