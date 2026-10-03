"""Liveness, public UI config, and RAG endpoint documentation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from config import FILEFLOW_API_BASE, FILEFLOW_API_KEY

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "testapp-fastapi"}


@router.get("/config/public")
def public_config() -> dict[str, Any]:
    """Safe for the UI: base URL only, never the API key."""
    return {
        "fileflow_api_base": FILEFLOW_API_BASE,
        "api_key_configured": bool(FILEFLOW_API_KEY and FILEFLOW_API_KEY.strip()),
    }


@router.get("/rag/endpoints")
def rag_endpoints() -> dict[str, Any]:
    return {
        "purpose": "These endpoints are the only RAG integration endpoints in TestApp.",
        "endpoints": [
            {
                "name": "RAG Upload",
                "method": "POST",
                "path": "/api/rag/upload",
                "forwards_to": "/api/vectors/upload",
                "notes": "multipart form, sends x-api-key, logs uploaded filename under thread_id locally",
            },
            {
                "name": "RAG Query",
                "method": "POST",
                "path": "/api/rag/query",
                "forwards_to": "/api/vectors/query",
                "notes": "JSON body, requires query_text, supports thread_id and local persistence",
            },
        ],
    }
