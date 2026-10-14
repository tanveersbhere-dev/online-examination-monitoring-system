from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.schemas.exam_session import ExamSessionResponse

class AISessionCreate(BaseModel):
    exam_session_id: int
    monitoring_status: Optional[str] = "ACTIVE"

class AISessionUpdate(BaseModel):
    state: Optional[str] = None
    monitoring_status: Optional[str] = None
    frames_processed: Optional[int] = None
    current_risk: Optional[float] = None

class AISessionResponse(BaseModel):
    id: int
    session_uuid: str
    state: str
    monitoring_status: str = "ACTIVE"
    frames_processed: int = 0
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    current_risk: float
    created_at: datetime
    updated_at: datetime
    
    exam_session: Optional[ExamSessionResponse] = None

    model_config = ConfigDict(from_attributes=True)
