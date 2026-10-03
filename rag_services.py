"""
RAG / FileFlow integration: take structured input, call upstream, optionally persist locally.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import requests

from config import FILEFLOW_API_BASE, FILEFLOW_API_KEY
from database import ensure_chat_row, get_db, save_user_assistant_turn
from utils import pretty_response_body, utc_now_iso


def send_rag_file_to_upstream(
    filename: str,
    file_bytes: bytes,
    content_type: str,
) -> dict[str, Any]:
    """
    POST multipart upload to FileFlow `/api/vectors/upload`.

    Input: file metadata and raw bytes. Output: normalized dict for the JSON API
    (status, parsed body, etc.). Raises ``requests.RequestException`` on transport errors.
    """
    url = f"{FILEFLOW_API_BASE}/api/vectors/upload"
    files = [("files", (filename, file_bytes, content_type or "application/octet-stream"))]
    data = {"insert_to_rag": "true"}
    response = requests.post(
        url,
        headers={"x-api-key": FILEFLOW_API_KEY},
        files=files,
        data=data,
        timeout=600,
    )
    parsed = _try_parse_json(response)
    return {
        "ok": response.ok,
        "status": response.status_code,
        "status_text": response.reason,
        "body": pretty_response_body(response.text),
        "parsed": parsed,
        "forwarded_endpoint": "/api/vectors/upload",
    }


def send_rag_query_to_upstream(body: dict[str, Any]) -> dict[str, Any]:
    """
    POST JSON to FileFlow `/api/vectors/query`.

    Input: already-built JSON body (``query_text``, ``top_k``, ``history``, optional ``thread_id``).
    Output: same normalized shape as upload. Raises ``requests.RequestException`` on transport errors.
    """
    url = f"{FILEFLOW_API_BASE}/api/vectors/query"
    response = requests.post(
        url,
        headers={"Content-Type": "application/json", "x-api-key": FILEFLOW_API_KEY},
        json=body,
        timeout=300,
    )
    parsed = _try_parse_json(response)
    return {
        "ok": response.ok,
        "status": response.status_code,
        "status_text": response.reason,
        "body": pretty_response_body(response.text),
        "parsed": parsed,
        "forwarded_endpoint": "/api/vectors/query",
    }


def apply_local_rag_persistence(
    *,
    upstream_ok: bool,
    thread_id: Optional[str] = None,
    upload_filename: Optional[str] = None,
    query_text: Optional[str] = None,
    parsed_response: Optional[dict[str, Any]] = None,
    persist_query_turn: bool = False,
) -> None:
    """
    After a successful upstream call, mirror metadata in SQLite when requested.

    - Upload path: when ``upstream_ok`` and ``thread_id`` and ``upload_filename`` are set,
      records the filename under that chat thread.
    - Query path: when ``upstream_ok``, ``persist_query_turn``, ``thread_id``, ``query_text``,
      and ``parsed_response`` are set, saves user + assistant messages if ``langgraph_response`` is present.
    """
    if upstream_ok and thread_id and upload_filename:
        db = get_db()
        try:
            ensure_chat_row(db, thread_id)
            db.execute(
                "INSERT INTO uploads (thread_id, filename, created_at) VALUES (?, ?, ?)",
                (thread_id, upload_filename, utc_now_iso()),
            )
            db.execute("UPDATE chats SET updated_at = ? WHERE thread_id = ?", (utc_now_iso(), thread_id))
            db.commit()
        finally:
            db.close()
        return

    if not (
        upstream_ok
        and persist_query_turn
        and thread_id
        and parsed_response
        and query_text
    ):
        return

    reply = parsed_response.get("langgraph_response")
    if not isinstance(reply, str) or not reply.strip():
        return

    db = get_db()
    try:
        save_user_assistant_turn(db, thread_id, query_text.strip(), reply.strip())
        db.commit()
    finally:
        db.close()


def _try_parse_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except (json.JSONDecodeError, ValueError):
        return None
