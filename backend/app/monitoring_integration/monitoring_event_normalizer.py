"""
Monitoring Event Normalizer
===========================
Translates ai_monitoring_playground violations, rule triggers, object detections,
and lifecycle events into normalized AIEventDTO objects for main-system AIEventProcessor ingestion.
"""
import logging
import time
import uuid
import asyncio
from typing import Dict, Any, List, Optional, Set

from app.schemas.ai_event import AIEventDTO
from app.services.ai_event_processor import AIEventProcessor
from app.monitoring_integration.monitoring_contracts import (
    EVENT_TYPE_MAPPING,
    SEVERITY_MAPPING,
    RULE_SEVERITY_MAPPING,
    NormalizedMonitoringEvent
)

logger = logging.getLogger(__name__)


class MonitoringEventNormalizer:
    """
    Normalizes monitoring outputs from ai_monitoring_playground into
    standard AIEventDTO structures consumed by AIEventProcessor.
    """

    @classmethod
    def normalize_event_type(cls, raw_type: str) -> str:
        """Maps subsystem rule/violation code to standard main-system event name."""
        return EVENT_TYPE_MAPPING.get(raw_type, raw_type)

    @classmethod
    def normalize_severity(cls, raw_severity: str, default: str = "MEDIUM") -> str:
        """Normalizes severity strings (e.g. ELEVATED -> HIGH)."""
        sev_upper = str(raw_severity).upper() if raw_severity else default
        return SEVERITY_MAPPING.get(sev_upper, default)

    @classmethod
    def process_frame_result(
        cls,
        frame_result: Dict[str, Any],
        exam_session_id: int,
        student_id: int,
        main_loop: Optional[Any] = None,
        evidence_path: Optional[str] = None
    ) -> List[NormalizedMonitoringEvent]:
        """
        Extracts violations, lifecycle transitions, triggered rules, and object detections
        from FrameResult, normalizes them with deduplication, and dispatches to AIEventProcessor.
        """
        emitted_events: List[NormalizedMonitoringEvent] = []
        emitted_types: Set[str] = set()

        # 1. Process Lifecycle Events (Transitions: STARTED, UPDATED, RESOLVED)
        lifecycle_events = frame_result.get("lifecycle_events") or []
        for le in lifecycle_events:
            if not isinstance(le, dict):
                continue

            raw_type = le.get("type") or le.get("violation_type") or "UNKNOWN"
            norm_type = cls.normalize_event_type(raw_type)
            norm_sev = cls.normalize_severity(le.get("severity") or RULE_SEVERITY_MAPPING.get(raw_type, "HIGH"))
            conf = float(le.get("confidence") or le.get("current_confidence") or 0.9)
            ts = float(le.get("timestamp") or le.get("started_at") or time.time())
            transition = str(le.get("transition", "STARTED")).upper()

            payload = {
                "description": le.get("description") or f"Monitoring incident: {norm_type}",
                "rule_id": raw_type,
                "violation_id": le.get("violation_id") or le.get("id"),
                "duration": le.get("duration", 0.0),
                "peak_confidence": le.get("peak_confidence", conf),
                "triggered_rules": le.get("triggered_rules", []),
                "transition": transition,
            }
            if evidence_path:
                payload["frame_path"] = evidence_path

            event = NormalizedMonitoringEvent(
                event_type=norm_type,
                severity=norm_sev,
                confidence=conf,
                timestamp=ts,
                exam_session_id=exam_session_id,
                student_id=student_id,
                source_module="monitoring_subsystem.lifecycle",
                payload=payload,
                frame_path=evidence_path,
                rule_id=raw_type,
                is_lifecycle_transition=True,
                transition_type=transition
            )
            emitted_events.append(event)
            emitted_types.add(norm_type)

            cls._dispatch_to_processor(event, main_loop)

        # 2. Process Active Violations
        active_violations = frame_result.get("violations") or []
        for v in active_violations:
            if not isinstance(v, dict):
                continue

            raw_type = v.get("type") or v.get("rule_id") or "UNKNOWN"
            norm_type = cls.normalize_event_type(raw_type)

            if norm_type in emitted_types:
                continue

            norm_sev = cls.normalize_severity(v.get("severity") or RULE_SEVERITY_MAPPING.get(raw_type, "HIGH"))
            conf = float(v.get("confidence") or v.get("peak_confidence") or 0.85)
            ts = float(v.get("last_seen_at") or v.get("timestamp") or time.time())

            payload = {
                "description": v.get("description") or v.get("title") or f"Active violation: {norm_type}",
                "rule_id": raw_type,
                "violation_id": v.get("id") or v.get("episode_id"),
                "duration": v.get("duration", 0.0),
                "triggered_rules": v.get("triggered_rules", []),
            }
            if evidence_path:
                payload["frame_path"] = evidence_path

            event = NormalizedMonitoringEvent(
                event_type=norm_type,
                severity=norm_sev,
                confidence=conf,
                timestamp=ts,
                exam_session_id=exam_session_id,
                student_id=student_id,
                source_module="monitoring_subsystem.violations",
                payload=payload,
                frame_path=evidence_path,
                rule_id=raw_type
            )
            emitted_events.append(event)
            emitted_types.add(norm_type)

            cls._dispatch_to_processor(event, main_loop)

        # 3. Process Triggered Rule Results from RuleEngine
        rule_results = frame_result.get("rule_results") or []
        for r in rule_results:
            if not isinstance(r, dict) or not r.get("triggered"):
                continue

            raw_type = r.get("rule_id") or "UNKNOWN"
            norm_type = cls.normalize_event_type(raw_type)

            if norm_type in emitted_types:
                continue

            norm_sev = cls.normalize_severity(r.get("severity") or RULE_SEVERITY_MAPPING.get(raw_type, "HIGH"))
            conf = float(r.get("confidence") or 0.85)
            ts = time.time()

            payload = {
                "description": r.get("support") or r.get("rule_name") or f"Rule triggered: {norm_type}",
                "rule_id": raw_type,
                "triggered_rules": [raw_type],
            }
            if evidence_path:
                payload["frame_path"] = evidence_path

            event = NormalizedMonitoringEvent(
                event_type=norm_type,
                severity=norm_sev,
                confidence=conf,
                timestamp=ts,
                exam_session_id=exam_session_id,
                student_id=student_id,
                source_module="monitoring_subsystem.rule_engine",
                payload=payload,
                frame_path=evidence_path,
                rule_id=raw_type
            )
            emitted_events.append(event)
            emitted_types.add(norm_type)

            cls._dispatch_to_processor(event, main_loop)

        # 4. Direct Object Detections (YOLO / Wearables fallback)
        objects = frame_result.get("objects") or []
        for obj in objects:
            if not isinstance(obj, dict):
                continue
            obj_name = str(obj.get("type", "")).upper()
            conf = float(obj.get("confidence", 0.85))

            if obj_name in ("CELL_PHONE", "PHONE", "MOBILE_PHONE") and "MOBILE_PHONE" not in emitted_types:
                payload = {"description": "Mobile phone detected in environment", "confidence": conf}
                if evidence_path:
                    payload["frame_path"] = evidence_path
                event = NormalizedMonitoringEvent(
                    event_type="MOBILE_PHONE",
                    severity="CRITICAL",
                    confidence=conf,
                    timestamp=time.time(),
                    exam_session_id=exam_session_id,
                    student_id=student_id,
                    source_module="monitoring_subsystem.object_detection",
                    payload=payload,
                    frame_path=evidence_path
                )
                emitted_events.append(event)
                emitted_types.add("MOBILE_PHONE")
                cls._dispatch_to_processor(event, main_loop)

            elif obj_name in ("BOOK", "NOTEBOOK", "PAPER") and "BOOK_USAGE" not in emitted_types:
                payload = {"description": "Book or unauthorized notes detected", "confidence": conf}
                if evidence_path:
                    payload["frame_path"] = evidence_path
                event = NormalizedMonitoringEvent(
                    event_type="BOOK_USAGE",
                    severity="HIGH",
                    confidence=conf,
                    timestamp=time.time(),
                    exam_session_id=exam_session_id,
                    student_id=student_id,
                    source_module="monitoring_subsystem.object_detection",
                    payload=payload,
                    frame_path=evidence_path
                )
                emitted_events.append(event)
                emitted_types.add("BOOK_USAGE")
                cls._dispatch_to_processor(event, main_loop)

            elif obj_name in ("EARPHONES", "HEADPHONES", "AIRPODS") and "EARPHONES_DETECTED" not in emitted_types:
                payload = {"description": "Earphones or wearable audio device detected", "confidence": conf}
                if evidence_path:
                    payload["frame_path"] = evidence_path
                event = NormalizedMonitoringEvent(
                    event_type="EARPHONES_DETECTED",
                    severity="HIGH",
                    confidence=conf,
                    timestamp=time.time(),
                    exam_session_id=exam_session_id,
                    student_id=student_id,
                    source_module="monitoring_subsystem.object_detection",
                    payload=payload,
                    frame_path=evidence_path
                )
                emitted_events.append(event)
                emitted_types.add("EARPHONES_DETECTED")
                cls._dispatch_to_processor(event, main_loop)

        # 5. Direct Face Anomaly Detection
        face = frame_result.get("face") or {}
        if isinstance(face, dict):
            face_count = face.get("face_count", 1 if face.get("face_detected") else 0)
            if face_count > 1 and "MULTIPLE_PERSONS" not in emitted_types:
                payload = {"description": f"Multiple persons detected ({face_count} faces)", "confidence": 0.95}
                if evidence_path:
                    payload["frame_path"] = evidence_path
                event = NormalizedMonitoringEvent(
                    event_type="MULTIPLE_PERSONS",
                    severity="CRITICAL",
                    confidence=0.95,
                    timestamp=time.time(),
                    exam_session_id=exam_session_id,
                    student_id=student_id,
                    source_module="monitoring_subsystem.face_detection",
                    payload=payload,
                    frame_path=evidence_path
                )
                emitted_events.append(event)
                emitted_types.add("MULTIPLE_PERSONS")
                cls._dispatch_to_processor(event, main_loop)

        # 6. Direct Gaze / Head Pose Anomaly
        gaze = frame_result.get("gaze") or {}
        if isinstance(gaze, dict):
            look_away_sec = float(gaze.get("look_away_seconds") or 0.0)
            gaze_state = str(gaze.get("state", "")).upper()
            if (look_away_sec >= 1.5 or gaze_state in ("LOOKING_AWAY", "AWAY", "LEFT", "RIGHT", "DOWN")) and "LOOKING_AWAY" not in emitted_types:
                payload = {"description": f"Candidate looking away from screen (gaze: {gaze_state})", "confidence": 0.85}
                if evidence_path:
                    payload["frame_path"] = evidence_path
                event = NormalizedMonitoringEvent(
                    event_type="LOOKING_AWAY",
                    severity="MEDIUM",
                    confidence=0.85,
                    timestamp=time.time(),
                    exam_session_id=exam_session_id,
                    student_id=student_id,
                    source_module="monitoring_subsystem.gaze",
                    payload=payload,
                    frame_path=evidence_path
                )
                emitted_events.append(event)
                emitted_types.add("LOOKING_AWAY")
                cls._dispatch_to_processor(event, main_loop)

        return emitted_events

    @classmethod
    def _dispatch_to_processor(cls, event: NormalizedMonitoringEvent, main_loop: Optional[Any] = None) -> None:
        """Dispatches normalized event to main system AIEventProcessor asynchronously."""
        dto = AIEventDTO(
            event_type=event.event_type,
            timestamp=event.timestamp,
            exam_session_id=event.exam_session_id,
            severity=event.severity,
            source_module=event.source_module,
            confidence=event.confidence,
            payload=event.payload
        )

        try:
            if main_loop and main_loop.is_running():
                asyncio.run_coroutine_threadsafe(AIEventProcessor.process_event(dto), main_loop)
            else:
                try:
                    current_loop = asyncio.get_running_loop()
                    current_loop.create_task(AIEventProcessor.process_event(dto))
                except RuntimeError:
                    asyncio.run(AIEventProcessor.process_event(dto))
        except Exception as e:
            logger.error(f"[MonitoringEventNormalizer] Failed to dispatch event {dto.event_type}: {e}")
