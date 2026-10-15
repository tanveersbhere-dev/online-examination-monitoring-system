"""
Violation Manager Processor
============================
Single source of truth for violation lifecycle.

Responsibilities:
  - Advance the ViolationTimeline state machine each frame.
  - Emit LifecycleEvent objects (STARTED / UPDATED / RESOLVED) on transitions.
  - Capture one screenshot per STARTED event (no repeated captures while ACTIVE).
  - Attach `context.lifecycle_events` so the serializer can forward transitions
    to the WebSocket and frontend.

Nothing outside this module may maintain parallel violation state.
"""
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_engine.core.exam_context import ExamContext
from ai_engine.intelligence.violation_manager.processor import ViolationManagerProcessorInterface
from ai_engine.intelligence.violation_manager.models import (
    ViolationManagerConfig,
    LifecycleEvent,
)
from ai_engine.intelligence.violation_manager.result import ViolationManagerResult
from ai_engine.intelligence.violation_manager.violation_timeline import ViolationTimelineManager
from ai_engine.intelligence.violation_manager.exceptions import ViolationManagerError

logger = logging.getLogger(__name__)


class ViolationManagerProcessor(ViolationManagerProcessorInterface):
    """
    Manages lifecycle of examination violations across time based on
    Rule Engine and Risk Engine outputs.

    This is the ONLY component permitted to own violation state or capture
    violation evidence.
    """

    def __init__(self, config: ViolationManagerConfig) -> None:
        super().__init__(config)
        self._timeline_manager = ViolationTimelineManager(config)
        self._initialized = False
        # Evidence store — populated only on STARTED events.
        self._evidence_store: List[Dict[str, Any]] = []
        self._evidence_dir: Optional[Path] = config.evidence_dir or Path("./evidence/playground")
        if self._evidence_dir is not None:
            self._evidence_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Evidence access — Orchestrator delegates its evidence_store here
    # ------------------------------------------------------------------

    @property
    def evidence_store(self) -> List[Dict[str, Any]]:
        """Evidence records captured during this session (one per RESOLVED episode)."""
        return [r for r in self._evidence_store if r.get("status") == "RESOLVED"]

    @property
    def all_evidence_records(self) -> List[Dict[str, Any]]:
        """All evidence records including active in-flight episodes."""
        return self._evidence_store

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        if self._config.enable_logging:
            logger.debug("Initializing ViolationManagerProcessor...")
        self._timeline_manager = ViolationTimelineManager(self._config)
        self._initialized = True
        if self._config.enable_logging:
            logger.debug("ViolationManagerProcessor initialized.")

    def start(self) -> None:
        if not self._initialized:
            raise ViolationManagerError("Cannot start uninitialized ViolationManagerProcessor.")
        if self._config.enable_logging:
            logger.debug("ViolationManagerProcessor started.")

    def stop(self) -> None:
        if self._config.enable_logging:
            logger.debug("ViolationManagerProcessor stopped.")
        self._timeline_manager.close_all(time.time())

    def cleanup(self) -> None:
        if self._config.enable_logging:
            logger.debug("Cleaning up ViolationManagerProcessor...")
        self._timeline_manager.close_all(time.time())
        self._initialized = False

    # ------------------------------------------------------------------
    # Per-frame processing
    # ------------------------------------------------------------------

    def process(self, context: ExamContext) -> None:
        current_time = getattr(context.current_frame, "timestamp", None) if getattr(context, "current_frame", None) else None
        if hasattr(context, "rule_results") and context.rule_results and hasattr(context.rule_results, "evaluations"):
            eval_times = [
                getattr(e, "evaluation_timestamp", getattr(e, "timestamp", 0.0))
                for e in context.rule_results.evaluations
                if getattr(e, "evaluation_timestamp", getattr(e, "timestamp", 0.0)) > 0
            ]
            if eval_times:
                max_eval_time = max(eval_times)
                if current_time is None or max_eval_time > current_time:
                    current_time = max_eval_time

        if current_time is None or current_time <= 0:
            current_time = time.time()

        # ── 1. Pull triggered rules from Rule Engine output ────────────
        triggered_rules = []
        if hasattr(context, "rule_results") and context.rule_results is not None:
            for ev in context.rule_results.evaluations:
                if ev.triggered:
                    triggered_rules.append({
                        "rule_id": ev.rule_id,
                        "category": ev.category,
                        "confidence": getattr(ev, "confidence", 1.0)
                    })

        # ── 2. Pull risk score from Risk Engine output ─────────────────
        risk_score = 0.0
        risk_level = "NORMAL"
        if hasattr(context, "risk_assessment") and context.risk_assessment is not None:
            risk_score = context.risk_assessment.overall_score
            risk_level = context.risk_assessment.risk_level

        # ── 3. Pull any external evidence references ────────────────────
        evidence_refs: List[str] = []
        if hasattr(context, "object_info") and context.object_info is not None:
            evidence = getattr(context.object_info, "evidence", None)
            if evidence:
                for ev in evidence:
                    if hasattr(ev, "snapshot_id"):
                        evidence_refs.append(ev.snapshot_id)

        # ── 4. Advance the state machine ───────────────────────────────
        # Returns only the transitions that fired this frame.
        # This is an empty list on the vast majority of frames.
        cam_id = str(getattr(getattr(context, "current_frame", None), "camera_id", "camera_1") or "camera_1")
        lifecycle_events: List[LifecycleEvent] = self._timeline_manager.process_triggers(
            triggered_rules=triggered_rules,
            risk_score=risk_score,
            risk_level=risk_level,
            evidence_refs=evidence_refs,
            current_time=current_time,
            camera_id=cam_id,
        )

        # TEMPORARY DEBUG TRACE - STAGE 8
        logger.info(f"[STAGE 8 - VIOLATION MANAGER] triggered_rules_count={len(triggered_rules)} triggered_ids={[r.get('rule_id') for r in triggered_rules]} created_events_count={len(lifecycle_events)}")
        for evt in lifecycle_events:
            logger.info(f"  [VM EVENT] type={evt.event_type} v_id={evt.violation_id} v_type={evt.violation_type} severity={evt.severity}")

        # ── 5. Evidence capture & In-Place Mutation ───────────────────
        # Capture exactly once upon confirmation (STARTED), update in place on ACTIVE,
        # rate-limit periodic snapshots, and finalize on RESOLVED.
        self._handle_evidence_and_updates(context, lifecycle_events, current_time, risk_score)

        # ── 6. Attach lifecycle events to context (empty list most frames)
        # The serializer reads this and includes it in the WebSocket payload.
        setattr(context, "lifecycle_events", lifecycle_events)

        # ── 7. Attach violation timeline result ────────────────────────
        result = ViolationManagerResult(
            timeline=self._timeline_manager.timeline,
            statistics=self._timeline_manager.statistics,
        )
        setattr(context, "violations", result)

    # ------------------------------------------------------------------
    # Private — evidence capture and in-place updates
    # ------------------------------------------------------------------

    def _handle_evidence_and_updates(
        self,
        context: ExamContext,
        lifecycle_events: List[LifecycleEvent],
        current_time: float,
        current_risk_score: float,
    ) -> None:
        """
        Manages evidence lifecycle adhering to professional proctoring standards:
          1. Exact single snapshot captured upon CONFIRMED/STARTED transition.
          2. In-place live metadata mutation (duration, peak/avg confidence, risk) while ACTIVE without new snapshots.
          3. Rate-limited periodic corroborating re-snapshots (e.g., every 30s) for long-duration violations.
          4. Final in-place metadata finalization on RESOLVED.
          5. Capacity ceiling enforcement (FIFO/severity pruning).
        """
        if self._evidence_dir is None:
            return

        try:
            import cv2

            current_frame = context.current_frame
            frame_id = getattr(current_frame, "frame_id", 0) if current_frame else 0
            cam_id = str(getattr(current_frame, "camera_id", "camera_1") or "camera_1")

            # 1. Extract frame annotations data
            contributing_violations = []
            if hasattr(context, "rule_results") and context.rule_results is not None:
                for ev in context.rule_results.evaluations:
                    if getattr(ev, "triggered", False):
                        contributing_violations.append({
                            "rule_id": ev.rule_id,
                            "rule_name": getattr(ev, "rule_name", ev.rule_id),
                            "category": getattr(ev, "category", "Violation"),
                            "confidence": round(getattr(ev, "confidence", 1.0), 4),
                        })

            detected_objects = []
            if hasattr(context, "object_info") and context.object_info is not None:
                oi = context.object_info
                tracked = (
                    getattr(oi, "validated_objects", None) or
                    getattr(oi, "tracked_objects", None) or
                    getattr(oi, "filtered_detections", None) or
                    []
                )
                for obj in tracked:
                    otype = getattr(obj.object_type, "name", str(obj.object_type))
                    conf = getattr(obj, "confidence", 0.0)
                    bbox = getattr(obj, "bbox", None)
                    bbox_list = [int(bbox.x), int(bbox.y), int(bbox.width), int(bbox.height)] if bbox and hasattr(bbox, "x") else [0, 0, 0, 0]
                    t_id = getattr(obj, "tracking_id", -1)
                    detected_objects.append({
                        "type": otype,
                        "confidence": round(conf, 4),
                        "bbox": bbox_list,
                        "tracking_id": t_id
                    })

            # Also include confirmed audio device in detected_objects for evidence snapshot annotation
            audio_info = getattr(context, "audio_device_info", None)
            if audio_info and getattr(audio_info, "detected", False) and getattr(audio_info, "bbox", None):
                abbox = audio_info.bbox
                detected_objects.append({
                    "type": "COMM_EARPHONES",
                    "confidence": round(float(getattr(audio_info, "confidence", 0.9)), 4),
                    "bbox": [int(abbox[0]), int(abbox[1]), int(abbox[2]), int(abbox[3])] if isinstance(abbox, (list, tuple)) and len(abbox) >= 4 else [0, 0, 0, 0],
                    "tracking_id": 999,
                })

            detected_faces = []
            identity_verification_result = {"consistent": True, "confidence": 1.0, "similarity_score": 1.0}
            if hasattr(context, "face_info") and context.face_info is not None:
                fi = context.face_info
                if getattr(fi, "face_detected", False):
                    fb = getattr(fi, "bbox", None)
                    if fb and hasattr(fb, "x"):
                        bbox_list = [int(fb.x), int(fb.y), int(fb.width), int(fb.height)]
                    elif fb and hasattr(fb, "__len__") and len(fb) >= 4:
                        bbox_list = [int(v) for v in fb[:4]]
                    else:
                        bbox_list = [0, 0, 0, 0]
                    detected_faces.append({
                        "detected": True,
                        "confidence": round(getattr(fi, "confidence", 0.0), 4),
                        "count": getattr(fi, "face_count", 1),
                        "bbox": bbox_list
                    })
                identity_verification_result = {
                    "consistent": getattr(fi, "identity_consistent", True),
                    "confidence": round(getattr(fi, "identity_confidence", 0.0), 4),
                    "similarity_score": round(getattr(fi, "similarity_score", 0.0), 4),
                    "presence_state": getattr(fi, "presence_state", "PRESENT"),
                }

            behavior_labels = []
            if hasattr(context, "behavior_result") and isinstance(context.behavior_result, dict):
                summary = context.behavior_result.get("summary", {})
                if isinstance(summary, dict):
                    behavior_labels = summary.get("composite_behaviors_detected", [])

            # Helper to find matching violation object from timeline
            def _find_v(v_id):
                for v in self._timeline_manager.timeline.violations:
                    if v.violation_id == v_id:
                        return v
                return None

            # Helper to build annotated image strictly matching the violation's reporting camera
            def _save_annotated_snapshot(v_obj, evt_type, total_dur, peak_c, avg_c, interruptions, target_camera_id=None):
                req_cam = str(target_camera_id or getattr(v_obj, "camera_id", None) or getattr(current_frame, "camera_id", "camera_1") or "camera_1")

                annotated_img = None
                # Prefer current_frame if it matches the target camera
                if current_frame is not None and getattr(current_frame, "camera_id", None) == req_cam and getattr(current_frame, "original_frame", None) is not None:
                    annotated_img = current_frame.original_frame.copy()
                else:
                    # Retrieve the authoritative latest frame for this camera from MultiCameraManager
                    try:
                        from backend.camera.multi_camera_manager import multi_camera_manager
                        c_info = multi_camera_manager.get_camera_info(req_cam)
                        if c_info and c_info.latest_jpeg_bytes:
                            import numpy as np
                            decoded = cv2.imdecode(np.frombuffer(c_info.latest_jpeg_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
                            if decoded is not None:
                                annotated_img = decoded.copy()
                    except Exception as e_fetch:
                        logger.debug(f"[ViolationManager] Fallback camera fetch error for {req_cam}: {e_fetch}")

                # If still None, fallback to current_frame
                if annotated_img is None:
                    if current_frame is not None and getattr(current_frame, "original_frame", None) is not None:
                        annotated_img = current_frame.original_frame.copy()
                    else:
                        return f"evidence_{v_obj.violation_type}_{v_obj.violation_id}.jpg", ""

                fname = f"evidence_{v_obj.violation_type}_{v_obj.violation_id}_{int(current_time * 1000) % 100000}.jpg"
                fpath = self._evidence_dir / fname

                try:
                    for obj in detected_objects:
                        bx = obj["bbox"]
                        if len(bx) == 4 and bx[2] > 0 and bx[3] > 0:
                            x, y, w, h = bx
                            cv2.rectangle(annotated_img, (x, y), (x + w, y + h), (0, 0, 255), 3)
                            raw_type = str(obj.get("type", ""))
                            display_type = "UNAUTHORIZED AUDIO DEVICE" if raw_type in ("COMM_EARPHONES", "EARBUDS", "HEADPHONES", "NECKBAND", "EARPHONE") else raw_type
                            lbl = f"{display_type} ({obj['confidence']:.2f})"
                            cv2.putText(annotated_img, lbl, (x, max(15, y - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                    # Only draw faces if the snapshot is for camera_1
                    if req_cam == "camera_1":
                        for f in detected_faces:
                            bx = f["bbox"]
                            if len(bx) == 4 and bx[2] > 0 and bx[3] > 0:
                                x, y, w, h = bx
                                color = (0, 255, 0) if identity_verification_result.get("consistent") else (0, 0, 255)
                                cv2.rectangle(annotated_img, (x, y), (x + w, y + h), color, 2)

                    from ai_engine.intelligence.behavior_engine.composite_behavior import format_composite_incident_title
                    c_rules = [v["rule_id"] for v in contributing_violations] if contributing_violations else [v_obj.violation_type]
                    descriptive_title = format_composite_incident_title(v_obj.violation_type, c_rules, detected_objects)
                    banner_text = f"[{req_cam.upper()}] {descriptive_title} | {evt_type} | DUR: {total_dur:.1f}s | PEAK: {peak_c:.2f} | AVG: {avg_c:.2f}"
                    cv2.rectangle(annotated_img, (0, 0), (annotated_img.shape[1], 30), (0, 0, 0), -1)
                    cv2.putText(annotated_img, banner_text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

                    cv2.imwrite(str(fpath), annotated_img)
                except Exception as e_ann:
                    logger.debug(f"Annotation save error: {e_ann}")
                return fname, str(fpath)

            # ── A. Handle STARTED Lifecycle Events (Initial Evidence Capture) ──
            for evt in lifecycle_events:
                if evt.event_type == "STARTED":
                    v_obj = _find_v(evt.violation_id)
                    if not v_obj:
                        continue

                    # Defensive idempotency: a retried STARTED transition must not
                    # create another record or another primary snapshot for this episode.
                    if any(r.get("violation_id") == evt.violation_id for r in self._evidence_store):
                        continue

                    # Rate-limiting check per violation type per minute
                    recent_captures_same_type = sum(
                        1 for r in self._evidence_store
                        if r.get("rule_id") == evt.violation_type and (current_time - r.get("timestamp", 0)) < 60.0
                    )
                    max_per_min = getattr(self._config, "max_captures_per_type_per_minute", 2)
                    if recent_captures_same_type >= max_per_min:
                        if self._config.enable_logging:
                            logger.warning(f"Rate limit hit for {evt.violation_type} ({recent_captures_same_type} in last 60s). Skipping additional file creation.")
                        continue

                    total_dur = 0.1
                    peak_c = round(v_obj.peak_confidence, 4)
                    avg_c = peak_c
                    interruptions = v_obj.interruption_count

                    cam_id = str(getattr(evt, "camera_id", getattr(v_obj, "camera_id", getattr(current_frame, "camera_id", "camera_1"))) or "camera_1")
                    fname, fpath = _save_annotated_snapshot(v_obj, "CONFIRMED", total_dur, peak_c, avg_c, interruptions, target_camera_id=cam_id)

                    from ai_engine.intelligence.behavior_engine.composite_behavior import format_composite_incident_title
                    evt_rules = getattr(evt, "triggered_rules", None) or [evt.violation_type]
                    descriptive_title = format_composite_incident_title(evt.violation_type, evt_rules, detected_objects)

                    confidence_scores = {
                        "risk_score": round(evt.risk_score, 4),
                        "identity_confidence": identity_verification_result.get("confidence", 1.0),
                        "objects": {obj["type"]: obj["confidence"] for obj in detected_objects}
                    }

                    record: Dict[str, Any] = {
                        "id": f"EV-{evt.violation_id}",
                        "violation_id": evt.violation_id,
                        "episode_id": evt.violation_id,
                        "camera_id": cam_id,
                        "filename": fname,
                        "filepath": fpath,
                        "latest_filename": fname,
                        "rule_id": evt.violation_type,
                        "incident_title": descriptive_title,
                        "behavior_type": descriptive_title,
                        "category": evt.violation_category,
                        "confidence": peak_c,
                        "current_confidence": round(v_obj.current_confidence, 4),
                        "peak_confidence": peak_c,
                        "avg_confidence": avg_c,
                        "detection_count": v_obj.detection_count,
                        "start_time": v_obj.start_timestamp,
                        "end_time": None,
                        "total_duration": total_dur,
                        "interruption_count": interruptions,
                        "frame_id": frame_id,
                        "timestamp": current_time,
                        "status": "ACTIVE",
                        "snapshots": [
                            {
                                "id": f"SNAP-{evt.violation_id}-1",
                                "camera_id": cam_id,
                                "filename": fname,
                                "filepath": fpath,
                                "snapshot_type": "INITIAL_CONFIRMATION",
                                "timestamp": current_time,
                                "duration": total_dur,
                                "confidence": peak_c,
                                "interruption_count": interruptions,
                            }
                        ],
                        "total_snapshots": 1,
                        "contributing_violations": [cv for cv in contributing_violations if cv["rule_id"] in evt_rules] or [{
                            "rule_id": evt.violation_type,
                            "rule_name": getattr(evt, "violation_name", evt.violation_type),
                            "category": evt.violation_category,
                            "confidence": peak_c
                        }],
                        "detected_objects": detected_objects,
                        "detected_faces": detected_faces,
                        "identity_verification_result": identity_verification_result,
                        "behavior_labels": behavior_labels,
                        "confidence_scores": confidence_scores,
                    }
                    self._evidence_store.append(record)
                    self._timeline_manager.statistics.total_evidence_captured += 1
                    v_obj.evidence_captured = True
                    v_obj.last_evidence_timestamp = current_time
                    v_obj.evidence_capture_count = 1

                    if self._config.enable_logging:
                        logger.info(f"[ViolationManager] Single Evidence Opened on CONFIRMED: {fname} (id={v_obj.violation_id})")

            # ── B. In-Place Live Mutation for Ongoing ACTIVE Violations ────────
            # No new snapshot files! Updates duration, peak conf, avg conf, and risk live.
            resnapshot_interval = getattr(self._config, "periodic_resnapshot_interval_seconds", 30.0)

            for v in self._timeline_manager.timeline.violations:
                if v.status in ("OPEN", "ACTIVE", "RECOVERING"):
                    total_dur = max(0.1, round(current_time - v.start_timestamp, 1))
                    avg_c = round(v.confidence_sum / max(1, v.confidence_samples), 4)

                    # Update in-place in evidence_store
                    rec = None
                    for r in self._evidence_store:
                        if r.get("violation_id") == v.violation_id:
                            r["total_duration"] = total_dur
                            r["peak_confidence"] = round(v.peak_confidence, 4)
                            r["current_confidence"] = round(v.current_confidence, 4)
                            r["confidence"] = round(v.peak_confidence, 4)
                            r["avg_confidence"] = avg_c
                            r["detection_count"] = v.detection_count
                            r["last_seen_at"] = v.last_updated_timestamp
                            r["interruption_count"] = v.interruption_count
                            r["confidence_scores"]["risk_score"] = round(current_risk_score, 4)
                            r["status"] = "ACTIVE"
                            rec = r
                            break

                    if rec is None:
                        continue

                    # Multi-angle / Cross-Camera Evidence Capture:
                    # If this ongoing violation is observed in the current frame by a different camera
                    # than the camera(s) that already contributed snapshots, capture an auxiliary snapshot.
                    # This preserves both camera angles under the single correlated episode without duplicate penalties.
                    snapshots = rec.setdefault("snapshots", [])
                    existing_cams = {s.get("camera_id") for s in snapshots if s.get("camera_id")}
                    triggered_rids = {cv["rule_id"] for cv in contributing_violations}
                    if cam_id not in existing_cams and (v.violation_type in triggered_rids):
                        fname_aux, fpath_aux = _save_annotated_snapshot(
                            v, f"CROSS_CAM_{cam_id.upper()}", total_dur, v.peak_confidence, avg_c, v.interruption_count, target_camera_id=cam_id
                        )
                        aux_snapshot = {
                            "id": f"SNAP-{v.violation_id}-{len(snapshots) + 1}",
                            "camera_id": cam_id,
                            "filename": fname_aux,
                            "filepath": fpath_aux,
                            "snapshot_type": f"CROSS_CAM_{cam_id.upper()}",
                            "timestamp": current_time,
                            "duration": total_dur,
                            "confidence": round(v.current_confidence or v.peak_confidence, 4),
                            "interruption_count": v.interruption_count,
                        }
                        snapshots.append(aux_snapshot)
                        rec["total_snapshots"] = len(snapshots)
                        v.evidence_capture_count = len(snapshots)
                        if self._config.enable_logging:
                            logger.info(
                                f"[VIOLATION] Multi-camera cross snapshot captured: {fname_aux} for cam={cam_id} (id={v.violation_id})"
                            )

                    # Consider sparse periodic frames as candidates, but retain only the
                    # primary snapshot plus the two strongest additional candidates. The
                    # gallery primary stays stable; better candidates replace only the
                    # weakest non-primary evidence.
                    if resnapshot_interval > 0.0 and v.evidence_captured:
                        if (current_time - v.last_evidence_timestamp) >= resnapshot_interval:
                            v.last_evidence_timestamp = current_time
                            max_snapshots = max(1, int(getattr(self._config, "max_snapshots_per_violation", 3)))
                            candidate_confidence = round(v.current_confidence or v.peak_confidence, 4)
                            replacement_index = None

                            if len(snapshots) < max_snapshots:
                                replacement_index = len(snapshots)
                            elif len(snapshots) > 1:
                                weakest_index = min(
                                    range(1, len(snapshots)),
                                    key=lambda idx: float(snapshots[idx].get("confidence", 0.0)),
                                )
                                if candidate_confidence > float(snapshots[weakest_index].get("confidence", 0.0)):
                                    replacement_index = weakest_index

                            if replacement_index is None:
                                if self._config.enable_logging:
                                    logger.debug("[VIOLATION] SNAPSHOT_SKIPPED id=%s reason=lower_confidence", v.violation_id)
                                continue

                            fname_kf, fpath_kf = _save_annotated_snapshot(
                                v, "PERIODIC_KEYFRAME", total_dur, v.peak_confidence, avg_c, v.interruption_count, target_camera_id=cam_id
                            )
                            snapshot = {
                                "id": f"SNAP-{v.violation_id}-{replacement_index + 1}",
                                "camera_id": cam_id,
                                "filename": fname_kf,
                                "filepath": fpath_kf,
                                "snapshot_type": "PERIODIC_KEYFRAME",
                                "timestamp": current_time,
                                "duration": total_dur,
                                "confidence": candidate_confidence,
                                "interruption_count": v.interruption_count,
                            }
                            if replacement_index < len(snapshots):
                                snapshots[replacement_index] = snapshot
                            else:
                                snapshots.append(snapshot)
                            rec["total_snapshots"] = len(snapshots)
                            v.evidence_capture_count = len(snapshots)
                            if self._config.enable_logging:
                                logger.info("[VIOLATION] SNAPSHOT_RETAINED id=%s count=%s", v.violation_id, len(snapshots))

            # ── C. Handle RESOLVED Lifecycle Events (Finalize Record In-Place) ──
            for evt in lifecycle_events:
                if evt.event_type == "RESOLVED":
                    v_obj = _find_v(evt.violation_id)
                    total_dur = max(0.1, round((evt.end_timestamp or current_time) - evt.start_timestamp, 1))
                    avg_c = round(v_obj.confidence_sum / max(1, v_obj.confidence_samples), 4) if v_obj else 1.0

                    found_in_store = False
                    for rec in self._evidence_store:
                        if rec.get("violation_id") == evt.violation_id:
                            rec["end_time"] = evt.end_timestamp or current_time
                            rec["total_duration"] = total_dur
                            rec["avg_confidence"] = avg_c
                            rec["status"] = "RESOLVED"
                            found_in_store = True
                            break

                    # Fallback: if no record was opened at STARTED (e.g. synthetic test), create finalized record
                    if not found_in_store and v_obj:
                        fname, fpath = _save_annotated_snapshot(v_obj, "RESOLVED", total_dur, v_obj.peak_confidence, avg_c, v_obj.interruption_count)
                        from ai_engine.intelligence.behavior_engine.composite_behavior import format_composite_incident_title
                        c_rules = [v["rule_id"] for v in contributing_violations] if contributing_violations else [evt.violation_type]
                        descriptive_title = format_composite_incident_title(evt.violation_type, c_rules, detected_objects)

                        record = {
                            "id": f"EV-{evt.violation_id}",
                            "violation_id": evt.violation_id,
                            "episode_id": evt.violation_id,
                            "camera_id": getattr(evt, "camera_id", getattr(v_obj, "camera_id", cam_id)),
                            "filename": fname,
                            "filepath": fpath,
                            "latest_filename": fname,
                            "rule_id": evt.violation_type,
                            "incident_title": descriptive_title,
                            "behavior_type": descriptive_title,
                            "category": evt.violation_category,
                            "confidence": round(v_obj.peak_confidence, 4),
                            "peak_confidence": round(v_obj.peak_confidence, 4),
                            "avg_confidence": avg_c,
                            "start_time": evt.start_timestamp,
                            "end_time": evt.end_timestamp or current_time,
                            "total_duration": total_dur,
                            "interruption_count": v_obj.interruption_count,
                            "frame_id": frame_id,
                            "timestamp": current_time,
                            "status": "RESOLVED",
                            "snapshots": [
                                {
                                    "id": f"SNAP-{evt.violation_id}-1",
                                    "camera_id": getattr(evt, "camera_id", getattr(v_obj, "camera_id", cam_id)),
                                    "filename": fname,
                                    "filepath": fpath,
                                    "snapshot_type": "RESOLVED_FALLBACK",
                                    "timestamp": current_time,
                                    "duration": total_dur,
                                    "confidence": round(v_obj.peak_confidence, 4),
                                    "interruption_count": v_obj.interruption_count,
                                }
                            ],
                            "total_snapshots": 1,
                            "contributing_violations": contributing_violations if contributing_violations else [{
                                "rule_id": evt.violation_type,
                                "rule_name": getattr(evt, "violation_name", evt.violation_type),
                                "category": evt.violation_category,
                                "confidence": round(v_obj.peak_confidence, 4)
                            }],
                            "detected_objects": detected_objects,
                            "detected_faces": detected_faces,
                            "identity_verification_result": identity_verification_result,
                            "behavior_labels": behavior_labels,
                            "confidence_scores": {
                                "risk_score": round(evt.risk_score, 4),
                                "identity_confidence": identity_verification_result.get("confidence", 1.0),
                                "objects": {obj["type"]: obj["confidence"] for obj in detected_objects}
                            },
                        }
                        self._evidence_store.append(record)

            # ── D. Enforce Hard Capacity Ceiling with FIFO Pruning ─────────────
            max_items = getattr(self._config, "max_evidence_items", 50)
            if len(self._evidence_store) > max_items:
                # Keep active items, prune oldest resolved items
                active_recs = [r for r in self._evidence_store if r.get("status") == "ACTIVE"]
                resolved_recs = [r for r in self._evidence_store if r.get("status") != "ACTIVE"]
                allow_resolved = max(0, max_items - len(active_recs))
                resolved_recs = resolved_recs[-allow_resolved:]
                self._evidence_store = active_recs + resolved_recs

        except Exception as e:
            logger.warning(f"[ViolationManager] Evidence handling error: {e}")
