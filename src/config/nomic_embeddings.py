"""Nomic Atlas cloud embeddings (remote API — no local GPU)."""

import os
from typing import List

from langchain_core.embeddings import Embeddings


def _ensure_nomic_api_key() -> None:
    from config.settings import get_nomic_api_key

    key = get_nomic_api_key()
    if not key:
        raise ValueError(
            "NOMIC_API_KEY is required. Get one at https://atlas.nomic.ai/ and set it in .env"
        )
    os.environ.setdefault("NOMIC_API_KEY", key)


def nomic_embed_texts(
    texts: List[str],
    model: str,
    dimensionality: int,
    task_type: str = "search_document",
) -> List[List[float]]:
    """Call Nomic embed API (inference_mode=remote, no local model)."""
    from nomic import embed

    _ensure_nomic_api_key()
    output = embed.text(
        texts=texts,
        model=model,
        task_type=task_type,
        dimensionality=dimensionality,
        inference_mode="remote",
    )
    return output["embeddings"]


class NomicEmbeddings(Embeddings):
    """LangChain-compatible wrapper for Nomic cloud embeddings."""

    def __init__(
        self,
        model: str,
        dimensionality: int,
        document_task: str = "search_document",
        query_task: str = "search_query",
    ):
        self.model = model
        self.dimensionality = dimensionality
        self.document_task = document_task
        self.query_task = query_task

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        return nomic_embed_texts(
            texts, self.model, self.dimensionality, self.document_task
        )

    def embed_query(self, text: str) -> List[float]:
        return nomic_embed_texts(
            [text], self.model, self.dimensionality, self.query_task
        )[0]
