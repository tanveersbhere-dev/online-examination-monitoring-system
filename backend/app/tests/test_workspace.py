import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository
from app.services.password_service import PasswordService

@pytest_asyncio.fixture(scope="function")
async def setup_test_users(db_session: AsyncSession):
    role_repo = RoleRepository(db_session)
    student_role = await role_repo.create(name="STUDENT")
    examiner_role = await role_repo.create(name="EXAMINER")
    
    user_repo = UserRepository(db_session)
    student = await user_repo.create(
        role_id=student_role.id,
        full_name="Student Bob",
        email="student@test.com",
        password_hash=PasswordService.hash("password123"),
        is_active=True
    )
    
    examiner = await user_repo.create(
        role_id=examiner_role.id,
        full_name="Dr. Alice",
        email="examiner@test.com",
        password_hash=PasswordService.hash("password123"),
        is_active=True
    )
    
    return {"student": student, "examiner": examiner}

@pytest.mark.asyncio
async def test_get_dashboard_summary(client: TestClient, setup_test_users):
    # Setup users fixture creates 'examiner@test.com' with password 'password123'
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "examiner@test.com",
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    
    resp = client.get("/api/v1/workspace/dashboard/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "stats" in data
    assert "upcoming_exams" in data
    assert "recent_activities" in data
    assert "recent_notifications" in data
    assert "system_status" in data

@pytest.mark.asyncio
async def test_get_activities(client: TestClient, setup_test_users):
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "examiner@test.com",
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    
    resp = client.get("/api/v1/workspace/activities?limit=10", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

@pytest.mark.asyncio
async def test_get_notifications(client: TestClient, setup_test_users):
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "examiner@test.com",
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    
    resp = client.get("/api/v1/workspace/notifications", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

@pytest.mark.asyncio
async def test_preferences_lifecycle(client: TestClient, setup_test_users):
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "examiner@test.com",
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    
    # 1. Get preferences (should auto-create default if not exists)
    resp = client.get("/api/v1/workspace/preferences", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "theme" in data
    assert data["theme"] == "light" or data["theme"] == "system" # default
    
    # 2. Update preferences
    update_resp = client.put("/api/v1/workspace/preferences", headers={"Authorization": f"Bearer {token}"}, json={
        "theme": "dark",
        "sidebar_collapsed": True
    })
    assert update_resp.status_code == 200
    updated_data = update_resp.json()
    assert updated_data["theme"] == "dark"
    assert updated_data["sidebar_collapsed"] is True

@pytest.mark.asyncio
async def test_global_search(client: TestClient, setup_test_users):
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "examiner@test.com",
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    
    resp = client.get("/api/v1/workspace/search?q=test", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
