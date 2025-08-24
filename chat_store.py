# chat_store.py
from __future__ import annotations
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Iterable, Tuple

# Toggle this if you want an in-memory DataFrame view too
USE_PANDAS = False
if USE_PANDAS:
    import pandas as pd

DB_PATH = Path(__file__).with_name("chat.db")

def _utc_iso() -> str:
    # ISO 8601 in UTC, sortable, ends with 'Z'
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def init_db() -> str:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        # Enable WAL for better concurrent writes
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user      TEXT NOT NULL,
            message   TEXT NOT NULL,
            timestamp TEXT NOT NULL,  -- ISO8601 UTC (e.g., 2025-08-11T17:05:32Z)
            reviewed  INTEGER NOT NULL DEFAULT 0
        );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_ts ON messages(user, timestamp DESC);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_reviewed ON messages(reviewed, timestamp DESC);")
        conn.commit()
    finally:
        conn.close()
    return str(DB_PATH.resolve())

def add_message(user: str, message: str) -> int:
    ts = _utc_iso()
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO messages(user, message, timestamp, reviewed) VALUES (?,?,?,0)",
            (user, message, ts)
        )
        conn.commit()
        row_id = cur.lastrowid
    finally:
        conn.close()
    if USE_PANDAS:
        _df_append({"user": user, "message": message, "timestamp": ts, "reviewed": False})
    return row_id

def mark_reviewed(ids: Iterable[int]) -> int:
    ids = list(ids)
    if not ids:
        return 0
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.executemany("UPDATE messages SET reviewed = 1 WHERE id = ?", [(i,) for i in ids])
        conn.commit()
        count = cur.rowcount
    finally:
        conn.close()
    if USE_PANDAS:
        _df_mark_reviewed(ids)
    return count

def most_recent_user() -> Optional[Tuple[str, str, str, int]]:
    """
    Returns (user, message, timestamp, id) for the newest message overall.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT user, message, timestamp, id
            FROM messages
            ORDER BY timestamp DESC, id DESC
            LIMIT 1;
        """)
        row = cur.fetchone()
    finally:
        conn.close()
    return row if row else None

def latest_message_per_user() -> list[Tuple[str, str, str, int]]:
    """
    Returns one row per user: (user, message, timestamp, id) for that user's most recent message.
    Uses a subquery to pick MAX(timestamp) per user.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("""
            WITH latest AS (
                SELECT user, MAX(timestamp) AS max_ts
                FROM messages
                GROUP BY user
            )
            SELECT m.user, m.message, m.timestamp, m.id
            FROM messages m
            JOIN latest l ON l.user = m.user AND l.max_ts = m.timestamp
            ORDER BY m.timestamp DESC;
        """)
        rows = cur.fetchall()
    finally:
        conn.close()
    return rows

def unreviewed(limit: int = 100) -> list[Tuple[int, str, str, str, int]]:
    """
    Returns unreviewed rows as (id, user, message, timestamp, reviewed)
    newest first.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, user, message, timestamp, reviewed
            FROM messages
            WHERE reviewed = 0
            ORDER BY timestamp DESC, id DESC
            LIMIT ?;
        """, (limit,))
        rows = cur.fetchall()
    finally:
        conn.close()
    return rows

# -------- Optional in-memory DataFrame mirror --------
_df = None
def _ensure_df():
    global _df
    if _df is None:
        _load_df()

def _load_df():
    global _df
    if not USE_PANDAS:
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        _df = pd.read_sql_query("SELECT id, user, message, timestamp, reviewed FROM messages", conn)
        # Ensure correct types
        _df["reviewed"] = _df["reviewed"].astype(bool)
    finally:
        conn.close()

def _df_append(row: dict):
    if not USE_PANDAS:
        return
    _ensure_df()
    global _df
    _df = pd.concat([_df, pd.DataFrame([row | {"id": _df["id"].max() + 1 if len(_df) else 1}])], ignore_index=True)

def _df_mark_reviewed(ids: Iterable[int]):
    if not USE_PANDAS:
        return
    _ensure_df()
    global _df
    _df.loc[_df["id"].isin(list(ids)), "reviewed"] = True

if __name__ == "__main__":
    print("DB at:", init_db())
