from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class QuestionPaperUpdate(BaseModel):
    title: Optional[str] = None
    course_name: Optional[str] = None

class QuestionPaperResponse(BaseModel):
    id: int
    title: str
    course_name: str
    uploaded_by: int
    file_path: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
