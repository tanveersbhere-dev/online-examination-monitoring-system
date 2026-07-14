from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.schemas.exam_session import ExamSessionResponse

class AISessionCreate(BaseModel):
    exam_session_id: int

class AISessionUpdate(BaseModel):
    state: Optional[str] = None
    current_risk: Optional[float] = None

class AISessionResponse(BaseModel):
    id: int
    session_uuid: str
    state: str
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    current_risk: float
    created_at: datetime
    updated_at: datetime
    
    exam_session: Optional[ExamSessionResponse] = None

    model_config = ConfigDict(from_attributes=True)
