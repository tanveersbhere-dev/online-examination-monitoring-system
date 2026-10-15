"""
Result Serializer
=================
Reads the ExamContext (and any dynamic attributes attached by processors)
after a pipeline run and produces a single flat, JSON-serialisable dict.

This is the ONLY layer that reads from ExamContext â€” all other playground
code sends / receives this dict.

Design notes:
- All numpy arrays are converted to Python lists.
- All dataclasses / objects are decomposed to primitives.
- All None values produce sensible defaults (no KeyErrors in the frontend).
- Dynamic context attributes (observation, rule_results, risk_assessment)
  are accessed via getattr to avoid AttributeError.
"""
import time
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("playground.serializer")


def _safe(val, default=None):
    """Return val if not None, else default."""
    return val if val is not None else default


def _tuple_to_list(t) -> list:
    if t is None:
        return []
    try:
        return list(t)
    except Exception:
        return []


def _bbox_to_list(bbox) -> list:
    """Convert BoundingBox dataclass or tuple to [x, y, w, h]."""
    if bbox is None:
        return [0, 0, 0, 0]
    if hasattr(bbox, "x"):
        return [bbox.x, bbox.y, bbox.width, bbox.height]
    try:
        return list(bbox)
    except Exception:
        return [0, 0, 0, 0]


