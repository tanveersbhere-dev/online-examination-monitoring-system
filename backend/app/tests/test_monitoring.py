import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository
from app.services.password_service import PasswordService
from app.database.session import get_db
from main import app

@pytest_asyncio.fixture(scope="function")
async def setup_auth(db_session: AsyncSession):
    role_repo = RoleRepository(db_session)
    examiner_role = await role_repo.create(name="Examiner")
    
    user_repo = UserRepository(db_session)
    examiner = await user_repo.create(
        role_id=examiner_role.id,
        full_name="Dr. Monit",
        email="monit@test.com",
        password_hash=PasswordService.hash("password123"),
        is_active=True
    )
    return examiner

@pytest.mark.asyncio
async def test_monitoring_status_endpoint(client: TestClient, setup_auth):
    # Login
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "monit@test.com",
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    
    # Get Status
    resp = client.get("/api/v1/monitoring/status?exam_session_id=1", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["exam_status"] == "RUNNING"
    assert data["current_risk_score"] == 45.5

@pytest.mark.asyncio
async def test_monitoring_current_endpoint(client: TestClient, setup_auth):
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "monit@test.com",
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    
    # Get Current metrics
    resp = client.get("/api/v1/monitoring/current?exam_session_id=1", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_face_status"] == "ACTIVE"
    assert "object_detection_summary" in data

@pytest.mark.asyncio
async def test_empty_violations_and_evidence(client: TestClient, setup_auth):
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "monit@test.com",
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    
    v_resp = client.get("/api/v1/violations?exam_session_id=1", headers={"Authorization": f"Bearer {token}"})
    assert v_resp.status_code == 200
    assert isinstance(v_resp.json(), list)
    
    e_resp = client.get("/api/v1/evidence", headers={"Authorization": f"Bearer {token}"})
    assert e_resp.status_code == 200
    assert isinstance(e_resp.json(), list)
