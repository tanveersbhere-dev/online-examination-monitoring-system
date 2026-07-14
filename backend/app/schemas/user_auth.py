from pydantic import BaseModel, EmailStr
from typing import Optional

class RoleResponse(BaseModel):
    id: int
    name: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    role: Optional[RoleResponse] = None

    class Config:
        from_attributes = True
