import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository
from app.services.password_service import PasswordService


@pytest_asyncio.fixture(scope="function")
async def setup_student_repo_data(db_session: AsyncSession):
    role_repo = RoleRepository(db_session)
    examiner_role = await role_repo.create(name="EXAMINER")
    
    user_repo = UserRepository(db_session)
    examiner = await user_repo.create(
        role_id=examiner_role.id,
        full_name="Prof. Repo",
        email="repo_examiner@test.com",
        password_hash=PasswordService.hash("password123"),
        is_active=True
    )
    
    examiner2 = await user_repo.create(
        role_id=examiner_role.id,
        full_name="Prof. Other",
        email="other_examiner@test.com",
        password_hash=PasswordService.hash("password123"),
        is_active=True
    )
    
    return {"examiner": examiner, "examiner2": examiner2}

@pytest.mark.asyncio
async def test_student_repo_crud_lifecycle(client: TestClient, setup_student_repo_data):
    # 1. Login
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "repo_examiner@test.com",
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create Student
    create_resp = client.post("/api/v1/workspace/students", headers=headers, json={
        "registration_number": "STU-2026-001",
        "full_name": "Alice Wonderland",
        "email": "alice.w@test.com",
        "department": "Computer Science"
    })
    assert create_resp.status_code == 201
    student_data = create_resp.json()
    assert student_data["full_name"] == "Alice Wonderland"
    assert student_data["status"] == "ACTIVE"
    student_id = student_data["id"]
    
    # 3. Read Student
    read_resp = client.get(f"/api/v1/workspace/students/{student_id}", headers=headers)
    assert read_resp.status_code == 200
    assert read_resp.json()["email"] == "alice.w@test.com"
    
    # 4. Update Student
    update_resp = client.put(f"/api/v1/workspace/students/{student_id}", headers=headers, json={
        "department": "Software Engineering"
    })
    assert update_resp.status_code == 200
    assert update_resp.json()["department"] == "Software Engineering"
    
    # 5. List Students (with filter)
    list_resp = client.get("/api/v1/workspace/students?department=Software Engineering", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1
    
    # 6. Delete (Archive) Student
    del_resp = client.delete(f"/api/v1/workspace/students/{student_id}", headers=headers)
    assert del_resp.status_code == 204
    
    # 7. Read Student (should be archived)
    read_archived = client.get(f"/api/v1/workspace/students/{student_id}", headers=headers)
    assert read_archived.status_code == 200
    assert read_archived.json()["status"] == "ARCHIVED"

@pytest.mark.asyncio
async def test_student_repo_ownership_isolation(client: TestClient, setup_student_repo_data):
    # Login Examiner 1
    login_resp1 = client.post("/api/v1/auth/login", json={
        "email": "repo_examiner@test.com",
        "password": "password123"
    })
    token1 = login_resp1.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}
    
    # Create Student under Examiner 1
    create_resp = client.post("/api/v1/workspace/students", headers=headers1, json={
        "registration_number": "STU-2026-002",
        "full_name": "Bob Builder",
        "email": "bob@test.com",
        "department": "Civil Engineering"
    })
    assert create_resp.status_code == 201
    student_id = create_resp.json()["id"]
    
    # Login Examiner 2
    login_resp2 = client.post("/api/v1/auth/login", json={
        "email": "other_examiner@test.com",
        "password": "password123"
    })
    token2 = login_resp2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}
    
    # Try to Read Student as Examiner 2
    read_resp = client.get(f"/api/v1/workspace/students/{student_id}", headers=headers2)
    assert read_resp.status_code == 404
    
    # Try to Update Student as Examiner 2
    update_resp = client.put(f"/api/v1/workspace/students/{student_id}", headers=headers2, json={
        "department": "Software Engineering"
    })
    assert update_resp.status_code == 404
    
    # Try to Delete Student as Examiner 2
    del_resp = client.delete(f"/api/v1/workspace/students/{student_id}", headers=headers2)
    assert del_resp.status_code == 404

@pytest.mark.asyncio
async def test_student_repo_bulk_actions(client: TestClient, setup_student_repo_data):
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "repo_examiner@test.com",
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create 2 students
    client.post("/api/v1/workspace/students", headers=headers, json={
        "registration_number": "BULK-01",
        "full_name": "Bulk 1",
        "email": "bulk1@test.com"
    })
    client.post("/api/v1/workspace/students", headers=headers, json={
        "registration_number": "BULK-02",
        "full_name": "Bulk 2",
        "email": "bulk2@test.com"
    })
    
    list_resp = client.get("/api/v1/workspace/students?search=BULK", headers=headers)
    assert list_resp.json()["total"] == 2
    ids = [s["id"] for s in list_resp.json()["items"]]
    
    # Bulk Archive
    bulk_resp = client.post("/api/v1/workspace/students/bulk-action", headers=headers, json={
        "student_ids": ids,
        "action": "ARCHIVE"
    })
    assert bulk_resp.status_code == 200
    
    # Verify Archived
    list_archived = client.get("/api/v1/workspace/students?search=BULK", headers=headers)
    for s in list_archived.json()["items"]:
        assert s["status"] == "ARCHIVED"
