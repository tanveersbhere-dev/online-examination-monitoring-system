import pytest
import asyncio
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from main import app
from app.database.session import get_db
from app.models.role import Role
from app.models.user import User
from app.models.exam import Exam
from app.models.exam_session import ExamSession
from app.websocket.connection_manager import manager
from app.websocket.websocket_events import WSEvent, WSEventType
from app.security.jwt_handler import create_access_token


async def setup_ws_session(db_session: AsyncSession, session_id: int):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Get/create Role
    res_r = await db_session.execute(select(Role).where(Role.name == "Admin"))
    admin_role = res_r.scalar_one_or_none()
    if not admin_role:
        admin_role = Role(name="Admin", description="Admin role")
        db_session.add(admin_role)
        await db_session.flush()

    # Get/create User
    res_u = await db_session.execute(select(User).where(User.username == "admin_ws_test"))
    user = res_u.scalar_one_or_none()
    if not user:
        user = User(
            role_id=admin_role.id,
            full_name="WS Admin Test",
            email="ws_admin@test.com",
            username="admin_ws_test",
            password_hash="hash",
            is_active=True
        )
        db_session.add(user)
        await db_session.flush()

    # Get/create Exam
    now = datetime.now(timezone.utc)
    res_ex = await db_session.execute(select(Exam).where(Exam.id == 1))
    exam = res_ex.scalar_one_or_none()
    if not exam:
        exam = Exam(
            id=1,
            title="WS Exam",
            created_by=user.id,
            scheduled_start=now - timedelta(hours=1),
            scheduled_end=now + timedelta(hours=2),
            status="RUNNING"
        )
        db_session.add(exam)
        await db_session.flush()

    # Get/create ExamSession with specified ID
    res_s = await db_session.execute(select(ExamSession).where(ExamSession.id == session_id))
    session_obj = res_s.scalar_one_or_none()
    if not session_obj:
        session_obj = ExamSession(
            id=session_id,
            exam_id=exam.id,
            student_id=user.id,
            start_time=now - timedelta(minutes=10),
            status="RUNNING"
        )
        db_session.add(session_obj)

    await db_session.commit()

    token = create_access_token(subject=str(user.id), role="Admin")
    return user, token


@pytest.mark.asyncio
async def test_websocket_connection_and_heartbeat(db_session, client):
    user, token = await setup_ws_session(db_session, 999)
    with client.websocket_connect(f"/api/v1/ws/999?token={token}") as websocket:
        assert 999 in manager.active_connections
        assert len(manager.active_connections[999]) == 1
        
        # Test heartbeat
        websocket.send_text("ping")
        response = websocket.receive_json()
        assert response["event"] == "HEARTBEAT"
        assert response["payload"]["status"] == "alive"


@pytest.mark.asyncio
async def test_websocket_broadcast(db_session, client):
    user, token = await setup_ws_session(db_session, 101)
    with client.websocket_connect(f"/api/v1/ws/101?token={token}") as websocket1:
        with client.websocket_connect(f"/api/v1/ws/101?token={token}") as websocket2:
            assert len(manager.active_connections[101]) == 2
            
            event = WSEvent(
                event=WSEventType.RISK_UPDATED,
                timestamp=datetime.utcnow(),
                exam_session_id=101,
                payload={"new_score": 85.0}
            )
            
            await manager.broadcast(event)
            
            resp1 = websocket1.receive_json()
            resp2 = websocket2.receive_json()
            
            assert resp1["event"] == "RISK_UPDATED"
            assert resp1["payload"]["new_score"] == 85.0
            assert resp2["event"] == "RISK_UPDATED"
            assert resp2["payload"]["new_score"] == 85.0


@pytest.mark.asyncio
async def test_websocket_disconnect(db_session, client):
    user, token = await setup_ws_session(db_session, 102)
    with client.websocket_connect(f"/api/v1/ws/102?token={token}") as websocket:
        assert 102 in manager.active_connections
        
    assert 102 not in manager.active_connections
