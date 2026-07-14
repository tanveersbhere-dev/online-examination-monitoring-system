import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.auth import LoginRequest, AuthResponse
from app.schemas.user_auth import UserResponse, RoleResponse
from app.repositories.user_repository import UserRepository
from app.services.password_service import PasswordService
from app.services.token_service import TokenService
from app.services.exceptions import InvalidCredentialsError, TokenValidationError, AuthorizationError

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, db: AsyncSession):
        self.user_repo = UserRepository(db)

    async def authenticate_user(self, login_data: LoginRequest) -> AuthResponse:
        user = await self.user_repo.get_by_email(login_data.email)
        if not user:
            logger.warning(f"Failed login attempt for unknown user: {login_data.email}")
            raise InvalidCredentialsError("Invalid email or password.")
            
        if not user.is_active:
            logger.warning(f"Failed login attempt for inactive user: {login_data.email}")
            raise AuthorizationError("Account is inactive.")
            
        if not PasswordService.verify(login_data.password, user.password_hash):
            logger.warning(f"Failed login attempt (wrong password) for: {login_data.email}")
            raise InvalidCredentialsError("Invalid email or password.")

        role_name = user.role.name if user.role else "UNKNOWN"
        token = TokenService.issue_tokens(str(user.id), role_name)
        
        logger.info(f"Successful login for user: {login_data.email}")
        
        role_resp = RoleResponse(id=user.role.id, name=role_name) if user.role else None
        user_resp = UserResponse(id=user.id, email=user.email, full_name=user.full_name, is_active=user.is_active, role=role_resp)
        
        return AuthResponse(
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            token_type=token.token_type,
            expires_in=token.expires_in,
            user=user_resp
        )

    async def refresh_access_token(self, refresh_token: str) -> AuthResponse:
        try:
            payload = TokenService.validate_token(refresh_token)
            
            if payload.get("type") != "refresh":
                raise TokenValidationError("Invalid token type.")
                
            user_id_str = payload.get("sub")
            if not user_id_str:
                raise TokenValidationError("Token missing subject.")
                
            user_id = int(user_id_str)
            user = await self.user_repo.get_by_id(user_id)
            
            if not user or not user.is_active:
                raise AuthorizationError("User not found or inactive.")
                
            role_name = user.role.name if user.role else "UNKNOWN"
            new_token = TokenService.issue_tokens(str(user.id), role_name)
            
            logger.info(f"Token refreshed for user_id: {user.id}")
            
            role_resp = RoleResponse(id=user.role.id, name=role_name) if user.role else None
            user_resp = UserResponse(id=user.id, email=user.email, full_name=user.full_name, is_active=user.is_active, role=role_resp)
            
            return AuthResponse(
                access_token=new_token.access_token,
                refresh_token=new_token.refresh_token,
                token_type=new_token.token_type,
                expires_in=new_token.expires_in,
                user=user_resp
            )
            
        except ValueError:
            raise TokenValidationError("Invalid user identity format.")

    async def logout(self, refresh_token: str) -> None:
        try:
            # Ensure it's a valid token before revoking
            payload = TokenService.validate_token(refresh_token)
            user_id = payload.get("sub")
            TokenService.revoke_refresh_token(refresh_token)
            logger.info(f"Logout successful for user_id: {user_id}")
        except Exception as e:
            logger.error(f"Logout failed or token invalid: {e}")
            raise TokenValidationError("Invalid token during logout.")
