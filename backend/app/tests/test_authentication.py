import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from main import app
from app.database.session import get_db
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository
from app.services.password_service import PasswordService

@pytest_asyncio.fixture(scope="function")
async def setup_test_users(db_session: AsyncSession):
    # This assumes db_session fixture from conftest (like in test_repositories) is shared
    # For now we'll just insert users directly via Repositories
    
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
async def test_login_success(client: TestClient, setup_test_users):
    response = client.post("/api/v1/auth/login", json={
        "email": "student@test.com",
        "password": "password123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "student@test.com"
    assert data["user"]["role"]["name"] == "STUDENT"

@pytest.mark.asyncio
async def test_login_invalid_password(client: TestClient, setup_test_users):
    response = client.post("/api/v1/auth/login", json={
        "email": "student@test.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_login_unknown_user(client: TestClient, db_session):
    response = client.post("/api/v1/auth/login", json={
        "email": "ghost@test.com",
        "password": "password123"
    })
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_me_and_rbac(client: TestClient, setup_test_users):
    # 1. Login as Student
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "student@test.com",
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    
    # 2. Get Me
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "student@test.com"
    
    # 3. Test RBAC: We need a temporary route to test dependencies
    from app.security.permissions import RequireExaminer
    from fastapi import APIRouter, Depends
    
    test_router = APIRouter()
    @test_router.get("/test-examiner", dependencies=[RequireExaminer])
    def examiner_only(): return {"ok": True}
    
    app.include_router(test_router)
    
    # Student accessing examiner route -> 403 Forbidden
    rbac_resp = client.get("/test-examiner", headers={"Authorization": f"Bearer {token}"})
    assert rbac_resp.status_code == 403

@pytest.mark.asyncio
async def test_refresh_token(client: TestClient, setup_test_users):
    # 1. Login
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "student@test.com",
        "password": "password123"
    })
    refresh_token = login_resp.json()["refresh_token"]
    
    # 2. Refresh
    refresh_resp = client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()

@pytest.mark.asyncio
async def test_logout(client: TestClient, setup_test_users):
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "student@test.com",
        "password": "password123"
    })
    refresh_token = login_resp.json()["refresh_token"]
    
    logout_resp = client.post("/api/v1/auth/logout", json={
        "refresh_token": refresh_token
    })
    assert logout_resp.status_code == 204
