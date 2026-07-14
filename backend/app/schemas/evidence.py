from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class EvidenceResponse(BaseModel):
    id: int
    violation_id: int
    evidence_type: str
    file_path: str
    timestamp: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
