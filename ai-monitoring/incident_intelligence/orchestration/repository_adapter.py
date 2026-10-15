"""
In-Memory Repository Adapter for Incident Intelligence Platform.
Implements IncidentRepositoryInterface from Package 10.1.
"""
from typing import Optional, List, Dict
from incident_intelligence.domain.incident import Incident
from incident_intelligence.domain.interfaces import IncidentRepositoryInterface

class InMemoryIncidentRepository(IncidentRepositoryInterface):
    """In-memory storage adapter for Incident aggregate roots."""

    def __init__(self):
        self._incidents: Dict[str, Incident] = {}
        self._episode_map: Dict[str, str] = {}  # episode_id -> incident_id

    def save(self, incident: Incident) -> None:
        """Save or update an incident aggregate."""
        self._incidents[incident.incident_id] = incident
        self._episode_map[incident.episode_id] = incident.incident_id

    def get_by_id(self, incident_id: str) -> Optional[Incident]:
        """Find incident aggregate by incident_id."""
        return self._incidents.get(incident_id)

    def get_by_episode_id(self, episode_id: str) -> Optional[Incident]:
        """Find incident aggregate by parent episode_id (UUID)."""
        incident_id = self._episode_map.get(episode_id)
        if incident_id:
            return self._incidents.get(incident_id)
        return None

    def list_active(self) -> List[Incident]:
        """List all currently active (non-RESOLVED) incidents."""
        return [
            inc for inc in self._incidents.values()
            if str(inc.status.value if hasattr(inc.status, 'value') else inc.status) != "RESOLVED"
        ]

    def list_all(self) -> List[Incident]:
        """List all incidents regardless of status."""
        return list(self._incidents.values())

    def clear(self) -> None:
        """Clear all stored incidents (useful for testing)."""
        self._incidents.clear()
        self._episode_map.clear()
