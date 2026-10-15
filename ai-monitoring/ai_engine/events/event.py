from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from ai_engine.core.enums import EventType, Severity

@dataclass
class Event:
    event_id: str
    event_type: EventType
    timestamp: float
    severity: Severity
    source_module: str
    confidence: float
    payload: Dict[str, Any] = field(default_factory=dict)
    frame_id: Optional[int] = None
    session_id: str = ""
    student_id: str = ""
    correlation_id: Optional[str] = None

