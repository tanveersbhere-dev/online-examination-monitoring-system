import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.database.base import Base
from app.models import Role, User, QuestionPaper, Exam, ExamSession, AISession, Violation, Evidence, SystemLog

# Set up synchronous in-memory SQLite database for testing SQLAlchemy relationships and constraints
engine = create_engine("sqlite:///:memory:", echo=False)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Create a clean database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

def test_create_role_and_user(db_session):
    role = Role(name="STUDENT", description="Student role")
    db_session.add(role)
    db_session.commit()
    
    user = User(
        role_id=role.id,
        full_name="John Doe",
        email="john@example.com",
        password_hash="hashed_pw"
    )
    db_session.add(user)
    db_session.commit()
    
    assert user.id is not None
    assert user.role.name == "STUDENT"
    assert len(role.users) == 1
    
    # Test unique constraint on email
    user2 = User(
        role_id=role.id,
        full_name="Jane Doe",
        email="john@example.com", # Duplicate
        password_hash="hashed_pw"
    )
    db_session.add(user2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_exam_hierarchy_and_cascade(db_session):
    # Setup Role and User
    role = Role(name="TEACHER")
    user = User(role=role, full_name="Dr. Smith", email="smith@test.com", password_hash="pw")
    db_session.add(user)
    db_session.commit()
    
    # Create Question Paper
    qp = QuestionPaper(title="Midterm", course_name="CS101", uploaded_by=user.id, file_path="/path")
    db_session.add(qp)
    
    # Create Exam
    exam = Exam(
        title="CS101 Midterm",
        course_name="CS101",
        question_paper=qp,
        scheduled_start=datetime.now(),
        scheduled_end=datetime.now(),
        duration_minutes=120,
        creator=user
    )
    db_session.add(exam)
    db_session.commit()
    
    assert len(user.exams_created) == 1
    assert qp.exams[0].title == "CS101 Midterm"
    
def test_exam_session_and_violations(db_session):
    role = Role(name="STUDENT")
    student = User(role=role, full_name="Student", email="s@s.com", password_hash="pw")
    qp = QuestionPaper(title="Q", course_name="C", uploader=student, file_path="P")
    exam = Exam(title="E", course_name="C", question_paper=qp, scheduled_start=datetime.now(), scheduled_end=datetime.now(), duration_minutes=60, creator=student)
    
    ai = AISession()
    session = ExamSession(
        exam=exam,
        student=student,
        ai_session=ai,
        start_time=datetime.now()
    )
    db_session.add(session)
    db_session.commit()
    
    # Create Violation
    violation = Violation(
        exam_session_id=session.id,
        violation_type="PHONE",
        category="MATERIAL",
        severity="HIGH",
        risk_score=75.0,
        timestamp=datetime.now(),
        description="Phone detected"
    )
    db_session.add(violation)
    
    # Create Evidence
    evidence = Evidence(
        violation=violation,
        file_path="/ev1.jpg",
        evidence_type="IMAGE",
        timestamp=datetime.now()
    )
    db_session.add(evidence)
    db_session.commit()
    
    assert session.ai_session_id is not None
    assert len(session.violations) == 1
    assert len(violation.evidence) == 1
    
    # Test Cascade Deletion: Deleting the Exam Session should wipe violations and evidence
    session_id = session.id
    violation_id = violation.id
    evidence_id = evidence.id
    
    db_session.delete(session)
    db_session.commit()
    
    assert db_session.get(ExamSession, session_id) is None
    assert db_session.get(Violation, violation_id) is None
    assert db_session.get(Evidence, evidence_id) is None

def test_system_log(db_session):
    log = SystemLog(level="INFO", message="System started", source="API", timestamp=datetime.now())
    db_session.add(log)
    db_session.commit()
    
    assert log.id is not None
