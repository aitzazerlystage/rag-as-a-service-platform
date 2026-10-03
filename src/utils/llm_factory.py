"""Backward-compatible shim — use config.llm_factory instead."""
from config.llm_factory import create_chat_llm

__all__ = ["create_chat_llm"]
