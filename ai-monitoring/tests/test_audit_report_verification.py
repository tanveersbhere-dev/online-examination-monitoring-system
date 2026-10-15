import json
import time
import uuid
import pytest
from backend.database.db import get_db_connection
from backend.database.session_repository import session_repository

def test_audio_device_and_voice_report_card_evidence():
    test_sid = f"test_audit_{uuid.uuid4().hex[:6]}"
    now = time.time()

    # 1. Create monitoring session
    session_repository.create_session(
        session_id=test_sid,
        exam_id="EXAM-AUDIT",
        student_id="STUDENT-AUDIT",
    )

    # 2. Insert COMM_EARPHONES violation with JPEG snapshot
    v_aud_id = f"V-AUD-{uuid.uuid4().hex[:6]}"
    v_voc_id = f"V-VOICE-{uuid.uuid4().hex[:6]}"
    conn = get_db_connection()
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO violations (
                id, session_id, episode_id, violation_type, category, title, description,
                status, start_time, end_time, duration, peak_confidence, avg_confidence,
                detection_count, risk_score, triggered_rules_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            v_aud_id, test_sid, v_aud_id, "COMM_EARPHONES", "Communication Device",
            "Unauthorized Audio Device", "Earphone detected",
            "RESOLVED", now, now + 3, 3.0, 0.95, 0.95, 1, 80.0,
            json.dumps(["COMM_EARPHONES"]), now, now
        ))
        conn.execute("""
            INSERT OR REPLACE INTO evidence_records (
                id, session_id, violation_id, evidence_type, filename, filepath, timestamp, confidence, duration, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"EV-{v_aud_id}", test_sid, v_aud_id, "SNAPSHOT",
            f"evidence_COMM_EARPHONES_{v_aud_id}.jpg",
            f"C:/evidence/evidence_COMM_EARPHONES_{v_aud_id}.jpg",
            now + 1, 0.95, 3.0, json.dumps({"camera_id": "camera_1"}), now
        ))

        # 3. Insert UNAUTH_VOICE violation with WAV audio evidence
        conn.execute("""
            INSERT OR REPLACE INTO violations (
                id, session_id, episode_id, violation_type, category, title, description,
                status, start_time, end_time, duration, peak_confidence, avg_confidence,
                detection_count, risk_score, triggered_rules_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            v_voc_id, test_sid, v_voc_id, "UNAUTH_VOICE", "Communication & Speech",
            "Unauthorized Human Voice", "Human voice detected",
            "RESOLVED", now + 10, now + 15, 5.0, 0.92, 0.92, 1, 75.0,
            json.dumps(["UNAUTH_VOICE"]), now + 10, now + 10
        ))
        conn.execute("""
            INSERT OR REPLACE INTO evidence_records (
                id, session_id, violation_id, evidence_type, filename, filepath, timestamp, confidence, duration, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"EV-{v_voc_id}", test_sid, v_voc_id, "AUDIO",
            f"evidence_UNAUTH_VOICE_{v_voc_id}.wav",
            f"C:/evidence/evidence_UNAUTH_VOICE_{v_voc_id}.wav",
            now + 11, 0.92, 5.0, json.dumps({"evidence_type": "AUDIO", "audio_format": "WAV"}), now + 10
        ))
    conn.close()

    # 4. Fetch session report
    report = session_repository.get_session_report(test_sid)
    assert report is not None
    assert report["summary"]["total_violations"] == 2
    assert "COMM_EARPHONES" in report["summary"]["violations_by_type"]
    assert "UNAUTH_VOICE" in report["summary"]["violations_by_type"]

    viols_by_type = {v["violation_type"]: v for v in report["violations"]}
    
    # Verify COMM_EARPHONES has evidence
    assert "COMM_EARPHONES" in viols_by_type
    assert len(viols_by_type["COMM_EARPHONES"]["evidence"]) == 1
    assert viols_by_type["COMM_EARPHONES"]["evidence"][0]["filename"] == f"evidence_COMM_EARPHONES_{v_aud_id}.jpg"

    # Verify UNAUTH_VOICE has evidence
    assert "UNAUTH_VOICE" in viols_by_type
    assert len(viols_by_type["UNAUTH_VOICE"]["evidence"]) == 1
    assert viols_by_type["UNAUTH_VOICE"]["evidence"][0]["filename"] == f"evidence_UNAUTH_VOICE_{v_voc_id}.wav"
    assert viols_by_type["UNAUTH_VOICE"]["evidence"][0]["metadata"]["evidence_type"] == "AUDIO"
