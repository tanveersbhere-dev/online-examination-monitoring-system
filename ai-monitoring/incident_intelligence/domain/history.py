"""
Immutable History Models and DTO for Confidence, Risk, and State Machine Transitions.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, List

@dataclass(frozen=True)
class ConfidenceHistoryEntry:
    timestamp: float
    confidence_value: float
    frame_number: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class RiskHistoryEntry:
    timestamp: float
    risk_score_value: float
    frame_number: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class StateHistoryEntry:
    timestamp: float
    previous_state: str
    new_state: str
    transition_reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class HistoryDTO:
    """Aggregated Data Transfer Object for incident history streams."""
    confidence_history: List[Dict[str, Any]]
    risk_history: List[Dict[str, Any]]
    state_history: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
