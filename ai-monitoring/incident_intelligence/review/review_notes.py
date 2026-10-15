"""
ReviewNote Model and DTO for Review Intelligence Engine.
Stores immutable reviewer annotations without user database dependencies.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass(frozen=True)
class ReviewNote:
    """Immutable reviewer note entry."""
    note_id: str
    timestamp: float
    author: str
    text: str

    def to_dto(self) -> 'ReviewNoteDTO':
        return ReviewNoteDTO(
            note_id=self.note_id,
            timestamp=self.timestamp,
            author=self.author,
            text=self.text
        )

@dataclass(frozen=True)
class ReviewNoteDTO:
    """Data Transfer Object for ReviewNote."""
    note_id: str
    timestamp: float
    author: str
    text: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
