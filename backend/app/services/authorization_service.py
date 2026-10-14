import logging
from typing import List
from app.schemas.user_auth import UserResponse
from app.services.exceptions import AuthorizationError

logger = logging.getLogger(__name__)

class AuthorizationService:
    """Service to handle Role-Based Access Control logic."""
    
    @staticmethod
    def require_role(user: UserResponse, allowed_roles: List[str]) -> None:
        user_role = user.role.name.upper() if (user and user.role and user.role.name) else None
        allowed_upper = [r.upper() for r in allowed_roles]
        if not user_role or user_role not in allowed_upper:
            logger.warning(f"Unauthorized access attempt by user {user.id if user else 'None'}. Required one of {allowed_roles}, got {user.role.name if user and user.role else 'None'}")
            raise AuthorizationError("User lacks required role to access this resource.")
