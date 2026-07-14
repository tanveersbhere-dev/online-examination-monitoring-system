from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenPayload(BaseModel):
    sub: Optional[str] = None # User ID
    role: Optional[str] = None
    exp: Optional[int] = None
