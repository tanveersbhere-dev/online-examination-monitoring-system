"""
ExportManifest Model and DTO for Export & Reporting Engine.
Stores package audit metadata and cryptographic integrity digest.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional

@dataclass(frozen=True)
class ExportManifest:
    """Immutable export manifest containing package provenance and hash."""
    package_uuid: str
    export_timestamp: float
    platform_version: str
    schema_versions: Dict[str, str]
    incident_id: str
    replay_id: Optional[str]
    analytics_snapshot_id: Optional[str]
    explanation_id: Optional[str]
    review_id: Optional[str]
    evidence_count: int
    timeline_count: int
    integrity_hash: str

    def to_dto(self) -> 'ExportManifestDTO':
        return ExportManifestDTO(
            package_uuid=self.package_uuid,
            export_timestamp=self.export_timestamp,
            platform_version=self.platform_version,
            schema_versions=dict(self.schema_versions),
            incident_id=self.incident_id,
            replay_id=self.replay_id,
            analytics_snapshot_id=self.analytics_snapshot_id,
            explanation_id=self.explanation_id,
            review_id=self.review_id,
            evidence_count=self.evidence_count,
            timeline_count=self.timeline_count,
            integrity_hash=self.integrity_hash
        )

@dataclass(frozen=True)
class ExportManifestDTO:
    """Data Transfer Object for ExportManifest."""
    package_uuid: str
    export_timestamp: float
    platform_version: str
    schema_versions: Dict[str, str]
    incident_id: str
    replay_id: Optional[str]
    analytics_snapshot_id: Optional[str]
    explanation_id: Optional[str]
    review_id: Optional[str]
    evidence_count: int
    timeline_count: int
    integrity_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
