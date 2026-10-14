import random
import string
import secrets
from datetime import datetime
from app.schemas.credential import CredentialData
from app.services.exceptions import CredentialGenerationError
import logging

logger = logging.getLogger(__name__)

class CredentialService:
    @staticmethod
    def generate_password(length: int = 12) -> str:
        """Generates a secure random password with mixed requirements."""
        if length < 10:
            raise CredentialGenerationError("Password length must be at least 10 characters.")
        
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        while True:
            password = ''.join(secrets.choice(alphabet) for i in range(length))
            if (any(c.islower() for c in password)
                    and any(c.isupper() for c in password)
                    and any(c.isdigit() for c in password)
                    and any(c in "!@#$%^&*" for c in password)):
                return password

    @classmethod
    def provision_credentials(cls) -> CredentialData:
        try:
            return CredentialData(
                password=cls.generate_password()
            )
        except Exception as e:
            logger.error(f"Failed to provision credentials: {e}")
            raise CredentialGenerationError("Failed to generate secure credentials.") from e

