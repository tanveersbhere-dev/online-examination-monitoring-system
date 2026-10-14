from pydantic import BaseModel, Field, validator
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
    
    # Association
    question_paper_id: Optional[int] = None

    # Configs
    total_marks: int = 100
    passing_marks: int = 50
    negative_marking: bool = False
    auto_submit: bool = True
    grace_period: int = 0
    late_join: int = 0
    randomization: bool = False

    monitoring_config: Optional[Dict[str, Any]] = None
    instructions: Optional[Dict[str, Any]] = None
    browser_rules: Optional[Dict[str, Any]] = None

    @validator('title', pre=True, always=True)
    def validate_title(cls, v):
        if v is not None:
            if not isinstance(v, str):
                raise ValueError("Title must be a string.")
            v_str = v.strip()
            if not v_str:
                raise ValueError("Title cannot be empty or whitespace only.")
            return v_str
        return v

    @validator('course_name', pre=True)
    def validate_course_name(cls, v):
        if v is not None and isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                raise ValueError("Course code/name cannot be empty or whitespace only.")
            return v_str
        return v

    @validator('description', pre=True)
    def validate_description(cls, v):
        if v is not None and isinstance(v, str):
            return v.strip()
        return v

    @validator('semester', pre=True)
    def validate_semester(cls, v):
        if v is None or v == '':
            return None
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return None
            if not v_str.isdigit():
                raise ValueError("Semester must be an integer between 1 and 8.")
            v = int(v_str)
        if not isinstance(v, int) or isinstance(v, bool) or v < 1 or v > 8:
            raise ValueError("Semester must be an integer between 1 and 8.")
        return v

    @validator('total_marks', pre=True, always=True)
    def validate_total_marks(cls, v):
        if v is not None:
            if isinstance(v, str):
                v_str = v.strip()
                if not v_str.isdigit():
                    raise ValueError("Total marks must be a positive integer greater than 0.")
                v = int(v_str)
            if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
                raise ValueError("Total marks must be a positive integer greater than 0.")
        return v

    @validator('passing_marks', pre=True, always=True)
    def validate_passing_marks(cls, v):
        if v is not None:
            if isinstance(v, str):
                v_str = v.strip()
                if not v_str.isdigit():
                    raise ValueError("Passing marks must be a non-negative integer.")
                v = int(v_str)
            if not isinstance(v, int) or isinstance(v, bool) or v < 0:
                raise ValueError("Passing marks must be a non-negative integer greater than or equal to 0.")
        return v

    @validator('duration_minutes', pre=True)
    def validate_duration_minutes(cls, v):
        if v is not None:
            if isinstance(v, float) and not v.is_integer():
                raise ValueError("Duration minutes must be an integer greater than 0.")
            if isinstance(v, str):
                v_str = v.strip()
                if not v_str.isdigit():
                    raise ValueError("Duration minutes must be a positive integer greater than 0.")
                v = int(v_str)
            if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
                raise ValueError("Duration minutes must be a positive integer greater than 0.")
        return v

    @validator('grace_period', 'late_join', pre=True)
    def validate_non_negative_ints(cls, v):
        if v is not None:
            if isinstance(v, float) and not v.is_integer():
                raise ValueError("Value must be a non-negative integer.")
            if isinstance(v, str):
                v_str = v.strip()
                if not v_str.isdigit():
                    raise ValueError("Value must be a non-negative integer.")
                v = int(v_str)
            if not isinstance(v, int) or isinstance(v, bool) or v < 0:
                raise ValueError("Value must be a non-negative integer.")
        return v

    @validator('passing_marks')
    def check_passing_less_than_total(cls, v, values):
        total = values.get('total_marks')
        if v is not None and total is not None and v > total:
            raise ValueError(f"Passing marks ({v}) cannot exceed total marks ({total}).")
        return v

    @validator('scheduled_end')
    def check_end_after_start(cls, v, values):
        start = values.get('scheduled_start')
        if v is not None and start is not None and v <= start:
            raise ValueError("Scheduled end time must be after scheduled start time.")
        return v

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
    assigned_students_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ExamAssignmentRequest(BaseModel):
    student_ids: List[int]

class ExamSupervisorRequest(BaseModel):
    supervisor_ids: List[int]
