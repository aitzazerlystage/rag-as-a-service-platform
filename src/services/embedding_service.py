import asyncio
import logging
import os
from typing import List, Optional

import cohere
import voyageai
from openai import OpenAI

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, model_provider: str = None, model_name: str = None, openai_key: str = None):
        from config.settings import (
            EMBEDDING_PROVIDERS,
            get_default_embedding_provider,
            get_pinecone_index_dimensions,
        )

        self.model_provider = model_provider or get_default_embedding_provider()
        self.model_name = model_name or self._get_default_model()
        provider_cfg = EMBEDDING_PROVIDERS.get(self.model_provider, {})
        self.dimensions = provider_cfg.get("dimensions", get_pinecone_index_dimensions())
        self.model_dimensions = provider_cfg.get("model_dimensions", self.dimensions)
        self._align_dims = self.model_dimensions != self.dimensions
        self.openai_key = openai_key
        self.embeddings = None
        self.client = None
        self._initialize_client()

    def _get_default_model(self) -> str:
        from config.settings import EMBEDDING_PROVIDERS

        if self.model_provider in EMBEDDING_PROVIDERS:
            return EMBEDDING_PROVIDERS[self.model_provider]["default"]
        return "mxbai-embed-large"

    def _initialize_client(self):
        if self.model_provider == "nomic":
            from config.settings import get_nomic_api_key

            if not get_nomic_api_key():
                raise ValueError("NOMIC_API_KEY is required for nomic embeddings")
            return

        if self.model_provider == "ollama":
            from langchain_ollama import OllamaEmbeddings
            from config.settings import get_ollama_base_url

            self.embeddings = OllamaEmbeddings(
                model=self.model_name,
                base_url=get_ollama_base_url(),
            )
            return

        if self.model_provider == "openai":
            api_key = self.openai_key
            if not api_key:
                raise ValueError("OPENAI_API_KEY is required for openai embeddings")
            self.client = OpenAI(api_key=api_key)
            return

        if self.model_provider == "voyageai":
            api_key = os.getenv("VOYAGE_API_KEY")
            if not api_key:
                raise ValueError("VOYAGE_API_KEY environment variable is required")
            self.client = voyageai.Client(api_key=api_key)
            return

        if self.model_provider == "cohere":
            api_key = os.getenv("COHERE_API_KEY")
            if not api_key:
                raise ValueError("COHERE_API_KEY environment variable is required")
            self.client = cohere.Client(api_key=api_key)
            return

        raise ValueError(f"Unsupported embedding provider: {self.model_provider}")

    def _finalize_vector(self, vector: List[float]) -> List[float]:
        from config.embedding_align import align_vector_to_index

        if self._align_dims:
            vector = align_vector_to_index(vector, self.dimensions)
        if len(vector) != self.dimensions:
            raise ValueError(
                f"Embedding dimension mismatch for {self.model_provider}/{self.model_name}: "
                f"got {len(vector)}, expected {self.dimensions} (Pinecone index)."
            )
        return vector

    def _finalize_vectors(self, vectors: List[List[float]]) -> List[List[float]]:
        return [self._finalize_vector(v) for v in vectors]

    async def generate_embedding(self, text: str) -> List[float]:
        try:
            max_chars = 8191 * 4
            if len(text) > max_chars:
                text = text[:max_chars]
                logger.warning("Text truncated for embedding")

            if self.model_provider == "nomic":
                vector = await self._generate_nomic_embedding(text, task_type="search_query")
                return self._finalize_vector(vector)
            if self.model_provider == "ollama":
                vector = await asyncio.to_thread(self.embeddings.embed_query, text)
                return self._finalize_vector(vector)
            if self.model_provider == "openai":
                return self._finalize_vector(await self._generate_openai_embedding(text))
            if self.model_provider == "voyageai":
                return self._finalize_vector(await self._generate_voyage_embedding(text))
            if self.model_provider == "cohere":
                return self._finalize_vector(await self._generate_cohere_embedding(text))
        except Exception as e:
            logger.error(f"Error generating embedding with {self.model_provider}: {e}")
            raise

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            processed_texts = []
            max_chars = 8191 * 4
            for text in texts:
                if len(text) > max_chars:
                    text = text[:max_chars]
                processed_texts.append(text)

            if self.model_provider == "nomic":
                vectors = await self._generate_nomic_embeddings_batch(processed_texts)
                return self._finalize_vectors(vectors)
            if self.model_provider == "ollama":
                vectors = await asyncio.to_thread(
                    self.embeddings.embed_documents, processed_texts
                )
                return self._finalize_vectors(vectors)
            if self.model_provider == "openai":
                return self._finalize_vectors(
                    await self._generate_openai_embeddings_batch(processed_texts)
                )
            if self.model_provider == "voyageai":
                return self._finalize_vectors(
                    await self._generate_voyage_embeddings_batch(processed_texts)
                )
            if self.model_provider == "cohere":
                return self._finalize_vectors(
                    await self._generate_cohere_embeddings_batch(processed_texts)
                )
        except Exception as e:
            logger.error(f"Error generating batch embeddings with {self.model_provider}: {e}")
            raise

    async def _generate_openai_embedding(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            model=self.model_name,
            input=text,
            dimensions=self.dimensions,
        )
        return response.data[0].embedding

    async def _generate_voyage_embedding(self, text: str) -> List[float]:
        result = self.client.embed(
            texts=[text],
            model=self.model_name,
            input_type="document",
        )
        return result.embeddings[0]

    async def _generate_cohere_embedding(self, text: str) -> List[float]:
        response = self.client.embed(
            texts=[text],
            model=self.model_name,
            input_type="search_document",
        )
        return response.embeddings[0]

    async def _generate_openai_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(
            model=self.model_name,
            input=texts,
            dimensions=self.dimensions,
        )
        return [data.embedding for data in response.data]

    async def _generate_voyage_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        result = self.client.embed(
            texts=texts,
            model=self.model_name,
            input_type="document",
        )
        return result.embeddings

    async def _generate_cohere_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embed(
            texts=texts,
            model=self.model_name,
            input_type="search_document",
        )
        return response.embeddings

    async def _generate_nomic_embedding(
        self, text: str, task_type: str = "search_document"
    ) -> List[float]:
        from config.nomic_embeddings import nomic_embed_texts

        vectors = await asyncio.to_thread(
            nomic_embed_texts,
            [text],
            self.model_name,
            self.model_dimensions,
            task_type,
        )
        return vectors[0]

    async def _generate_nomic_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        from config.nomic_embeddings import nomic_embed_texts

        return await asyncio.to_thread(
            nomic_embed_texts,
            texts,
            self.model_name,
            self.model_dimensions,
            "search_document",
        )
