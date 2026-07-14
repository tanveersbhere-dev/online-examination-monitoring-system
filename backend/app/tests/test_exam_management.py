import pytest
import pytest_asyncio
import os
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient
from fastapi import UploadFile

from app.services.exam_service import ExamService
from app.services.exceptions import ScheduleConflictError, InvalidExamStateError
from app.schemas.exam import ExamCreate, ExamUpdate
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository

class MockUploadFile(UploadFile):
    def __init__(self, filename, content):
        super().__init__(filename=filename)
        self._content = content
        
    async def read(self):
        return self._content

@pytest_asyncio.fixture(scope="function")
async def setup_users(db_session: AsyncSession):
    role_repo = RoleRepository(db_session)
    examiner_role = await role_repo.create(name="EXAMINER")
    
    user_repo = UserRepository(db_session)
    examiner = await user_repo.create(
        role_id=examiner_role.id,
        full_name="Exam Admin",
        email="admin@exams.com",
        password_hash="hash",
        is_active=True
    )
    return examiner

@pytest.mark.asyncio
async def test_question_paper_upload(db_session: AsyncSession, setup_users):
    examiner = setup_users
    service = ExamService(db_session)
    
    mock_file = MockUploadFile("test_paper.pdf", b"dummy pdf content")
    
    paper = await service.upload_paper(
        title="CS101 Final",
        course_name="CS101",
        uploader_id=examiner.id,
        file=mock_file
    )
    
    assert paper.id is not None
    assert paper.title == "CS101 Final"
    assert paper.file_path.endswith(".pdf")
    
    # Cleanup physical file
    await service.delete_paper(paper.id)
    assert not os.path.exists(paper.file_path)

@pytest.mark.asyncio
async def test_exam_creation_and_conflict(db_session: AsyncSession, setup_users):
    examiner = setup_users
    ex_service = ExamService(db_session)
    
    # Upload dummy paper
    mock_file = MockUploadFile("midterm.pdf", b"dummy pdf content")
    paper = await ex_service.upload_paper("CS101 Midterm", "CS101", examiner.id, mock_file)
    
    now = datetime.now()
    start1 = now + timedelta(days=1)
    end1 = start1 + timedelta(hours=2)
    
    # 1. Create first exam
    exam1 = await ex_service.create_exam(examiner.id, ExamCreate(
        title="Midterm A",
        course_name="CS101",
        question_paper_id=paper.id,
        scheduled_start=start1,
        scheduled_end=end1,
        duration_minutes=120
    ))
    assert exam1.id is not None
    assert exam1.status == "DRAFT"
    
    # 2. Test conflict: Create overlapping exam
    start2 = start1 + timedelta(hours=1) # Overlaps with exam1
    end2 = start2 + timedelta(hours=2)
    
    with pytest.raises(ScheduleConflictError):
        await ex_service.create_exam(examiner.id, ExamCreate(
            title="Midterm B",
            course_name="CS101",
            question_paper_id=paper.id,
            scheduled_start=start2,
            scheduled_end=end2,
            duration_minutes=120
        ))
        
    # Cleanup
    await ex_service.delete_paper(paper.id)

@pytest.mark.asyncio
async def test_exam_state_transitions_and_ai_hooks(db_session: AsyncSession, setup_users):
    examiner = setup_users
    ex_service = ExamService(db_session)
    
    mock_file = MockUploadFile("final.pdf", b"pdf content")
    paper = await ex_service.upload_paper("CS102 Final", "CS102", examiner.id, mock_file)
    
    now = datetime.now()
    exam = await ex_service.create_exam(examiner.id, ExamCreate(
        title="Final Exam",
        course_name="CS102",
        question_paper_id=paper.id,
        scheduled_start=now + timedelta(days=2),
        scheduled_end=now + timedelta(days=2, hours=3),
        duration_minutes=180
    ))
    
    # Move to READY
    exam = await ex_service._change_status(exam.id, "SCHEDULED")
    exam = await ex_service._change_status(exam.id, "READY")
    
    # Start Exam (Triggers AI Session Manager)
    exam = await ex_service.start_exam(exam.id)
    assert exam.status == "RUNNING"
    assert exam.ai_session_status == "ACTIVE"
    
    # Pause Exam
    exam = await ex_service.pause_exam(exam.id)
    assert exam.status == "PAUSED"
    assert exam.ai_session_status == "ACTIVE"
    
    # Resume Exam
    exam = await ex_service.resume_exam(exam.id)
    assert exam.status == "RUNNING"
    
    # Complete Exam
    exam = await ex_service.complete_exam(exam.id)
    assert exam.status == "COMPLETED"
    assert exam.ai_session_status == "INACTIVE"
    
    # Cleanup
    await ex_service.delete_paper(paper.id)
