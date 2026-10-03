"""SQLite connection, schema init, and chat/message persistence helpers."""

from __future__ import annotations

import sqlite3
import uuid

from config import DB_PATH
from utils import utc_now_iso


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS chats (
            thread_id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT 'New chat',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (thread_id) REFERENCES chats(thread_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (thread_id) REFERENCES chats(thread_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id);
        CREATE INDEX IF NOT EXISTS idx_uploads_thread ON uploads(thread_id);
        """
    )
    conn.commit()
    conn.close()


def ensure_chat_row(db: sqlite3.Connection, thread_id: str) -> None:
    row = db.execute("SELECT 1 FROM chats WHERE thread_id = ?", (thread_id,)).fetchone()
    if row:
        return
    now = utc_now_iso()
    db.execute(
        "INSERT INTO chats (thread_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (thread_id, "New chat", now, now),
    )


def save_user_assistant_turn(
    db: sqlite3.Connection, thread_id: str, user_text: str, assistant_text: str
) -> None:
    ensure_chat_row(db, thread_id)
    now = utc_now_iso()
    db.execute(
        "INSERT INTO messages (thread_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (thread_id, "user", user_text, now),
    )
    db.execute(
        "INSERT INTO messages (thread_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (thread_id, "assistant", assistant_text, now),
    )
    db.execute("UPDATE chats SET updated_at = ? WHERE thread_id = ?", (utc_now_iso(), thread_id))
    row = db.execute("SELECT COUNT(*) AS c FROM messages WHERE thread_id = ?", (thread_id,)).fetchone()
    if row and row["c"] == 2:
        chat = db.execute("SELECT title FROM chats WHERE thread_id = ?", (thread_id,)).fetchone()
        if chat and chat["title"] in ("New chat", ""):
            short = user_text.strip().replace("\n", " ")[:48]
            if len(user_text.strip()) > 48:
                short += "..."
            db.execute(
                "UPDATE chats SET title = ?, updated_at = ? WHERE thread_id = ?",
                (short or "Chat", utc_now_iso(), thread_id),
            )


def new_thread_id() -> str:
    return str(uuid.uuid4())
