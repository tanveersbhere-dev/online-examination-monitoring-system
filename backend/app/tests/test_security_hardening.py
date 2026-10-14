import pytest
import os
import asyncio
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from starlette.websockets import WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from main import app
from app.core.config import Settings
from app.database.session import get_db
from app.models.role import Role
from app.models.user import User
from app.models.student import Student
from app.models.exam import Exam
from app.models.exam_session import ExamSession
from app.models.violation import Violation
from app.models.evidence import Evidence
from app.models.question_paper import QuestionPaper
from app.models.exam_assignment import ExamAssignment
from app.security.jwt_handler import create_access_token
from app.websocket.connection_manager import manager


async def setup_security_data(db_session: AsyncSession):
    """Setup roles, examiners, students, exams, question papers, and evidence safely."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # 1. Get or create Roles
    res = await db_session.execute(select(Role))
    roles = {r.name: r for r in res.scalars().all()}
    
    if "Admin" not in roles:
        admin_role = Role(name="Admin", description="Admin role")
        examiner_role = Role(name="Examiner", description="Examiner role")
        student_role = Role(name="Student", description="Student role")
        db_session.add_all([admin_role, examiner_role, student_role])
        await db_session.flush()
        roles = {"Admin": admin_role, "Examiner": examiner_role, "Student": student_role}
    
    admin_role = roles["Admin"]
    examiner_role = roles["Examiner"]
    student_role = roles["Student"]

    # 2. Get or create Users
    res_u = await db_session.execute(select(User))
    users = {u.username: u for u in res_u.scalars().all()}

    if "admin_test" not in users:
        admin_user = User(
            role_id=admin_role.id,
            full_name="Admin User",
            email="admin@test.com",
            username="admin_test",
            password_hash="hash",
            is_active=True
        )
        examiner1 = User(
            role_id=examiner_role.id,
            full_name="Examiner One",
            email="examiner1@test.com",
            username="examiner1",
            password_hash="hash",
            is_active=True
        )
        examiner2 = User(
            role_id=examiner_role.id,
            full_name="Examiner Two",
            email="examiner2@test.com",
            username="examiner2",
            password_hash="hash",
            is_active=True
        )
        student1_user = User(
            role_id=student_role.id,
            full_name="Student One",
            email="student1@test.com",
            username="student1",
            password_hash="hash",
            is_active=True
        )
        student2_user = User(
            role_id=student_role.id,
            full_name="Student Two",
            email="student2@test.com",
            username="student2",
            password_hash="hash",
            is_active=True
        )
        db_session.add_all([admin_user, examiner1, examiner2, student1_user, student2_user])
        await db_session.flush()
        users = {
            "admin_test": admin_user,
            "examiner1": examiner1,
            "examiner2": examiner2,
            "student1": student1_user,
            "student2": student2_user
        }

    admin_user = users["admin_test"]
    examiner1 = users["examiner1"]
    examiner2 = users["examiner2"]
    student1_user = users["student1"]
    student2_user = users["student2"]

    # 3. Create Physical Files for testing
    upload_dir = os.path.abspath("uploads")
    os.makedirs(os.path.join(upload_dir, "question_papers"), exist_ok=True)
    os.makedirs(os.path.join(upload_dir, "evidence"), exist_ok=True)

    paper1_path = os.path.join(upload_dir, "question_papers", "paper1_test.pdf")
    with open(paper1_path, "wb") as f:
        f.write(b"%PDF-1.4 Mock Question Paper 1 Content")

    evidence1_path = os.path.join(upload_dir, "evidence", "evidence_student1.jpg")
    with open(evidence1_path, "wb") as f:
        f.write(b"\xFF\xD8\xFF\xE0 Mock JPEG Evidence 1 Content")

    # 4. Get or create Question Paper 1
    res_qp = await db_session.execute(select(QuestionPaper).where(QuestionPaper.title == "Physics 101"))
    qp1 = res_qp.scalar_one_or_none()
    if not qp1:
        qp1 = QuestionPaper(
            title="Physics 101",
            course_name="Physics",
            uploaded_by=examiner1.id,
            file_path="uploads/question_papers/paper1_test.pdf",
            mime_type="application/pdf",
            file_size_bytes=len(b"%PDF-1.4 Mock Question Paper 1 Content"),
            status="PUBLISHED"
        )
        db_session.add(qp1)
        await db_session.flush()

    # 5. Get or create Exam 1
    now = datetime.now(timezone.utc)
    res_ex = await db_session.execute(select(Exam).where(Exam.title == "Physics Midterm"))
    exam1 = res_ex.scalar_one_or_none()
    if not exam1:
        exam1 = Exam(
            title="Physics Midterm",
            course_name="Physics",
            created_by=examiner1.id,
            question_paper_id=qp1.id,
            scheduled_start=now - timedelta(hours=1),
            scheduled_end=now + timedelta(hours=2),
            duration_minutes=60,
            status="RUNNING"
        )
        db_session.add(exam1)
        await db_session.flush()

    # 6. Assign Student 1 to Exam 1
    res_as = await db_session.execute(
        select(ExamAssignment).where(
            ExamAssignment.exam_id == exam1.id,
            ExamAssignment.student_id == student1_user.id
        )
    )
    if not res_as.scalar_one_or_none():
        assign1 = ExamAssignment(
            exam_id=exam1.id,
            student_id=student1_user.id
        )
        db_session.add(assign1)

    # 7. Get or create Exam Session 1
    res_sess = await db_session.execute(
        select(ExamSession).where(
            ExamSession.exam_id == exam1.id,
            ExamSession.student_id == student1_user.id
        )
    )
    session1 = res_sess.scalar_one_or_none()
    if not session1:
        session1 = ExamSession(
            exam_id=exam1.id,
            student_id=student1_user.id,
            start_time=now - timedelta(minutes=30),
            status="RUNNING"
        )
        db_session.add(session1)
        await db_session.flush()

    # 8. Get or create Violation & Evidence for Session 1
    res_v = await db_session.execute(
        select(Violation).where(Violation.exam_session_id == session1.id)
    )
    violation1 = res_v.scalar_one_or_none()
    if not violation1:
        violation1 = Violation(
            exam_session_id=session1.id,
            violation_type="GAZE_DEVIATION",
            category="LOOKING_AWAY",
            severity="MEDIUM",
            risk_score=45.0,
            timestamp=now - timedelta(minutes=10),
            status="PENDING"
        )
        db_session.add(violation1)
        await db_session.flush()

    res_ev = await db_session.execute(
        select(Evidence).where(Evidence.violation_id == violation1.id)
    )
    ev1 = res_ev.scalar_one_or_none()
    if not ev1:
        ev1 = Evidence(
            violation_id=violation1.id,
            file_path="uploads/evidence/evidence_student1.jpg",
            evidence_type="IMAGE",
            timestamp=now - timedelta(minutes=10)
        )
        db_session.add(ev1)
        
    await db_session.commit()

    # Generate auth tokens
    tokens = {
        "admin": create_access_token(subject=str(admin_user.id), role="Admin"),
        "examiner1": create_access_token(subject=str(examiner1.id), role="Examiner"),
        "examiner2": create_access_token(subject=str(examiner2.id), role="Examiner"),
        "student1": create_access_token(subject=str(student1_user.id), role="Student"),
        "student2": create_access_token(subject=str(student2_user.id), role="Student"),
        "expired": create_access_token(subject=str(student1_user.id), role="Student", expires_delta=timedelta(seconds=-60))
    }

    return {
        "admin": admin_user,
        "examiner1": examiner1,
        "examiner2": examiner2,
        "student1": student1_user,
        "student2": student2_user,
        "exam1": exam1,
        "session1": session1,
        "qp1": qp1,
        "ev1": ev1,
        "tokens": tokens
    }


# ==============================================================================
# PHASE B TESTS: SECURE UPLOAD & EVIDENCE FILE ACCESS
# ==============================================================================

@pytest.mark.asyncio
async def test_1_unauthenticated_upload_access_rejected(db_session):
    """Test 1: Unauthenticated request to /uploads is rejected with 401."""
    await setup_security_data(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/uploads/evidence/evidence_student1.jpg")
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]


@pytest.mark.asyncio
async def test_2_authenticated_authorized_file_access_succeeds(db_session):
    """Test 2: Authenticated and authorized examiner can retrieve their evidence file."""
    sec = await setup_security_data(db_session)
    token = sec["tokens"]["examiner1"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(
            "/uploads/evidence/evidence_student1.jpg",
            headers={"Authorization": f"Bearer {token}"}
        )
    assert res.status_code == 200
    assert len(res.content) > 0


@pytest.mark.asyncio
async def test_3_student_accessing_another_students_evidence_rejected(db_session):
    """Test 3: Student 2 attempting to access Student 1's evidence is rejected with 403."""
    sec = await setup_security_data(db_session)
    token = sec["tokens"]["student2"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(
            "/uploads/evidence/evidence_student1.jpg",
            headers={"Authorization": f"Bearer {token}"}
        )
    assert res.status_code == 403
    assert "cannot access evidence belonging to another student" in res.json()["detail"]


@pytest.mark.asyncio
async def test_4_examiner_accessing_another_examiners_private_file_rejected(db_session):
    """Test 4: Examiner 2 attempting to access Examiner 1's evidence/paper is rejected with 403."""
    sec = await setup_security_data(db_session)
    token = sec["tokens"]["examiner2"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Evidence check
        res_ev = await ac.get(
            "/uploads/evidence/evidence_student1.jpg",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res_ev.status_code == 403
        assert "not authorized to view evidence" in res_ev.json()["detail"]

        # Question Paper check
        res_qp = await ac.get(
            "/uploads/question_papers/paper1_test.pdf",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res_qp.status_code == 403
        assert "do not own this question paper" in res_qp.json()["detail"]


@pytest.mark.asyncio
async def test_5_path_traversal_attempt_rejected(db_session):
    """Test 5: Path traversal attempts (e.g. '../', absolute paths) are rejected with 400/403."""
    sec = await setup_security_data(db_session)
    token = sec["tokens"]["examiner1"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Dot-dot attempt
        res = await ac.get(
            "/uploads/../../app/core/config.py",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code in [400, 403, 404]

        # Encoded dot-dot
        res_enc = await ac.get(
            "/uploads/%2e%2e%2f%2e%2e%2fmain.py",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res_enc.status_code in [400, 403, 404]


# ==============================================================================
# PHASE C TESTS: PRODUCTION SECRET ENFORCEMENT
# ==============================================================================

def test_6_missing_production_secret_key_fails():
    """Test 6: In production (DEBUG=False, TESTING=False), empty SECRET_KEY raises validation failure."""
    with pytest.raises(ValueError) as exc_info:
        Settings(
            DEBUG=False,
            TESTING=False,
            SECRET_KEY=""
        )
    assert "Production Security Configuration Error" in str(exc_info.value)


def test_7_known_development_secret_in_production_fails():
    """Test 7: In production, known default development SECRET_KEY raises validation failure."""
    with pytest.raises(ValueError) as exc_info:
        Settings(
            DEBUG=False,
            TESTING=False,
            SECRET_KEY="super_secret_development_key_change_in_production"
        )
    assert "Production Security Configuration Error" in str(exc_info.value)


# ==============================================================================
# PHASE D TESTS: WEBSOCKET AUTHENTICATION & ISOLATION
# ==============================================================================

@pytest.mark.asyncio
async def test_8_valid_websocket_authentication_succeeds(db_session, client):
    """Test 8: Valid token allows WebSocket connection and receives heartbeat pong."""
    sec = await setup_security_data(db_session)
    session_id = sec["session1"].id
    token = sec["tokens"]["examiner1"]

    with client.websocket_connect(f"/api/v1/ws/{session_id}?token={token}") as ws:
        # Send heartbeat ping
        ws.send_text("ping")
        resp = ws.receive_json()
        assert resp["event"] == "HEARTBEAT"
        assert resp["payload"]["status"] == "alive"


def test_9_invalid_websocket_token_rejected(client):
    """Test 9: Invalid token is cleanly closed with policy violation."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/ws/999?token=invalid_garbage_token"):
            pass
    assert exc_info.value.code == 1008


def test_10_expired_websocket_token_rejected(client):
    """Test 10: Expired token is cleanly closed with policy violation."""
    expired_token = create_access_token(
        subject="999", role="Student", expires_delta=timedelta(seconds=-60)
    )
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/ws/999?token={expired_token}"):
            pass
    assert exc_info.value.code == 1008


@pytest.mark.asyncio
async def test_11_unauthorized_exam_session_websocket_access_rejected(db_session, client):
    """Test 11: Examiner 2 cannot monitor Examiner 1's exam session."""
    sec = await setup_security_data(db_session)
    session_id = sec["session1"].id
    token_examiner2 = sec["tokens"]["examiner2"]

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/ws/{session_id}?token={token_examiner2}"):
            pass
    assert exc_info.value.code == 1008
