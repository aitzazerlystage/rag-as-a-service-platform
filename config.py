"""Paths and environment-driven settings (FileFlow RAG, server host/port)."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "testapp.db"

_FILEFLOW_API_BASE_DEFAULT = "http://localhost:8001"
_FILEFLOW_API_KEY_DEFAULT = (
    "39a1fdac796b62659bf219e54f0abe428df7feadb4ea1f40b0205b3377f3366f"
)

FILEFLOW_API_BASE = (os.environ.get("FILEFLOW_API_BASE") or _FILEFLOW_API_BASE_DEFAULT).rstrip("/")
FILEFLOW_API_KEY = os.environ.get("FILEFLOW_API_KEY") or _FILEFLOW_API_KEY_DEFAULT
