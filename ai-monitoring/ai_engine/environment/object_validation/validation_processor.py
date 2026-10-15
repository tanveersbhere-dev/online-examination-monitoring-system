"""
Object Validation & Reliability Processor (Step 13 in Pipeline Orchestrator).
Enforces class whitelisting, per-class confidence thresholds, and temporal confirmation.
"""
import time
import logging
from typing import List, Dict, Any, Optional

from ai_engine.core.exam_context import ExamContext, TrackedObject
from ai_engine.environment.object_validation.models import (
    ObjectValidationConfig, ValidationReason, ValidationAuditRecord, ValidationStatistics
)
from ai_engine.environment.object_validation.temporal_buffer import TemporalConfirmationBuffer

logger = logging.getLogger("ai_engine.object_validation.processor")

class ObjectValidationProcessor:
    """
    Step 13 Processor. Validates object detections for class whitelisting, confidence,
    and temporal persistence prior to observation fusion and rule evaluation.
    """
    def __init__(self, config: Optional[ObjectValidationConfig] = None) -> None:
        self.config: ObjectValidationConfig = config or ObjectValidationConfig()
        self.temporal_buffer: TemporalConfirmationBuffer = TemporalConfirmationBuffer(self.config)
        self._initialized: bool = False
        self.last_proc_time_ms: float = 0.0

    def initialize(self) -> None:
        self.temporal_buffer.clear()
        self._initialized = True
        if self.config.enable_logging:
            logger.info("ObjectValidationProcessor initialized.")

    def start(self) -> None:
        self.initialize()

    def stop(self) -> None:
        pass

    def cleanup(self) -> None:
        self._initialized = False

    def clear_camera(self, camera_id: str) -> None:
        """Purges temporal buffer state for a specific camera (e.g. on disconnect)."""
        if hasattr(self, "temporal_buffer") and hasattr(self.temporal_buffer, "clear_camera"):
            self.temporal_buffer.clear_camera(camera_id)

    def process(self, context: ExamContext) -> None:
        if not self._initialized:
            return

        t0 = time.perf_counter()
        current_ts = time.time()
        frame_id = getattr(context.object_info, "frame_id", 0)

        # 1. Resolve raw inputs (tracked_objects -> filtered_detections -> current_detections)
        o_info = context.object_info
        raw_tracked = getattr(o_info, "tracked_objects", None)
        raw_filtered = getattr(o_info, "filtered_detections", None)

        items_to_validate: List[Any] = []
        if isinstance(raw_tracked, list) and len(raw_tracked) > 0:
            items_to_validate = raw_tracked
        elif isinstance(raw_filtered, list) and len(raw_filtered) > 0:
            items_to_validate = raw_filtered
        elif isinstance(raw_tracked, list):
            items_to_validate = raw_tracked

        stats = ValidationStatistics(total_received=len(items_to_validate))
        audit_records: List[ValidationAuditRecord] = []
        validated_items: List[Any] = []
        active_keys_seen = set()

        curr_frame = getattr(context, "current_frame", None)
        cam_id = str(getattr(curr_frame, "camera_id", "camera_1") or "camera_1")

        # 2. Iterate each detection candidate
        for item in items_to_validate:
            # Determine object type string
            raw_type = getattr(item, "object_type", None)
            type_str = getattr(raw_type, "name", str(raw_type)) if raw_type is not None else "UNKNOWN"
            confidence = getattr(item, "confidence", 0.0)
            track_id = getattr(item, "tracking_id", getattr(item, "track_id", None))
            bbox = getattr(item, "bbox", None)

            # Build track key (track identity allows smoothing across fluctuating class predictions, isolated per camera)
            if track_id is not None and track_id >= 0:
                track_key = f"{cam_id}_trk_{track_id}"
            else:
                x_center = round(getattr(bbox, 'x', 0) / 50.0) if bbox else 0
                y_center = round(getattr(bbox, 'y', 0) / 50.0) if bbox else 0
                track_key = f"{cam_id}_sp_{x_center}_{y_center}"

            active_keys_seen.add(track_key)

            # Step A: Class Whitelisting Check
            if type_str not in self.config.whitelisted_classes:
                stats.rejected_unsupported_class += 1
                audit_records.append(ValidationAuditRecord(
                    frame_id=frame_id,
                    object_type=type_str,
                    confidence=confidence,
                    tracking_id=track_id,
                    status="REJECTED",
                    reason=ValidationReason.REJECTED_UNSUPPORTED_CLASS,
                    details=f"Class '{type_str}' is not whitelisted"
                ))
                continue

            # Step B: Per-Class Confidence Threshold Check (with confusable candidate allowance)
            class_cfg = self.config.class_configs.get(type_str, self.config.default_config)
            confusable_types = ("LAPTOP", "BOOK", "NOTEBOOK", "REGISTER", "PAPER", "UNAUTHORIZED_MATERIAL", "PAGE", "TEXTBOOK")
            candidate_min_conf = 0.22 if cam_id == "camera_2" else 0.28
            is_confusable_candidate = (type_str in confusable_types and confidence >= candidate_min_conf)
            is_cam2_phone_candidate = (cam_id == "camera_2" and type_str == "CELL_PHONE" and confidence >= 0.22)
            if confidence < class_cfg.min_confidence and not (is_confusable_candidate or is_cam2_phone_candidate):
                stats.rejected_low_confidence += 1
                audit_records.append(ValidationAuditRecord(
                    frame_id=frame_id,
                    object_type=type_str,
                    confidence=confidence,
                    tracking_id=track_id,
                    status="REJECTED",
                    reason=ValidationReason.REJECTED_LOW_CONFIDENCE,
                    details=f"Confidence {confidence:.2f} < threshold {class_cfg.min_confidence:.2f}"
                ))
                continue

            # Step C: Temporal Confirmation Buffer Check (with Majority Voting & Disambiguation)
            confirmed, frames_count, dur_sec, reason = self.temporal_buffer.update_and_evaluate(
                track_id=track_id,
                object_type=type_str,
                confidence=confidence,
                current_ts=current_ts,
                bbox=bbox,
                camera_id=cam_id,
            )

            resolved_type_str = self.temporal_buffer.get_resolved_type(track_key, type_str)
            resolved_conf = self.temporal_buffer.get_resolved_confidence(track_key, confidence)

            # Check final confirmed class threshold
            resolved_cfg = self.config.class_configs.get(resolved_type_str, self.config.default_config)
            is_resolved_confusable = (resolved_type_str in confusable_types and resolved_conf >= candidate_min_conf)
            is_resolved_cam2_phone = (cam_id == "camera_2" and resolved_type_str == "CELL_PHONE" and resolved_conf >= 0.22)
            if resolved_conf < resolved_cfg.min_confidence and not (is_resolved_confusable or is_resolved_cam2_phone):
                confirmed = False

            if confirmed:
                stats.accepted_count += 1
                # Apply smoothed/disambiguated object class or normalize material / earphone types
                from ai_engine.core.enums import DetectedObjectType
                wearable_types = ("EARBUDS", "EARPHONES", "HEADPHONES", "HEADSET", "NECKBAND", "WIRED_HANDSFREE", "COMM_EARPHONES")
                material_types = (
                    "BOOK", "NOTEBOOK", "REGISTER", "PAPER", "PAGE", "TEXTBOOK",
                    "DIARY", "JOURNAL", "EXERCISE_BOOK", "WRITING_PAD", "EXAM_NOTEBOOK",
                    "PRINTED_BOOK", "PRINTED_PAGE"
                )
                if resolved_type_str in wearable_types or type_str in wearable_types:
                    resolved_type_str = "COMM_EARPHONES"
                    setattr(item, "object_type", DetectedObjectType.COMM_EARPHONES)
                elif resolved_type_str == "UNAUTHORIZED_MATERIAL" or type_str == "UNAUTHORIZED_MATERIAL":
                    resolved_type_str = "UNAUTHORIZED_MATERIAL"
                    setattr(item, "object_type", DetectedObjectType.UNAUTHORIZED_MATERIAL)
                elif resolved_type_str in material_types or type_str in material_types:
                    # Normalize physical reading/writing material to canonical material family
                    if resolved_type_str == "REGISTER" or type_str == "REGISTER":
                        resolved_type_str = "REGISTER"
                        setattr(item, "object_type", DetectedObjectType.REGISTER)
                    elif resolved_type_str == "NOTEBOOK" or type_str in ("NOTEBOOK", "EXERCISE_BOOK", "EXAM_NOTEBOOK", "WRITING_PAD"):
                        resolved_type_str = "NOTEBOOK"
                        setattr(item, "object_type", DetectedObjectType.NOTEBOOK)
                    elif resolved_type_str in ("PAPER", "PAGE", "PRINTED_PAGE") or type_str in ("PAPER", "PAGE", "PRINTED_PAGE"):
                        resolved_type_str = "PAPER"
                        setattr(item, "object_type", DetectedObjectType.PAPER)
                    else:
                        resolved_type_str = "BOOK"
                        setattr(item, "object_type", DetectedObjectType.BOOK)
                elif resolved_type_str != type_str:
                    if hasattr(DetectedObjectType, resolved_type_str):
                        setattr(item, "object_type", getattr(DetectedObjectType, resolved_type_str))
                setattr(item, "confidence", resolved_conf)

                validated_items.append(item)
                audit_records.append(ValidationAuditRecord(
                    frame_id=frame_id,
                    object_type=resolved_type_str,
                    confidence=resolved_conf,
                    tracking_id=track_id,
                    status="ACCEPTED",
                    reason=ValidationReason.ACCEPTED_CONFIRMED,
                    consecutive_frames=frames_count,
                    tracking_seconds=round(dur_sec, 2),
                    details=f"Confirmed after {frames_count} frames ({dur_sec:.1f}s) as {resolved_type_str}"
                ))
            else:
                stats.rejected_unconfirmed_transient += 1
                audit_records.append(ValidationAuditRecord(
                    frame_id=frame_id,
                    object_type=type_str,
                    confidence=confidence,
                    tracking_id=track_id,
                    status="PENDING_CONFIRMATION",
                    reason=ValidationReason.REJECTED_TEMPORAL_UNCONFIRMED,
                    consecutive_frames=frames_count,
                    tracking_seconds=round(dur_sec, 2),
                    details=f"Pending confirmation: {frames_count}/{resolved_cfg.min_consecutive_frames} frames"
                ))

        # 3. Age un-seen tracks for current camera only
        self.temporal_buffer.age_missing_tracks(active_keys_seen, current_camera_id=cam_id)
        stats.active_tracks_count = self.temporal_buffer.active_track_count

        # 4. Measure Latency
        self.last_proc_time_ms = (time.perf_counter() - t0) * 1000.0
        stats.processing_time_ms = round(self.last_proc_time_ms, 2)

        # 5. Update Context
        # Attach validated_objects and update tracked_objects to emit clean items
        setattr(o_info, "validated_objects", validated_items)
        if hasattr(o_info, "tracked_objects"):
            o_info.tracked_objects = validated_items
        context.object_info = o_info

        validation_payload = {
            "statistics": {
                "total_received": stats.total_received,
                "accepted_count": stats.accepted_count,
                "rejected_unsupported_class": stats.rejected_unsupported_class,
                "rejected_low_confidence": stats.rejected_low_confidence,
                "rejected_unconfirmed_transient": stats.rejected_unconfirmed_transient,
                "active_tracks_count": stats.active_tracks_count,
                "processing_time_ms": stats.processing_time_ms,
            },
            "audit_records": [
                {
                    "frame_id": r.frame_id,
                    "object_type": r.object_type,
                    "confidence": r.confidence,
                    "tracking_id": r.tracking_id,
                    "status": r.status,
                    "reason": r.reason.value,
                    "consecutive_frames": r.consecutive_frames,
                    "tracking_seconds": r.tracking_seconds,
                    "details": r.details,
                }
                for r in audit_records
            ]
        }

        setattr(context, "object_validation", validation_payload)
        context.object_info = o_info
