

import os
from backend.crud import get_current_api_key
from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException
from backend.crud import (
    get_user_by_id, get_user_by_email, get_user_by_username, create_user, get_user_info,
    check_pdf_exists, get_existing_pdf_data, save_pdf_to_db, validate_user_pdf,
    get_user_pdfs, filter_unprocessed_pdf_ids, mark_pdfs_as_processed,
    get_pdf_info, update_pdf_llm_processed_flag, delete_pdf,
    create_thread_id, save_thread_to_db, update_thread_title, get_thread_by_id,
    get_user_threads, get_thread_pdfs, validate_thread_pdf_access, update_thread_pdfs,
    remove_pdf_from_thread, save_message_to_db, get_thread_messages,
    set_user_organization, get_organization_by_name, delete_user,
    get_organization_by_id, create_project, get_project_by_name_in_org,
    record_token_usage, record_aggregated_token_usage,count_tokens_with_tiktoken
) 

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from backend.crud import get_current_api_key, record_token_usage
from backend.database import get_db
from services.service_factory import create_services_from_auth, get_namespace_from_auth

router = APIRouter()

async def _semantic_chunk_text(text: str, embedding_service, chunk_size: int = 2500, chunk_overlap: int = 600) -> list:
    """
    Semantic chunking implementation that splits text based on semantic similarity.
    Falls back to simple sentence-based splitting if embeddings fail.
    """
    if not text.strip():
        return []
    
    # First, split by sentences as a base
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
            
        # If adding this sentence would exceed chunk size, finalize current chunk
        if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += (" " + sentence) if current_chunk else sentence
    
    # Add the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # If we have embeddings available, try to merge semantically similar chunks
    if len(chunks) > 1 and embedding_service:
        try:
            # Get embeddings for all chunks
            chunk_embeddings = await embedding_service.generate_embeddings_batch(chunks)
            
            # Merge chunks that are semantically similar
            merged_chunks = []
            i = 0
            
            while i < len(chunks):
                current_chunk = chunks[i]
                current_embedding = chunk_embeddings[i]
                
                # Look ahead to merge similar chunks
                j = i + 1
                while j < len(chunks):
                    next_chunk = chunks[j]
                    next_embedding = chunk_embeddings[j]
                    
                    # Calculate cosine similarity
                    import numpy as np
                    similarity = np.dot(current_embedding, next_embedding) / (
                        np.linalg.norm(current_embedding) * np.linalg.norm(next_embedding)
                    )
                    
                    # If chunks are similar and combined size is reasonable, merge them
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





# async def _recursive_chunk_text(text: str, embedding_service=None, chunk_size: int = 2500, chunk_overlap: int = 200) -> list:
#     """
#     Recursive text splitting implementation that splits text hierarchically by separators.
#     Tries larger separators first (paragraphs, sentences) and recursively falls back to smaller ones (words, characters).
    
#     Args:
#         text: Text to chunk
#         embedding_service: Optional embedding service (kept for compatibility, not used)
#         chunk_size: Maximum size of each chunk
#         chunk_overlap: Number of characters to overlap between chunks
    
#     Returns:
#         List of text chunks
#     """
#     if not text.strip():
#         return []
    
#     # If text is already small enough, return as single chunk
#     if len(text) <= chunk_size:
#         return [text.strip()]
    
#     # Ordered list of separators to try (from largest to smallest semantic units)
#     separators = [
#         "\n\n\n",      # Multiple paragraph breaks
#         "\n\n",        # Paragraph breaks
#         "\n",          # Line breaks
#         ". ",          # Sentence endings followed by space
#         "! ",          # Exclamation followed by space
#         "? ",          # Question mark followed by space
#         "; ",          # Semicolon
#         ", ",          # Comma followed by space
#         " ",           # Single space
#         "",            # Character-level (fallback)
#     ]
    
#     def _split_recursive(text: str, separators: list, chunk_size: int, chunk_overlap: int) -> list:
#         """
#         Recursively split text using separators.
#         """
#         # Base case: if text is small enough, return it
#         if len(text) <= chunk_size:
#             return [text.strip()] if text.strip() else []
        
