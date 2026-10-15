"""
Incident Factory for Incident Intelligence Platform.
Implements IncidentFactoryInterface. Responsibilities: Create NEW Incident Aggregate Roots only.
"""
from typing import Optional, List
import time
import uuid

from incident_intelligence.domain.incident import Incident
from incident_intelligence.domain.enums import IncidentState, IncidentSeverity, IncidentPriority
from incident_intelligence.domain.metadata import IncidentMetadata
from incident_intelligence.domain.interfaces import IncidentFactoryInterface

class IncidentFactory(IncidentFactoryInterface):
    """Factory responsible for instantiating new Incident aggregates."""

    def __init__(self, id_prefix: str = "INC"):
        self.id_prefix = id_prefix

    def create_incident(
        self,
        episode_id: str,
        incident_type: str,
        category: str = "Security",
        title: str = "Behavioral Incident",
        description: str = "Behavioral anomaly observed",
        initial_confidence: float = 0.0,
        start_time: Optional[float] = None,
        severity: IncidentSeverity = IncidentSeverity.MEDIUM,
        priority: IncidentPriority = IncidentPriority.P3_MEDIUM,
        triggered_rules: Optional[List[str]] = None
    ) -> Incident:
        """Instantiate a brand new Incident aggregate root."""
        ts = start_time if start_time is not None else time.time()
        incident_id = f"{self.id_prefix}-{uuid.uuid4().hex[:8].upper()}"

        metadata = IncidentMetadata(
            category=category,
            title=title,
            description=description,
            triggered_rules=triggered_rules or [incident_type]
        )

        incident = Incident(
            incident_id=incident_id,
            episode_id=episode_id,
            incident_type=incident_type,
            severity=severity,
            priority=priority,
            status=IncidentState.STARTED,
            start_time=ts,
            last_updated=ts,
            current_confidence=initial_confidence,
            peak_confidence=initial_confidence,
            average_confidence=initial_confidence,
            current_state=IncidentState.STARTED,
            metadata=metadata
        )

        # Record initial confidence entry if provided
        if initial_confidence > 0.0:
            incident.append_confidence(ts, initial_confidence, 1)

        # Prepare future domain event placeholder
        incident.domain_events.append({
            "event_type": "IncidentCreated",
            "incident_id": incident_id,
            "episode_id": episode_id,
            "timestamp": ts
        })

        return incident
