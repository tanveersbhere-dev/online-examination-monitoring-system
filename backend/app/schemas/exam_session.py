from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.schemas.exam import ExamResponse
from app.schemas.user_auth import UserResponse

class ExamSessionCreate(BaseModel):
    exam_id: int
    student_id: int

class ExamSessionUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None

class ExamSessionResponse(BaseModel):
    id: int
    exam_id: int
    student_id: int
    ai_session_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str
    
    exam: Optional[ExamResponse] = None
    student: Optional[UserResponse] = None
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