#         # Try each separator until we find one that works
#         for separator in separators:
#             if separator == "":
#                 # Character-level fallback: just split at chunk_size
#                 chunks = []
#                 start = 0
#                 while start < len(text):
#                     end = min(start + chunk_size, len(text))
#                     chunk = text[start:end].strip()
#                     if chunk:
#                         chunks.append(chunk)
                    
#                     # Move forward with overlap
#                     start = end - chunk_overlap
#                     if start <= 0:  # Prevent infinite loop
#                         start = end
#                 return chunks
            
#             # Split by separator
#             splits = text.split(separator)
            
#             # If we can't split further or only got one part, continue to next separator
#             if len(splits) <= 1:
#                 continue
            
#             # Check if we can create reasonable chunks with this separator
#             chunks = []
#             current_chunk = ""
            
#             for i, split in enumerate(splits):
#                 split = split.strip()
#                 if not split:
#                     continue
                
#                 # Add separator back (except for the last split)
#                 if i < len(splits) - 1 and separator:
#                     split_with_sep = split + separator
#                 else:
#                     split_with_sep = split
                
#                 # If single split is too large, recursively split it
#                 if len(split) > chunk_size:
#                     # Recursively split this large piece using remaining separators
#                     remaining_separators = separators[separators.index(separator) + 1:]
#                     if remaining_separators:
#                         sub_chunks = _split_recursive(split, remaining_separators, chunk_size, chunk_overlap)
#                         # Add sub_chunks to current_chunk or directly to chunks
#                         for sub_chunk in sub_chunks:
#                             if len(current_chunk) + len(sub_chunk) > chunk_size and current_chunk:
#                                 chunks.append(current_chunk.strip())
#                                 # For overlap, take last chunk_overlap chars from previous chunk
#                                 if chunk_overlap > 0 and chunks and len(chunks[-1]) >= chunk_overlap:
#                                     overlap_text = chunks[-1][-chunk_overlap:]
#                                     current_chunk = overlap_text + " " + sub_chunk
#                                 else:
#                                     current_chunk = sub_chunk
#                             else:
#                                 current_chunk += (" " + sub_chunk) if current_chunk else sub_chunk
#                     else:
#                         # No more separators, force split at character level
#                         if current_chunk:
#                             chunks.append(current_chunk.strip())
#                         # Character-level split
#                         start = 0
#                         while start < len(split):
#                             end = min(start + chunk_size, len(split))
#                             chunk = split[start:end].strip()
#                             if chunk:
#                                 chunks.append(chunk)
#                             start = end - chunk_overlap
#                             if start <= 0:
#                                 start = end
#                         current_chunk = ""
#                 else:
#                     # Check if adding this split would exceed chunk size
#                     potential_chunk = (current_chunk + (" " + split_with_sep) if current_chunk else split_with_sep)
                    
#                     if len(potential_chunk) > chunk_size and current_chunk:
#                         # Finalize current chunk
#                         chunks.append(current_chunk.strip())
                        
#                         # For overlap, take last chunk_overlap chars from previous chunk
#                         if chunk_overlap > 0 and len(current_chunk) >= chunk_overlap:
#                             overlap_text = current_chunk[-chunk_overlap:]
#                             current_chunk = overlap_text + " " + split_with_sep
#                         else:
#                             current_chunk = split_with_sep
#                     else:
#                         current_chunk = potential_chunk
            
#             # Add the last chunk
#             if current_chunk.strip():
#                 chunks.append(current_chunk.strip())
            
#             # If we successfully created chunks, return them
#             if chunks:
#                 return [chunk for chunk in chunks if chunk.strip()]
        
#         # Fallback: if nothing worked, split by character
#         chunks = []
#         start = 0
#         while start < len(text):
#             end = min(start + chunk_size, len(text))
#             chunk = text[start:end].strip()
#             if chunk:
#                 chunks.append(chunk)
#             start = end - chunk_overlap
#             if start <= 0:
#                 start = end
#         return chunks
    
