from fastapi import Depends, HTTPException, status
from app.schemas.user_auth import UserResponse
from app.security.dependencies import get_current_user
from app.services.authorization_service import AuthorizationService
from app.services.exceptions import AuthorizationError

class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: UserResponse = Depends(get_current_user)) -> UserResponse:
        try:
            AuthorizationService.require_role(user, self.allowed_roles)
            return user
        except AuthorizationError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )

# Convenience Dependencies
RequireAuthenticated = Depends(get_current_user)
RequireExaminer = Depends(RoleChecker(["EXAMINER"]))
RequireStudent = Depends(RoleChecker(["STUDENT"]))
