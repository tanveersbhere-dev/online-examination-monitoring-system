from app.core.config import Settings
import os

def test_settings_loading():
    """Verify settings correctly load from env variables or defaults."""
    # Temporarily set environment variables
    os.environ["PROJECT_NAME"] = "Test API"
    os.environ["BACKEND_CORS_ORIGINS"] = "http://test.local"
    
    settings = Settings()
    
    assert settings.PROJECT_NAME == "Test API"
    assert len(settings.BACKEND_CORS_ORIGINS) == 1
    assert "http://test.local" in str(settings.BACKEND_CORS_ORIGINS[0])
    
    # Cleanup
    del os.environ["PROJECT_NAME"]
    del os.environ["BACKEND_CORS_ORIGINS"]
