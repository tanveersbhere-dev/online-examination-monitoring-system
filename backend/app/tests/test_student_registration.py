import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from unittest.mock import patch

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
    examiner_role = await role_repo.create(name="Examiner")
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
    qp = QuestionPaper(title="Test Paper", course_name="CS101", file_path="dummy.pdf", uploaded_by=examiner.id)
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
        "exam_id": str(exam.id),
        "credential_expiry_date": (datetime.utcnow() + timedelta(days=7)).isoformat()
    }
    
    valid_jpeg = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\x7f\xff\xd9'
    files = {
        "face_image": ("dummy.jpg", valid_jpeg, "image/jpeg")
    }
    
    with patch("app.services.student_service.EmbeddingIdentityProcessor._extract_embedding", return_value=[0.1] * 512):
        resp = client.post("/api/v1/students/register", data=req_payload, files=files, headers={"Authorization": f"Bearer {token}"})
        
    if resp.status_code != 201:
        print(resp.text)
    assert resp.status_code == 201
    
    data = resp.json()
    assert data["full_name"] == "Jane Doe"
    assert data["email"] == "jane@student.com"
    assert "username" in data
    assert data["username"].startswith("STU-")
    assert data["account_status"] == "ACTIVE"
    
    student_id = data["id"]
    
    # Attempt Duplicate Email
    with patch("ai_engine.features.face_identity.embedding_processor.EmbeddingIdentityProcessor._extract_embedding", return_value=[0.1] * 512):
        resp_dup = client.post("/api/v1/students/register", data=req_payload, files=files, headers={"Authorization": f"Bearer {token}"})
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
