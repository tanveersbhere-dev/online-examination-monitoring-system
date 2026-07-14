from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.auth import LoginRequest, RefreshRequest, AuthResponse
from app.schemas.user_auth import UserResponse
from app.services.auth_service import AuthService
from app.services.exceptions import InvalidCredentialsError, TokenValidationError, AuthorizationError
from app.security.dependencies import get_current_user

router = APIRouter()

@router.post("/login", response_model=AuthResponse)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and issue JWTs."""
    try:
        auth_service = AuthService(db)
        return await auth_service.authenticate_user(login_data)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except AuthorizationError as e:
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
