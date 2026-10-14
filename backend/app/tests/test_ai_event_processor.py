import pytest
import pytest_asyncio
import time
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ai_event_processor import AIEventProcessor
from app.schemas.ai_event import AIEventDTO
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.exam_session_repository import ExamSessionRepository
from app.services.password_service import PasswordService
from app.models.exam import Exam
from app.models.question_paper import QuestionPaper
from app.models.exam_session import ExamSession
from app.models.violation import Violation
from app.models.evidence import Evidence
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.orm import selectinload

@pytest_asyncio.fixture(scope="function")
async def setup_ai_data(db_session: AsyncSession):
    # Create Role
    role_repo = RoleRepository(db_session)
    student_role = await role_repo.create(name="Student")
    examiner_role = await role_repo.create(name="Examiner")
    
    # Create User
    user_repo = UserRepository(db_session)
    student = await user_repo.create(
        role_id=student_role.id,
        full_name="AI Student",
        email="ai.student@test.com",
        password_hash=PasswordService.hash("pwd"),
        is_active=True
    )
    examiner = await user_repo.create(
        role_id=examiner_role.id,
        full_name="AI Examiner",
        email="ai.examiner@test.com",
        password_hash=PasswordService.hash("pwd"),
        is_active=True
    )

    # Create QP & Exam
    paper = QuestionPaper(title="AI QP", course_name="AI Course", uploaded_by=examiner.id, file_path="/null", status="READY")
    db_session.add(paper)
    await db_session.commit()
    await db_session.refresh(paper)

    now = datetime.now(timezone.utc)
    exam = Exam(
        title="AI Exam", course_name="AI Course", created_by=examiner.id, question_paper_id=paper.id,
        scheduled_start=now - timedelta(minutes=10), scheduled_end=now + timedelta(hours=2),
        duration_minutes=120, passing_marks=40, total_marks=100, status="RUNNING"
    )
    db_session.add(exam)
    await db_session.commit()
    await db_session.refresh(exam)

    # Create ExamSession
    session_repo = ExamSessionRepository(db_session)
    exam_session = await session_repo.create(exam_id=exam.id, student_id=student.id, status="RUNNING")
    
    # Clear tracking times
    AIEventProcessor._last_event_times.clear()

    return exam_session

@pytest.mark.asyncio
async def test_ai_event_processing(setup_ai_data, db_session: AsyncSession, monkeypatch):
    import contextlib
    @contextlib.asynccontextmanager
    async def mock_session_factory():
        yield db_session
    monkeypatch.setattr("app.services.ai_event_processor.async_session_factory", mock_session_factory)
    
    exam_session = setup_ai_data
    base_t = time.time()
    
    # 1. Process Low Confidence Event (should NOT create violation)
    low_conf_event = AIEventDTO(
        event_type="NO_FACE",
        timestamp=base_t,
        exam_session_id=exam_session.id,
        severity="HIGH",
        source_module="face_detector",
        confidence=0.1,  # below 0.5 threshold
        payload={}
    )
    await AIEventProcessor.process_event(low_conf_event)
    
    result = await db_session.execute(select(Violation).where(Violation.exam_session_id == exam_session.id))
    assert len(result.scalars().all()) == 0

    # 2. Process High Confidence Event (should create violation)
    high_conf_event = AIEventDTO(
        event_type="NO_FACE",
        timestamp=base_t + 1.0,
        exam_session_id=exam_session.id,
        severity="HIGH",
        source_module="face_detector",
        confidence=0.9,  # above 0.5 threshold
        payload={"frame_path": "uploads/evidence_1.jpg"}
    )
    await AIEventProcessor.process_event(high_conf_event)
    
    result = await db_session.execute(
        select(Violation).options(selectinload(Violation.evidence)).where(Violation.exam_session_id == exam_session.id)
    )
    violations = result.scalars().all()
    assert len(violations) == 1
    assert violations[0].violation_type == "NO_FACE"
    assert violations[0].duration_seconds == 0.0
    assert len(violations[0].evidence) == 1
    assert violations[0].evidence[0].is_primary is True

    # 3. Process Ongoing Event within episode (should deduplicate and increase duration)
    cont_event = AIEventDTO(
        event_type="NO_FACE",
        timestamp=base_t + 4.5,
        exam_session_id=exam_session.id,
        severity="HIGH",
        source_module="face_detector",
        confidence=0.95,
        payload={"frame_path": "uploads/evidence_2.jpg"}
    )
    await AIEventProcessor.process_event(cont_event)
    
    result = await db_session.execute(
        select(Violation).options(selectinload(Violation.evidence)).where(Violation.exam_session_id == exam_session.id)
    )
    violations = result.scalars().all()
    assert len(violations) == 1  # Deduplicated into 1 violation
    assert violations[0].duration_seconds > 0.0
    assert len(violations[0].evidence) == 2
    assert violations[0].evidence[1].is_primary is False
