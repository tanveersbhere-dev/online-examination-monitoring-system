from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ViolationResponse(BaseModel):
    id: int
    exam_session_id: int
    violation_type: str
    category: str
    severity: str
    risk_score: float
    timestamp: datetime
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
