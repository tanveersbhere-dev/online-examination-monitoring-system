"""
ReviewPackage Aggregate Model and DTO for Review Intelligence Engine.
Encapsulates read-only references to Incident, Evidence, Timeline, Analytics, and Explanations.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from incident_intelligence.domain.incident import IncidentDTO
from incident_intelligence.domain.evidence_reference import EvidenceReferenceDTO
from incident_intelligence.review.review_status import ReviewStatusEnum
from incident_intelligence.review.review_decision import ReviewDecisionEnum
from incident_intelligence.review.review_notes import ReviewNote, ReviewNoteDTO
from incident_intelligence.review.review_audit import ReviewAuditEntry, ReviewAuditEntryDTO

@dataclass
class ReviewPackage:
    """ReviewPackage holding read-only incident references and review metadata."""
    package_id: str
    incident_id: str
    created_timestamp: float
    last_updated_timestamp: float
    incident_dto: IncidentDTO
    evidence_references: List[EvidenceReferenceDTO] = field(default_factory=list)
    human_timeline_projection: Optional[Dict[str, Any]] = None
    analytics_snapshot_id: Optional[str] = None
    explanation_package_id: Optional[str] = None
    reason_codes: List[str] = field(default_factory=list)
    review_status: ReviewStatusEnum = ReviewStatusEnum.UNREVIEWED
    review_decision: ReviewDecisionEnum = ReviewDecisionEnum.NO_DECISION
    notes: List[ReviewNote] = field(default_factory=list)
    audit_trail: List[ReviewAuditEntry] = field(default_factory=list)
    package_version: str = "1.0.0"

    def update_decision(
        self,
        new_decision: ReviewDecisionEnum,
        timestamp: float,
        reason: str = "Decision updated"
    ) -> None:
        """Update review decision, set status to REVIEWED, and append to audit trail."""
        prev_dec = self.review_decision.value if hasattr(self.review_decision, 'value') else str(self.review_decision)
        new_dec_str = new_decision.value if hasattr(new_decision, 'value') else str(new_decision)

        self.review_decision = new_decision
        self.review_status = ReviewStatusEnum.REVIEWED
        self.last_updated_timestamp = timestamp

        entry = ReviewAuditEntry(
            entry_id=f"AUD-{len(self.audit_trail) + 1}",
            timestamp=timestamp,
            action="DECISION_CHANGED",
            details=f"Decision changed from '{prev_dec}' to '{new_dec_str}'. Reason: {reason}"
        )
        self.audit_trail.append(entry)

    def add_note(self, note: ReviewNote) -> None:
        """Add an immutable reviewer note and log audit entry."""
        self.notes.append(note)
        self.last_updated_timestamp = note.timestamp

        entry = ReviewAuditEntry(
            entry_id=f"AUD-{len(self.audit_trail) + 1}",
            timestamp=note.timestamp,
            action="NOTE_ADDED",
            details=f"Note added by author '{note.author}'"
        )
        self.audit_trail.append(entry)

    def set_under_review(self, timestamp: float) -> None:
        """Set review status to UNDER_REVIEW."""
        self.review_status = ReviewStatusEnum.UNDER_REVIEW
        self.last_updated_timestamp = timestamp

        entry = ReviewAuditEntry(
            entry_id=f"AUD-{len(self.audit_trail) + 1}",
            timestamp=timestamp,
            action="REVIEW_STARTED",
            details="Review session initiated"
        )
        self.audit_trail.append(entry)

    def to_dto(self) -> 'ReviewPackageDTO':
        """Convert ReviewPackage into pure Data Transfer Object."""
        return ReviewPackageDTO(
            package_id=self.package_id,
            incident_id=self.incident_id,
            created_timestamp=self.created_timestamp,
            last_updated_timestamp=self.last_updated_timestamp,
            incident_dto=self.incident_dto,
            evidence_references=list(self.evidence_references),
            human_timeline_projection=dict(self.human_timeline_projection) if self.human_timeline_projection else None,
            analytics_snapshot_id=self.analytics_snapshot_id,
            explanation_package_id=self.explanation_package_id,
            reason_codes=list(self.reason_codes),
            review_status=self.review_status.value if hasattr(self.review_status, 'value') else str(self.review_status),
            review_decision=self.review_decision.value if hasattr(self.review_decision, 'value') else str(self.review_decision),
            notes=[n.to_dto() for n in self.notes],
            audit_trail=[a.to_dto() for a in self.audit_trail],
            package_version=self.package_version
        )

@dataclass(frozen=True)
class ReviewPackageDTO:
    """Data Transfer Object for ReviewPackage."""
    package_id: str
    incident_id: str
    created_timestamp: float
    last_updated_timestamp: float
    incident_dto: IncidentDTO
    evidence_references: List[EvidenceReferenceDTO]
    human_timeline_projection: Optional[Dict[str, Any]]
    analytics_snapshot_id: Optional[str]
    explanation_package_id: Optional[str]
    reason_codes: List[str]
    review_status: str
    review_decision: str
    notes: List[ReviewNoteDTO]
    audit_trail: List[ReviewAuditEntryDTO]
    package_version: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert DTO to dictionary payload."""
        return {
            "package_id": self.package_id,
            "incident_id": self.incident_id,
            "created_timestamp": self.created_timestamp,
            "last_updated_timestamp": self.last_updated_timestamp,
            "incident": self.incident_dto.to_dict(),
            "evidence_references": [ref.to_dict() for ref in self.evidence_references],
            "human_timeline_projection": self.human_timeline_projection,
            "analytics_snapshot_id": self.analytics_snapshot_id,
            "explanation_package_id": self.explanation_package_id,
            "reason_codes": self.reason_codes,
            "review_status": self.review_status,
            "review_decision": self.review_decision,
            "notes": [n.to_dict() for n in self.notes],
            "audit_trail": [a.to_dict() for a in self.audit_trail],
            "package_version": self.package_version
        }
