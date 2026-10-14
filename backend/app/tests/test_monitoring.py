import pytest
import pytest_asyncio
import numpy as np
import time
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository
from app.services.password_service import PasswordService
from app.models.exam import Exam
from app.models.exam_session import ExamSession
from app.models.question_paper import QuestionPaper

@pytest_asyncio.fixture(scope="function")
async def setup_auth(db_session: AsyncSession):
    role_repo = RoleRepository(db_session)
    examiner_role = await role_repo.get_by_name("Examiner")
    if not examiner_role:
        examiner_role = await role_repo.create(name="Examiner")
    student_role = await role_repo.get_by_name("Student")
    if not student_role:
        student_role = await role_repo.create(name="Student")
    
    user_repo = UserRepository(db_session)
    examiner = await user_repo.create(
        role_id=examiner_role.id,
        full_name="Dr. Monit",
        email="monit@test.com",
        password_hash=PasswordService.hash("password123"),
        is_active=True
    )
    student = await user_repo.create(
        role_id=student_role.id,
        full_name="Candidate Student",
        email="student@test.com",
        password_hash="hash",
        is_active=True
    )

    qp = QuestionPaper(title="Test Paper", course_name="CS101", file_path="dummy.pdf", uploaded_by=examiner.id)
    db_session.add(qp)
    await db_session.flush()

    exam = Exam(
        title="Live Monitoring Exam",
        course_name="CS101",
        description="Exam",
        duration_minutes=60,
        total_marks=100.0,
        passing_marks=50.0,
        scheduled_start=datetime.utcnow() - timedelta(days=1),
        scheduled_end=datetime.utcnow() + timedelta(days=1),
        created_by=examiner.id,
        question_paper_id=qp.id
    )
    db_session.add(exam)
    await db_session.flush()

    exam_session = ExamSession(
        exam_id=exam.id,
        student_id=student.id,
        status="RUNNING",
        start_time=datetime.utcnow()
    )
    db_session.add(exam_session)
    await db_session.commit()

    return examiner, exam_session

@pytest.mark.asyncio
async def test_monitoring_status_endpoint(client: TestClient, setup_auth):
    examiner, exam_session = setup_auth
    login_resp = client.post("/api/v1/auth/login", json={
        "email": examiner.email,
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    
    resp = client.get(f"/api/v1/monitoring/status?exam_session_id={exam_session.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "exam_status" in data
    assert "current_risk_level" in data

@pytest.mark.asyncio
async def test_monitoring_current_endpoint(client: TestClient, setup_auth):
    examiner, exam_session = setup_auth
    login_resp = client.post("/api/v1/auth/login", json={
        "email": examiner.email,
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    
    resp = client.get(f"/api/v1/monitoring/current?exam_session_id={exam_session.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "current_risk_score" in data
    assert "active_violations" in data

@pytest.mark.asyncio
async def test_active_monitoring_sessions_endpoint(client: TestClient, setup_auth):
    examiner, exam_session = setup_auth
    login_resp = client.post("/api/v1/auth/login", json={
        "email": examiner.email,
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    
    resp = client.get("/api/v1/monitoring/active-sessions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_session_health_endpoint(client: TestClient, setup_auth):
    examiner, exam_session = setup_auth
    login_resp = client.post("/api/v1/auth/login", json={
        "email": examiner.email,
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    
    resp = client.get(f"/api/v1/monitoring/health/{exam_session.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["exam_session_id"] == exam_session.id
    assert "thread_alive" in data
    assert "frames_processed" in data

@pytest.mark.asyncio
async def test_empty_violations_and_evidence(client: TestClient, setup_auth):
    examiner, exam_session = setup_auth
    login_resp = client.post("/api/v1/auth/login", json={
        "email": examiner.email,
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    
    v_resp = client.get(f"/api/v1/violations?exam_session_id={exam_session.id}", headers={"Authorization": f"Bearer {token}"})
    assert v_resp.status_code == 200
    assert isinstance(v_resp.json(), list)
    
    e_resp = client.get("/api/v1/evidence", headers={"Authorization": f"Bearer {token}"})
    assert e_resp.status_code == 200
    assert isinstance(e_resp.json(), list)
