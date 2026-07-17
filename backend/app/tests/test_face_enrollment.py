import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import json
import numpy as np

from main import app
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository
from app.models.exam import Exam
from app.models.user import User
from app.models.question_paper import QuestionPaper
from app.services.password_service import PasswordService

from ai_engine.features.face_identity.embedding_processor import EmbeddingIdentityProcessor
from ai_engine.features.face_identity.models import FaceIdentityConfig
from ai_engine.core.exam_context import ExamContext, FaceInfo

@pytest_asyncio.fixture(scope="function")
async def setup_enrollment_data(db_session: AsyncSession):
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
    
    # Create Exam
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

def test_processor_embedding_injection():
    config = FaceIdentityConfig(enable_logging=False)
    processor = EmbeddingIdentityProcessor(config)
    processor.initialize()
    
    # Inject reference
    dummy_embedding = [0.1, 0.2, 0.3]
    processor.set_reference_embedding(dummy_embedding)
    assert processor._reference_embedding == dummy_embedding

    # Simulate face reappearance / tracking loss bypass
    context = ExamContext()
    context.face_info = FaceInfo(
        face_detected=True,
        face_count=1,
        confidence=0.9
    )
    
    # Normally we mock the extraction since insightface is heavy.
    # We just want to check if `_frames_since_last_check` correctly triggers.
    processor._frames_since_last_check = 0
    processor._last_tracking_id = "TRACK_000"
    
    try:
        processor.process(context)
    except Exception:
        pass # Ignore extraction errors from missing insightface model in CI
    
    assert processor._frames_since_last_check == config.verification_interval_frames
    assert processor._last_tracking_id == "TRACK_123"

@pytest.mark.asyncio
async def test_student_enrollment_multipart(client: TestClient, setup_enrollment_data, monkeypatch):
    examiner, exam = setup_enrollment_data
    
    # Mock InsightFace Processor to avoid CI crash
    async def mock_extract_embedding(*args, **kwargs):
        return [0.5, 0.5, 0.5, 0.5]
    
    monkeypatch.setattr(EmbeddingIdentityProcessor, "_extract_embedding", mock_extract_embedding)
    
    login_resp = client.post("/api/v1/auth/login", json={
        "email": examiner.email,
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    
    # Generate dummy image bytes (valid JPEG)
    # Just an empty numpy array converted to bytes
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

    resp = client.post(
        "/api/v1/students/register", 
        data=req_data,
        files=files,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert resp.status_code == 201
    data = resp.json()
    assert data["face_enrollment_status"] == True
    
    # Verify DB directly
    student_id = data["id"]
    from app.database.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        user_obj = await db.get(User, student_id)
        assert user_obj.face_embedding is not None
        emb = json.loads(user_obj.face_embedding)
        assert len(emb) == 4
        assert emb[0] == 0.5
