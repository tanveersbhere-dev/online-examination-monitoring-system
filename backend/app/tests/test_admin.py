import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository
from app.services.password_service import PasswordService
from app.models.system_setting import SystemSetting
from sqlalchemy import text

@pytest_asyncio.fixture(scope="function")
async def setup_admin_data(db_session: AsyncSession):
    # Setup Roles & Users
    role_repo = RoleRepository(db_session)
    admin_role = await role_repo.create(name="Admin")
    examiner_role = await role_repo.create(name="Examiner")

    user_repo = UserRepository(db_session)
    admin_user = await user_repo.create(
        role_id=admin_role.id,
        full_name="Super Admin",
        email="superadmin@admin.com",
        password_hash=PasswordService.hash("adminpass"),
        is_active=True
    )
    examiner = await user_repo.create(
        role_id=examiner_role.id,
        full_name="Normal Examiner",
        email="examiner@admin.com",
        password_hash=PasswordService.hash("examinerpass"),
        is_active=True
    )
    
    # Create some settings
    setting = SystemSetting(
        key="TEST_SETTING",
        value="initial_value",
        description="A test setting",
        is_public=False
    )
    db_session.add(setting)
    await db_session.commit()

    return admin_user, examiner

@pytest.mark.asyncio
async def test_admin_dashboard(client: TestClient, setup_admin_data):
    admin_user, examiner = setup_admin_data

    # Login Admin
    login_resp = client.post("/api/v1/auth/login", json={
        "email": admin_user.email,
        "password": "adminpass"
    })
    token = login_resp.json()["access_token"]

    # Access Dashboard
    resp = client.get("/api/v1/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_users" in data
    assert "active_sessions" in data
    assert "system_health" in data

@pytest.mark.asyncio
async def test_admin_logs(client: TestClient, setup_admin_data):
    admin_user, examiner = setup_admin_data

    login_resp = client.post("/api/v1/auth/login", json={
        "email": admin_user.email,
        "password": "adminpass"
    })
    token = login_resp.json()["access_token"]

    resp = client.get("/api/v1/admin/logs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_admin_settings_update(client: TestClient, setup_admin_data):
    admin_user, examiner = setup_admin_data

    # Login Admin
    login_resp = client.post("/api/v1/auth/login", json={
        "email": admin_user.email,
        "password": "adminpass"
    })
    token = login_resp.json()["access_token"]

    # Get Settings
    resp = client.get("/api/v1/admin/settings", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    settings = resp.json()
    assert len(settings) > 0
    assert any(s["key"] == "TEST_SETTING" for s in settings)

    # Update Setting
    resp = client.put(
        "/api/v1/admin/settings/TEST_SETTING",
        headers={"Authorization": f"Bearer {token}"},
        json={"value": "new_value", "description": "Updated description"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["value"] == "new_value"

@pytest.mark.asyncio
async def test_admin_authorization_failure(client: TestClient, setup_admin_data):
    admin_user, examiner = setup_admin_data

    # Login Examiner (Not Admin)
    login_resp = client.post("/api/v1/auth/login", json={
        "email": examiner.email,
        "password": "examinerpass"
    })
    token = login_resp.json()["access_token"]

    # Access Dashboard
    resp = client.get("/api/v1/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403

    # Update Settings
    resp = client.put(
        "/api/v1/admin/settings/TEST_SETTING",
        headers={"Authorization": f"Bearer {token}"},
        json={"value": "hacked"}
    )
    assert resp.status_code == 403
