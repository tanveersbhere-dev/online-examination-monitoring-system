from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

class CandidateAnswerBase(BaseModel):
    section_index: int
    question_index: int
    answer_data: Dict[str, Any] = Field(default_factory=dict)
    answer_status: str = "NOT_ANSWERED"
    is_submitted: bool = False
    awarded_marks: Optional[float] = None
    examiner_comments: Optional[str] = None

class CandidateAnswerCreate(CandidateAnswerBase):
    pass

class CandidateAnswerUpdate(BaseModel):
    answer_data: Optional[Dict[str, Any]] = None
    answer_status: Optional[str] = None
    is_submitted: Optional[bool] = None

class CandidateAnswerResponse(CandidateAnswerBase):
    id: int
    exam_session_id: int
    submission_count: int
    last_saved_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
