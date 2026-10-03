import os
from typing import Tuple

_SHARED_OPENAI_KEY = os.getenv("OPENAI_API_KEY")
_SHARED_PINECONE_KEY = os.getenv("PINECONE_API_KEY")
_SHARED_PINECONE_INDEX = os.getenv("PINECONE_INDEX_NAME")
_SHARED_PINECONE_ENV = os.getenv("PINECONE_ENVIRONMENT")


def _get_shared_keys() -> Tuple[str, str, str, str]:
    """OpenAI + Pinecone from environment (all RAG traffic uses these keys)."""
    if not _SHARED_OPENAI_KEY:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    if not _SHARED_PINECONE_KEY:
        raise ValueError("PINECONE_API_KEY environment variable is not set")

    return _SHARED_OPENAI_KEY, _SHARED_PINECONE_KEY, _SHARED_PINECONE_INDEX, _SHARED_PINECONE_ENV


def get_key(subscription) -> Tuple[str, str, str, str]:
    """
    Return platform API keys. Subscription row is used for quotas only; keys
    always come from environment.
    """
    return _get_shared_keys()
