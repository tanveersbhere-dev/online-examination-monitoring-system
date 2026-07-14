from app.security.password_hasher import verify_password, get_password_hash

class PasswordService:
    """Service to handle password validation policies and hashing."""
    
    @staticmethod
    def verify(plain_password: str, hashed_password: str) -> bool:
        return verify_password(plain_password, hashed_password)

    @staticmethod
    def hash(password: str) -> str:
        return get_password_hash(password)
