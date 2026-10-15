"""
Incident Event Router for Incident Orchestration Engine.
Routes incoming lifecycle events to Factory, Repository, and Lifecycle Manager based on Matching Engine decisions.
"""
from typing import Dict, Any, Optional
from incident_intelligence.domain.incident import Incident
from incident_intelligence.domain.enums import IncidentState, IncidentSeverity
from incident_intelligence.domain.interfaces import IncidentRepositoryInterface
from incident_intelligence.orchestration.incident_factory import IncidentFactory
from incident_intelligence.orchestration.incident_lifecycle import IncidentLifecycleManager
from incident_intelligence.orchestration.incident_matching import IncidentMatchingEngine, MatchAction

class IncidentEventRouter:
    """Routes lifecycle event dictionaries to target execution handlers."""

    def __init__(
        self,
        repository: IncidentRepositoryInterface,
        factory: IncidentFactory,
        lifecycle_manager: IncidentLifecycleManager,
        matching_engine: IncidentMatchingEngine
    ):
        self.repository = repository
        self.factory = factory
        self.lifecycle_manager = lifecycle_manager
        self.matching_engine = matching_engine

    def route_event(self, event_data: Dict[str, Any]) -> Optional[Incident]:
        """Process incoming lifecycle event dictionary and update repository."""
        action, incident = self.matching_engine.determine_match_action(event_data)
        
        episode_id = event_data.get("violation_id") or event_data.get("episode_id")
        v_type = event_data.get("violation_type") or event_data.get("incident_type") or event_data.get("type", "BEHAVIOR_ANOMALY")
        category = event_data.get("violation_category") or event_data.get("category", "Security")
        title = event_data.get("title") or event_data.get("incident_title") or event_data.get("display_name")
        if not title or title in ("UNKNOWN_VIOLATION", "GENERAL_ANOMALY", "UNKNOWN", "Behavioral Incident"):
            from ai_engine.intelligence.behavior_engine.composite_behavior import format_composite_incident_title
            title = format_composite_incident_title(v_type, event_data.get("triggered_rules") or [v_type], [])
        desc = event_data.get("description") or f"Behavior episode {title} observed"
        ts = float(event_data.get("timestamp", 0.0))
        conf = float(event_data.get("confidence", event_data.get("risk_score", 0.0) / 100.0))
        risk = float(event_data.get("risk_score", 0.0))
        frame_num = int(event_data.get("frame_number", 1))

        if action == MatchAction.CREATE:
            new_incident = self.factory.create_incident(
                episode_id=episode_id,
                incident_type=v_type,
                category=category,
                title=title,
                description=desc,
                initial_confidence=conf,
                start_time=ts,
                triggered_rules=event_data.get("triggered_rules")
            )
            if risk > 0.0:
                new_incident.append_risk(ts, risk, frame_num)
            self.repository.save(new_incident)
            return new_incident

        elif action == MatchAction.UPDATE:
            assert incident is not None
            self.lifecycle_manager.update_incident(
                incident=incident,
                timestamp=ts,
                confidence=conf,
                risk_score=risk,
                frame_number=frame_num,
                reason=desc
            )
            # Check state transition if event explicitly mandates state change
            event_type = event_data.get("event_type") or event_data.get("transition")
            if event_type == "ESCALATED":
                self.lifecycle_manager.transition_state(incident, ts, IncidentState.ESCALATED, "Escalated severity")
            elif event_type == "RECOVERING":
                self.lifecycle_manager.transition_state(incident, ts, IncidentState.RECOVERING, "Transient signal loss")
            
            self.repository.save(incident)
            return incident

        elif action == MatchAction.RESUME:
            assert incident is not None
            self.lifecycle_manager.transition_state(incident, ts, IncidentState.ACTIVE, "Resumed active episode")
            self.lifecycle_manager.update_incident(
                incident=incident,
                timestamp=ts,
                confidence=conf,
                risk_score=risk,
                frame_number=frame_num,
                reason="Resumed episode"
            )
            self.repository.save(incident)
            return incident

        elif action == MatchAction.RESOLVE:
            assert incident is not None
            self.lifecycle_manager.resolve_incident(incident, ts, reason=desc)
            self.repository.save(incident)
            return incident

        return None
