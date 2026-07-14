from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ReportSummaryItem(BaseModel):
    exam_session_id: int
    exam_name: str
    student_name: str
    date: Optional[datetime]
    duration_minutes: Optional[float]
    final_risk_score: float
    total_violations: int

class StudentInfo(BaseModel):
    student_name: str
    student_id: int
    email: str

class ExamInfo(BaseModel):
    exam_name: str
    course: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_minutes: Optional[float]

class SessionSummary(BaseModel):
    final_status: str
    total_monitoring_duration_minutes: Optional[float]
    ai_session_status: str

class RiskSummary(BaseModel):
    final_risk_score: float
    highest_risk_level: str
    average_risk_level: str
    total_violations: int

class ViolationTimelineItem(BaseModel):
    timestamp: datetime
    violation_type: str
    category: str
    severity: str
    risk_score: float
    short_description: Optional[str]

class EvidenceItem(BaseModel):
    timestamp: datetime
    evidence_type: str
    file_path: str

class EvidenceGalleryItem(BaseModel):
    violation_id: int
    snapshots: List[EvidenceItem]

class ReportStatistics(BaseModel):
    total_phone_detections: int = 0
    total_looking_away: int = 0
    total_identity_events: int = 0
    total_face_absence: int = 0
    total_multiple_person: int = 0
    total_earphone_events: int = 0
    total_snapshots: int = 0
    total_violations: int = 0
    highest_risk_score: float = 0.0
    average_risk_score: float = 0.0

class MonitoringReportResponse(BaseModel):
    exam_session_id: int
    student_info: StudentInfo
    exam_info: ExamInfo
    session_summary: SessionSummary
    risk_summary: RiskSummary
    timeline: List[ViolationTimelineItem]
    evidence_gallery: List[EvidenceGalleryItem]
    statistics: ReportStatistics
    recommendation: str
