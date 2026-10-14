import logging
import asyncio
import uuid
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.schemas.ai_event import AIEventDTO
from app.websocket.connection_manager import manager
from app.websocket.websocket_events import WSEvent
from app.database.session import async_session_factory
from app.models.violation import Violation
from app.models.evidence import Evidence
from app.models.ai_session import AISession
from app.models.ai_event import AIEvent
from app.models.exam_session import ExamSession
from app.repositories.exam_session_repository import ExamSessionRepository

logger = logging.getLogger(__name__)

# Map AI Event Type to (ViolationCategory, DefaultSeverity, CooldownSeconds, MinimumConfidence)
EVENT_CONFIG = {
    "NO_FACE": ("Identity", "HIGH", 3.0, 0.5),
    "MULTIPLE_PERSONS": ("Environment", "CRITICAL", 3.0, 0.6),
    "MOBILE_PHONE": ("Prohibited Item", "CRITICAL", 2.0, 0.7),
    "BOOK_USAGE": ("Prohibited Item", "HIGH", 2.0, 0.7),
    "LOOKING_AWAY": ("Behavior", "MEDIUM", 3.0, 0.6),
    "FACE_SPOOFING": ("Identity", "CRITICAL", 5.0, 0.8),
    "WINDOW_SWITCHING": ("System", "HIGH", 2.0, 1.0),
    "AUDIO_ANOMALY": ("Environment", "MEDIUM", 5.0, 0.7),
    "UNKNOWN_PERSON": ("Identity", "CRITICAL", 5.0, 0.6),
    "CAMERA_DISCONNECTED": ("System", "CRITICAL", 5.0, 1.0),
    "MICROPHONE_DISABLED": ("System", "HIGH", 5.0, 1.0),
    "BROWSER_TAMPERING": ("System", "CRITICAL", 3.0, 1.0),
    "COMPOSITE_PHONE_LOOKING_AWAY_TALKING": ("Composite Malpractice", "CRITICAL", 3.0, 0.7),
    "COMPOSITE_FACE_MISSING_UNKNOWN": ("Identity", "CRITICAL", 3.0, 0.7),
    "BEHAVIOR_REPEATED_PATTERN": ("Behavioral Pattern", "HIGH", 5.0, 0.7),
    "CONFIRMED_PRESENTATION_ATTACK": ("Identity Protection", "CRITICAL", 3.0, 0.70),
    "IDENTITY_LOW_INTEGRITY": ("Identity Protection", "HIGH", 4.0, 0.50),
    "IDENTITY_REPEATED_MISMATCH": ("Identity Protection", "HIGH", 4.0, 0.50),
    "IDENTITY_INSTABILITY": ("Identity Protection", "MEDIUM", 4.0, 0.40),
    "INSUFFICIENT_IDENTITY_EVIDENCE": ("Identity Protection", "MEDIUM", 5.0, 0.40),
    "EARPHONES_DETECTED": ("Prohibited Item", "HIGH", 3.0, 0.65),
    "CAMERA_OBSTRUCTION": ("System", "HIGH", 3.0, 0.70),
    "REPEATED_VIOLATION_PATTERN": ("Behavioral Pattern", "HIGH", 5.0, 0.70),
    "PRESENTATION_ATTACK": ("Identity Protection", "CRITICAL", 3.0, 0.75),
}

# Auto-close window: if no new event of this type is received within this many seconds, mark resolved
AUTO_RESOLVE_TIMEOUT_SECONDS = 8.0
MAX_EVIDENCE_PER_VIOLATION = 3


