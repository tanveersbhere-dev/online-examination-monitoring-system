from pydantic import BaseModel, EmailStr, Field, validator
import re
from typing import Optional
from app.schemas.token import Token
from app.schemas.user_auth import UserResponse

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

def validate_password_complexity(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise ValueError("Password must contain at least one special character")
    return password

class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    password: str
    confirm_password: str
    phone_number: Optional[str] = None
    profile_picture_url: Optional[str] = None

    @validator("password")
    def password_valid(cls, v):
        return validate_password_complexity(v)

    @validator("confirm_password")
    def passwords_match(cls, v, values, **kwargs):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)

class ResendOTPRequest(BaseModel):
    email: EmailStr

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)
    new_password: str
    confirm_password: str

    @validator("new_password")
    def password_valid(cls, v):
        return validate_password_complexity(v)

    @validator("confirm_password")
    def passwords_match(cls, v, values, **kwargs):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("Passwords do not match")
        return v

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    @validator("new_password")
    def password_valid(cls, v):
        return validate_password_complexity(v)

    @validator("confirm_password")
    def passwords_match(cls, v, values, **kwargs):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("Passwords do not match")
        return v

class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=50)
    phone_number: Optional[str] = None
    profile_picture_url: Optional[str] = None

class EmailChangeRequest(BaseModel):
    new_email: EmailStr

