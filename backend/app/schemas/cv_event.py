from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any

class CVEventIngestRequest(BaseModel):
    session_id: int = Field(..., description="The ID of the Exam Session")
    timestamp: float = Field(..., description="Unix timestamp of the event")
    event_type: str = Field(..., description="Raw string identifier of the CV event (e.g., 'mobile_phone')")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score bounded between 0.0 and 1.0")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary JSON metadata for the event")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": 1,
                "timestamp": 1784017134.0,
                "event_type": "mobile_phone",
                "confidence": 0.85,
                "metadata": {
                    "bounding_box": [10, 20, 100, 200]
                }
            }
        }
    )
