"""
Abstract Domain Interfaces for Package 10.1.
Defines structural contracts for Repository, Factory, and Builder components without implementation logic.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from incident_intelligence.domain.incident import Incident, IncidentDTO
from incident_intelligence.domain.evidence_reference import EvidenceReference
from incident_intelligence.domain.enums import IncidentState

class IncidentRepositoryInterface(ABC):
    """Abstract interface for Incident storage operations."""
    
    @abstractmethod
    def save(self, incident: Incident) -> None:
        """Save or update an incident aggregate."""
        pass

    @abstractmethod
    def get_by_id(self, incident_id: str) -> Optional[Incident]:
        """Find incident aggregate by incident_id."""
        pass

    @abstractmethod
    def get_by_episode_id(self, episode_id: str) -> Optional[Incident]:
        """Find incident aggregate by parent episode_id (UUID)."""
        pass

    @abstractmethod
    def list_active(self) -> List[Incident]:
        """List all currently active incidents."""
        pass


class IncidentFactoryInterface(ABC):
    """Abstract interface for instantiating new Incident aggregates."""

    @abstractmethod
    def create_incident(
        self,
        episode_id: str,
        incident_type: str,
        category: str,
        title: str,
        description: str,
        initial_confidence: float = 0.0,
        start_time: Optional[float] = None
    ) -> Incident:
        """Instantiate a new Incident aggregate root."""
        pass


class IncidentBuilderInterface(ABC):
    """Abstract interface for constructing and updating Incident aggregates from raw events."""

    @abstractmethod
    def process_lifecycle_event(self, event_data: Dict[str, Any]) -> Optional[Incident]:
        """Process a lifecycle transition event and update or create an incident."""
        pass

    @abstractmethod
    def add_evidence_to_incident(self, incident_id: str, evidence: EvidenceReference) -> bool:
        """Attach an evidence reference to an incident."""
        pass
