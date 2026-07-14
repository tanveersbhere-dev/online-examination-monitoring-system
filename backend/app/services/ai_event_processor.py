import logging
import asyncio
from typing import Dict, Any, Tuple
from datetime import datetime

from app.schemas.ai_event import AIEventDTO
from app.websocket.connection_manager import manager
from app.websocket.websocket_events import WSEvent
from app.database.session import async_session_factory
from app.repositories.violation_repository import ViolationRepository
from app.repositories.exam_session_repository import ExamSessionRepository
from app.services.violation_service import ViolationService
from app.services.evidence_service import EvidenceService
from app.schemas.violation import ViolationCreate
from app.schemas.evidence import EvidenceCreate

logger = logging.getLogger(__name__)

# Map AI Event Type to (ViolationCategory, DefaultSeverity, CooldownSeconds, MinimumConfidence)
EVENT_CONFIG = {
    "NO_FACE": ("Identity", "HIGH", 5.0, 0.5),
    "MULTIPLE_PERSONS": ("Environment", "CRITICAL", 5.0, 0.6),
    "MOBILE_PHONE": ("Prohibited Item", "CRITICAL", 3.0, 0.7),
    "LOOKING_AWAY": ("Behavior", "MEDIUM", 5.0, 0.6),
    "FACE_SPOOFING": ("Identity", "CRITICAL", 10.0, 0.8),
    "WINDOW_SWITCHING": ("System", "HIGH", 2.0, 1.0),
    "AUDIO_ANOMALY": ("Environment", "MEDIUM", 5.0, 0.7),
    "UNKNOWN_PERSON": ("Identity", "CRITICAL", 10.0, 0.6),
    "CAMERA_DISCONNECTED": ("System", "CRITICAL", 10.0, 1.0),
    "MICROPHONE_DISABLED": ("System", "HIGH", 10.0, 1.0),
    "BROWSER_TAMPERING": ("System", "CRITICAL", 5.0, 1.0),
}

class AIEventProcessor:
    """
    Central processor mapping raw AI Engine events to Violations and WebSockets.
    Maintains an in-memory TTL dictionary for duplicate event suppression.
    """
    _cooldowns: Dict[str, float] = {}
    
    @classmethod
    def _is_suppressed(cls, exam_session_id: int, event_type: str, cooldown_secs: float, current_time: float) -> bool:
        key = f"{exam_session_id}_{event_type}"
        last_seen = cls._cooldowns.get(key, 0.0)
        
        if current_time - last_seen < cooldown_secs:
            return True
            
        cls._cooldowns[key] = current_time
        return False

    @classmethod
    async def process_event(cls, event: AIEventDTO):
        """Processes an incoming AI Event. Runs in the main AsyncIO loop."""
        
        # 1. Telemetry Broadcast (Always send raw telemetry)
        ws_event = WSEvent(
            event=event.event_type,
            timestamp=datetime.fromtimestamp(event.timestamp),
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
            logger.error(f"Failed to broadcast telemetry event {event.event_type}: {e}")

        # 2. Check if event maps to a actionable Violation
        config = EVENT_CONFIG.get(event.event_type)
        if not config:
            # Not actionable, just telemetry
            return
            
        category, mapped_severity, cooldown_secs, min_confidence = config
        
        # 3. Confidence Threshold Filter
        if event.confidence < min_confidence:
            return
            
        # 4. Duplicate Suppression (Rate Limiting)
        if cls._is_suppressed(event.exam_session_id, event.event_type, cooldown_secs, event.timestamp):
            return

        # 5. DB Persistence using standalone session
        try:
            async with async_session_factory() as db:
                exam_session_repo = ExamSessionRepository(db)
                exam_session = await exam_session_repo.get_by_id(event.exam_session_id)
                if not exam_session:
                    logger.error(f"Cannot process event for missing exam_session {event.exam_session_id}")
                    return

                # Create Violation
                violation_service = ViolationService(db)
                violation_in = ViolationCreate(
                    exam_session_id=event.exam_session_id,
                    ai_session_id=exam_session.ai_session_id,
                    violation_type=event.event_type,
                    category=category,
                    severity=mapped_severity,
                    risk_score=event.confidence,
                    description=event.payload.get("description", f"AI detected {event.event_type}")
                )
                violation = await violation_service.create_violation(violation_in)
                
                # Optionally, if a frame is provided in payload for evidence, generate Evidence
                # Often the AI payload will contain `frame_path` or `evidence_path`
                evidence_path = event.payload.get("frame_path") or event.payload.get("evidence_path")
                if evidence_path:
                    evidence_service = EvidenceService(db)
                    evidence_in = EvidenceCreate(
                        violation_id=violation.id,
                        file_path=evidence_path,
                        evidence_type="IMAGE",
                        timestamp=datetime.fromtimestamp(event.timestamp),
                        metadata_payload=event.payload,
                        confidence_score=event.confidence
                    )
                    await evidence_service.create_evidence(evidence_in)
                    
                # Broadcast VIOLATION_CREATED
                v_event = WSEvent(
                    event="VIOLATION_CREATED",
                    timestamp=datetime.fromtimestamp(event.timestamp),
                    exam_session_id=event.exam_session_id,
                    payload={
                        "violation_id": violation.id,
                        "violation_type": violation.violation_type,
                        "category": violation.category,
                        "severity": violation.severity,
                        "status": violation.status
                    }
                )
                await manager.broadcast(v_event)
                
        except Exception as e:
            logger.error(f"Database error during AI event processing: {e}")
