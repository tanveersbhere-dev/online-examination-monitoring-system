"""
CasePackage Aggregate Model and DTO for Export & Reporting Engine.
Encapsulates complete investigation package components.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from incident_intelligence.domain.incident import IncidentDTO
from incident_intelligence.domain.evidence_reference import EvidenceReferenceDTO
from incident_intelligence.timeline.timeline_event import TimelineEventDTO
from incident_intelligence.analytics.analytics_repository import IncidentAnalyticsSnapshotDTO
from incident_intelligence.explainability.narrative_builder import IncidentExplanationPackageDTO
from incident_intelligence.review.review_package import ReviewPackageDTO
from incident_intelligence.replay.replay_session import ReplaySessionDTO
from incident_intelligence.export.export_manifest import ExportManifest, ExportManifestDTO

@dataclass(frozen=True)
class CasePackage:
    """Immutable aggregate CasePackage."""
    incident_dto: IncidentDTO
    evidence_references: List[EvidenceReferenceDTO]
    timeline_events: List[TimelineEventDTO]
    analytics_snapshot_dto: Optional[IncidentAnalyticsSnapshotDTO]
    explanation_package_dto: Optional[IncidentExplanationPackageDTO]
    review_package_dto: Optional[ReviewPackageDTO]
    replay_session_dto: Optional[ReplaySessionDTO]
    manifest: ExportManifest
    integrity_hash: str

    def to_dto(self) -> 'CasePackageDTO':
        return CasePackageDTO(
            incident_dto=self.incident_dto,
            evidence_references=list(self.evidence_references),
            timeline_events=list(self.timeline_events),
            analytics_snapshot_dto=self.analytics_snapshot_dto,
            explanation_package_dto=self.explanation_package_dto,
            review_package_dto=self.review_package_dto,
            replay_session_dto=self.replay_session_dto,
            manifest=self.manifest.to_dto(),
            integrity_hash=self.integrity_hash
        )

@dataclass(frozen=True)
class CasePackageDTO:
    """Data Transfer Object for CasePackage."""
    incident_dto: IncidentDTO
    evidence_references: List[EvidenceReferenceDTO]
    timeline_events: List[TimelineEventDTO]
    analytics_snapshot_dto: Optional[IncidentAnalyticsSnapshotDTO]
    explanation_package_dto: Optional[IncidentExplanationPackageDTO]
    review_package_dto: Optional[ReviewPackageDTO]
    replay_session_dto: Optional[ReplaySessionDTO]
    manifest: ExportManifestDTO
    integrity_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident": self.incident_dto.to_dict(),
            "evidence_references": [ref.to_dict() for ref in self.evidence_references],
            "timeline_events": [ev.to_dict() for ev in self.timeline_events],
            "analytics": self.analytics_snapshot_dto.to_dict() if self.analytics_snapshot_dto else None,
            "explanation": self.explanation_package_dto.to_dict() if self.explanation_package_dto else None,
            "review": self.review_package_dto.to_dict() if self.review_package_dto else None,
            "replay": self.replay_session_dto.to_dict() if self.replay_session_dto else None,
            "manifest": self.manifest.to_dict(),
            "integrity_hash": self.integrity_hash
        }