class AIEventProcessor:
    """
    Central processor mapping raw AI Engine events to Violations, Evidence, and WebSockets.
    Implements persistent violation deduplication, episode duration tracking,
    evidence ranking (primary vs secondary), and 3-second replay clip attachment.
    """
    _last_event_times: Dict[str, float] = {}

    @classmethod
    async def process_event(cls, event: AIEventDTO):
        """Processes an incoming AI Event. Runs in the main AsyncIO loop."""
        # 1. Telemetry Broadcast (Always send raw telemetry to WebSocket subscribers)
        ws_event = WSEvent(
            event=event.event_type,
            timestamp=datetime.fromtimestamp(event.timestamp, tz=timezone.utc),
            exam_session_id=event.exam_session_id,
            payload={
                "severity": event.severity,
                "source": event.source_module,
                "confidence": event.confidence,
                "description": event.payload.get("description", ""),
                "data": {k: v for k, v in event.payload.items() if k != "description"}
            }
        )
        try:
            await manager.broadcast(ws_event)
        except Exception as e:
            logger.error(f"[AIEventProcessor] Failed to broadcast telemetry: {e}")

        # 2. DB Persistence and Violation Management
        try:
            async with async_session_factory() as db:
                exam_session_repo = ExamSessionRepository(db)
                exam_session = await exam_session_repo.get_by_id(event.exam_session_id)
                if not exam_session:
                    logger.error(f"[AIEventProcessor] Missing exam_session {event.exam_session_id}")
                    return

                # Persist raw AI Event History
                ai_event_record = AIEvent(
                    exam_session_id=event.exam_session_id,
                    event_type=event.event_type,
                    severity=event.severity,
                    confidence=event.confidence,
                    source_module=event.source_module,
                    payload=event.payload,
                    timestamp=datetime.fromtimestamp(event.timestamp, tz=timezone.utc)
                )
                db.add(ai_event_record)
                await db.commit()

                # Update frames processed on AISession
                if exam_session.ai_session_id:
                    ai_sess = await db.get(AISession, exam_session.ai_session_id)
                    if ai_sess:
                        ai_sess.frames_processed = (ai_sess.frames_processed or 0) + 1
                        await db.commit()

                # Check if event maps to an actionable Violation
                config = EVENT_CONFIG.get(event.event_type)
                if not config:
                    return

                category, mapped_severity, cooldown_secs, min_confidence = config

                # Confidence Threshold Filter
                if event.confidence < min_confidence:
                    return

                # Calculate Risk Score
                severity_base_weights = {
                    "CRITICAL": 100.0,
                    "HIGH": 75.0,
                    "MEDIUM": 50.0,
                    "LOW": 25.0
                }
                base_weight = severity_base_weights.get(mapped_severity, 50.0)
                conf_factor = event.confidence if event.confidence <= 1.0 else event.confidence / 100.0
                calc_risk = round(base_weight * conf_factor, 2)

                event_dt = datetime.fromtimestamp(event.timestamp, tz=timezone.utc)
                evidence_path = event.payload.get("frame_path") or event.payload.get("evidence_path")
                if evidence_path:
                    evidence_path = str(evidence_path).replace("\\", "/")

                # ── Step 3: Check for Existing OPEN Violation of Same Type ──────
                # Find an open violation in this exam session where resolved_at is NULL
                stmt = (
                    select(Violation)
                    .options(selectinload(Violation.evidence))
                    .where(
                        and_(
                            Violation.exam_session_id == event.exam_session_id,
                            Violation.violation_type == event.event_type,
                            Violation.status.in_(["PENDING", "REVIEWED"]),
                            Violation.resolved_at.is_(None)
                        )
                    )
                    .order_by(Violation.timestamp.desc())
                    .limit(1)
                )
                res = await db.execute(stmt)
                open_violation = res.scalar_one_or_none()

                # Check if open violation has timed out
                if open_violation:
                    start_ts = open_violation.timestamp.timestamp() if open_violation.timestamp.tzinfo else open_violation.timestamp.replace(tzinfo=timezone.utc).timestamp()
                    time_since_last = event.timestamp - cls._last_event_times.get(f"{event.exam_session_id}_{event.event_type}", start_ts)

                    if time_since_last > AUTO_RESOLVE_TIMEOUT_SECONDS:
                        # Auto-resolve stale violation episode, allowing a new one to be created
                        open_violation.resolved_at = datetime.fromtimestamp(
                            cls._last_event_times.get(f"{event.exam_session_id}_{event.event_type}", event.timestamp),
                            tz=timezone.utc
                        )
                        await db.commit()
                        open_violation = None

                cls._last_event_times[f"{event.exam_session_id}_{event.event_type}"] = event.timestamp

                if open_violation:
                    # ── DEDUPLICATION PATH: Update ongoing violation duration & risk ──
                    start_ts = open_violation.timestamp.timestamp() if open_violation.timestamp.tzinfo else open_violation.timestamp.replace(tzinfo=timezone.utc).timestamp()
                    duration = max(0.0, round(event.timestamp - start_ts, 2))
                    open_violation.duration_seconds = duration
                    open_violation.confidence = max(open_violation.confidence or 0.0, event.confidence)
                    open_violation.risk_score = max(open_violation.risk_score or 0.0, calc_risk)

                    # Evidence limits: up to MAX_EVIDENCE_PER_VIOLATION (1 primary + 2 secondary)
                    if evidence_path and len(open_violation.evidence) < MAX_EVIDENCE_PER_VIOLATION:
                        new_evidence = Evidence(
                            violation_id=open_violation.id,
                            file_path=evidence_path,
                            evidence_type="IMAGE",
                            timestamp=event_dt,
                            metadata_payload=event.payload,
                            confidence_score=event.confidence,
                            is_primary=False,
                            replay_clip_path=None
                        )
                        db.add(new_evidence)

                    await db.commit()
                    await db.refresh(open_violation)

                    # Broadcast VIOLATION_UPDATED
                    await manager.broadcast(WSEvent(
                        event="VIOLATION_UPDATED",
                        timestamp=event_dt,
                        exam_session_id=event.exam_session_id,
                        payload={
                            "violation_id": open_violation.id,
                            "violation_type": open_violation.violation_type,
                            "category": open_violation.category,
                            "severity": open_violation.severity,
                            "status": open_violation.status,
                            "duration_seconds": open_violation.duration_seconds,
                            "risk_score": open_violation.risk_score,
                            "confidence": open_violation.confidence,
                            "evidence_count": len(open_violation.evidence)
                        }
                    ))

                else:
                    # ── NEW VIOLATION EPISODE PATH ──
                    new_violation = Violation(
                        exam_session_id=event.exam_session_id,
                        ai_session_id=exam_session.ai_session_id,
                        violation_type=event.event_type,
                        category=category,
                        severity=mapped_severity,
                        risk_score=calc_risk,
                        confidence=event.confidence,
                        duration_seconds=0.0,
                        external_violation_id=str(uuid.uuid4()),
                        timestamp=event_dt,
                        status="PENDING",
                        description=event.payload.get("description", f"AI detected {event.event_type}")
                    )
                    db.add(new_violation)
                    await db.flush()

                    replay_clip = None

                    # Create Primary Evidence record
                    if evidence_path or replay_clip:
                        primary_ev = Evidence(
                            violation_id=new_violation.id,
                            file_path=evidence_path or (replay_clip or ""),
                            evidence_type="IMAGE" if evidence_path else "VIDEO_CLIP",
                            timestamp=event_dt,
                            metadata_payload=event.payload,
                            confidence_score=event.confidence,
                            is_primary=True,
                            replay_clip_path=replay_clip
                        )
                        db.add(primary_ev)

                    # Update AISession current risk
                    if exam_session.ai_session_id:
                        ai_sess = await db.get(AISession, exam_session.ai_session_id)
                        if ai_sess:
                            ai_sess.current_risk = max(ai_sess.current_risk or 0.0, calc_risk)

                    await db.commit()
                    await db.refresh(new_violation)

                    # Broadcast VIOLATION_CREATED
                    await manager.broadcast(WSEvent(
                        event="VIOLATION_CREATED",
                        timestamp=event_dt,
                        exam_session_id=event.exam_session_id,
                        payload={
                            "violation_id": new_violation.id,
                            "violation_type": new_violation.violation_type,
                            "category": new_violation.category,
                            "severity": new_violation.severity,
                            "status": new_violation.status,
                            "duration_seconds": 0.0,
                            "risk_score": new_violation.risk_score,
                            "confidence": new_violation.confidence,
                            "has_replay": bool(replay_clip)
                        }
                    ))

        except Exception as e:
            logger.error(f"[AIEventProcessor] Database error processing event {event.event_type}: {e}", exc_info=True)
