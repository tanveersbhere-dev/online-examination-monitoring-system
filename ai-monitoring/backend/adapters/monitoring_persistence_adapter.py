"""
Monitoring Persistence Adapter
==============================
Downstream adapter connecting authoritative AI monitoring pipeline events
to SQLite database persistence.

Guarantees:
- Never interferes with AI detection or pipeline execution.
- Idempotent violation recording (one violation per episode).
- Preserves 1:1 mapping between ViolationTimelineManager episodes and database rows.
"""
import time
import logging
from typing import Any, Dict, List, Optional

from backend.database.session_repository import session_repository

logger = logging.getLogger("playground.persistence_adapter")


class MonitoringPersistenceAdapter:
    """Downstream persistence bridge for the AI Monitoring Pipeline."""

    def __init__(self, active_session_id: Optional[str] = None):
        self._active_session_id: Optional[str] = active_session_id
        self._recorded_evidence_ids = set()

    @property
    def active_session_id(self) -> Optional[str]:
        return self._active_session_id

    @active_session_id.setter
    def active_session_id(self, session_id: Optional[str]):
        self._active_session_id = session_id
        self._recorded_evidence_ids.clear()
        logger.info(f"[PersistenceAdapter] Active session set to: {session_id}")

    def handle_frame_lifecycle(self, context: Any, session_id: Optional[str] = None) -> None:
        """Consume lifecycle events from the context and persist to database."""
        sid = session_id or self._active_session_id
        if not sid:
            return

        try:
            # 0. Feed camera frame to rolling replay buffer
            from backend.evidence.replay_service import replay_capture_manager
            frame_obj = getattr(context, "current_frame", None)
            raw_img = getattr(frame_obj, "original_frame", None) if frame_obj else None
            frame_ts = float(getattr(frame_obj, "timestamp", time.time())) if frame_obj else time.time()
            frame_cam = str(getattr(frame_obj, "camera_id", "camera_1") or "camera_1")
            if raw_img is not None:
                replay_capture_manager.push_camera_frame(frame_ts, raw_img, camera_id=frame_cam)

            # 1. Process Lifecycle Events (STARTED, UPDATED, RESOLVED)
            events = getattr(context, "lifecycle_events", None) or []
            for ev in events:
                v_id = session_repository.upsert_violation(sid, ev)
                evt_type = getattr(ev, "event_type", getattr(ev, "transition", "UPDATED"))
                # Trigger 3-second replay capture upon violation STARTED
                if evt_type == "STARTED" and v_id:
                    v_cam = str(getattr(ev, "camera_id", frame_cam) or "camera_1")
                    v_start_ts = float(getattr(ev, "start_timestamp", getattr(ev, "started_at", frame_ts)))
                    replay_capture_manager.trigger_replay_capture(
                        session_id=sid,
                        violation_id=v_id,
                        trigger_ts=v_start_ts,
                        pre_sec=1.5,
                        post_sec=1.5,
                        camera_id=v_cam,
                    )

            # 2. Process Evidence Store Snapshots
            ev_list = getattr(context, "evidence_store", None) or []
            for rec in ev_list:
                if not isinstance(rec, dict):
                    continue
                v_id = rec.get("violation_id") or rec.get("episode_id")
                if not v_id:
                    continue

                snapshots = rec.get("snapshots")
                if isinstance(snapshots, list) and snapshots:
                    for snap in snapshots:
                        s_fname = snap.get("filename")
                        s_fpath = snap.get("filepath")
                        if not s_fname or not s_fpath:
                            continue
                        ev_key = f"{sid}_{v_id}_{s_fname}"
                        if ev_key not in self._recorded_evidence_ids:
                            snap_cam = snap.get("camera_id", rec.get("camera_id", "camera_1"))
                            meta = dict(rec)
                            meta["camera_id"] = snap_cam
                            meta["snapshot"] = snap
                            session_repository.record_evidence(
                                session_id=sid,
                                violation_id=v_id,
                                filename=s_fname,
                                filepath=s_fpath,
                                timestamp=float(snap.get("timestamp", rec.get("timestamp", time.time()))),
                                confidence=float(snap.get("confidence", rec.get("confidence", 0.0))),
                                duration=float(snap.get("duration", rec.get("total_duration", 0.0))),
                                metadata=meta,
                            )
                            self._recorded_evidence_ids.add(ev_key)
                else:
                    fname = rec.get("filename")
                    fpath = rec.get("filepath")
                    if not fname or not fpath:
                        continue
                    ev_key = f"{sid}_{v_id}_{fname}"
                    if ev_key not in self._recorded_evidence_ids:
                        session_repository.record_evidence(
                            session_id=sid,
                            violation_id=v_id,
                            filename=fname,
                            filepath=fpath,
                            timestamp=float(rec.get("timestamp", time.time())),
                            confidence=float(rec.get("confidence", rec.get("peak_confidence", 0.0))),
                            duration=float(rec.get("total_duration", 0.0)),
                            metadata=rec,
                        )
                        self._recorded_evidence_ids.add(ev_key)

        except Exception as e:
            logger.error(f"[PersistenceAdapter] Error handling frame lifecycle: {e}", exc_info=True)


# Singleton adapter
monitoring_persistence_adapter = MonitoringPersistenceAdapter()
