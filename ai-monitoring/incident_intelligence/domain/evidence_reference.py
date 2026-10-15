"""
Evidence Reference Model and Data Transfer Object (DTO).
Stores metadata references to captured keyframe evidence assets without storing raw images.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from incident_intelligence.domain.versions import EVIDENCE_SCHEMA_VERSION

@dataclass(frozen=True)
class EvidenceReference:
    """Immutable evidence reference object."""
    evidence_id: str
    frame_number: int
    timestamp: float
    uri: str
    importance: float = 0.5
    crop_type: str = "FULL_FRAME"
    schema_version: str = EVIDENCE_SCHEMA_VERSION

    def to_dto(self) -> 'EvidenceReferenceDTO':
        return EvidenceReferenceDTO(
            evidence_id=self.evidence_id,
            frame_number=self.frame_number,
            timestamp=self.timestamp,
            uri=self.uri,
            importance=self.importance,
            crop_type=self.crop_type,
            schema_version=self.schema_version
        )

@dataclass(frozen=True)
class EvidenceReferenceDTO:
    """Data Transfer Object for EvidenceReference."""
    evidence_id: str
    frame_number: int
    timestamp: float
    uri: str
    importance: float
    crop_type: str
    schema_version: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
