"""
ReviewerSummary Model and DTO for Explainability Engine.
Generates concise, human-readable proctor review summaries without speculation.
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

from incident_intelligence.domain.incident import Incident
from incident_intelligence.analytics.analytics_repository import IncidentAnalyticsSnapshot

@dataclass(frozen=True)
class ReviewerSummary:
    """Immutable human-readable reviewer summary."""
    incident_id: str
    title: str
    what_happened: str
    why_it_matters: str
    duration_formatted: str
    risk_assessment: str
    supporting_evidence_summary: str

    def to_dto(self) -> 'ReviewerSummaryDTO':
        return ReviewerSummaryDTO(
            incident_id=self.incident_id,
            title=self.title,
            what_happened=self.what_happened,
            why_it_matters=self.why_it_matters,
            duration_formatted=self.duration_formatted,
            risk_assessment=self.risk_assessment,
            supporting_evidence_summary=self.supporting_evidence_summary
        )

@dataclass(frozen=True)
class ReviewerSummaryDTO:
    """Data Transfer Object for ReviewerSummary."""
    incident_id: str
    title: str
    what_happened: str
    why_it_matters: str
    duration_formatted: str
    risk_assessment: str
    supporting_evidence_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def generate_reviewer_summary(
    incident: Incident,
    analytics_snapshot: Optional[IncidentAnalyticsSnapshot] = None
) -> ReviewerSummary:
    """Generate concise, deterministic proctor summary."""
    title = incident.metadata.title or incident.incident_type
    desc = incident.metadata.description or "Behavioral anomaly detected"

    # Category relevance
    cat = incident.metadata.category
    if cat == "Security":
        relevance = "Potential integrity anomaly requiring proctor audit."
    elif cat == "Identity":
        relevance = "Candidate identity verification fluctuation."
    elif cat == "Attention":
        relevance = "Off-screen candidate attention deviation."
    else:
        relevance = "Behavioral observation logged for session record."

    dur_str = f"{incident.duration:.1f} seconds"
    sev_str = str(incident.severity.value if hasattr(incident.severity, 'value') else incident.severity)
    risk_str = f"{sev_str} (Risk Score: {incident.current_risk:.1f})"

    ev_count = len(incident.evidence_references)
    ev_summary = f"{ev_count} keyframe asset(s) attached" if ev_count > 0 else "No keyframes attached"

    return ReviewerSummary(
        incident_id=incident.incident_id,
        title=title,
        what_happened=desc,
        why_it_matters=relevance,
        duration_formatted=dur_str,
        risk_assessment=risk_str,
        supporting_evidence_summary=ev_summary
    )
