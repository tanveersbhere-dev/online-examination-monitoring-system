from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class QuestionPaperResponse(BaseModel):
    id: int
    title: str
    course_name: str
    uploaded_by: int
    file_path: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ExamCreate(BaseModel):
    title: str = Field(..., max_length=200)
    course_name: str = Field(..., max_length=100)
    question_paper_id: int
    scheduled_start: datetime
    scheduled_end: datetime
    duration_minutes: int = Field(..., gt=0)

    @validator('scheduled_end')
    def check_end_after_start(cls, v, values):
        if 'scheduled_start' in values and v <= values['scheduled_start']:
            raise ValueError("scheduled_end must be after scheduled_start")
        return v

class ExamUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, gt=0)

class AssignStudentsRequest(BaseModel):
    student_ids: List[int]

class ExamResponse(BaseModel):
    id: int
    title: str
    course_name: str
    status: str
    scheduled_start: datetime
    scheduled_end: datetime
    duration_minutes: int
    created_by: int
    question_paper: Optional[QuestionPaperResponse] = None
    created_at: datetime
    updated_at: datetime
    ai_session_status: str = "INACTIVE" # Appended for UI convenience, usually inferred from state
    assigned_students_count: int = 0

    class Config:
        from_attributes = True
