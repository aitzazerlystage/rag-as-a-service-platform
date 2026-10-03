"""
RAG Insert Service - Insert text into Pinecone vector store.

This service encapsulates the logic for chunking text, generating embeddings,
and storing chunks in Pinecone. Used by:
- /api/vectors/insert endpoint
- /api/vectors/upload endpoint (when insert_to_rag=True)
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException

from backend.crud import record_token_usage
from services.service_factory import create_services_from_auth, get_namespace_from_auth


def _sanitize_metadata_value(value: Any, field: str) -> str:
    """Convert metadata values to strings for Pinecone storage with case normalization"""
    if value is None:
        return ""
    text_fields_to_normalize = ["doc.author", "doc.category", "part.section_type", "part.clause_type"]
    if isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, bool):
        return str(value).lower()
    else:
        str_value = str(value).strip()
        if field in text_fields_to_normalize:
            return str_value.lower()
        return str_value


CUSTOM_METADATA_FIELDS = [
    "doc.author", "doc.category", "doc.publishedyear", "doc.priority",
    "part.section_type", "part.sentiment_score", "part.clause_type", "user_id",
    "document_title", "pdf_name", "is_eligible", "screening_result_id", "knowledge_base_id", "study_id",
]


async def _semantic_chunk_text(
    text: str,
    embedding_service,
    chunk_size: int = 2500,
    chunk_overlap: int = 600,
) -> list:
    """
    Semantic chunking implementation that splits text based on semantic similarity.
    Falls back to simple sentence-based splitting if embeddings fail.
    """
    if not text.strip():
        return []

    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)

    if len(sentences) <= 1:
        return [text.strip()] if text.strip() else []

    chunks = []
    current_chunk = ""

    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += (" " + sentence) if current_chunk else sentence

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    if len(chunks) > 1 and embedding_service:
        try:
            import numpy as np
            chunk_embeddings = await embedding_service.generate_embeddings_batch(chunks)
            merged_chunks = []
            i = 0

            while i < len(chunks):
                current_chunk = chunks[i]
                current_embedding = chunk_embeddings[i]
                j = i + 1

                while j < len(chunks):
                    next_chunk = chunks[j]
                    next_embedding = chunk_embeddings[j]
                    similarity = np.dot(current_embedding, next_embedding) / (
                        np.linalg.norm(current_embedding) * np.linalg.norm(next_embedding)
                    )
                    if similarity > 0.8 and len(current_chunk + " " + next_chunk) <= chunk_size * 1.5:
                        current_chunk += " " + next_chunk
                        j += 1
                    else:
                        break

                merged_chunks.append(current_chunk)
                i = j

            chunks = merged_chunks

        except Exception as e:
            print(f"Warning: Semantic merging failed, using sentence-based chunks: {e}")

    return [chunk for chunk in chunks if chunk.strip()]


async def insert_text_into_rag(
    pdf_text: str,
    metadata: Dict[str, Any],
    auth: Dict[str, Any],
    db,
    embedding_provider: Optional[str] = None,
    embedding_model: Optional[str] = None,
    endpoint_suffix: str = "vectors/insert",
) -> Dict[str, Any]:
    """
    Insert text into RAG: chunk, embed, store in Pinecone.

    Used by both /vectors/insert endpoint and /vectors/upload (when insert_to_rag=True).

    Args:
        pdf_text: Text to insert (extracted from document)
        metadata: Dict with at least "doc_id"; optional: title, filename, authors, etc.
        auth: Auth dict from get_current_api_key: { "api_key": obj, "subscription": obj }
        db: Database session
        embedding_provider: "ollama", "openai", "voyageai", or "cohere"
        embedding_model: Optional model name (uses provider default if None)
        endpoint_suffix: For token usage recording (e.g. "vectors/insert", "vectors/upload")

    Returns:
        {"doc_id", "vector_ids", "vector_count", "namespace", "total_tokens_org", "message"}

    Raises:
        HTTPException: On validation or quota errors
    """
    from config.settings import SUPPORTED_EMBEDDING_PROVIDERS, get_default_embedding_provider

    if embedding_provider is None:
        embedding_provider = get_default_embedding_provider()

    pdf_text = (pdf_text or "").strip()
    if not pdf_text:
        raise HTTPException(status_code=400, detail="pdf_text is required")

    doc_id = metadata.get("doc_id")
    if not doc_id:
        raise HTTPException(status_code=400, detail="metadata.doc_id is required")

    if embedding_provider not in SUPPORTED_EMBEDDING_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported embedding provider: {embedding_provider}. "
                f"Supported: {', '.join(SUPPORTED_EMBEDDING_PROVIDERS)}"
            ),
        )

    api_key_obj = auth["api_key"]
    subscription = auth["subscription"]
    org_id = api_key_obj.org_id
    project_id = api_key_obj.project_id

    if subscription.monthly_limit_ingest is not None and subscription.used_ingest >= subscription.monthly_limit_ingest:
        raise HTTPException(status_code=402, detail="Ingest quota exceeded.")
    if subscription.monthly_limit_tokens is not None and subscription.used_tokens >= subscription.monthly_limit_tokens:
        raise HTTPException(status_code=402, detail="Tokens quota exceeded.")

    embedding_service, pinecone_service = create_services_from_auth(
        auth=auth,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
    )

    chunks = await _semantic_chunk_text(pdf_text, embedding_service, chunk_size=2500, chunk_overlap=600)
    if not chunks:
        raise HTTPException(status_code=400, detail="No text chunks produced; cannot insert empty content.")

    embeddings = await embedding_service.generate_embeddings_batch(chunks)

    document_title = metadata.get("title", "")
    pdf_name = metadata.get("filename", "")
    authors = metadata.get("authors", "")
    journal = metadata.get("journal", "")
    publication_date = metadata.get("publication_date", "")
    doi = metadata.get("doi", "")

    safe_metadata = {
        "doc_id": str(doc_id),
        "org_id": str(org_id),
        "project_id": str(project_id),
        "embedding_provider": embedding_provider,
        "embedding_model": embedding_service.model_name,
        "document_title": document_title,
        "pdf_name": pdf_name,
        "authors": authors,
        "journal": journal,
        "publication_date": publication_date,
        "doi": doi,
    }

    for field in CUSTOM_METADATA_FIELDS:
        if field in metadata:
            safe_metadata[field] = _sanitize_metadata_value(metadata[field], field)

    namespace = get_namespace_from_auth(auth)

    vector_ids = await pinecone_service.store_pdf_chunks(
        chunk_texts=chunks,
        base_metadata=safe_metadata,
        embeddings=embeddings,
        namespace=namespace,
    )

    subscription.used_ingest += 1
    subscription.used_tokens += len(chunks)
    subscription.used_storage_mb += len(chunks)
    db.commit()

    total_tokens = 0
    try:
        total_tokens = record_token_usage(
            db=db,
            api_key_id=api_key_obj.id,
            endpoint=endpoint_suffix,
            operation_type="insert",
            input_text=pdf_text,
            output_text="",
        )
    except Exception as e:
        print(f"WARNING: Failed to record token usage: {e}")

    return {
        "doc_id": str(doc_id),
        "vector_ids": [str(v) for v in vector_ids],
        "vector_count": len(vector_ids),
        "namespace": namespace,
        "embedding_provider": embedding_provider,
        "embedding_model": embedding_service.model_name,
        "total_tokens_org": total_tokens,
        "message": "stored",
    }