#     chunks = _split_recursive(text.strip(), separators, chunk_size, chunk_overlap)
#     return [chunk for chunk in chunks if chunk.strip()]


@router.post("/vectors/insert")
async def insert_vector(
    request: Dict[str, Any],
    auth=Depends(get_current_api_key)  # returns { "api_key": obj, "subscription": obj }
):

    """
    Insert an embedding for provided text into Pinecone, keyed by doc_id.
    All metadata fields are stored with each chunk in the vector database.

    Input:
    {
      "pdf_text": "...",
      "embedding_provider": "openai",       # Optional: "openai", "voyageai", "cohere" (default: "openai")
      "embedding_model": "text-embedding-3-small",  # Optional: specific model name (uses provider default if not specified)
      "metadata": { 
        "doc_id": "doc_001",                # Required: Document identifier
        "title": "My Document",    # Optional: Document title
        "filename": "document.pdf",         # Optional: PDF filename
        "authors": "John Doe, Jane Smith",  # Optional: Document authors
        "journal": "Journal Name",          # Optional: Journal/publication name
        "publication_date": "2024-01-15",   # Optional: Publication date
        "doi": "10.1234/example",           # Optional: DOI identifier
        "doc.author": "John Doe",           # Optional: Author name (alternative field)
        "doc.category": "research",         # Optional: Category/Topic
        "doc.publishedyear": 2024,          # Optional: Year (integer)
        "doc.priority": 8,                  # Optional: Priority score (integer)
        "part.section_type": "abstract",    # Optional: Section type
        "part.sentiment_score": 0.85,       # Optional: Numeric score
        "part.clause_type": "terms",        # Optional: Legal/contract parts
        "knowledge_base_id": "kb_123",      # Optional: Knowledge base ID
        "user_id": "user_456",              # Optional: User ID
        "study_id": "study_789",            # Optional: Study ID
        "is_eligible": true,                # Optional: Screening eligibility status
        "screening_result_id": "screen_abc" # Optional: Screening result reference
      }
    }
    
    Note: All metadata fields are stored with each chunk in Pinecone, allowing for filtering
    and retrieval based on document title, PDF name, authors, and other metadata fields.
    """
    try:
        pdf_text = (request.get("pdf_text") or "").strip()

        #also return the tokens as well from the database of intern endpoint

        #get the tokens from the database of intern endpoint
        


        print("----------------------------pdf--------------------")
        print(pdf_text)
        print("----------------------------pdf--------------------")

        with open("pdf_text.txt", "w", encoding="utf-8") as f:
            f.write(pdf_text)

        if not pdf_text:
            raise HTTPException(status_code=400, detail="pdf_text is required")

        metadata = request.get("metadata") or {}
        doc_id = metadata.get("doc_id")
        document_title=metadata.get("title","")
        pdf_name=metadata.get("filename","")
        authors=metadata.get("authors","")
        journal=metadata.get("journal","")
        publication_date=metadata.get("publication_date","")
        doi=metadata.get("doi","")

        if not doc_id:
            raise HTTPException(status_code=400, detail="metadata.doc_id is required")

        # Extract embedding model from request
        from config.settings import SUPPORTED_EMBEDDING_PROVIDERS, get_default_embedding_provider

        embedding_provider = request.get("embedding_provider", get_default_embedding_provider())
        embedding_model = request.get("embedding_model", None)
        
        # Validate provider
        if embedding_provider not in SUPPORTED_EMBEDDING_PROVIDERS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported embedding provider: {embedding_provider}. "
                    f"Supported: {', '.join(SUPPORTED_EMBEDDING_PROVIDERS)}"
                ),
            )

        # Extract org/project from API key
        api_key_obj = auth["api_key"]
        subscription = auth["subscription"]
        org_id = api_key_obj.org_id
        project_id = api_key_obj.project_id

        print(f"DEBUG: org_id: {org_id}, project_id: {project_id} , subscription: {subscription}")

        # 🔒 Enforce subscription ingest quota
        if subscription.monthly_limit_ingest is not None:
            if subscription.used_ingest >= subscription.monthly_limit_ingest:
                raise HTTPException(status_code=402, detail="Ingest quota exceeded.")
            
        if subscription.monthly_limit_tokens is not None:
            if subscription.used_tokens >= subscription.monthly_limit_tokens:
                raise HTTPException(status_code=402, detail="Tokens quota exceeded.")

        # ✨ Initialize services using factory (handles all key management automatically)
        try:
            embedding_service, pinecone_service = create_services_from_auth(
                auth=auth,
                embedding_provider=embedding_provider,
                embedding_model=embedding_model
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Service initialization failed: {str(e)}")

        chunks = await _semantic_chunk_text(pdf_text, embedding_service, chunk_size=2500, chunk_overlap=600)

        print("----------------------------chunks--------------------")
        print(chunks)
        print("----------------------------chunks--------------------")
        print("-----------------------------legth---------------------")
        print(len(chunks))
        print("-----------------------------legth---------------------")
        embeddings = await embedding_service.generate_embeddings_batch(chunks)

        # Metadata cleanup - include system metadata + optional user metadata
        safe_metadata = {
            "doc_id": str(doc_id),
            "org_id": str(org_id),
            "project_id": str(project_id),
            "embedding_provider": embedding_provider,
            "embedding_model": embedding_service.model_name,
            "document_title":document_title,
            "pdf_name":pdf_name,
            "authors":authors,
            "journal":journal,
            "publication_date":publication_date,
            "doi":doi


        }

        print("----------------------------safe_metadata--------------------")
        print(safe_metadata)
        print("----------------------------safe_metadata--------------------")
        
        # Add optional custom user metadata (sanitize and validate)
        def _sanitize_metadata_value(value: Any, field: str) -> str:
            """Convert metadata values to strings for Pinecone storage with case normalization"""
            if value is None:
                return ""
            
            # Fields that should be normalized to lowercase (text fields)
            text_fields_to_normalize = [
                "doc.author", 
                "doc.category", 
                "part.section_type", 
                "part.clause_type"
            ] 
            
            if isinstance(value, (int, float)):
                return str(value)
            elif isinstance(value, bool):
                return str(value).lower()
            else:
                # Convert to string first
                str_value = str(value).strip()
                # Normalize case for text fields
                if field in text_fields_to_normalize:
                    return str_value.lower()
                return str_value
        
        # Process custom user metadata (all optional)
        custom_metadata_fields = [
            "doc.author", "doc.category", "doc.publishedyear", "doc.priority",
            "part.section_type", "part.sentiment_score", "part.clause_type","user_id","document_title", "pdf_name",
            # Screening metadata fields
            "is_eligible", "screening_result_id","knowledge_base_id", "study_id",
        ]
        
        for field in custom_metadata_fields:
            if field in metadata:
                safe_metadata[field] = _sanitize_metadata_value(metadata[field], field)
                print(f"DEBUG: Added custom metadata {field}: {safe_metadata[field]}")

        namespace = get_namespace_from_auth(auth)

        # Store in Pinecone
        vector_ids = await pinecone_service.store_pdf_chunks(
            chunk_texts=chunks,
            base_metadata=safe_metadata,
            embeddings=embeddings,
            namespace=namespace,
        )

        # ✅ Increment subscription ingest usage
        db = next(get_db())
        subscription.used_ingest += 1

        #INCREMENT THE TOKEN
        subscription.used_tokens += len(chunks)
        subscription.used_storage_mb += len(chunks)

        llm_model_used="gpt-3.5-turbo"

        print("--------------------------before tokens used................")
        

        # input_tokens = count_tokens_with_tiktoken(pdf_text, llm_model_used)
        # output_tokens = count_tokens_with_tiktoken("", llm_model_used)
        # total_tokens = input_tokens + output_tokens


        
        db.commit()

        # Record token usage
        try:
           total_tokens= record_token_usage(
                db=db,
                api_key_id=api_key_obj.id,
                endpoint="vectors/insert",
                operation_type="insert",
                input_text=pdf_text,
                output_text=""
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
            "message": "stored"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to insert vector: {str(e)}")