class ResultSerializer:
    """Converts ExamContext â†’ JSON-safe FrameResult dict."""

    def to_dict(
        self,
        context,
        processor_health: Dict[str, Dict[str, Any]],
        frame_counter: int,
        pipeline_ms: float,
        evidence_store: List[Dict[str, Any]],
        integration_manager: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Build the complete FrameResult.
        All errors are caught per-section so one bad field never breaks the whole message.
        """
        frame = context.current_frame

        result: Dict[str, Any] = {
            "frame_number": frame_counter,
            "timestamp": time.time(),
            "fps": round(getattr(frame, "fps", 0.0), 2) if frame else 0.0,
            "latency_ms": round(pipeline_ms, 2),
            "session": self._session(context),
            "face": self._face(context),
            "identity": self._identity(context),
            "head_pose": self._head_pose(context),
            "gaze": self._gaze(context),
            "blink": self._blink(context),
            "mouth": self._mouth(context),
            "objects": self._objects(context),
            "risk": self._risk(context),
            "violations": self._violations(context),
            "rule_results": self._rule_results(context),
            # Lifecycle transition events: empty on most frames, non-empty only
            # when a violation STARTS, escalates in severity, or RESOLVES.
            # Frontend must use these — not rule_results — to drive the timeline.
            "lifecycle_events": self._lifecycle_events(context),
            "evidence": self._evidence(evidence_store, context),
            "pipeline_health": processor_health,
            "liveness": self._liveness(context),
            "calibration": getattr(context, "calibration_info", None),
            "behavior": getattr(context, "behavior_result", None),
            "object_validation": getattr(context, "object_validation", None),
            "wearable_audio_debug": getattr(context, "wearable_audio_debug", None),
        }

        # Append Incident Intelligence Platform payload (Packages 10.1 - 10.9)
        if integration_manager:
            try:
                result["incident_platform"] = integration_manager.get_platform_serializer_payload()
            except Exception as e:
                logger.error(f"Error serializing incident_platform payload: {e}")

        # Per-frame debug trace (debug level only — not info, to avoid log flood)
        logger.debug(f"[STAGE 9 - SERIALIZER] frame={frame_counter} lifecycle_events_count={len(result['lifecycle_events'])} active_violations_count={len(result['violations'])}")
        return result

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Section serializers
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _face(self, context) -> Dict[str, Any]:
        try:
            fi = context.face_info
            return {
                "detected": _safe(fi.face_detected, False),
                "confidence": round(_safe(fi.confidence, 0.0), 4),
                "count": _safe(fi.face_count, 0),
                "bbox": _bbox_to_list(fi.bbox),
                "all_bboxes": [_bbox_to_list(b) for b in _safe(fi.all_bboxes, [])],
                "presence_state": _safe(fi.presence_state, "UNKNOWN"),
                "presence_confidence": round(_safe(fi.presence_confidence, 0.0), 4),
                "absent_duration": round(_safe(fi.absent_duration, 0.0), 2),
                "consecutive_missing_frames": _safe(fi.consecutive_missing_frames, 0),
                "occlusion_flag": _safe(fi.occlusion_flag, False),
                "detection_timestamp": _safe(fi.detection_timestamp, 0.0),
                "processing_time_ms": round(_safe(fi.processing_time_ms, 0.0), 2),
            }
        except Exception as e:
            logger.debug(f"_face serializer error: {e}")
            return {"detected": False, "confidence": 0.0, "count": 0, "bbox": []}

    def _identity(self, context) -> Dict[str, Any]:
        try:
            fi = context.face_info
            return {
                "consistent": _safe(fi.identity_consistent, True),
                "confidence": round(_safe(fi.identity_confidence, 0.0), 4),
                "similarity_score": round(_safe(fi.similarity_score, 0.0), 4),
                "has_reference": fi.reference_embedding is not None,
                "verification_timestamp": _safe(fi.verification_timestamp, 0.0),
                "processing_time_ms": round(_safe(fi.identity_processing_time_ms, 0.0), 2),
            }
        except Exception as e:
            logger.debug(f"_identity serializer error: {e}")
            return {"consistent": True, "confidence": 0.0, "similarity_score": 0.0}

    def _head_pose(self, context) -> Dict[str, Any]:
        try:
            hp = context.head_pose_info
            return {
                "yaw": round(_safe(hp.yaw, 0.0), 2),
                "pitch": round(_safe(hp.pitch, 0.0), 2),
                "roll": round(_safe(hp.roll, 0.0), 2),
                "pose_class": _safe(hp.pose_class, "UNKNOWN"),
                "success": _safe(hp.success, False),
                "processing_time_ms": round(_safe(hp.processing_time_ms, 0.0), 2),
            }
        except Exception as e:
            logger.debug(f"_head_pose serializer error: {e}")
            return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0, "pose_class": "UNKNOWN", "success": False}

    def _gaze(self, context) -> Dict[str, Any]:
        try:
            ei = context.eye_info
            # Try to get gaze state from observation first (fusion output)
            obs = getattr(context, "observation", None)
            gaze_state = "UNCERTAIN"
            calibration = getattr(context, "calibration_info", None)
            decision = calibration.get("gaze_decision", {}) if isinstance(calibration, dict) else {}
            if decision.get("state"):
                gaze_state = _safe(decision.get("state"), "UNCERTAIN")
            elif obs and obs.face:
                gaze_state = _safe(obs.face.gaze_state, "UNCERTAIN")

            combined = _tuple_to_list(getattr(ei, "combined_gaze", (0.0, 0.0, 0.0)))
            return {
                "state": gaze_state,
                "confidence": round(_safe(ei.gaze_confidence, 0.0), 4),
                "combined_vector": combined,
                "left_iris": _tuple_to_list(getattr(ei, "left_iris_center", None)),
                "right_iris": _tuple_to_list(getattr(ei, "right_iris_center", None)),
                "look_away_seconds": round(_safe(ei.look_away_seconds, 0.0), 2),
                "decision": decision,
                "processing_time_ms": round(_safe(ei.processing_time_ms, 0.0), 2),
            }
        except Exception as e:
            logger.debug(f"_gaze serializer error: {e}")
            return {"state": "UNKNOWN", "confidence": 0.0}

    def _blink(self, context) -> Dict[str, Any]:
        try:
            ei = context.eye_info
            return {
                "detected": _safe(ei.blink_detected, False),
                "frequency": round(_safe(ei.blink_frequency, 0.0), 2),
                "eye_state": _safe(ei.eye_state, "UNKNOWN"),
                "blink_count": _safe(ei.blink_count, 0),
                "blink_duration": round(_safe(ei.blink_duration, 0.0), 3),
                "consecutive_closed_frames": _safe(ei.consecutive_closed_frames, 0),
                "ear": {
                    "left": round(_safe(ei.left_ear, 0.0), 4),
                    "right": round(_safe(ei.right_ear, 0.0), 4),
                    "average": round(_safe(ei.average_ear, 0.0), 4),
                    "confidence": round(_safe(ei.ear_confidence, 0.0), 4),
                },
            }
        except Exception as e:
            logger.debug(f"_blink serializer error: {e}")
            return {"detected": False, "eye_state": "UNKNOWN", "ear": {"left": 0, "right": 0, "average": 0}}

    def _mouth(self, context) -> Dict[str, Any]:
        try:
            mi = context.mouth_info
            return {
                "mar": round(_safe(mi.mar, 0.0), 4),
                "is_talking": _safe(mi.is_talking, False),
                "talking_seconds": round(_safe(mi.talking_seconds, 0.0), 2),
                "confidence": round(_safe(mi.confidence, 0.0), 4),
                "mouth_width": round(_safe(mi.mouth_width, 0.0), 4),
                "mouth_height": round(_safe(mi.mouth_height, 0.0), 4),
                "processing_time_ms": round(_safe(mi.processing_time_ms, 0.0), 2),
            }
        except Exception as e:
            logger.debug(f"_mouth serializer error: {e}")
            return {"mar": 0.0, "is_talking": False}

    def _objects(self, context) -> List[Dict[str, Any]]:
        try:
            oi = context.object_info
            items = []

            # Prefer tracked objects; fall back to filtered detections
            source = oi.tracked_objects or oi.filtered_detections or oi.current_detections or []

            for obj in source:
                obj_type = getattr(obj, "object_type", None)
                type_name = obj_type.name if hasattr(obj_type, "name") else str(obj_type)
                items.append({
                    "type": type_name,
                    "confidence": round(_safe(getattr(obj, "confidence", 0.0), 0.0), 4),
                    "bbox": _bbox_to_list(getattr(obj, "bbox", None)),
                    "tracking_id": _safe(getattr(obj, "tracking_id", None), -1),
                    "status": _safe(getattr(obj, "current_state", "DETECTED"), "DETECTED"),
                    "visible_duration": round(_safe(getattr(obj, "visible_duration", 0.0), 0.0), 2),
                })

            # If audio device is detected on dedicated branch, include it in objects
            # so UI bounding box overlay renders the earphone bounding box immediately
            audio_info = getattr(context, "audio_device_info", None)
            if audio_info and (getattr(audio_info, "detected", False) or getattr(audio_info, "confidence", 0.0) >= 0.35) and getattr(audio_info, "bbox", None):
                items.append({
                    "type": "COMM_EARPHONES",
                    "confidence": round(_safe(getattr(audio_info, "confidence", 0.0), 0.0), 4),
                    "bbox": _bbox_to_list(getattr(audio_info, "bbox", None)),
                    "tracking_id": 999,
                    "status": "DETECTED",
                    "visible_duration": 0.0,
                })

            return items
        except Exception as e:
            logger.debug(f"_objects serializer error: {e}")
            return []

    def _risk(self, context) -> Dict[str, Any]:
        try:
            ra = getattr(context, "risk_assessment", None)
            if ra is None:
                return {"score": 0.0, "level": "NORMAL", "triggered_rules": 0}
            return {
                "score": round(_safe(ra.overall_score, 0.0), 2),
                "level": _safe(ra.risk_level, "NORMAL"),
                "triggered_rules": _safe(ra.triggered_rule_count, 0),
                "highest_rule": _safe(ra.highest_priority_rule_id, "NONE"),
                "contributions": [
                    {
                        "rule_id": c.rule_id,
                        "rule_name": c.rule_name,
                        "contribution": round(c.contribution, 2),
                        "weight": c.weight,
                    }
                    for c in _safe(ra.contributions, [])
                ],
            }
        except Exception as e:
            logger.debug(f"_risk serializer error: {e}")
            return {"score": 0.0, "level": "NORMAL", "triggered_rules": 0}

    def _violations(self, context) -> List[Dict[str, Any]]:
        try:
            from ai_engine.intelligence.behavior_engine.composite_behavior import format_composite_incident_title
            violations_obj = getattr(context, "violations", None)
            if violations_obj is None:
                return []

            # Handle ViolationManagerResult vs raw Violations
            timeline = getattr(violations_obj, "timeline", violations_obj)
            viol_list = getattr(timeline, "violations", getattr(timeline, "list_violations", []))

            res = []
            for v in viol_list:
                if getattr(v, "status", "") in ("OPEN", "ACTIVE", "RECOVERING"):
                    title = format_composite_incident_title(v.violation_type, v.triggered_rules)
                    res.append({
                        "id": v.violation_id,
                        "episode_id": v.violation_id,
                        "camera_id": getattr(v, "camera_id", "camera_1"),
                        "violation": True,
                        "type": v.violation_type,
                        "message": title,
                        "rule_id": v.violation_type,
                        "title": title,
                        "incident_title": title,
                        "display_name": title,
                        "category": v.violation_category,
                        "severity": v.severity,
                        "risk_score": round(v.risk_score, 2),
                        "confidence": round(getattr(v, "peak_confidence", 0.90), 4),
                        "current_confidence": round(getattr(v, "current_confidence", 0.0), 4),
                        "peak_confidence": round(getattr(v, "peak_confidence", 0.0), 4),
                        "detection_count": getattr(v, "detection_count", 0),
                        "duration": round(max(0.0, v.last_updated_timestamp - v.start_timestamp), 2),
                        "last_seen_at": v.last_updated_timestamp,
                        "status": v.status,
                        "triggered_rules": v.triggered_rules,
                        "start_timestamp": v.start_timestamp,
                        "last_updated": v.last_updated_timestamp,
                        "timestamp": v.last_updated_timestamp,
                        "transition": "UPDATED" if v.status == "ACTIVE" else "STARTED",
                        "description": f"{title} | {v.description}",
                    })
            return res
        except Exception as e:
            logger.debug(f"_violations serializer error: {e}")
            return []

    def _rule_results(self, context) -> List[Dict[str, Any]]:
        try:
            rr = getattr(context, "rule_results", None)
            if rr is None:
                return []
            return [
                {
                    "rule_id": e.rule_id,
                    "rule_name": e.rule_name,
                    "category": e.category,
                    "triggered": e.triggered,
                    "confidence": round(e.confidence, 4),
                    "support": e.supporting_observations,
                    "duration_ms": round(e.evaluation_duration, 2),
                }
                for e in _safe(rr.evaluations, [])
            ]
        except Exception as e:
            logger.debug(f"_rule_results serializer error: {e}")
            return []

    def _session(self, context) -> Dict[str, Any]:
        try:
            ms = getattr(context, "monitoring_session", None)
            if ms:
                return {
                    "monitoring_session_id": ms.monitoring_session_id,
                    "student_id": ms.student_id,
                    "examiner_id": ms.examiner_id,
                    "exam_id": ms.exam_id,
                    "attempt_id": ms.attempt_id,
                    "mode": ms.mode,
                    "status": ms.status,
                    "start_time": ms.start_time,
                }
            si = getattr(context, "session_info", None)
            if si:
                return {
                    "monitoring_session_id": "standalone_session",
                    "student_id": getattr(si, "student_id", "local_student"),
                    "examiner_id": "local_examiner",
                    "exam_id": getattr(si, "exam_id", "local_exam"),
                    "attempt_id": "local_attempt_1",
                    "mode": "standalone",
                    "status": "IN_PROGRESS",
                    "start_time": getattr(si, "start_time", 0.0),
                }
            return {
                "monitoring_session_id": "standalone_session",
                "student_id": "local_student",
                "exam_id": "local_exam",
                "attempt_id": "local_attempt_1",
                "mode": "standalone",
                "status": "IN_PROGRESS",
            }
        except Exception as e:
            logger.debug(f"_session serializer error: {e}")
            return {"mode": "standalone", "status": "IN_PROGRESS"}

    def _evidence(self, evidence_store: List[Dict[str, Any]], context=None) -> List[Dict[str, Any]]:
        """Return the last 50 evidence records enriched with session traceability."""
        items = evidence_store[-50:]
        ms = getattr(context, "monitoring_session", None) if context else None
        if ms:
            for item in items:
                if isinstance(item, dict):
                    if "student_id" not in item:
                        item["student_id"] = ms.student_id
                    if "exam_id" not in item:
                        item["exam_id"] = ms.exam_id
                    if "attempt_id" not in item:
                        item["attempt_id"] = ms.attempt_id
                    if "monitoring_session_id" not in item:
                        item["monitoring_session_id"] = ms.monitoring_session_id
        return items

    def _lifecycle_events(self, context) -> List[Dict[str, Any]]:
        """
        Serialize lifecycle transition events attached by ViolationManager.

        Returns an empty list on the vast majority of frames.
        Non-empty only when a violation STARTS, severity escalates/updates, or RESOLVES.
        The frontend EventTimeline must consume these exclusively â€” not rule_results.
        """
        try:
            from ai_engine.intelligence.behavior_engine.composite_behavior import format_composite_incident_title
            events = getattr(context, "lifecycle_events", None)
            if not events:
                return []
            res = []
            for e in events:
                title = format_composite_incident_title(e.violation_type, e.triggered_rules)
                res.append({
                    "id": e.violation_id,
                    "violation_id": e.violation_id,
                    "episode_id": e.violation_id,
                    "camera_id": getattr(e, "camera_id", "camera_1"),
                    "type": e.violation_type,
                    "title": title,
                    "incident_title": title,
                    "display_name": title,
                    "category": e.violation_category,
                    "transition": e.event_type,       # "STARTED" | "UPDATED" | "RESOLVED"
                    "status": "RESOLVED" if e.event_type == "RESOLVED" else "ACTIVE",
                    "severity": e.severity,
                    "confidence": round(getattr(e, "current_confidence", 0.0), 4),
                    "peak_confidence": round(getattr(e, "peak_confidence", 0.0), 4),
                    "detection_count": getattr(e, "detection_count", 0),
                    "duration": round(getattr(e, "duration", 0.0), 2),
                    "risk_score": round(e.risk_score, 2),
                    "triggered_rules": e.triggered_rules,
                    "started_at": e.start_timestamp,
                    "ended_at": e.end_timestamp,
                    "timestamp": e.timestamp,
                    "description": f"{title} | {e.description}",
                })
            return res
        except Exception as e:
            logger.debug(f"_lifecycle_events serializer error: {e}")
            return []


    def _liveness(self, context) -> Dict[str, Any]:
        try:
            obs = getattr(context, "identity_protection_observation", None)
            if obs is None:
                return {"state": "UNKNOWN", "score": 0.0}

            assessment = getattr(obs, "assessment", None)
            return {
                "state": _safe(getattr(obs, "liveness_state", None), "UNKNOWN"),
                "score": round(_safe(getattr(obs, "liveness_score", 0.0), 0.0), 4),
                "spoof_confidence": round(_safe(getattr(obs, "spoof_confidence", 0.0), 0.0), 4),
                "reflection_score": round(_safe(getattr(obs, "reflection_score", 0.0), 0.0), 4),
                "temporal_consistency": round(_safe(getattr(obs, "temporal_consistency", 1.0), 1.0), 4),
                "integrity_score": round(
                    _safe(getattr(assessment, "integrity_score", None) if assessment else None, 0.0), 4
                ),
                "latency_ms": round(_safe(getattr(obs, "inference_latency_ms", 0.0), 0.0), 2),
            }
        except Exception as e:
            logger.debug(f"_liveness serializer error: {e}")
            return {"state": "UNKNOWN", "score": 0.0}
