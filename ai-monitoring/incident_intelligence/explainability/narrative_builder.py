"""
NarrativeBuilder for Explainability Engine.
Combines ReasonCodes, TechnicalExplanation, ReviewerSummary, and MachineExplanation into a deterministic package.
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import time

from incident_intelligence.domain.incident import Incident
from incident_intelligence.timeline.timeline_event import TimelineEvent
from incident_intelligence.analytics.analytics_repository import IncidentAnalyticsSnapshot
from incident_intelligence.explainability.reason_codes import ReasonCode
from incident_intelligence.explainability.reason_code_generator import ReasonCodeGenerator
from incident_intelligence.explainability.technical_explanation import TechnicalExplanation, TechnicalExplanationDTO, generate_technical_explanation
from incident_intelligence.explainability.reviewer_summary import ReviewerSummary, ReviewerSummaryDTO, generate_reviewer_summary
from incident_intelligence.explainability.machine_explanation import MachineExplanation, MachineExplanationDTO, generate_machine_explanation

@dataclass(frozen=True)
class IncidentExplanationPackage:
    """Immutable aggregate explanation package."""
    incident_id: str
    timestamp: float
    reason_codes: List[ReasonCode]
    technical_explanation: TechnicalExplanation
    reviewer_summary: ReviewerSummary
    machine_explanation: MachineExplanation
    deterministic_narrative: str

    def to_dto(self) -> 'IncidentExplanationPackageDTO':
        return IncidentExplanationPackageDTO(
            incident_id=self.incident_id,
            timestamp=self.timestamp,
            reason_codes=[rc.to_dict() for rc in self.reason_codes],
            technical_explanation=self.technical_explanation.to_dto(),
            reviewer_summary=self.reviewer_summary.to_dto(),
            machine_explanation=self.machine_explanation.to_dto(),
            deterministic_narrative=self.deterministic_narrative
        )

@dataclass(frozen=True)
class IncidentExplanationPackageDTO:
    """Data Transfer Object for IncidentExplanationPackage."""
    incident_id: str
    timestamp: float
    reason_codes: List[Dict[str, Any]]
    technical_explanation: TechnicalExplanationDTO
    reviewer_summary: ReviewerSummaryDTO
    machine_explanation: MachineExplanationDTO
    deterministic_narrative: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "timestamp": self.timestamp,
            "reason_codes": self.reason_codes,
            "technical_explanation": self.technical_explanation.to_dict(),
            "reviewer_summary": self.reviewer_summary.to_dict(),
            "machine_explanation": self.machine_explanation.to_dict(),
            "deterministic_narrative": self.deterministic_narrative
        }

class NarrativeBuilder:
    """Deterministic builder constructing comprehensive explanation packages."""

    def __init__(self):
        self.reason_code_generator = ReasonCodeGenerator()

    def build_explanation_package(
        self,
        incident: Incident,
        timeline_events: Optional[List[TimelineEvent]] = None,
        analytics_snapshot: Optional[IncidentAnalyticsSnapshot] = None
    ) -> IncidentExplanationPackage:
        """Build deterministic explanation package."""
        ts_now = time.time()

        # 1. Generate Reason Codes
        rc_list = self.reason_code_generator.generate_reason_codes(
            incident, timeline_events, analytics_snapshot
        )

        # 2. Generate Technical Explanation
        tech_exp = generate_technical_explanation(incident, timeline_events, analytics_snapshot)

        # 3. Generate Reviewer Summary
        rev_sum = generate_reviewer_summary(incident, analytics_snapshot)

        # 4. Generate Machine Explanation
        mach_exp = generate_machine_explanation(incident, rc_list, timeline_events, analytics_snapshot)

        # 5. Build Deterministic Narrative
        rc_descriptions = "; ".join(rc.description for rc in rc_list) if rc_list else "Behavior anomaly observed"
        title = incident.metadata.title or incident.incident_type
        narrative = (
            f"Incident {incident.incident_id} [{title}]: {rev_sum.what_happened}. "
            f"Evaluated for duration of {incident.duration:.1f}s with peak confidence {incident.peak_confidence:.2f}. "
            f"Reason Codes: ({rc_descriptions})."
        )

        return IncidentExplanationPackage(
            incident_id=incident.incident_id,
            timestamp=ts_now,
            reason_codes=rc_list,
            technical_explanation=tech_exp,
            reviewer_summary=rev_sum,
            machine_explanation=mach_exp,
            deterministic_narrative=narrative
        )
