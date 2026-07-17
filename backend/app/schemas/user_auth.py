from pydantic import BaseModel, EmailStr
from typing import Optional

class RoleResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    phone_number: Optional[str] = None
    profile_picture_url: Optional[str] = None
    role: Optional[RoleResponse] = None

    class Config:
        from_attributes = True
