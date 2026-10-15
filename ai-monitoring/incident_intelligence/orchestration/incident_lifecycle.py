"""
Incident Lifecycle Manager for Incident Orchestration Engine.
Owns lifecycle state transitions and aggregate updates.
"""
from typing import Dict, Any, Optional
from incident_intelligence.domain.incident import Incident
from incident_intelligence.domain.enums import IncidentState

class IncidentLifecycleManager:
    """Manages aggregate state transitions and updating confidence/risk measurements."""

    def update_incident(
        self,
        incident: Incident,
        timestamp: float,
        confidence: float = 0.0,
        risk_score: float = 0.0,
        frame_number: int = 1,
        severity: Optional[str] = None,
        reason: str = "Lifecycle update"
    ) -> Incident:
        """Update existing Incident aggregate metrics and state."""
        # Append confidence & risk to history via aggregate methods
        if confidence > 0.0:
            incident.append_confidence(timestamp, confidence, frame_number)

        if risk_score > 0.0:
            incident.append_risk(timestamp, risk_score, frame_number)

        # Update severity if provided
        if severity:
            incident.severity = severity

        # Add domain event for update
        incident.domain_events.append({
            "event_type": "IncidentUpdated",
            "incident_id": incident.incident_id,
            "timestamp": timestamp,
            "confidence": confidence,
            "risk_score": risk_score
        })

        return incident

    def transition_state(
        self,
        incident: Incident,
        timestamp: float,
        new_state: IncidentState,
        reason: str
    ) -> Incident:
        """Transition incident state and log history entry."""
        if incident.current_state != new_state:
            incident.transition_state(timestamp, new_state, reason)

            # Record domain event
            event_name = "IncidentResolved" if new_state == IncidentState.RESOLVED else (
                "IncidentEscalated" if new_state == IncidentState.ESCALATED else "IncidentStateChanged"
            )
            incident.domain_events.append({
                "event_type": event_name,
                "incident_id": incident.incident_id,
                "previous_state": str(incident.current_state),
                "new_state": str(new_state),
                "timestamp": timestamp,
                "reason": reason
            })

        return incident

    def resolve_incident(
        self,
        incident: Incident,
        timestamp: float,
        reason: str = "Behavior episode resolved"
    ) -> Incident:
        """Resolve an active incident aggregate."""
        return self.transition_state(incident, timestamp, IncidentState.RESOLVED, reason)
