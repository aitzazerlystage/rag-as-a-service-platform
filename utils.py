"""Small helpers shared by routes (timestamps, response formatting)."""

from __future__ import annotations

import json
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def pretty_response_body(text: str) -> str:
    try:
        return json.dumps(json.loads(text), indent=2)
    except (json.JSONDecodeError, TypeError):
        return text
