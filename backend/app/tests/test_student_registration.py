import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from main import app
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository
from app.models.exam import Exam
from app.models.user import User
from app.models.question_paper import QuestionPaper
from app.services.password_service import PasswordService
from app.services.credential_service import CredentialService
from app.services.exceptions import CredentialGenerationError

@pytest_asyncio.fixture(scope="function")
async def setup_registration_data(db_session: AsyncSession):
    # Setup Roles & Examiner
    role_repo = RoleRepository(db_session)
    examiner_role = await role_repo.create(name="EXAMINER")
    student_role = await role_repo.create(name="STUDENT")
    
    user_repo = UserRepository(db_session)
    examiner = await user_repo.create(
        role_id=examiner_role.id,
        full_name="Registration Admin",
        email="admin@register.com",
        password_hash=PasswordService.hash("password123"),
        is_active=True
    )
    
    # Create Question Paper and Exam
    qp = QuestionPaper(title="Test Paper", course_name="CS101", file_path="dummy.pdf", uploader_id=examiner.id)
    db_session.add(qp)
    await db_session.flush()

    exam = Exam(
        title="Final Exam",
        course_name="CS101",
        question_paper_id=qp.id,
        scheduled_start=datetime.utcnow() + timedelta(days=1),
        scheduled_end=datetime.utcnow() + timedelta(days=1, hours=2),
        duration_minutes=120,
        created_by=examiner.id,
        status="SCHEDULED"
    )
    db_session.add(exam)
    await db_session.commit()
    
    return examiner, exam

def test_credential_generation():
    username = CredentialService.generate_username()
    assert username.startswith("STU-")
    
    password = CredentialService.generate_password(12)
    assert len(password) == 12
    assert any(c.islower() for c in password)
    assert any(c.isupper() for c in password)
    assert any(c.isdigit() for c in password)
    assert any(c in "!@#$%^&*" for c in password)
    
    with pytest.raises(CredentialGenerationError):
        CredentialService.generate_password(8)

@pytest.mark.asyncio
async def test_student_registration_workflow(client: TestClient, setup_registration_data):
    examiner, exam = setup_registration_data
    
    login_resp = client.post("/api/v1/auth/login", json={
        "email": examiner.email,
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    
    # Register Student
    req_payload = {
        "full_name": "Jane Doe",
        "father_name": "John Doe Sr",
        "email": "jane@student.com",
        "exam_id": exam.id,
        "credential_expiry_date": (datetime.utcnow() + timedelta(days=7)).isoformat()
    }
    
    resp = client.post("/api/v1/students/register", json=req_payload, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    
    data = resp.json()
    assert data["full_name"] == "Jane Doe"
    assert data["email"] == "jane@student.com"
    assert "username" in data
    assert data["username"].startswith("STU-")
    assert data["account_status"] == "ACTIVE"
    
    student_id = data["id"]
    
    # Attempt Duplicate Email
    resp_dup = client.post("/api/v1/students/register", json=req_payload, headers={"Authorization": f"Bearer {token}"})
    assert resp_dup.status_code == 409
    
    # List Students
    resp_list = client.get("/api/v1/students", headers={"Authorization": f"Bearer {token}"})
    assert resp_list.status_code == 200
    assert len(resp_list.json()) == 1
    
    # Deactivate Student (Soft Delete)
    resp_del = client.delete(f"/api/v1/students/{student_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp_del.status_code == 204
    
    # Verify Deactivation
    resp_get = client.get(f"/api/v1/students/{student_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp_get.status_code == 200
    assert resp_get.json()["account_status"] == "DISABLED"
    assert resp_get.json()["is_active"] == False
