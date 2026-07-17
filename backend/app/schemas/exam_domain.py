from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ExamBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    course_name: Optional[str] = Field(None, max_length=255)
    subject: Optional[str] = Field(None, max_length=255)
    semester: Optional[int] = None
    session_name: Optional[str] = Field(None, max_length=100)
    
    # Schedule
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    timezone: str = Field("UTC", max_length=50)

    # Configs
    passing_marks: int = 50
    total_marks: int = 100
    negative_marking: bool = False
    auto_submit: bool = True
    grace_period: int = 0
    late_join: int = 0
    randomization: bool = False

    monitoring_config: Optional[Dict[str, Any]] = None
    instructions: Optional[Dict[str, Any]] = None
    browser_rules: Optional[Dict[str, Any]] = None

class ExamCreate(ExamBase):
    pass

class ExamUpdate(ExamBase):
    title: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, max_length=50)
    question_paper_id: Optional[int] = None

class ExamResponse(ExamBase):
    id: int
    uuid: str
    exam_code: str
    status: str
    created_by: int
    question_paper_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ExamAssignmentRequest(BaseModel):
    student_ids: List[int]

class ExamSupervisorRequest(BaseModel):
    supervisor_ids: List[int]
