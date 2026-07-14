from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, Optional
from datetime import datetime

class AIEventDTO(BaseModel):
    event_type: str
    timestamp: float  # Unix timestamp
    exam_session_id: int
    severity: str
    source_module: str
    confidence: float
    payload: Dict[str, Any]
    
    model_config = ConfigDict(from_attributes=True)
