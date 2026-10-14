import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import json
import numpy as np
from unittest.mock import patch

from main import app
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository
from app.models.exam import Exam
from app.models.user import User
from app.models.question_paper import QuestionPaper
from app.services.password_service import PasswordService


@pytest_asyncio.fixture(scope="function")
async def setup_enrollment_data(db_session: AsyncSession):
    role_repo = RoleRepository(db_session)
    examiner_role = await role_repo.get_by_name("Examiner")
    if not examiner_role:
        examiner_role = await role_repo.create(name="Examiner")
    student_role = await role_repo.get_by_name("STUDENT")
    if not student_role:
        student_role = await role_repo.create(name="STUDENT")
    
    user_repo = UserRepository(db_session)
    examiner = await user_repo.create(
        role_id=examiner_role.id,
        full_name="Registration Admin",
        email="admin@register.com",
        password_hash=PasswordService.hash("password123"),
        is_active=True
    )
    
    # Create Exam
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


@pytest.mark.asyncio
async def test_student_enrollment_multipart(client: TestClient, setup_enrollment_data):
    examiner, exam = setup_enrollment_data
    
    login_resp = client.post("/api/v1/auth/login", json={
        "email": examiner.email,
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    
    import cv2
    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    _, img_encoded = cv2.imencode('.jpg', dummy_img)
    img_bytes = img_encoded.tobytes()

    req_data = {
        "full_name": "Enrollment Student",
        "email": "enroll@student.com",
        "exam_id": str(exam.id)
    }
    
    files = {
        "face_image": ("face.jpg", img_bytes, "image/jpeg")
    }

    with patch("app.monitoring_integration.face_embedding_service.FaceEmbeddingService.extract_embedding", return_value=[0.5, 0.5, 0.5, 0.5]):
        resp = client.post(
            "/api/v1/students/register", 
            data=req_data,
            files=files,
            headers={"Authorization": f"Bearer {token}"}
        )
    
    assert resp.status_code == 201
    data = resp.json()
    assert data["face_enrollment_status"] == True
    
    # Verify via API endpoint
    student_id = data["id"]
    get_resp = client.get(f"/api/v1/students/{student_id}", headers={"Authorization": f"Bearer {token}"})
    assert get_resp.status_code == 200
    assert get_resp.json()["face_enrollment_status"] == True
