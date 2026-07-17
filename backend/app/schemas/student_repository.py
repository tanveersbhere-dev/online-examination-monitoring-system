from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class StudentRepoBase(BaseModel):
    registration_number: str = Field(..., max_length=100)
    full_name: str = Field(..., max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field("ACTIVE", max_length=50)
    
    roll_number: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    program: Optional[str] = Field(None, max_length=100)
    semester: Optional[int] = None
    batch: Optional[str] = Field(None, max_length=50)
    section: Optional[str] = Field(None, max_length=50)

class StudentRepoCreate(StudentRepoBase):
    pass

class StudentRepoUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=50)
    roll_number: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    program: Optional[str] = Field(None, max_length=100)
    semester: Optional[int] = None
    batch: Optional[str] = Field(None, max_length=50)
    section: Optional[str] = Field(None, max_length=50)

class StudentRepoResponse(StudentRepoBase):
    id: int
    uuid: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class StudentImportRow(BaseModel):
    registration_number: str
    full_name: str
    email: str
    phone: Optional[str] = None
    roll_number: Optional[str] = None
    department: Optional[str] = None
    program: Optional[str] = None
    semester: Optional[int] = None
    batch: Optional[str] = None
    section: Optional[str] = None

class ImportConflict(BaseModel):
    row_index: int
    registration_number: str
    reason: str
    suggested_resolution: str

class ImportPreviewResponse(BaseModel):
    total_rows: int
    valid_rows: int
    duplicates: int
    conflicts: List[ImportConflict]
    valid_data: List[StudentImportRow]

class BulkActionRequest(BaseModel):
    student_ids: List[int]
    action: str # "ARCHIVE", "RESTORE", "ACTIVATE", "DELETE"
