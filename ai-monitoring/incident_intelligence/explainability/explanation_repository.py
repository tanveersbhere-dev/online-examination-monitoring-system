"""
InMemoryExplanationRepository for Explainability Engine.
Stores immutable IncidentExplanationPackage objects.
"""
from typing import Dict, Any, Optional, List
from incident_intelligence.explainability.narrative_builder import IncidentExplanationPackage

class InMemoryExplanationRepository:
    """In-memory storage adapter for explanation packages."""

    def __init__(self):
        self._explanations: Dict[str, IncidentExplanationPackage] = {}

    def save(self, package: IncidentExplanationPackage) -> None:
        """Save explanation package."""
        self._explanations[package.incident_id] = package

    def get_by_incident_id(self, incident_id: str) -> Optional[IncidentExplanationPackage]:
        """Fetch explanation package by incident_id."""
        return self._explanations.get(incident_id)

    def list_all(self) -> List[IncidentExplanationPackage]:
        """List all stored explanation packages."""
        return list(self._explanations.values())

    def clear(self) -> None:
        """Clear repository."""
        self._explanations.clear()
