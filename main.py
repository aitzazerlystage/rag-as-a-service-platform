"""
TestApp (FastAPI) — application factory and server entry.

Run:
  pip install -r requirements.txt
  python app.py
"""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import DB_PATH, FILEFLOW_API_BASE, FILEFLOW_API_KEY, ROOT
from database import init_db
from routers import chats, health, pages, rag

app = FastAPI(
    title="TestApp Helper Chatbot (FastAPI)",
    description="Demo app with dummy landing UI and explicit RAG integration endpoints.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chats.router)
app.include_router(rag.router)
app.include_router(pages.router)

app.mount("/static", StaticFiles(directory=ROOT), name="static")


def main() -> None:
    init_db()
    host = os.environ.get("TESTAPP_HOST", "127.0.0.1")
    port = int(os.environ.get("TESTAPP_PORT", "8765"))
    print(f"TestApp (FastAPI) -> http://{host}:{port} (SQLite: {DB_PATH})")
    print(
        f"FileFlow RAG -> {FILEFLOW_API_BASE} "
        f"(key configured: {bool(FILEFLOW_API_KEY and FILEFLOW_API_KEY.strip())})"
    )
    uvicorn.run("app:app", host=host, port=port, reload=False)
