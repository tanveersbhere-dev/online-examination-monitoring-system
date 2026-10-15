"""
Reason Code Generator for Explainability Engine.
Deterministically maps Incident state, timeline events, and metrics to stable ReasonCode objects.
"""
from typing import List, Dict, Any, Optional
from incident_intelligence.domain.incident import Incident
from incident_intelligence.timeline.timeline_event import TimelineEvent
from incident_intelligence.analytics.analytics_repository import IncidentAnalyticsSnapshot
from incident_intelligence.explainability.reason_codes import ReasonCode, ReasonCodeEnum, REASON_CODE_REGISTRY

class ReasonCodeGenerator:
    """Generates deterministic reason code lists from structured incident data."""

    def generate_reason_codes(
        self,
        incident: Incident,
        timeline_events: Optional[List[TimelineEvent]] = None,
        analytics_snapshot: Optional[IncidentAnalyticsSnapshot] = None
    ) -> List[ReasonCode]:
        """
        Generate deterministic list of ReasonCode objects.
        """
        codes: List[ReasonCode] = []
        code_keys: set = set()

        def add_code(key: str):
            if key not in code_keys and key in REASON_CODE_REGISTRY:
                code_keys.add(key)
                codes.append(REASON_CODE_REGISTRY[key])

        inc_type = incident.incident_type
        rules = incident.metadata.triggered_rules

        # Rule type mapping
        if (("PHONE" in inc_type and "EARPHONE" not in inc_type and "HEADPHONE" not in inc_type) or "UNAUTH_PHONE" in rules):
            add_code(ReasonCodeEnum.PHONE_VISIBLE.value)
            if incident.duration >= 5.0:
                add_code(ReasonCodeEnum.PHONE_LONG_DURATION.value)

        if "PERSON" in inc_type or "COMM_MULTIPLE_PERSONS" in rules:
            add_code(ReasonCodeEnum.MULTIPLE_PERSON.value)

        if "LOOKING_AWAY" in inc_type or "ATT_LOOKING_AWAY" in rules:
            add_code(ReasonCodeEnum.LOOKING_AWAY.value)

        if "DOWNWARD" in inc_type or "ATT_DOWNWARD_GAZE" in rules:
            add_code(ReasonCodeEnum.DOWNWARD_GAZE.value)

        if "PRESENTATION_ATTACK" in inc_type or "CONFIRMED_PRESENTATION_ATTACK" in rules:
            add_code(ReasonCodeEnum.PRESENTATION_ATTACK.value)

        if "BOOK" in inc_type or "NOTEBOOK" in inc_type or "PAPER" in inc_type or any(r in rules for r in ["UNAUTH_BOOK", "UNAUTH_NOTEBOOK", "UNAUTH_PAPER"]):
            add_code(ReasonCodeEnum.UNAUTHORIZED_MATERIAL.value)

        if "CAM_OCCLUDED" in inc_type or "ENV_CAM_OCCLUDED" in rules:
            add_code(ReasonCodeEnum.CAMERA_OCCLUSION.value)

        if "FACE_MISSING" in inc_type or "ID_FACE_MISSING" in rules:
            add_code(ReasonCodeEnum.FACE_MISSING.value)

        if "COMPOSITE" in inc_type or len(rules) > 1:
            add_code(ReasonCodeEnum.COMPOSITE_BEHAVIOR.value)

        # Timeline event analysis
        if timeline_events:
            for e in timeline_events:
                if e.event_type == "STATE_CHANGED" and e.new_state == "ESCALATED":
                    add_code(ReasonCodeEnum.ESCALATION_OCCURRED.value)
                elif e.event_type == "RESOLVED":
                    add_code(ReasonCodeEnum.RECOVERY_COMPLETED.value)

        # Analytics snapshot analysis
        if analytics_snapshot:
            if analytics_snapshot.metrics.escalation_count > 0:
                add_code(ReasonCodeEnum.ESCALATION_OCCURRED.value)

        return codes
