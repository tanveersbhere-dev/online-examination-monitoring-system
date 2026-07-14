from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime

class EvidenceCreate(BaseModel):
    violation_id: int
    file_path: str
    evidence_type: str
    timestamp: Optional[datetime] = None
    metadata_payload: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None

class EvidenceUpdate(BaseModel):
    # Mostly for updating metadata or fixing file_path if it moved, but rare
    file_path: Optional[str] = None
    metadata_payload: Optional[Dict[str, Any]] = None

class EvidenceResponse(BaseModel):
    id: int
    violation_id: int
    file_path: str
    evidence_type: str
    timestamp: datetime
    metadata_payload: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
