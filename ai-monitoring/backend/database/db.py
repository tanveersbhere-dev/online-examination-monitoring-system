"""
Monitoring Database Layer
=========================
Thread-safe SQLite storage for Monitoring Sessions, Violations, Evidence, and Replays.
"""
import os
import sqlite3
import json
import time
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("playground.database")

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DB_DIR / "monitoring.db"


def get_db_connection() -> sqlite3.Connection:
    """Create a SQLite connection with WAL mode and row factory."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=15.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Initialize database tables and indexes."""
    conn = get_db_connection()
    try:
        with conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS monitoring_sessions (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                student_id TEXT DEFAULT 'local_student',
                examiner_id TEXT,
                exam_id TEXT,
                attempt_id TEXT,
                started_at REAL NOT NULL,
                ended_at REAL,
                total_duration REAL DEFAULT 0.0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                metadata_json TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS violations (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                episode_id TEXT NOT NULL,
                violation_type TEXT NOT NULL,
                category TEXT DEFAULT 'BEHAVIOR',
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'STARTED',
                start_time REAL NOT NULL,
                end_time REAL,
                duration REAL DEFAULT 0.0,
                peak_confidence REAL DEFAULT 0.0,
                avg_confidence REAL DEFAULT 0.0,
                detection_count INTEGER DEFAULT 1,
                risk_score REAL DEFAULT 0.0,
                triggered_rules_json TEXT DEFAULT '[]',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                FOREIGN KEY (session_id) REFERENCES monitoring_sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS evidence_records (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                violation_id TEXT NOT NULL,
                evidence_type TEXT NOT NULL DEFAULT 'SNAPSHOT',
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                timestamp REAL NOT NULL,
                confidence REAL DEFAULT 0.0,
                duration REAL DEFAULT 0.0,
                metadata_json TEXT DEFAULT '{}',
                created_at REAL NOT NULL,
                FOREIGN KEY (session_id) REFERENCES monitoring_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (violation_id) REFERENCES violations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS replay_records (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                violation_id TEXT NOT NULL,
                clip_path TEXT,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                duration REAL DEFAULT 3.0,
                frame_count INTEGER DEFAULT 30,
                metadata_json TEXT DEFAULT '{}',
                created_at REAL NOT NULL,
                FOREIGN KEY (session_id) REFERENCES monitoring_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (violation_id) REFERENCES violations(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_violations_session ON violations(session_id);
            CREATE INDEX IF NOT EXISTS idx_violations_episode ON violations(episode_id);
            CREATE INDEX IF NOT EXISTS idx_evidence_violation ON evidence_records(violation_id);
            CREATE INDEX IF NOT EXISTS idx_evidence_session ON evidence_records(session_id);
            CREATE INDEX IF NOT EXISTS idx_replay_violation ON replay_records(violation_id);
            """)
        logger.info(f"Database initialized successfully at {DB_PATH}")
    finally:
        conn.close()


# Ensure DB is initialized on module load
init_db()
