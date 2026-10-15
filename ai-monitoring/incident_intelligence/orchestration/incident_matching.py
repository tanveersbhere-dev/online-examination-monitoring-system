"""
Incident Matching Engine for Incident Orchestration Engine.
Deterministically matches lifecycle events to existing Incident aggregates or determines new creation.
"""
from typing import Optional, Dict, Any, List
from incident_intelligence.domain.incident import Incident
from incident_intelligence.domain.interfaces import IncidentRepositoryInterface

class MatchAction:
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    RESUME = "RESUME"
    RESOLVE = "RESOLVE"
    IGNORE = "IGNORE"

class IncidentMatchingEngine:
    """Matches incoming lifecycle events to target Incident aggregates or creation actions."""

    def __init__(self, repository: IncidentRepositoryInterface):
        self.repository = repository

    def determine_match_action(self, event_data: Dict[str, Any]) -> tuple[str, Optional[Incident]]:
        """
        Analyze incoming lifecycle event dict and determine matching action and aggregate.
        Returns tuple: (MatchAction, Optional[Incident])
        """
        episode_id = event_data.get("violation_id") or event_data.get("episode_id")
        event_type = event_data.get("event_type") or event_data.get("transition")

        if not episode_id:
            return MatchAction.IGNORE, None

        # Look up existing incident by episode_id
        existing_incident = self.repository.get_by_episode_id(episode_id)

        if event_type == "STARTED":
            if existing_incident is not None:
                # Duplicate STARTED for active episode -> route as UPDATE to avoid duplicate creation
                return MatchAction.UPDATE, existing_incident
            return MatchAction.CREATE, None

        elif event_type in ("UPDATED", "ESCALATED", "RECOVERING"):
            if existing_incident is not None:
                status_str = str(existing_incident.status.value if hasattr(existing_incident.status, 'value') else existing_incident.status)
                if status_str == "RESOLVED":
                    return MatchAction.RESUME, existing_incident
                return MatchAction.UPDATE, existing_incident
            # Unknown UPDATE without prior STARTED -> create new aggregate for safety
            return MatchAction.CREATE, None

        elif event_type == "RESOLVED":
            if existing_incident is not None:
                return MatchAction.RESOLVE, existing_incident
            return MatchAction.IGNORE, None

        return MatchAction.IGNORE, None
