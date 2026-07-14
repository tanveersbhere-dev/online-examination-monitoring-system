from pydantic import BaseModel

class CredentialData(BaseModel):
    """Data Transfer Object for moving sensitive plain-text credentials prior to hashing/emailing."""
    username: str
    password: str
