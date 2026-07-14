import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database.session import get_db
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
        
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(int(user_id_str))
        if user and user.is_active:
            return user
        return None
    except (TokenValidationError, ExpiredTokenError, ValueError):
        return None

@router.websocket("/{exam_session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    exam_session_id: int,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    user = await get_websocket_user(token, db)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")
        return

    # Check isolation rules
    exam_session_repo = ExamSessionRepository(db)
    exam_session = await exam_session_repo.get_by_id(exam_session_id)

    if not exam_session:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Exam Session not found")
        return

    role_name = user.role.name.upper()

    if role_name == "STUDENT":
        if exam_session.student_id != user.id:
            logger.warning(f"Student {user.id} attempted to access exam session {exam_session_id}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Not authorized for this session")
            return
    elif role_name == "EXAMINER":
        if exam_session.exam.created_by != user.id:
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
