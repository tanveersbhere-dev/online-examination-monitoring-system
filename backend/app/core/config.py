import json
import os
import sys
from typing import List, Union, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource
from pydantic import field_validator, model_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "Online Examination Monitoring System API"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    APP_TIMEZONE: str = "Asia/Karachi"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: Union[bool, str]) -> bool:
        if isinstance(v, str):
            v_lower = v.strip().lower()
            if v_lower in ("true", "1", "t", "yes", "y", "debug", "dev", "development", "release"):
                return True
            if v_lower in ("false", "0", "f", "no", "n", "prod", "production", ""):
                return False
        return bool(v)
    
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    parsed = json.loads(v_stripped)
                    if isinstance(parsed, list):
                        return [str(i).strip() for i in parsed if str(i).strip()]
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return [str(i).strip() for i in v if str(i).strip()]
        return []

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/exam_db"
    
    # JWT Auth
    SECRET_KEY: str = "super_secret_development_key_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # File Uploads
    UPLOAD_DIR: str = "uploads"
    
    # SMTP Email Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_FROM_EMAIL: Optional[str] = None
    
    # Feature Flags
    ENABLE_STUDENT_MONITORING_PREVIEW: bool = True

    # Testing override
    TESTING: bool = False

    @model_validator(mode="after")
    def validate_configuration(self) -> 'Settings':
        # Resolve SMTP sender address:
        # 1. If SMTP_FROM_EMAIL was explicitly set, it takes precedence.
        # 2. If SMTP_FROM was explicitly set, preserve it.
        # 3. Fall back to SMTP_FROM_EMAIL from env/default, then SMTP_FROM, then SMTP_USERNAME.
        if "SMTP_FROM_EMAIL" in self.model_fields_set and self.SMTP_FROM_EMAIL and self.SMTP_FROM_EMAIL.strip():
            self.SMTP_FROM = self.SMTP_FROM_EMAIL.strip()
        elif "SMTP_FROM" in self.model_fields_set and self.SMTP_FROM and self.SMTP_FROM.strip():
            pass
        elif self.SMTP_FROM_EMAIL and self.SMTP_FROM_EMAIL.strip():
            self.SMTP_FROM = self.SMTP_FROM_EMAIL.strip()
        elif not self.SMTP_FROM or not self.SMTP_FROM.strip():
            if self.SMTP_USERNAME and self.SMTP_USERNAME.strip():
                self.SMTP_FROM = self.SMTP_USERNAME.strip()
            else:
                self.SMTP_FROM = "no-reply@onlinesystem.com"

        insecure_defaults = [
            "super_secret_development_key_change_in_production",
            "secret",
            "changeme",
            "development_secret",
            "test_secret",
            ""
        ]
        if not self.DEBUG and not self.TESTING:
            if not self.SECRET_KEY or self.SECRET_KEY.strip() in insecure_defaults or len(self.SECRET_KEY.strip()) < 16:
                raise ValueError(
                    "Production Security Configuration Error: A strong, non-default SECRET_KEY must be "
                    "explicitly configured when running in production mode (DEBUG=False). Please configure a secure SECRET_KEY in your environment."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=(
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
            ".env"
        ),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
