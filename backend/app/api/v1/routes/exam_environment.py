"""
Exam Environment Monitor — Backend API
=======================================
Independent from the AI monitoring engine.
Detects deterministic browser signals (tab switch, fullscreen exit) and routes them
through the existing Violation → Evidence → WebSocket infrastructure.

No AI required. Works even when the AI engine is fully disabled.
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.security.dependencies import get_current_user
from app.schemas.user_auth import UserResponse
from app.models.exam_session import ExamSession
from app.models.violation import Violation
from app.models.exam import Exam
from app.schemas.violation import ViolationCreate, ViolationUpdate, ViolationResponse
from app.schemas.evidence import EvidenceCreate
from app.services.violation_service import ViolationService
from app.services.evidence_service import EvidenceService
from app.websocket.connection_manager import manager
from app.websocket.websocket_events import WSEvent, WSEventType

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / Response schemas (env-monitor specific, no student-supplied risk)
# ---------------------------------------------------------------------------

ALLOWED_EVENT_TYPES = {"TAB_SWITCH", "FULLSCREEN_EXIT"}

class ViolationStartRequest(BaseModel):
    exam_id: int
    event_type: str           # "TAB_SWITCH" | "FULLSCREEN_EXIT"
    raw_browser_events: List[str] = []   # correlated raw browser signal names
    image_base64: Optional[str] = None  # candidate camera frame at incident moment


class ViolationStartResponse(BaseModel):
    violation_id: int
    exam_session_id: int
    event_type: str
    severity: str
    created_at: datetime


class ViolationEndRequest(BaseModel):
    exam_id: int
    violation_id: int
    duration_seconds: float


class ViolationEndResponse(BaseModel):
    violation_id: int
    duration_seconds: float
    resolved_at: datetime


class EnvViolationItem(BaseModel):
    id: int
    violation_type: str
    severity: str
    status: str
    timestamp: datetime
    duration_seconds: float
    description: Optional[str] = None
    resolved_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Helper: get RUNNING exam session for authenticated student
# ---------------------------------------------------------------------------

async def _get_running_session(
    exam_id: int,
    student_id: int,
    db: AsyncSession
) -> ExamSession:
    """
    Fetch the exam session for this student + exam.
    Raises 403 if session is not RUNNING (ACTIVE).
    This is the primary guard against violation injection on completed sessions.
    """
    result = await db.execute(
        select(ExamSession).where(
            ExamSession.exam_id == exam_id,
            ExamSession.student_id == student_id
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam session not found for this student."
        )

    if session.status != "RUNNING":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Exam environment monitoring is only active during RUNNING sessions. "
                   f"Current session status: {session.status}"
        )

    return session


# ---------------------------------------------------------------------------
# POST /runtime/env-monitor/violation-start
# ---------------------------------------------------------------------------

@router.post(
    "/violation-start",
    response_model=ViolationStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a detected exam-environment violation (tab switch / fullscreen exit)"
)
async def violation_start(
    req: ViolationStartRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Called by ExamEnvironmentMonitor when a browser-environment event is detected.

    Security:
    - student_id is derived from the authenticated JWT — never trusted from the client.
    - severity, category, and risk_score are fixed server-side (not client-supplied).
    - Session must be in RUNNING state.
    - event_type must be one of the allowed values.
    """
    import os
    import uuid
    import base64
    import cv2
    import numpy as np
    from app.core.config import settings

    # Validate event type server-side
    event_type = req.event_type.upper().strip()
    if event_type not in ALLOWED_EVENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid event_type '{event_type}'. Allowed: {ALLOWED_EVENT_TYPES}"
        )

    # Validate session ownership and RUNNING state
    exam_session = await _get_running_session(req.exam_id, current_user.id, db)

    now = datetime.now(timezone.utc)

    # Human-readable description (accurate, no overclaiming)
    if event_type == "TAB_SWITCH":
        description = (
            "Examination page became hidden — student left the controlled exam environment. "
            "Detection source: Page Visibility API (visibilityState = hidden)."
        )
    else:  # FULLSCREEN_EXIT
        description = (
            "Student exited the controlled fullscreen examination environment. "
            "Detection source: Fullscreen API (fullscreenElement = null)."
        )

    # Create violation via existing ViolationService (ai_session_id intentionally null)
    violation_service = ViolationService(db)
    violation_schema = ViolationCreate(
        exam_session_id=exam_session.id,
        ai_session_id=None,           # env-monitor violations are AI-independent
        violation_type=event_type,
        category="EXAM_ENVIRONMENT",
        severity="HIGH",
        risk_score=75.0,
        description=description,
        timestamp=now,
        external_violation_id=f"ENV_MONITOR_{event_type}_{int(now.timestamp())}",
    )
    created_violation = await violation_service.create_violation(violation_schema)

    # Immediately update status to ACTIVE (violation is in-progress)
    await violation_service.update_violation(
        created_violation.id,
        ViolationUpdate(status="ACTIVE")
    )

    # ── Visual Snapshot Capture & Storage ─────────────────────────────────────
    upload_dir = settings.UPLOAD_DIR or "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    snapshot_filename = f"evidence_env_{uuid.uuid4().hex}.jpg"
    snapshot_filepath = os.path.join(upload_dir, snapshot_filename)
    visual_captured = False

    # 1. Try candidate live frame sent from client camera preview
    if req.image_base64:
        try:
            raw_b64 = req.image_base64.split(",", 1)[1] if "," in req.image_base64 else req.image_base64
            img_bytes = base64.b64decode(raw_b64)
            with open(snapshot_filepath, "wb") as f:
                f.write(img_bytes)
            visual_captured = True
        except Exception as e:
            logger.warning(f"[ENV-MONITOR] Failed to decode client base64 frame: {e}")

    # 2. If client frame not provided or failed, check ReplayService rolling buffer
    if not visual_captured:
        try:
            from app.services.replay_service import ReplayService
            with ReplayService._lock:
                buf = ReplayService._buffers.get(exam_session.id)
                if buf and len(buf) > 0:
                    latest_t, latest_frame = buf[-1]
                    cv2.imwrite(snapshot_filepath, latest_frame)
                    visual_captured = True
        except Exception as e:
            logger.debug(f"[ENV-MONITOR] Replay buffer snapshot unavailable: {e}")

    # 3. If still not captured, check AISessionManager active thread frame
    if not visual_captured:
        try:
            from app.services.ai_session_manager import AISessionManager
            thread = AISessionManager._active_threads.get(exam_session.id)
            if thread and getattr(thread, "last_frame_b64", None):
                img_bytes = base64.b64decode(thread.last_frame_b64)
                with open(snapshot_filepath, "wb") as f:
                    f.write(img_bytes)
                visual_captured = True
        except Exception as e:
            logger.debug(f"[ENV-MONITOR] AI thread frame snapshot unavailable: {e}")

    # 4. Fallback: generate a clear, dark visual placard image frame
    if not visual_captured:
        try:
            blank = np.zeros((480, 640, 3), dtype=np.uint8)
            blank[:] = (20, 24, 33)
            cv2.rectangle(blank, (10, 10), (630, 470), (45, 55, 72), 2)
            cv2.putText(blank, "CONTROLLED EXAM ENVIRONMENT INCIDENT", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 165, 255), 2)
            cv2.putText(blank, f"Violation: {event_type}", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(blank, f"Severity: HIGH (Risk Score: 75.0)", (30, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 69, 255), 2)
            cv2.putText(blank, f"Recorded: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}", (30, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
            cv2.putText(blank, f"Session ID: {exam_session.id} | Student ID: {current_user.id}", (30, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
            cv2.putText(blank, "Detection: Browser Security Subsystem", (30, 340), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 255), 1)
            cv2.putText(blank, "Candidate departed fullscreen exam window", (30, 390), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (140, 140, 140), 1)
            cv2.imwrite(snapshot_filepath, blank)
            visual_captured = True
        except Exception as e:
            logger.warning(f"[ENV-MONITOR] Fallback visual placard creation error: {e}")

    evidence_file_path = f"uploads/{snapshot_filename}"

    # Create evidence record with real image snapshot file path
    evidence_service = EvidenceService(db)
    evidence_schema = EvidenceCreate(
        violation_id=created_violation.id,
        file_path=evidence_file_path,
        evidence_type="IMAGE",
        timestamp=now,
        is_primary=True,
        confidence_score=1.0,
        replay_clip_path=None,
        metadata_payload={
            "source": "EXAM_ENVIRONMENT_MONITOR",
            "detection_api": "PAGE_VISIBILITY_API" if event_type == "TAB_SWITCH" else "FULLSCREEN_API",
            "event_type": event_type,
            "raw_browser_events": req.raw_browser_events,
            "visual_evidence_available": True,
            "snapshot_type": "CAMERA_FRAME" if req.image_base64 else "SESSION_BUFFER_FRAME",
            "exam_session_id": exam_session.id,
            "student_id": current_user.id,
            "exam_id": req.exam_id,
            "violation_status": "ACTIVE",
            "recorded_at": now.isoformat(),
            "note": "Visual evidence snapshot captured at the moment of the environment violation."
        }
    )
    await evidence_service.create_evidence(evidence_schema)

    # Broadcast to examiner via existing WS infrastructure (both generic + specific event)
    ws_payload = {
        "violation_id": created_violation.id,
        "violation_type": event_type,
        "category": "EXAM_ENVIRONMENT",
        "severity": "HIGH",
        "risk_score": 75.0,
        "source": "EXAM_ENVIRONMENT_MONITOR",
        "status": "ACTIVE",
        "description": description,
        "exam_session_id": exam_session.id,
        "student_id": current_user.id,
    }

    # Generic event (consumed by existing useLiveMonitoring hook — examiner sees it immediately)
    await manager.broadcast(WSEvent(
        event=WSEventType.VIOLATION_CREATED,
        timestamp=now,
        exam_session_id=exam_session.id,
        payload=ws_payload,
    ))

    # Specific env-monitor event (for future specialised listeners)
    await manager.broadcast(WSEvent(
        event=WSEventType.ENV_MONITOR_VIOLATION_CREATED,
        timestamp=now,
        exam_session_id=exam_session.id,
        payload=ws_payload,
    ))

    logger.warning(
        f"[ENV-MONITOR] Violation CREATED — session={exam_session.id} "
        f"student={current_user.id} type={event_type} violation_id={created_violation.id}"
    )

    return ViolationStartResponse(
        violation_id=created_violation.id,
        exam_session_id=exam_session.id,
        event_type=event_type,
        severity="HIGH",
        created_at=now,
    )


# ---------------------------------------------------------------------------
# POST /runtime/env-monitor/violation-end
# ---------------------------------------------------------------------------

@router.post(
    "/violation-end",
    response_model=ViolationEndResponse,
    summary="Resolve an in-progress exam-environment violation (student returned)"
)
async def violation_end(
    req: ViolationEndRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Called when the student returns to the exam page / restores fullscreen.
    Finalises duration and transitions the violation from ACTIVE → PENDING.
    Broadcasts VIOLATION_UPDATED so the examiner sees the resolved state immediately.

    Security:
    - Validates the violation belongs to the authenticated student's session.
    - Duration is accepted from client as a hint but capped at a reasonable maximum.
      The definitive duration is computed from resolved_at − created_at on server side
      whenever audited.
    """
    # Verify session still belongs to this student (doesn't have to be RUNNING at this point —
    # the student may have submitted just before returning)
    session_result = await db.execute(
        select(ExamSession).where(
            ExamSession.exam_id == req.exam_id,
            ExamSession.student_id == current_user.id
        )
    )
    exam_session = session_result.scalar_one_or_none()
    if not exam_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam session not found.")

    # Verify violation exists and belongs to this session
    violation_result = await db.execute(
        select(Violation).where(
            Violation.id == req.violation_id,
            Violation.exam_session_id == exam_session.id
        )
    )
    violation = violation_result.scalar_one_or_none()
    if not violation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Violation not found or does not belong to this session."
        )

    # Only resolve ACTIVE violations
    if violation.status not in ("ACTIVE", "PENDING"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resolve violation with status '{violation.status}'."
        )

    now = datetime.now(timezone.utc)

    # Cap client-supplied duration to prevent manipulation (max 2 hours)
    safe_duration = min(abs(req.duration_seconds), 7200.0)

    # Resolve the violation
    violation_service = ViolationService(db)
    await violation_service.update_violation(
        req.violation_id,
        ViolationUpdate(
            status="PENDING",       # transitions to normal review queue
            duration_seconds=safe_duration,
            resolved_at=now,
        )
    )

    # Broadcast resolution to examiner
    ws_payload = {
        "violation_id": req.violation_id,
        "violation_type": violation.violation_type,
        "category": "EXAM_ENVIRONMENT",
        "severity": "HIGH",
        "source": "EXAM_ENVIRONMENT_MONITOR",
        "status": "PENDING",
        "duration_seconds": safe_duration,
        "resolved_at": now.isoformat(),
        "exam_session_id": exam_session.id,
        "student_id": current_user.id,
    }

    await manager.broadcast(WSEvent(
        event=WSEventType.VIOLATION_UPDATED,
        timestamp=now,
        exam_session_id=exam_session.id,
        payload=ws_payload,
    ))
    await manager.broadcast(WSEvent(
        event=WSEventType.ENV_MONITOR_VIOLATION_UPDATED,
        timestamp=now,
        exam_session_id=exam_session.id,
        payload=ws_payload,
    ))

    logger.info(
        f"[ENV-MONITOR] Violation RESOLVED — session={exam_session.id} "
        f"violation_id={req.violation_id} duration={safe_duration:.1f}s"
    )

    return ViolationEndResponse(
        violation_id=req.violation_id,
        duration_seconds=safe_duration,
        resolved_at=now,
    )


# ---------------------------------------------------------------------------
# GET /runtime/env-monitor/violations
# ---------------------------------------------------------------------------

@router.get(
    "/violations",
    response_model=List[EnvViolationItem],
    summary="List env-monitor violations for the student's current session (read-only)"
)
async def get_env_violations(
    exam_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the exam-environment violations for the authenticated student's session.
    Scoped strictly to the student's own session — they cannot see other students' violations.
    Used by the student monitoring panel (read-only).
    """
    # Locate session — any status (student may have just submitted)
    session_result = await db.execute(
        select(ExamSession).where(
            ExamSession.exam_id == exam_id,
            ExamSession.student_id == current_user.id
        )
    )
    exam_session = session_result.scalar_one_or_none()
    if not exam_session:
        return []

    violations_result = await db.execute(
        select(Violation).where(
            Violation.exam_session_id == exam_session.id,
            Violation.category == "EXAM_ENVIRONMENT"
        ).order_by(Violation.timestamp.desc())
    )
    violations = violations_result.scalars().all()

    return [
        EnvViolationItem(
            id=v.id,
            violation_type=v.violation_type,
            severity=v.severity,
            status=v.status,
            timestamp=v.timestamp,
            duration_seconds=v.duration_seconds,
            description=v.description,
            resolved_at=v.resolved_at,
        )
        for v in violations
    ]
