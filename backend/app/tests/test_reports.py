import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from main import app
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository
from app.models.exam import Exam
from app.models.exam_session import ExamSession
from app.models.violation import Violation
from app.models.ai_session import AISession
from app.services.password_service import PasswordService
from app.models.question_paper import QuestionPaper

@pytest_asyncio.fixture(scope="function")
async def setup_report_data(db_session: AsyncSession):
    # Setup Roles & Users
    role_repo = RoleRepository(db_session)
    examiner_role = await role_repo.create(name="EXAMINER")
    student_role = await role_repo.create(name="STUDENT")
    
    user_repo = UserRepository(db_session)
    examiner = await user_repo.create(
        role_id=examiner_role.id,
        full_name="Report Admin",
        email="admin@reports.com",
        password_hash=PasswordService.hash("password123"),
        is_active=True
    )
    student = await user_repo.create(
        role_id=student_role.id,
        full_name="John Doe",
        email="john@student.com",
        password_hash="hash",
        is_active=True
    )
    
    # Create Question Paper and Exam directly to bypass services
    qp = QuestionPaper(title="Test Paper", course_name="CS101", file_path="dummy.pdf", uploader_id=examiner.id)
    db_session.add(qp)
    await db_session.flush()

    exam = Exam(
        title="Final Exam",
        course_name="CS101",
        question_paper_id=qp.id,
        scheduled_start=datetime.utcnow() - timedelta(days=1),
        scheduled_end=datetime.utcnow(),
        duration_minutes=120,
        created_by=examiner.id,
        status="COMPLETED"
    )
    db_session.add(exam)
    await db_session.flush()

    # Create AI Session & ExamSession (COMPLETED)
    ai_session = AISession(exam_id=exam.id, status="INACTIVE")
    db_session.add(ai_session)
    await db_session.flush()

    exam_session = ExamSession(
        exam_id=exam.id,
        student_id=student.id,
        ai_session_id=ai_session.id,
        start_time=datetime.utcnow() - timedelta(minutes=60),
        end_time=datetime.utcnow(),
        status="COMPLETED"
    )
    db_session.add(exam_session)
    await db_session.flush()
    
    # Add Violations
    v1 = Violation(
        exam_session_id=exam_session.id,
        violation_type="PHONE_DETECTED",
        category="OBJECT",
        severity="HIGH",
        risk_score=85.0,
        timestamp=datetime.utcnow() - timedelta(minutes=45)
    )
    v2 = Violation(
        exam_session_id=exam_session.id,
        violation_type="GAZE_AWAY",
        category="GAZE",
        severity="LOW",
        risk_score=20.0,
        timestamp=datetime.utcnow() - timedelta(minutes=50) # Earlier than v1
    )
    db_session.add_all([v1, v2])
    await db_session.commit()
    
    return examiner, exam_session

@pytest.mark.asyncio
async def test_get_reports_list(client: TestClient, setup_report_data):
    examiner, exam_session = setup_report_data
    
    # Login
    login_resp = client.post("/api/v1/auth/login", json={
        "email": examiner.email,
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    
    # Get List
    resp = client.get("/api/v1/reports", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    
    data = resp.json()
    assert len(data) == 1
    
    summary = data[0]
    assert summary["exam_session_id"] == exam_session.id
    assert summary["total_violations"] == 2
    assert summary["final_risk_score"] == 85.0 # Max of 85.0 and 20.0
    assert summary["student_name"] == "John Doe"
    assert summary["exam_name"] == "Final Exam"

@pytest.mark.asyncio
async def test_get_report_details(client: TestClient, setup_report_data):
    examiner, exam_session = setup_report_data
    
    login_resp = client.post("/api/v1/auth/login", json={
        "email": examiner.email,
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    
    # Get Detailed Report
    resp = client.get(f"/api/v1/reports/{exam_session.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    
    data = resp.json()
    
    # 1. Student Info
    assert data["student_info"]["student_name"] == "John Doe"
    
    # 2. Session Summary
    assert data["session_summary"]["final_status"] == "COMPLETED"
    
    # 4. Risk Summary
    assert data["risk_summary"]["final_risk_score"] == 85.0
    assert data["risk_summary"]["highest_risk_level"] == "CRITICAL"
    assert data["risk_summary"]["average_risk_level"] == "HIGH" # (85+20)/2 = 52.5 -> HIGH
    
    # 5. Timeline Formatting (Should be ordered by timestamp asc)
    timeline = data["timeline"]
    assert len(timeline) == 2
    assert timeline[0]["violation_type"] == "GAZE_AWAY" # Earlier
    assert timeline[1]["violation_type"] == "PHONE_DETECTED" # Later
    
    # 7. Statistics
    stats = data["statistics"]
    assert stats["total_phone_detections"] == 1
    assert stats["total_looking_away"] == 1
    assert stats["total_multiple_person"] == 0
    assert stats["total_violations"] == 2
    
    # 8. Recommendation 
    # Because highest is CRITICAL, we expect:
    assert data["recommendation"] == "Strong Evidence of Suspicious Behaviour"
