"""Pydantic request/response models for API bodies."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CreateChatRequest(BaseModel):
    title: str = "New chat"


class RenameChatRequest(BaseModel):
    title: str = Field(..., min_length=1)


class RagQueryRequest(BaseModel):
    query_text: str = Field(..., min_length=1)
    top_k: int = 5
    thread_id: Optional[str] = None
    history: bool = True
    persist: bool = True
