"""Chat threads, messages, and per-thread upload metadata."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from database import get_db, new_thread_id
from schemas import CreateChatRequest, RenameChatRequest
from utils import utc_now_iso

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.get("")
def list_chats() -> dict[str, Any]:
    db = get_db()
    try:
        rows = db.execute(
            """
            SELECT c.thread_id, c.title, c.created_at, c.updated_at,
                   (SELECT content FROM messages m WHERE m.thread_id = c.thread_id
                    ORDER BY m.id DESC LIMIT 1) AS last_message
            FROM chats c
            ORDER BY c.updated_at DESC
            """
        ).fetchall()
        return {
            "chats": [
                {
                    "thread_id": r["thread_id"],
                    "title": r["title"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                    "last_message": r["last_message"],
                }
                for r in rows
            ]
        }
    finally:
        db.close()


@router.post("")
def create_chat(payload: CreateChatRequest) -> dict[str, Any]:
    title = payload.title.strip() or "New chat"
    thread_id = new_thread_id()
    now = utc_now_iso()
    db = get_db()
    try:
        db.execute(
            "INSERT INTO chats (thread_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (thread_id, title, now, now),
        )
        db.commit()
        return {"thread_id": thread_id, "title": title, "created_at": now}
    finally:
        db.close()


@router.patch("/{thread_id}")
def rename_chat(thread_id: str, payload: RenameChatRequest) -> dict[str, Any]:
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="title required")
    db = get_db()
    try:
        cur = db.execute(
            "UPDATE chats SET title = ?, updated_at = ? WHERE thread_id = ?",
            (title, utc_now_iso(), thread_id),
        )
        db.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="chat not found")
        return {"ok": True}
    finally:
        db.close()


@router.delete("/{thread_id}")
def delete_chat(thread_id: str) -> dict[str, Any]:
    db = get_db()
    try:
        db.execute("DELETE FROM chats WHERE thread_id = ?", (thread_id,))
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.get("/{thread_id}/messages")
def list_messages(thread_id: str) -> dict[str, Any]:
    db = get_db()
    try:
        rows = db.execute(
            "SELECT id, role, content, created_at FROM messages WHERE thread_id = ? ORDER BY id ASC",
            (thread_id,),
        ).fetchall()
        return {
            "messages": [
                {"id": r["id"], "role": r["role"], "content": r["content"], "created_at": r["created_at"]}
                for r in rows
            ]
        }
    finally:
        db.close()


@router.get("/{thread_id}/uploads")
def list_uploads(thread_id: str) -> dict[str, Any]:
    db = get_db()
    try:
        rows = db.execute(
            "SELECT id, filename, created_at FROM uploads WHERE thread_id = ? ORDER BY id DESC",
            (thread_id,),
        ).fetchall()
        return {
            "uploads": [{"id": r["id"], "filename": r["filename"], "created_at": r["created_at"]} for r in rows]
        }
    finally:
        db.close()
