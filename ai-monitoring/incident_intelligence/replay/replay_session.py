"""
ReplaySession Aggregate Model and DTO for Replay Intelligence Engine.
Aggregates FrameIndex, BookmarkManager, and read-only references to Incident domain data.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from incident_intelligence.domain.incident import IncidentDTO
from incident_intelligence.domain.evidence_reference import EvidenceReferenceDTO
from incident_intelligence.replay.frame_index import FrameIndex, FrameIndexEntry
from incident_intelligence.replay.bookmark_manager import BookmarkManager, ReplayBookmark

@dataclass
class ReplaySession:
    """Active replay navigation session state."""
    session_id: str
    incident_id: str
    current_frame_number: int
    current_timestamp: float
    frame_index: FrameIndex = field(default_factory=FrameIndex)
    bookmark_manager: BookmarkManager = field(default_factory=BookmarkManager)
    incident_dto: Optional[IncidentDTO] = None
    evidence_references: List[EvidenceReferenceDTO] = field(default_factory=list)
    analytics_snapshot_id: Optional[str] = None
    explanation_package_id: Optional[str] = None
    review_package_id: Optional[str] = None

    def seek_to_frame(self, frame_number: int) -> Optional[FrameIndexEntry]:
        """Seek session to specific frame number."""
        entry = self.frame_index.get_by_frame(frame_number)
        if entry:
            self.current_frame_number = entry.frame_number
            self.current_timestamp = entry.timestamp
        return entry

    def seek_to_timestamp(self, timestamp: float) -> Optional[FrameIndexEntry]:
        """Seek session to closest timestamp."""
        entry = self.frame_index.get_nearest_by_timestamp(timestamp)
        if entry:
            self.current_frame_number = entry.frame_number
            self.current_timestamp = entry.timestamp
        return entry

    def add_bookmark(self, bookmark: ReplayBookmark) -> None:
        """Add bookmark to session."""
        self.bookmark_manager.add_bookmark(bookmark)

    def to_dto(self) -> 'ReplaySessionDTO':
        """Convert session to pure DTO."""
        return ReplaySessionDTO(
            session_id=self.session_id,
            incident_id=self.incident_id,
            current_frame_number=self.current_frame_number,
            current_timestamp=self.current_timestamp,
            incident_dto=self.incident_dto,
            evidence_references=list(self.evidence_references),
            analytics_snapshot_id=self.analytics_snapshot_id,
            explanation_package_id=self.explanation_package_id,
            review_package_id=self.review_package_id,
            bookmarks=[b.to_dict() for b in self.bookmark_manager.list_all()]
        )

@dataclass(frozen=True)
class ReplaySessionDTO:
    """Data Transfer Object for ReplaySession."""
    session_id: str
    incident_id: str
    current_frame_number: int
    current_timestamp: float
    incident_dto: Optional[IncidentDTO]
    evidence_references: List[EvidenceReferenceDTO]
    analytics_snapshot_id: Optional[str]
    explanation_package_id: Optional[str]
    review_package_id: Optional[str]
    bookmarks: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "incident_id": self.incident_id,
            "current_frame_number": self.current_frame_number,
            "current_timestamp": self.current_timestamp,
            "incident": self.incident_dto.to_dict() if self.incident_dto else None,
            "evidence_references": [ref.to_dict() for ref in self.evidence_references],
            "analytics_snapshot_id": self.analytics_snapshot_id,
            "explanation_package_id": self.explanation_package_id,
            "review_package_id": self.review_package_id,
            "bookmarks": self.bookmarks
        }
