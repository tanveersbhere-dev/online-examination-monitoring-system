"""
Incident Metadata Model and Data Transfer Object (DTO).
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List

@dataclass(frozen=True)
class IncidentMetadata:
    """Immutable metadata container for an incident."""
    category: str = "General"
    title: str = "Behavioral Incident"
    description: str = "Observed behavioral anomaly."
    triggered_rules: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    custom_attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dto(self) -> 'MetadataDTO':
        return MetadataDTO(
            category=self.category,
            title=self.title,
            description=self.description,
            triggered_rules=list(self.triggered_rules),
            tags=list(self.tags),
            custom_attributes=dict(self.custom_attributes)
        )

@dataclass(frozen=True)
class MetadataDTO:
    """Data Transfer Object for IncidentMetadata."""
    category: str
    title: str
    description: str
    triggered_rules: List[str]
    tags: List[str]
    custom_attributes: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
