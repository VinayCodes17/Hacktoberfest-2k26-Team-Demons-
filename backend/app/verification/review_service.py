import datetime

from app.routing.ontology import OntologyProvider
from app.schemas import Decision, Review


class ReviewService:
    def __init__(self, ontology: OntologyProvider):
        self.ontology = ontology
        # Normally injected DB repository
        self.reviews: list[Review] = []

    def submit_review(self, reviewer_id: str, decision: Decision, corrected_label: str, reason: str, authority: str, source: str) -> Review | None:
        """
        Creates an immutable correction history.
        Corrections become gold only under declared trusted-review policy; 
        conflicting annotations stay unresolved (can be added later).
        """
        # Validate revised label
        if corrected_label:
            if not self.ontology.get_by_name(corrected_label):
                raise ValueError("Invalid corrected label")

        # Conflict handling logic
        # For MVP, we check if the decision's expected revision matches the stored revision.
        # Since we don't have revisions in Decision schema yet, we assume the latest applies.
        # A full system checks expected_revision == actual_revision in DB.

        review = Review(
            prediction_id=decision.id,
            expected_revision=1, # Mock
            reviewer_id=reviewer_id,
            corrected_label=corrected_label,
            reason=reason,
            authority=authority,
            source=source,
            created_at=datetime.datetime.now(datetime.timezone.utc)
        )
        
        self.reviews.append(review)
        return review
