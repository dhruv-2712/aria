# core/memory.py
from __future__ import annotations
import json
import os
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "")
_PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))

if not _PG:
    import sqlite3
    _DB_PATH = os.path.join(os.path.dirname(__file__), "../db/aria.db")
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)

_P = "%s" if _PG else "?"


def _conn():
    if _PG:
        import psycopg2
        import psycopg2.extras
        return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    c = sqlite3.connect(_DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _rows(rows):
    return [dict(r) for r in rows]


def init_db():
    conn = _conn()
    cur = conn.cursor()
    if _PG:
        for stmt in [
            """CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, query TEXT NOT NULL,
                created_at TEXT NOT NULL, status TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS agent_logs (
                id SERIAL PRIMARY KEY, session_id TEXT NOT NULL,
                agent_name TEXT NOT NULL, input_json TEXT, output_json TEXT,
                timestamp TEXT NOT NULL, duration_ms INTEGER)""",
            """CREATE TABLE IF NOT EXISTS reports (
                id SERIAL PRIMARY KEY, session_id TEXT NOT NULL,
                executive TEXT, standard TEXT, technical TEXT,
                citations_json TEXT, follow_ups_json TEXT, created_at TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS findings (
                id SERIAL PRIMARY KEY, session_id TEXT NOT NULL,
                content TEXT, source_url TEXT, confidence REAL, domain TEXT)""",
        ]:
            cur.execute(stmt)
        cur.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS follow_ups_json TEXT")
    else:
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, query TEXT NOT NULL,
                created_at TEXT NOT NULL, status TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS agent_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                agent_name TEXT NOT NULL, input_json TEXT, output_json TEXT,
                timestamp TEXT NOT NULL, duration_ms INTEGER);
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                executive TEXT, standard TEXT, technical TEXT,
                citations_json TEXT, follow_ups_json TEXT, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                content TEXT, source_url TEXT, confidence REAL, domain TEXT);
        """)
        try:
            conn.execute("ALTER TABLE reports ADD COLUMN follow_ups_json TEXT")
        except Exception:
            pass  # Column already exists in this DB
    conn.commit()
    conn.close()
    print(f"[Memory] Database initialized ({'PostgreSQL' if _PG else 'SQLite'}).")


def create_session(session_id: str, query: str):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO sessions (id,query,created_at,status) VALUES ({_P},{_P},{_P},{_P})",
        (session_id, query, datetime.utcnow().isoformat(), "started"),
    )
    conn.commit()
    conn.close()


def update_session_status(session_id: str, status: str):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE sessions SET status={_P} WHERE id={_P}", (status, session_id))
    conn.commit()
    conn.close()


def log_agent_call(session_id: str, agent_name: str,
                   input_data: dict, output_data: dict, duration_ms: int):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO agent_logs (session_id,agent_name,input_json,output_json,timestamp,duration_ms)"
        f" VALUES ({_P},{_P},{_P},{_P},{_P},{_P})",
        (session_id, agent_name, json.dumps(input_data),
         json.dumps(output_data), datetime.utcnow().isoformat(), duration_ms),
    )
    conn.commit()
    conn.close()


def save_report(session_id: str, executive: str, standard: str,
                technical: str, citations: list):
    if not isinstance(executive, str): executive = json.dumps(executive)
    if not isinstance(standard, str):  standard  = json.dumps(standard)
    if not isinstance(technical, str): technical = json.dumps(technical)
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO reports (session_id,executive,standard,technical,citations_json,created_at)"
        f" VALUES ({_P},{_P},{_P},{_P},{_P},{_P})",
        (session_id, executive, standard, technical,
         json.dumps(citations), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def update_report_standard(session_id: str, standard: str):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE reports SET standard={_P} WHERE session_id={_P}",
        (standard, session_id),
    )
    conn.commit()
    conn.close()


def update_report_follow_ups(session_id: str, follow_ups: list):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE reports SET follow_ups_json={_P} WHERE session_id={_P}",
        (json.dumps(follow_ups), session_id),
    )
    conn.commit()
    conn.close()


def save_findings(session_id: str, findings: list):
    conn = _conn()
    cur = conn.cursor()
    for f in findings:
        cur.execute(
            f"INSERT INTO findings (session_id,content,source_url,confidence,domain)"
            f" VALUES ({_P},{_P},{_P},{_P},{_P})",
            (session_id, f.get("content"), f.get("source_url"),
             f.get("confidence_score", 0.0), f.get("domain", "unknown")),
        )
    conn.commit()
    conn.close()


def get_session(session_id: str) -> dict | None:
    conn = _conn()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM sessions WHERE id={_P}", (session_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_session_logs(session_id: str) -> list:
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM agent_logs WHERE session_id={_P} ORDER BY timestamp", (session_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return _rows(rows)


def get_report(session_id: str) -> dict | None:
    conn = _conn()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM reports WHERE session_id={_P}", (session_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_sessions(limit: int = 20) -> list:
    conn = _conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT s.id, s.query, s.created_at, s.status,
               CASE WHEN r.id IS NOT NULL THEN 1 ELSE 0 END AS has_report
        FROM sessions s
        LEFT JOIN reports r ON s.id = r.session_id
        WHERE s.status = 'done'
        ORDER BY s.created_at DESC
        LIMIT {_P}
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return _rows(rows)


def get_cached_findings(query: str) -> list | None:
    conn = _conn()
    cur = conn.cursor()
    if _PG:
        cur.execute("""
            SELECT f.content, f.source_url, f.confidence, f.domain
            FROM findings f JOIN sessions s ON f.session_id = s.id
            WHERE s.query = %s
              AND CAST(s.created_at AS TIMESTAMP) > NOW() - INTERVAL '24 hours'
            ORDER BY s.created_at DESC LIMIT 20
        """, (query,))
    else:
        cur.execute("""
            SELECT f.content, f.source_url, f.confidence, f.domain
            FROM findings f JOIN sessions s ON f.session_id = s.id
            WHERE s.query = ? AND datetime(s.created_at) > datetime('now', '-24 hours')
            ORDER BY s.created_at DESC LIMIT 20
        """, (query,))
    rows = cur.fetchall()
    conn.close()
    if rows:
        print(f"[Memory] Cache hit for query: '{query[:50]}'")
        return _rows(rows)
    return None
