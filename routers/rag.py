"""Proxy endpoints to the FileFlow vector backend; logic lives in ``rag_services``."""

from __future__ import annotations

from typing import Any, Optional

import requests
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from config import FILEFLOW_API_KEY
from rag_services import apply_local_rag_persistence, send_rag_file_to_upstream, send_rag_query_to_upstream
from schemas import RagQueryRequest

router = APIRouter(prefix="/api/rag", tags=["rag"])


def _require_fileflow_key() -> None:
    if not FILEFLOW_API_KEY or not FILEFLOW_API_KEY.strip():
        raise HTTPException(
            status_code=503,
            detail="FILEFLOW_API_KEY is not set (use config default or FILEFLOW_API_KEY env).",
        )


@router.post("/upload")
async def rag_upload(
    file: UploadFile = File(...),
    thread_id: Optional[str] = Form(None),
) -> dict[str, Any]:
    _require_fileflow_key()
    if not file.filename:
        raise HTTPException(status_code=400, detail="file is required")

    raw = await file.read()
    content_type = file.content_type or "application/octet-stream"
    try:
        result = send_rag_file_to_upstream(file.filename, raw, content_type)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    apply_local_rag_persistence(
        upstream_ok=bool(result.get("ok")),
        thread_id=thread_id,
        upload_filename=file.filename,
    )

    return result


@router.post("/query")
def rag_query(payload: RagQueryRequest) -> dict[str, Any]:
    _require_fileflow_key()

    body: dict[str, Any] = {
        "query_text": payload.query_text.strip(),
        "top_k": payload.top_k,
        "history": payload.history,
    }
    if payload.thread_id:
        body["thread_id"] = payload.thread_id

    try:
        result = send_rag_query_to_upstream(body)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    parsed = result.get("parsed")
    parsed_dict = parsed if isinstance(parsed, dict) else None
    apply_local_rag_persistence(
        upstream_ok=bool(result.get("ok")),
        thread_id=payload.thread_id,
        query_text=payload.query_text,
        parsed_response=parsed_dict,
        persist_query_turn=payload.persist,
    )

    return result
