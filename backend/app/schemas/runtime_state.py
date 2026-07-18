from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class RuntimeStateBase(BaseModel):
    current_section_index: int = 0
    current_question_index: int = 0
    navigation_history: List[Dict[str, Any]] = Field(default_factory=list)
    completed_sections: List[int] = Field(default_factory=list)
    locked_sections: List[int] = Field(default_factory=list)
    locked_questions: List[int] = Field(default_factory=list)
    execution_flags: Dict[str, Any] = Field(default_factory=dict)

class RuntimeStateCreate(RuntimeStateBase):
    exam_session_id: int

class RuntimeStateUpdate(BaseModel):
    current_section_index: Optional[int] = None
    current_question_index: Optional[int] = None
    navigation_history: Optional[List[Dict[str, Any]]] = None
    completed_sections: Optional[List[int]] = None
    locked_sections: Optional[List[int]] = None
    locked_questions: Optional[List[int]] = None
    execution_flags: Optional[Dict[str, Any]] = None

class RuntimeStateResponse(RuntimeStateBase):
    id: int
    exam_session_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
