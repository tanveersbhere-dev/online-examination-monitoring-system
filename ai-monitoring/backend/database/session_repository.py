"""
Monitoring Session & Violation Repository
=========================================
Handles CRUD operations for Monitoring Sessions, Violations, Evidence, and Replays.
"""
import json
import time
import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple

from .db import get_db_connection

logger = logging.getLogger("playground.repository")


class SessionRepository:
    """Repository for persisting monitoring sessions and authoritative violations."""

    def __init__(self):
        pass

    def create_session(
        self,
        session_id: Optional[str] = None,
        student_id: str = "local_student",
        examiner_id: Optional[str] = None,
        exam_id: Optional[str] = None,
        attempt_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new active monitoring session."""
        now = time.time()
        sid = session_id or f"session_{uuid.uuid4().hex[:12]}"
        meta_json = json.dumps(metadata or {})

        conn = get_db_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO monitoring_sessions (
                        id, status, student_id, examiner_id, exam_id, attempt_id,
                        started_at, ended_at, total_duration, created_at, updated_at, metadata_json
                    ) VALUES (?, 'ACTIVE', ?, ?, ?, ?, ?, NULL, 0.0, ?, ?, ?)
                    """,
                    (sid, student_id, examiner_id, exam_id, attempt_id, now, now, now, meta_json),
                )
            logger.info(f"Created new MonitoringSession {sid}")
            return self.get_session(sid)
        finally:
            conn.close()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a session by its ID."""
        conn = get_db_connection()
        try:
            cur = conn.execute(
                "SELECT * FROM monitoring_sessions WHERE id = ?",
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            res["metadata"] = json.loads(res.get("metadata_json") or "{}")
            return res
        finally:
            conn.close()

    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List all monitoring sessions ordered by start time descending."""
        conn = get_db_connection()
        try:
            cur = conn.execute(
                "SELECT * FROM monitoring_sessions ORDER BY started_at DESC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
            result = []
            for r in rows:
                item = dict(r)
                item["metadata"] = json.loads(item.get("metadata_json") or "{}")
                result.append(item)
            return result
        finally:
            conn.close()

    def finalize_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Mark session as COMPLETED, compute duration, and resolve any open violations."""
        now = time.time()
        conn = get_db_connection()
        try:
            with conn:
                cur = conn.execute(
                    "SELECT started_at FROM monitoring_sessions WHERE id = ?",
                    (session_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                started_at = row["started_at"]
                duration = round(max(0.0, now - started_at), 2)

                # Update session status
                conn.execute(
                    """
                    UPDATE monitoring_sessions
                    SET status = 'COMPLETED', ended_at = ?, total_duration = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (now, duration, now, session_id),
                )

                # Close any pending unclosed violations
                conn.execute(
                    """
                    UPDATE violations
                    SET status = 'RESOLVED', end_time = ?, duration = (? - start_time), updated_at = ?
                    WHERE session_id = ? AND status IN ('STARTED', 'ACTIVE', 'OPEN', 'RECOVERING')
                    """,
                    (now, now, now, session_id),
                )

            logger.info(f"Finalized MonitoringSession {session_id} (duration={duration:.1f}s)")
            return self.get_session(session_id)
        finally:
            conn.close()

    def upsert_violation(
        self,
        session_id: str,
        event_obj: Any,
    ) -> Optional[str]:
        """Record or update authoritative violation based on LifecycleEvent."""
        if not event_obj:
            return None

        event_type = getattr(event_obj, "event_type", getattr(event_obj, "transition", "STARTED"))
        violation_id = getattr(event_obj, "violation_id", getattr(event_obj, "id", None))
        if not violation_id:
            return None

        v_type = getattr(event_obj, "violation_type", getattr(event_obj, "type", "VIOLATION"))
        category = getattr(event_obj, "violation_category", getattr(event_obj, "category", "BEHAVIOR"))
        TITLE_MAP = {
            "ATT_DOWNWARD_GAZE": "Downward Gaze",
            "ATT_LOOKING_AWAY": "Looking Away",
            "UNAUTH_PHONE": "Phone Violation",
            "UNAUTH_LAPTOP": "Laptop Violation",
            "COMM_EARPHONES": "Unauthorized Audio Device",
            "COMM_HEADPHONES": "Unauthorized Audio Device",
            "COMM_NECKBAND": "Unauthorized Audio Device",
            "UNAUTH_VOICE": "Unauthorized Human Voice",
            "UNAUTH_BOOK": "Unauthorized Book / Material",
            "BOOK_MATERIAL": "Unauthorized Book / Material",
            "UNAUTHORIZED_MATERIAL": "Unauthorized Book / Material",
            "COMM_MULTIPLE_PERSONS": "Multiple Persons Detected",
            "ID_FACE_MISSING": "Face Absence Detected",
        }
        raw_title = getattr(event_obj, "incident_title", getattr(event_obj, "title", None))
        title = raw_title if (raw_title and raw_title != v_type) else TITLE_MAP.get(v_type, raw_title or v_type)
        description = getattr(event_obj, "description", getattr(event_obj, "msg", "Behavior anomaly observed."))
        start_time = float(getattr(event_obj, "start_timestamp", getattr(event_obj, "started_at", getattr(event_obj, "timestamp", time.time()))))
        current_time = float(getattr(event_obj, "timestamp", time.time()))
        end_time = getattr(event_obj, "end_timestamp", getattr(event_obj, "ended_at", None))
        peak_conf = float(getattr(event_obj, "peak_confidence", getattr(event_obj, "confidence", 0.0)))
        current_conf = float(getattr(event_obj, "current_confidence", getattr(event_obj, "confidence", peak_conf)))
        det_count = int(getattr(event_obj, "detection_count", 1))
        risk_score = float(getattr(event_obj, "risk_score", 50.0))
        duration = float(getattr(event_obj, "duration", round(max(0.0, current_time - start_time), 2)))
        rules_json = json.dumps(getattr(event_obj, "triggered_rules", [v_type]))

        conn = get_db_connection()
        try:
            with conn:
                # Check if violation already exists for this session and violation_id
                cur = conn.execute(
                    "SELECT id, peak_confidence, start_time FROM violations WHERE session_id = ? AND id = ?",
                    (session_id, violation_id),
                )
                existing = cur.fetchone()

                now = time.time()
                if not existing:
                    # Insert new violation
                    conn.execute(
                        """
                        INSERT INTO violations (
                            id, session_id, episode_id, violation_type, category, title, description,
                            status, start_time, end_time, duration, peak_confidence, avg_confidence,
                            detection_count, risk_score, triggered_rules_json, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            violation_id,
                            session_id,
                            violation_id,
                            v_type,
                            category,
                            title,
                            description,
                            event_type,
                            start_time,
                            end_time,
                            duration,
                            peak_conf,
                            current_conf,
                            det_count,
                            risk_score,
                            rules_json,
                            now,
                            now,
                        ),
                    )
                else:
                    # Update existing record
                    new_peak = max(existing["peak_confidence"], peak_conf)
                    conn.execute(
                        """
                        UPDATE violations
                        SET status = ?, duration = ?, peak_confidence = ?, detection_count = ?,
                            risk_score = ?, end_time = ?, updated_at = ?
                        WHERE session_id = ? AND id = ?
                        """,
                        (
                            event_type,
                            duration,
                            new_peak,
                            det_count,
                            risk_score,
                            end_time,
                            now,
                            session_id,
                            violation_id,
                        ),
                    )
            return violation_id
        except Exception as e:
            logger.error(f"Error upserting violation {violation_id}: {e}")
            return None
        finally:
            conn.close()

    def record_evidence(
        self,
        session_id: str,
        violation_id: str,
        filename: str,
        filepath: str,
        timestamp: float,
        confidence: float = 0.0,
        duration: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Record evidence snapshot linked to a violation."""
        evidence_id = f"EV-{violation_id}-{int(timestamp * 1000) % 10000}"
        meta_json = json.dumps(metadata or {})
        now = time.time()

        conn = get_db_connection()
        try:
            with conn:
                # Check for duplicate file
                cur = conn.execute(
                    "SELECT id FROM evidence_records WHERE violation_id = ? AND filename = ?",
                    (violation_id, filename),
                )
                if cur.fetchone():
                    return None

                conn.execute(
                    """
                    INSERT INTO evidence_records (
                        id, session_id, violation_id, evidence_type, filename, filepath,
                        timestamp, confidence, duration, metadata_json, created_at
                    ) VALUES (?, ?, ?, 'SNAPSHOT', ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        evidence_id,
                        session_id,
                        violation_id,
                        filename,
                        filepath,
                        timestamp,
                        confidence,
                        duration,
                        meta_json,
                        now,
                    ),
                )
            return evidence_id
        except Exception as e:
            logger.error(f"Error recording evidence for {violation_id}: {e}")
            return None
        finally:
            conn.close()

    def record_replay(
        self,
        session_id: str,
        violation_id: str,
        clip_path: str,
        start_time: float,
        end_time: float,
        duration: float = 3.0,
        frame_count: int = 30,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Record a 3-second replay clip entry linked to a violation."""
        replay_id = f"REP-{violation_id}"
        meta_json = json.dumps(metadata or {})
        now = time.time()

        conn = get_db_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO replay_records (
                        id, session_id, violation_id, clip_path, start_time, end_time,
                        duration, frame_count, metadata_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        replay_id,
                        session_id,
                        violation_id,
                        clip_path,
                        start_time,
                        end_time,
                        duration,
                        frame_count,
                        meta_json,
                        now,
                    ),
                )
            return replay_id
        except Exception as e:
            logger.error(f"Error recording replay for {violation_id}: {e}")
            return None
        finally:
            conn.close()

    def get_session_report(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Generate comprehensive report for the exact monitoring session."""
        session = self.get_session(session_id)
        if not session:
            return None

        conn = get_db_connection()
        try:
            # 1. Fetch violations
            cur_v = conn.execute(
                "SELECT * FROM violations WHERE session_id = ? ORDER BY start_time ASC",
                (session_id,),
            )
            v_rows = cur_v.fetchall()
            violations = []
            type_counts = {}
            category_counts = {}

            for r in v_rows:
                v_dict = dict(r)
                v_dict["triggered_rules"] = json.loads(v_dict.get("triggered_rules_json") or "[]")
                v_type = v_dict["violation_type"]
                cat = v_dict["category"]
                type_counts[v_type] = type_counts.get(v_type, 0) + 1
                category_counts[cat] = category_counts.get(cat, 0) + 1

                if v_dict.get("title") in (v_type, None, ""):
                    TITLE_MAP = {
                        "ATT_DOWNWARD_GAZE": "Downward Gaze",
                        "ATT_LOOKING_AWAY": "Looking Away",
                        "UNAUTH_PHONE": "Phone Violation",
                        "UNAUTH_LAPTOP": "Laptop Violation",
                        "COMM_EARPHONES": "Unauthorized Audio Device",
                        "COMM_HEADPHONES": "Unauthorized Audio Device",
                        "COMM_NECKBAND": "Unauthorized Audio Device",
                        "UNAUTH_VOICE": "Unauthorized Human Voice",
                        "UNAUTH_BOOK": "Unauthorized Book / Material",
                        "BOOK_MATERIAL": "Unauthorized Book / Material",
                        "UNAUTHORIZED_MATERIAL": "Unauthorized Book / Material",
                        "COMM_MULTIPLE_PERSONS": "Multiple Persons Detected",
                        "ID_FACE_MISSING": "Face Absence Detected",
                    }
                    v_dict["title"] = TITLE_MAP.get(v_type, v_dict.get("title") or v_type)

                # Fetch evidence for this violation
                cur_e = conn.execute(
                    "SELECT * FROM evidence_records WHERE violation_id = ? ORDER BY timestamp ASC",
                    (v_dict["id"],),
                )
                ev_items = [dict(er) for er in cur_e.fetchall()]
                if not ev_items:
                    cur_e_fallback = conn.execute(
                        "SELECT * FROM evidence_records WHERE session_id = ? AND (filename LIKE ? OR filepath LIKE ?) ORDER BY timestamp ASC",
                        (session_id, f"%{v_type}%", f"%{v_type}%"),
                    )
                    ev_items = [dict(er) for er in cur_e_fallback.fetchall()]
                if not ev_items and v_type == "UNAUTH_VOICE":
                    cur_e_audio = conn.execute(
                        "SELECT * FROM evidence_records WHERE session_id = ? AND (filename LIKE '%.wav' OR filename LIKE '%UNAUTH_VOICE%') ORDER BY timestamp ASC",
                        (session_id,),
                    )
                    ev_items = [dict(er) for er in cur_e_audio.fetchall()]
                for e in ev_items:
                    e["metadata"] = json.loads(e.get("metadata_json") or "{}")
                v_dict["evidence"] = ev_items

                # Fetch replay for this violation
                cur_rep = conn.execute(
                    "SELECT * FROM replay_records WHERE violation_id = ?",
                    (v_dict["id"],),
                )
                rep_row = cur_rep.fetchone()
                if rep_row:
                    rep_dict = dict(rep_row)
                    rep_dict["metadata"] = json.loads(rep_dict.get("metadata_json") or "{}")
                    v_dict["replay"] = rep_dict
                else:
                    v_dict["replay"] = None

                violations.append(v_dict)

            # 2. Fetch all session evidence
            cur_all_e = conn.execute(
                "SELECT * FROM evidence_records WHERE session_id = ? ORDER BY timestamp ASC",
                (session_id,),
            )
            all_evidence = [dict(er) for er in cur_all_e.fetchall()]
            for e in all_evidence:
                e["metadata"] = json.loads(e.get("metadata_json") or "{}")

            # 3. Overall statistics
            total_violations = len(violations)
            total_duration = session.get("total_duration") or (
                max(0.0, (session.get("ended_at") or time.time()) - session["started_at"])
            )
            integrity_score = max(0, 100 - (total_violations * 12))

            report = {
                "session": session,
                "summary": {
                    "session_id": session_id,
                    "status": session["status"],
                    "started_at": session["started_at"],
                    "ended_at": session["ended_at"],
                    "duration_seconds": round(total_duration, 1),
                    "total_violations": total_violations,
                    "violations_by_type": type_counts,
                    "violations_by_category": category_counts,
                    "total_evidence_count": len(all_evidence),
                    "integrity_score": integrity_score,
                },
                "violations": violations,
                "evidence": all_evidence,
            }
            return report
        finally:
            conn.close()


# Singleton repository instance
session_repository = SessionRepository()
