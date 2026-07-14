import logging
from typing import List
from app.schemas.user_auth import UserResponse
from app.services.exceptions import AuthorizationError

logger = logging.getLogger(__name__)

class AuthorizationService:
    """Service to handle Role-Based Access Control logic."""
    
    @staticmethod
    def require_role(user: UserResponse, allowed_roles: List[str]) -> None:
        if not user.role or user.role.name not in allowed_roles:
            logger.warning(f"Unauthorized access attempt by user {user.id}. Required one of {allowed_roles}, got {user.role.name if user.role else 'None'}")
            raise AuthorizationError(f"User lacks required role to access this resource.")
