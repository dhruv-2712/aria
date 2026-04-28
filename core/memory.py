# core/memory.py
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "../db/aria.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they don't exist. Call once at startup."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            input_json TEXT,
            output_json TEXT,
            timestamp TEXT NOT NULL,
            duration_ms INTEGER,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            executive TEXT,
            standard TEXT,
            technical TEXT,
            citations_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            content TEXT,
            source_url TEXT,
            confidence REAL,
            domain TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
    """)

    conn.commit()
    conn.close()
    print("[Memory] Database initialized.")


def create_session(session_id: str, query: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO sessions (id, query, created_at, status) VALUES (?, ?, ?, ?)",
        (session_id, query, datetime.utcnow().isoformat(), "started")
    )
    conn.commit()
    conn.close()


def update_session_status(session_id: str, status: str):
    conn = get_connection()
    conn.execute(
        "UPDATE sessions SET status = ? WHERE id = ?",
        (status, session_id)
    )
    conn.commit()
    conn.close()


def log_agent_call(session_id: str, agent_name: str,
                   input_data: dict, output_data: dict, duration_ms: int):
    conn = get_connection()
    conn.execute(
        """INSERT INTO agent_logs 
           (session_id, agent_name, input_json, output_json, timestamp, duration_ms)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            session_id,
            agent_name,
            json.dumps(input_data),
            json.dumps(output_data),
            datetime.utcnow().isoformat(),
            duration_ms
        )
    )
    conn.commit()
    conn.close()


def save_report(session_id: str, executive: str, standard: str,
                technical: str, citations: list):
    # Defensive: convert anything non-string to JSON string
    if not isinstance(executive, str):
        executive = json.dumps(executive)
    if not isinstance(standard, str):
        standard = json.dumps(standard)
    if not isinstance(technical, str):
        technical = json.dumps(technical)

    conn = get_connection()
    conn.execute(
        """INSERT INTO reports (session_id, executive, standard, technical, citations_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (session_id, executive, standard, technical,
         json.dumps(citations), datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def save_findings(session_id: str, findings: list):
    conn = get_connection()
    for f in findings:
        conn.execute(
            """INSERT INTO findings (session_id, content, source_url, confidence, domain)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, f.get("content"), f.get("source_url"),
             f.get("confidence_score", 0.0), f.get("domain", "unknown"))
        )
    conn.commit()
    conn.close()


def get_session_logs(session_id: str) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM agent_logs WHERE session_id = ? ORDER BY timestamp",
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_report(session_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM reports WHERE session_id = ?", (session_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_cached_findings(query: str) -> list | None:
    """Return findings from a previous identical query if < 24 hours old."""
    conn = get_connection()
    row = conn.execute("""
        SELECT f.content, f.source_url, f.confidence, f.domain
        FROM findings f
        JOIN sessions s ON f.session_id = s.id
        WHERE s.query = ?
        AND datetime(s.created_at) > datetime('now', '-24 hours')
        ORDER BY s.created_at DESC
        LIMIT 20
    """, (query,)).fetchall()
    conn.close()
    if row:
        print(f"[Memory] Cache hit for query: '{query[:50]}'")
        return [dict(r) for r in row]
    return None