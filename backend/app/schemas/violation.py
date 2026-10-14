from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

# Forward ref to EvidenceResponse if we have it. For now, empty list is fine.
# Actually we can do a minimal Evidence schema or omit it here if evidence has its own route.
# The prompt says: Every ORM entity returned to API responses MUST eagerly load required relationships.
# So we need at least a minimal EvidenceResponse
class EvidenceMinimalResponse(BaseModel):
    id: int
    file_path: str
    evidence_type: str
    timestamp: datetime
    is_primary: bool = False
    replay_clip_path: Optional[str] = None
    confidence_score: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)

class ViolationCreate(BaseModel):
    exam_session_id: int
    ai_session_id: Optional[int] = None
    violation_type: str
    category: str
    severity: str
    risk_score: float
    duration_seconds: float = 0.0
    confidence: Optional[float] = None
    external_violation_id: Optional[str] = None
    resolved_at: Optional[datetime] = None
    description: Optional[str] = None
    timestamp: Optional[datetime] = None

class ViolationUpdate(BaseModel):
    status: Optional[str] = None
    reviewer_notes: Optional[str] = None
    severity: Optional[str] = None
    risk_score: Optional[float] = None
    duration_seconds: Optional[float] = None
    confidence: Optional[float] = None
    resolved_at: Optional[datetime] = None
    description: Optional[str] = None

class ViolationResponse(BaseModel):
    id: int
    exam_session_id: int
    ai_session_id: Optional[int] = None
    violation_type: str
    category: str
    severity: str
    risk_score: float
    duration_seconds: float = 0.0
    confidence: Optional[float] = None
    external_violation_id: Optional[str] = None
    resolved_at: Optional[datetime] = None
    timestamp: datetime
    status: str
    description: Optional[str] = None
    reviewer_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    evidence: List[EvidenceMinimalResponse] = []

    model_config = ConfigDict(from_attributes=True)
