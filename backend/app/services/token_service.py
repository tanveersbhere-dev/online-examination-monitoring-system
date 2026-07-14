from app.security.jwt_handler import create_access_token, create_refresh_token, decode_token
from app.schemas.token import Token
from app.core.config import settings
from typing import Dict, Any

class TokenService:
    """Service to handle token generation and revocation logic."""
    
    # In a full production app with stateful logout, this might interact with a Redis blacklist repository.
    # For now, it manages the standard stateless issuance.
    
    @staticmethod
    def issue_tokens(user_id: str, role_name: str) -> Token:
        access_token = create_access_token(subject=user_id, role=role_name)
        refresh_token = create_refresh_token(subject=user_id)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    @staticmethod
    def validate_token(token: str) -> Dict[str, Any]:
        return decode_token(token)

    @staticmethod
    def revoke_refresh_token(token: str) -> None:
        """
        Placeholder for stateful refresh token revocation.
        In a stateless JWT setup, this might just decode to verify validity, 
        but actually revoking requires a DB or Redis blacklist.
        """
        # E.g., blacklist_repo.add(token)
        pass
