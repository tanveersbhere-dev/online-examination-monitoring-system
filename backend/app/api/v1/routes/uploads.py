import os
import mimetypes
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.database.session import get_db
from app.services.token_service import TokenService
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.models.question_paper import QuestionPaper
from app.models.evidence import Evidence
from app.models.violation import Violation
from app.models.exam_session import ExamSession
from app.models.exam import Exam
from app.models.student import Student
from app.models.exam_assignment import ExamAssignment
from app.services.exceptions import TokenValidationError, ExpiredTokenError

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_file_user(
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Extract and validate the user token from query params or Authorization header."""
    auth_token = token
    if not auth_token and authorization and authorization.lower().startswith("bearer "):
        auth_token = authorization.split(" ", 1)[1].strip()

    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access uploaded files."
        )

    try:
        payload = TokenService.validate_token(auth_token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload."
            )

        user_res = await db.execute(
            select(User).options(selectinload(User.role)).where(User.id == int(user_id_str))
        )
        user = user_res.scalars().first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User inactive or not found."
            )
        return user
    except (TokenValidationError, ExpiredTokenError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token."
        )


async def check_file_authorization(
    db: AsyncSession,
    user: User,
    relative_path: str,
    filename: str
) -> None:
    """
    Validates that the authenticated user has explicit permission to retrieve the requested file.
    Prevents cross-student, cross-examiner, and unassigned data leaks.
    """
    role_name = user.role.name.upper() if user.role else ""
    
    # 1. System Administrators have universal read access
    if role_name == "ADMIN":
        return

    # 2. Check Question Papers
    if "question_paper" in relative_path.lower() or filename.endswith((".pdf", ".docx", ".txt")):
        qp_res = await db.execute(
            select(QuestionPaper).filter(QuestionPaper.file_path.ilike(f"%{filename}%"))
        )
        paper = qp_res.scalars().first()
        if paper:
            if role_name == "EXAMINER":
                if paper.uploaded_by != user.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access forbidden: You do not own this question paper."
                    )
                return
            elif role_name == "STUDENT":
                # Check if student is assigned to any exam using this question paper
                assign_res = await db.execute(
                    select(ExamAssignment)
                    .join(Exam, Exam.id == ExamAssignment.exam_id)
                    .filter(
                        ExamAssignment.student_id == user.id,
                        Exam.question_paper_id == paper.id
                    )
                )
                if not assign_res.scalars().first():
                    # Also check exam sessions
                    session_res = await db.execute(
                        select(ExamSession)
                        .join(Exam, Exam.id == ExamSession.exam_id)
                        .filter(
                            ExamSession.student_id == user.id,
                            Exam.question_paper_id == paper.id
                        )
                    )
                    if not session_res.scalars().first():
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access forbidden: You are not assigned to the exam for this question paper."
                        )
                return

    # 3. Check Evidence Snapshots
    ev_res = await db.execute(
        select(Evidence)
        .options(
            selectinload(Evidence.violation)
            .selectinload(Violation.exam_session)
            .selectinload(ExamSession.exam)
            .selectinload(Exam.supervisors)
        )
        .filter(Evidence.file_path.ilike(f"%{filename}%"))
    )
    evidence = ev_res.scalars().first()
    if evidence and evidence.violation and evidence.violation.exam_session:
        session = evidence.violation.exam_session
        if role_name == "EXAMINER":
            is_creator = session.exam and session.exam.created_by == user.id
            is_supervisor = any(s.supervisor_id == user.id for s in getattr(session.exam, "supervisors", [])) if session.exam else False
            if not (is_creator or is_supervisor):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: You are not authorized to view evidence for this exam session."
                )
            return
        elif role_name == "ADMIN":
            return
        elif role_name == "STUDENT":
            # A student can only view their own evidence (never another student's)
            if session.student_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: You cannot access evidence belonging to another student."
                )
            return
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Role not authorized for evidence."
            )

    # 4. Check Student Face Images
    student_res = await db.execute(
        select(Student).filter(Student.face_image_path.ilike(f"%{filename}%"))
    )
    student = student_res.scalars().first()
    if student:
        if role_name == "EXAMINER":
            if student.examiner_id != user.id:
                # Check if student is assigned to any exam created by this examiner
                exam_check = await db.execute(
                    select(ExamAssignment)
                    .join(Exam, Exam.id == ExamAssignment.exam_id)
                    .filter(
                        ExamAssignment.student_id == student.id,
                        Exam.created_by == user.id
                    )
                )
                if not exam_check.scalars().first():
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access forbidden: You do not manage this student."
                    )
            return
        elif role_name == "STUDENT":
            if student.email != user.email:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: You cannot access another student's face photo."
                )
            return

    # 5. Check User Face Images / Profile Pictures
    user_face_res = await db.execute(
        select(User).filter(User.face_image_path.ilike(f"%{filename}%"))
    )
    face_user = user_face_res.scalars().first()
    if face_user:
        if role_name == "STUDENT" and face_user.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You cannot access another user's face photo."
            )
        return

    # If it's another general file and user is authenticated examiner/admin, permit
    if role_name in ["EXAMINER", "ADMIN"]:
        return

    # Default deny for unclassified private student requests
    if role_name == "STUDENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Unauthorized file request."
        )


@router.get("/{file_path:path}")
async def serve_secure_file(
    file_path: str,
    user: User = Depends(get_file_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Secure authenticated file serving endpoint.
    Guarantees:
    - Path traversal defense.
    - Role-based isolation.
    - Owner/Exam verification.
    """
    # 1. Clean and normalize relative path
    cleaned = file_path.replace("\\", "/").strip("/")
    if cleaned.lower().startswith("uploads/"):
        cleaned = cleaned[8:].strip("/")

    if not cleaned or ".." in cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path."
        )

    # 2. Strict directory boundary verification
    base_dir = os.path.abspath(settings.UPLOAD_DIR or "uploads")
    target_path = os.path.abspath(os.path.join(base_dir, cleaned))

    # Verify that the target path is strictly within the upload directory
    try:
        common = os.path.commonpath([base_dir, target_path])
    except Exception:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    if common != base_dir or not target_path.startswith(base_dir):
        logger.warning(f"Path traversal attempt blocked: {file_path}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    if not os.path.isfile(target_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")

    # 3. Ownership and Authorization check
    filename = os.path.basename(target_path)
    await check_file_authorization(db, user, cleaned, filename)

    # 4. Stream file response
    media_type, _ = mimetypes.guess_type(target_path)
    if not media_type:
        media_type = "application/octet-stream"

    return FileResponse(
        path=target_path,
        media_type=media_type,
        filename=filename
    )
