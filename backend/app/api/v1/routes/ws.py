import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.session import get_db
from app.models.user import User
from app.models.exam_session import ExamSession
from app.models.exam import Exam
from app.services.token_service import TokenService
from app.repositories.user_repository import UserRepository
from app.repositories.exam_session_repository import ExamSessionRepository
from app.websocket.connection_manager import manager
from app.services.exceptions import TokenValidationError, ExpiredTokenError

logger = logging.getLogger(__name__)

router = APIRouter()

async def get_websocket_user(token: str, db: AsyncSession):
    """Decode JWT token and retrieve the user for WebSocket context."""
    try:
        payload = TokenService.validate_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        
        user_res = await db.execute(
            select(User).options(selectinload(User.role)).where(User.id == int(user_id_str))
        )
        user = user_res.scalars().first()
        if user and user.is_active:
            return user
        return None
    except (TokenValidationError, ExpiredTokenError, ValueError):
        return None

@router.websocket("/{exam_session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    exam_session_id: int,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    # Extract token from query or headers
    auth_token = token
    if not auth_token:
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            auth_token = auth_header.split(" ", 1)[1].strip()

    if not auth_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication token required")
        return

    user = await get_websocket_user(auth_token, db)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")
        return

    # Check isolation rules
    exam_session_res = await db.execute(
        select(ExamSession)
        .options(
            selectinload(ExamSession.exam).selectinload(Exam.supervisors)
        )
        .where(ExamSession.id == exam_session_id)
    )
    exam_session = exam_session_res.scalars().first()

    if not exam_session:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Exam Session not found")
        return

    role_name = user.role.name.upper() if user.role else ""

    if role_name == "STUDENT":
        from app.core.config import settings
        if not settings.ENABLE_STUDENT_MONITORING_PREVIEW:
            logger.warning(f"Student {user.id} attempted to access monitoring WebSocket but feature is disabled")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Student monitoring preview is disabled")
            return
        if exam_session.student_id != user.id:
            logger.warning(f"Student {user.id} attempted to access exam session {exam_session_id}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Not authorized for this session")
            return
    elif role_name == "EXAMINER":
        is_creator = exam_session.exam and exam_session.exam.created_by == user.id
        is_supervisor = any(s.supervisor_id == user.id for s in getattr(exam_session.exam, "supervisors", [])) if exam_session.exam else False
        if not (is_creator or is_supervisor):
            logger.warning(f"Examiner {user.id} attempted to access exam session {exam_session_id}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Not authorized to supervise this session")
            return
    elif role_name == "ADMIN":
        # Admins can monitor any session
        pass
    else:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Role unauthorized")
        return

    # Authorized, connect to manager
    await manager.connect(websocket, exam_session_id)
    try:
        # Blocks until disconnect
        await manager.heartbeat_loop(websocket, exam_session_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, exam_session_id)
        logger.info(f"User {user.id} disconnected from session {exam_session_id}")
    except Exception as e:
        manager.disconnect(websocket, exam_session_id)
        logger.error(f"WebSocket error for user {user.id}: {e}")
