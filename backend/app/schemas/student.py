from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class StudentCreate(BaseModel):
    full_name: str
    father_name: Optional[str] = None
    email: EmailStr
    exam_id: int
    credential_expiry_date: Optional[datetime] = None

class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    father_name: Optional[str] = None
    account_status: Optional[str] = None

class StudentResponse(BaseModel):
    id: int
    full_name: str
    father_name: Optional[str]
    email: str
    username: str
    credential_expiry_date: Optional[datetime]
    account_status: str
    is_active: bool
    face_enrollment_status: bool = False
    registration_status: str = "SUCCESS"
    credential_delivery_status: str = "SENT"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        
    @classmethod
    def model_validate(cls, obj: any):
        m = super().model_validate(obj)
        if getattr(obj, "face_embedding", None):
            m.face_enrollment_status = True
        return m
