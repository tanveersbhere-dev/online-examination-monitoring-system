from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

class WSEventType(str, Enum):
    SESSION_STARTED = "SESSION_STARTED"
    SESSION_PAUSED = "SESSION_PAUSED"
    SESSION_RESUMED = "SESSION_RESUMED"
    SESSION_COMPLETED = "SESSION_COMPLETED"
    RISK_UPDATED = "RISK_UPDATED"
    VIOLATION_CREATED = "VIOLATION_CREATED"
    VIOLATION_UPDATED = "VIOLATION_UPDATED"
    FACE_STATUS_CHANGED = "FACE_STATUS_CHANGED"
    OBJECT_STATUS_CHANGED = "OBJECT_STATUS_CHANGED"
    STUDENT_STATUS_CHANGED = "STUDENT_STATUS_CHANGED"
    EVIDENCE_CAPTURED = "EVIDENCE_CAPTURED"
    HEARTBEAT = "HEARTBEAT"

class WSEvent(BaseModel):
    event: str
    timestamp: datetime
    exam_session_id: int
    payload: Dict[str, Any]
