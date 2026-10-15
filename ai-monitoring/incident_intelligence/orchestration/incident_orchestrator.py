"""
Incident Orchestrator entry point for Incident Orchestration Engine.
Implements IncidentBuilderInterface from Package 10.1.
Consumes monitoring engine outputs downstream without modifying pipeline execution.
"""
from typing import Optional, List, Dict, Any
from incident_intelligence.domain.incident import Incident
from incident_intelligence.domain.evidence_reference import EvidenceReference
from incident_intelligence.domain.interfaces import IncidentBuilderInterface, IncidentRepositoryInterface
from incident_intelligence.orchestration.repository_adapter import InMemoryIncidentRepository
from incident_intelligence.orchestration.incident_factory import IncidentFactory
from incident_intelligence.orchestration.incident_lifecycle import IncidentLifecycleManager
from incident_intelligence.orchestration.incident_matching import IncidentMatchingEngine
from incident_intelligence.orchestration.incident_event_router import IncidentEventRouter

class IncidentOrchestrator(IncidentBuilderInterface):
    """High-level Orchestrator coordinating incident building, state transitions, and repository persistence."""

    def __init__(self, repository: Optional[IncidentRepositoryInterface] = None):
        self.repository = repository or InMemoryIncidentRepository()
        self.factory = IncidentFactory()
        self.lifecycle_manager = IncidentLifecycleManager()
        self.matching_engine = IncidentMatchingEngine(self.repository)
        self.event_router = IncidentEventRouter(
            repository=self.repository,
            factory=self.factory,
            lifecycle_manager=self.lifecycle_manager,
            matching_engine=self.matching_engine
        )

    def process_lifecycle_event(self, event_data: Dict[str, Any]) -> Optional[Incident]:
        """
        Public entry point to consume a serialized lifecycle event dictionary from the monitoring engine.
        Returns the updated or created Incident aggregate root.
        """
        if not isinstance(event_data, dict):
            return None
        return self.event_router.route_event(event_data)

    def add_evidence_to_incident(self, incident_id: str, evidence: EvidenceReference) -> bool:
        """Attach an immutable evidence reference to an active or resolved incident."""
        incident = self.repository.get_by_id(incident_id)
        if incident is None:
            return False

        incident.add_evidence_reference(evidence)
        incident.domain_events.append({
            "event_type": "EvidenceAttached",
            "incident_id": incident_id,
            "evidence_id": evidence.evidence_id,
            "timestamp": evidence.timestamp
        })
        self.repository.save(incident)
        return True

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Fetch incident aggregate by incident_id."""
        return self.repository.get_by_id(incident_id)

    def get_incident_by_episode(self, episode_id: str) -> Optional[Incident]:
        """Fetch incident aggregate by parent episode UUID."""
        return self.repository.get_by_episode_id(episode_id)

    def list_active_incidents(self) -> List[Incident]:
        """List all active (non-RESOLVED) incidents."""
        return self.repository.list_active()
