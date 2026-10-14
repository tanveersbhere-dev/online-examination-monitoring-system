import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository
from app.services.password_service import PasswordService

@pytest.mark.asyncio
async def test_student_archive_and_reactivate_lifecycle(client: TestClient, db_session: AsyncSession):
    # Setup examiner
    role_repo = RoleRepository(db_session)
    examiner_role = await role_repo.create(name="EXAMINER")
    
    user_repo = UserRepository(db_session)
    examiner = await user_repo.create(
        role_id=examiner_role.id,
        full_name="Prof. Lifecycle",
        email="lifecycle_examiner@test.com",
        password_hash=PasswordService.hash("password123"),
        is_active=True
    )

    login_resp = client.post("/api/v1/auth/login", json={
        "email": "lifecycle_examiner@test.com",
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Student (Status ACTIVE)
    create_resp = client.post("/api/v1/workspace/students", headers=headers, json={
        "registration_number": "STU-LIFECYCLE-001",
        "full_name": "Charlie Lifecycle",
        "email": "charlie.l@test.com",
        "department": "Computer Science"
    })
    assert create_resp.status_code == 201
    student_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "ACTIVE"

    # 2. Archive Student
    archive_resp = client.delete(f"/api/v1/workspace/students/{student_id}", headers=headers)
    assert archive_resp.status_code in [200, 204]

    # Verify status is ARCHIVED
    read_resp = client.get(f"/api/v1/workspace/students/{student_id}", headers=headers)
    assert read_resp.status_code == 200
    assert read_resp.json()["status"] == "ARCHIVED"

    # 3. Attempt Duplicate Archive (Must fail with 400)
    dup_archive = client.delete(f"/api/v1/workspace/students/{student_id}", headers=headers)
    assert dup_archive.status_code == 400
    assert dup_archive.json()["detail"] == "This student is already archived."

    # 4. Reactivate Student (ARCHIVED -> ACTIVE)
    reactivate_resp = client.post(f"/api/v1/workspace/students/{student_id}/reactivate", headers=headers)
    assert reactivate_resp.status_code == 200
    assert reactivate_resp.json()["status"] == "ACTIVE"

    # Verify status is back to ACTIVE
    read_active = client.get(f"/api/v1/workspace/students/{student_id}", headers=headers)
    assert read_active.status_code == 200
    assert read_active.json()["status"] == "ACTIVE"
