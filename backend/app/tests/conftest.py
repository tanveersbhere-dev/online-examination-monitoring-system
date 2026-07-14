import pytest
from fastapi.testclient import TestClient
from typing import AsyncGenerator
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from main import app
from app.core.config import settings
from app.database.session import get_db

@pytest.fixture
def override_settings():
    settings.TESTING = True
    settings.DEBUG = True
    yield settings
    settings.TESTING = False

# Mock DB Dependency
async def override_get_db() -> AsyncGenerator:
    class MockSession:
        async def execute(self, query):
            class MockResult:
                def scalar(self):
                    return 1
            return MockResult()
            
        async def commit(self): pass
        async def rollback(self): pass
        async def close(self): pass
        
    yield MockSession()

@pytest.fixture
def client(override_settings):
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
