"""LangChain embeddings for SemanticChunker (uses default embedding provider)."""

from typing import List

from langchain_core.embeddings import Embeddings

from config.embedding_align import align_vector_to_index
from config.settings import (
    EMBEDDING_PROVIDERS,
    get_OPENAI_API_KEY,
    get_cohere_api_key,
    get_default_embedding_model,
    get_default_embedding_provider,
    get_ollama_base_url,
    get_pinecone_index_dimensions,
    get_voyage_api_key,
)


class IndexAlignedEmbeddings(Embeddings):
    """Wraps an embedder and pads/truncates vectors to the Pinecone index size."""

    def __init__(self, base: Embeddings, index_dimensions: int):
        self.base = base
        self.index_dimensions = index_dimensions

    def _align(self, vectors: List[List[float]]) -> List[List[float]]:
        return [align_vector_to_index(v, self.index_dimensions) for v in vectors]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._align(self.base.embed_documents(texts))

    def embed_query(self, text: str) -> List[float]:
        return align_vector_to_index(self.base.embed_query(text), self.index_dimensions)


def get_chunking_embeddings() -> Embeddings:
    provider = get_default_embedding_provider()
    model = get_default_embedding_model()
    index_dims = get_pinecone_index_dimensions()
    provider_cfg = EMBEDDING_PROVIDERS.get(provider, {})
    model_dims = provider_cfg.get("model_dimensions", index_dims)
    needs_align = model_dims != index_dims

    if provider == "cohere":
        from langchain_cohere import CohereEmbeddings

        base = CohereEmbeddings(model=model, cohere_api_key=get_cohere_api_key())
        return IndexAlignedEmbeddings(base, index_dims) if needs_align else base

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        base = OpenAIEmbeddings(
            model=model,
            api_key=get_OPENAI_API_KEY(),
            dimensions=index_dims,
        )
        return base

    if provider == "voyageai":
        from langchain_community.embeddings import VoyageEmbeddings

        base = VoyageEmbeddings(voyage_api_key=get_voyage_api_key(), model=model)
        return IndexAlignedEmbeddings(base, index_dims) if needs_align else base

    if provider == "nomic":
        from config.nomic_embeddings import NomicEmbeddings

        base = NomicEmbeddings(model=model, dimensionality=model_dims)
        return IndexAlignedEmbeddings(base, index_dims) if needs_align else base

    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        base = OllamaEmbeddings(model=model, base_url=get_ollama_base_url())
        return IndexAlignedEmbeddings(base, index_dims) if needs_align else base

    raise ValueError(f"Unsupported embedding provider for chunking: {provider}")
