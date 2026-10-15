"""
BookmarkManager and ReplayBookmark Model for Replay Intelligence Engine.
Manages immutable replay bookmarks.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional

@dataclass(frozen=True)
class ReplayBookmark:
    """Immutable replay bookmark."""
    bookmark_id: str
    timestamp: float
    frame_number: int
    target_type: str  # TIMELINE_EVENT, EVIDENCE, EXPLANATION, REASON_CODE, REVIEW_NOTE
    target_id: str
    label: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class BookmarkManager:
    """Manages collection of ReplayBookmark instances for a replay session."""

    def __init__(self):
        self._bookmarks: List[ReplayBookmark] = []
        self._by_id: Dict[str, ReplayBookmark] = {}

    def add_bookmark(self, bookmark: ReplayBookmark) -> None:
        """Add an immutable bookmark."""
        self._bookmarks.append(bookmark)
        self._by_id[bookmark.bookmark_id] = bookmark
        self._bookmarks.sort(key=lambda b: (b.timestamp, b.frame_number))

    def get_by_id(self, bookmark_id: str) -> Optional[ReplayBookmark]:
        """Fetch bookmark by bookmark_id."""
        return self._by_id.get(bookmark_id)

    def get_by_target_type(self, target_type: str) -> List[ReplayBookmark]:
        """Filter bookmarks by target_type."""
        return [b for b in self._bookmarks if b.target_type == target_type]

    def list_all(self) -> List[ReplayBookmark]:
        """List all bookmarks chronologically."""
        return list(self._bookmarks)
