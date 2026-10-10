import datetime
from uuid import uuid4

from app.schemas import ActivationEvent, HarnessBundle


class HarnessManager:
    def __init__(self):
        # Mocks a DB repository
        self.bundles: dict[str, HarnessBundle] = {}
        self.active_bundle_id: str | None = None
        self.events: list[ActivationEvent] = []

    def register_bundle(self, bundle: HarnessBundle):
        self.bundles[bundle.id] = bundle

    def activate_bundle(self, bundle_id: str, authorizer: str) -> ActivationEvent:
        """
        Atomically change active pointer.
        Validate complete artifacts, require authorized activation.
        """
        if bundle_id not in self.bundles:
            raise ValueError("Bundle not found")
        if not authorizer:
            raise ValueError("Activation requires authorizer")
            
        parent_id = self.active_bundle_id
        
        # In a real DB this would be a transaction
        self.active_bundle_id = bundle_id
        
        event = ActivationEvent(
            id=str(uuid4()),
            harness_id=bundle_id,
            parent_id=parent_id,
            action="activate",
            authorizer=authorizer,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        self.events.append(event)
        return event

    def rollback(self, target_bundle_id: str, authorizer: str) -> ActivationEvent:
        """
        Rollback restores exact old snapshot.
        """
        if target_bundle_id not in self.bundles:
            raise ValueError("Target bundle not found for rollback")
            
        current_id = self.active_bundle_id
        self.active_bundle_id = target_bundle_id
        
        event = ActivationEvent(
            id=str(uuid4()),
            harness_id=target_bundle_id,
            parent_id=current_id,
            action="rollback",
            authorizer=authorizer,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        self.events.append(event)
        return event
