from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.auth import (
    LoginRequest, RefreshRequest, AuthResponse, RegisterRequest, OTPVerifyRequest, 
    ResendOTPRequest, ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest, 
    ProfileUpdateRequest, EmailChangeRequest
)
from app.schemas.user_auth import UserResponse
from app.services.auth_service import AuthService
from app.services.exceptions import InvalidCredentialsError, TokenValidationError, AuthorizationError
from app.security.dependencies import get_current_user

router = APIRouter()

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        auth_service = AuthService(db)
        return await auth_service.register(data)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/verify-email", response_model=AuthResponse)
async def verify_email(data: OTPVerifyRequest, db: AsyncSession = Depends(get_db)):
    try:
        auth_service = AuthService(db)
        return await auth_service.verify_email(data)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/resend-otp")
async def resend_otp(data: ResendOTPRequest, db: AsyncSession = Depends(get_db)):
    try:
        auth_service = AuthService(db)
        return await auth_service.resend_otp(data)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    return await auth_service.forgot_password(data)

@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        auth_service = AuthService(db)
        return await auth_service.reset_password(data)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login", response_model=AuthResponse)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and issue JWTs."""
    try:
        auth_service = AuthService(db)
        return await auth_service.authenticate_user(login_data)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except AuthorizationError as e:
        # e.g., Account is inactive
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

@router.post("/refresh", response_model=AuthResponse)
async def refresh(refresh_data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token using a valid refresh token."""
    try:
        auth_service = AuthService(db)
        return await auth_service.refresh_access_token(refresh_data.refresh_token)
    except TokenValidationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(refresh_data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Log out a user by invalidating their refresh token."""
    try:
        auth_service = AuthService(db)
        await auth_service.logout(refresh_data.refresh_token)
    except TokenValidationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    """Get the currently authenticated user."""
    return current_user

@router.put("/change-password")
async def change_password(
    data: ChangePasswordRequest, 
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        auth_service = AuthService(db)
        return await auth_service.change_password(current_user.id, data)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    data: ProfileUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        auth_service = AuthService(db)
        return await auth_service.update_profile(current_user.id, data)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/profile/email")
async def request_email_change(
    data: EmailChangeRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        auth_service = AuthService(db)
        return await auth_service.request_email_change(current_user.id, data)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/profile/email/verify", response_model=UserResponse)
async def verify_email_change(
    data: OTPVerifyRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        auth_service = AuthService(db)
        return await auth_service.verify_email_change(current_user.id, data)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
