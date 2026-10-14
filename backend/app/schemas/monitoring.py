from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class MonitoringStatusResponse(BaseModel):
    exam_status: str
    ai_session_status: str
    current_risk_level: str
    current_risk_score: float
    current_student_status: str

class TimelineEventSchema(BaseModel):
    event_type: str
    timestamp: datetime
    severity: str
    description: str

class ViolationSchema(BaseModel):
    id: int
    violation_type: str
    severity: str
    timestamp: datetime

class MonitoringCurrentResponse(BaseModel):
    current_risk_score: float
    current_face_status: str
    current_gaze: str
    current_head_pose: str
    object_detection_summary: Dict[str, Any]
    environment_summary: Dict[str, Any]
    active_violations: List[ViolationSchema]
    timeline_events: List[TimelineEventSchema]

class ActiveMonitoringSessionItem(BaseModel):
    session_id: int
    exam_id: int
    exam_title: str
    student_id: int
    student_name: str
    student_reg_no: Optional[str] = None
    start_time: Optional[datetime] = None
    session_status: str
    monitoring_status: str
    current_risk: float
    risk_level: str
    active_violations_count: int
    total_violations_count: int
    latest_event: Optional[str] = None
    camera_status: str = "CONNECTED"

class MonitoringHealthResponse(BaseModel):
    exam_session_id: int
    thread_alive: bool
    monitoring_status: str
    frames_processed: int
    current_risk: float
    processor_health: Dict[str, Any] = {}
