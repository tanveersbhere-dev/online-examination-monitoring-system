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

from app.schemas.runtime_rules import SectionRuleResponse

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
    ai_session_status: str = "INACTIVE"
    assigned_students_count: int = 0
    
    # Level 1 Rules
    allow_resume_after_disconnect: bool = True
    global_navigation: str = "FREE"
    randomize_sections: bool = False
    randomize_questions: bool = False
    allow_review_before_submit: bool = True
    show_remaining_time: bool = True
    show_question_numbers: bool = True
    show_marks: bool = True
    
    # Level 2 & 3 Rules
    section_rules: List[SectionRuleResponse] = []

    class Config:
        from_attributes = True
