import os
import logging
from typing import Dict, Any, List, Optional
from pinecone import Pinecone, ServerlessSpec
import uuid
import re
import logging
from typing import List, Dict, Any, Optional


logger = logging.getLogger(__name__)

class PineconeService:
    def __init__(self, pinecone_api_key: str, pinecone_index_name: str, pinecone_env: str):
        self.api_key = pinecone_api_key
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY is required")
        self.index_name = pinecone_index_name
        self.env = pinecone_env
        self.pc = Pinecone(api_key=self.api_key)
        self.dimension = 1024  # OpenAI text-embedding-3-small dimension
        self._ensure_index_exists()
    
    def _ensure_index_exists(self):
        """Ensure the Pinecone index exists, create if it doesn't"""
        try:
            # Check if index exists
            existing_indexes = [index.name for index in self.pc.list_indexes()]
            
            if self.index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self.env
                    )
                )
                logger.info(f"Successfully created Pinecone index: {self.index_name}")
            else:
                logger.info(f"Pinecone index {self.index_name} already exists")
                
        except Exception as e:
            logger.error(f"Error ensuring Pinecone index exists: {str(e)}")
            raise
    
    def get_index(self):
        """Get the Pinecone index"""
        return self.pc.Index(self.index_name)
    
    def get_index_stats(self):
        """Get statistics about the Pinecone index, returning JSON-serializable data"""
        try:
            index = self.get_index()
            stats = index.describe_index_stats()

            # Safely extract and convert namespaces into a serializable dict
            namespaces_serializable: Dict[str, Any] = {}
            raw_namespaces = getattr(stats, "namespaces", None)
            if isinstance(raw_namespaces, dict):
                for namespace, summary in raw_namespaces.items():
                    vector_count = getattr(summary, "vector_count", None)
                    # Fallback: if summary has to_dict, use it
                    if vector_count is None and hasattr(summary, "to_dict"):
                        try:
                            summary_dict = summary.to_dict()
                            vector_count = summary_dict.get("vector_count")
                        except Exception:
                            vector_count = None
                    namespaces_serializable[namespace] = {"vector_count": vector_count}
            elif raw_namespaces is not None:
                # Last resort: try to coerce to string
                namespaces_serializable = {"_raw": str(raw_namespaces)}

            # Some SDKs use different property names; use getattr with defaults
            total_vector_count = getattr(stats, "total_vector_count", None)
            if total_vector_count is None:
                total_vector_count = getattr(stats, "totalVectorCount", None)

            dimension = getattr(stats, "dimension", None)
            if dimension is None:
                dimension = getattr(stats, "vector_dimension", None)

            index_name = getattr(stats, "name", self.index_name)

            return {
                "index_name": index_name,
                "dimension": dimension,
                "total_vector_count": total_vector_count,
                "namespaces": namespaces_serializable,
            }
        except Exception as e:
            logger.error(f"Error getting index stats: {str(e)}")
            raise
    
    async def store_pdf_text(
        self, 
        pdf_text: str, 
        metadata: Dict[str, Any],
        embedding: List[float],
        namespace: Optional[str] = None,
    ) -> str:
        """
        Store PDF text in Pinecone with metadata
        
        Args:
            pdf_text: The text content of the PDF
            metadata: Dictionary containing doc_id, org_id, project_id and other metadata
            embedding: Vector embedding of the PDF text
            
        Returns:
            str: The ID of the stored vector (same as pdf_id)
        """
        try:
            index = self.get_index()
            
            # Use doc_id as the vector ID for consistency
            doc_id = metadata.get("doc_id")
            if not doc_id:
                raise ValueError("doc_id is required in metadata to use as vector ID")
            
            vector_id = str(doc_id)
            
            # Prepare metadata (keep all metadata including doc_id)
            vector_metadata = {
                "pdf_text": pdf_text[:1000],  # Store first 1000 chars as preview
                "text_length": len(pdf_text),
                "content_type": "doc",
                **metadata
            }
            
            # Upsert the vector
            index.upsert(
                vectors=[{
                    "id": vector_id,
                    "values": embedding,
                    "metadata": vector_metadata
                }],
                namespace=namespace,
            )
            
            logger.info(f"Successfully stored PDF text in Pinecone with ID: {vector_id}")
            return vector_id
            
        except Exception as e:
            logger.error(f"Error storing PDF text in Pinecone: {str(e)}")
            raise


    # async def keyword_search(
    #     self,
    #     query_text: str,
    #     filter_metadata: Optional[Dict[str, Any]] = None,
    #     top_k: int = 10,
    #     namespace: Optional[str] = None
    # ) -> List[Dict[str, Any]]:
    #     """
    #     Fallback keyword-based search when no semantic matches are found.
    #     Scans stored PDF text chunks in Pinecone metadata and returns those 
    #     containing any of the query keywords.
    #     """
    #     try:
    #         index = self.get_index()

    #         # 🧩 1. Extract keywords (ignore very short words)
    #         keywords = [word.lower() for word in re.findall(r'\b\w+\b', query_text) if len(word) > 3]
    #         if not keywords:
    #             logger.warning("Keyword search skipped — no valid keywords found.")
    #             return []

    #         # 🧩 2. Fetch all vectors that match filter (broad scan)
    #         fetch_kwargs = {"include_metadata": True}
    #         if namespace:
    #             fetch_kwargs["namespace"] = namespace
    #         if filter_metadata:
    #             fetch_kwargs["filter"] = filter_metadata

    #         results = index.query(
    #             vector=[0] * 1536,  # dummy vector; just to trigger metadata fetch
    #             top_k=200,          # limit: scan top 200 stored vectors
    #             include_metadata=True,
    #             namespace=namespace
    #         )

    #         # 🧩 3. Match keyword occurrences inside metadata["pdf_text"]
    #         matches = []
    #         for match in results.matches:
    #             text = match.metadata.get("pdf_text", "").lower()
    #             if any(keyword in text for keyword in keywords):
    #                 match_score = sum(text.count(k) for k in keywords)
    #                 matches.append({
    #                     "id": match.id,
    #                     "score": match_score,
    #                     "metadata": match.metadata
    #                 })

    #         # 🧩 4. Sort and truncate
    #         matches = sorted(matches, key=lambda m: m["score"], reverse=True)[:top_k]

    #         logger.info(f"Keyword search found {len(matches)} matches for query '{query_text}'")
    #         return matches

    #     except Exception as e:
    #         logger.error(f"Error during keyword search: {str(e)}")
    #         return []

    
    async def search_similar_pdfs(
        self, 
        query_embedding: List[float], 
        filter_metadata: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar PDFs in Pinecone
        
        Args:
            query_embedding: Vector embedding of the search query
            filter_metadata: Optional metadata filters
            top_k: Number of results to return
            
        Returns:
            List of similar PDF documents with scores
        """
        try:
            index = self.get_index()
            
            # Prepare query
            query_kwargs = {
                "vector": query_embedding,
                "top_k": top_k,
                "include_metadata": True
            }
            
            # Add filter if provided
            if filter_metadata:
                query_kwargs["filter"] = filter_metadata
            
            # Query the index
            if namespace:
                query_kwargs["namespace"] = namespace
            results = index.query(**query_kwargs)
            
            # Format results
            formatted_results = []
            for match in results.matches:
                formatted_results.append({
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata
                })
            
            logger.info(f"Found {len(formatted_results)} similar PDFs")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching Pinecone: {str(e)}")
            raise
    
    async def delete_pdf_vectors(self, chunk_ids: List[str], filter_metadata: Dict[str, Any], namespace: Optional[str] = None) -> int:
        """
        Delete PDF vectors by chunk IDs and/or metadata filter
        
        Args:
            chunk_ids: List of chunk IDs to delete
            filter_metadata: Metadata filter for additional validation
            namespace: Optional namespace
            
        Returns:
            int: Number of vectors deleted
        """
        try:
            index = self.get_index()

            # Strip keys used for API validation; optional keys may be absent (e.g. dashboard delete by doc_id only).
            filter_metadata.pop("project_id", None)
            filter_metadata.pop("org_id", None)
            filter_metadata.pop("knowledge_base_id", None)
            filter_metadata.pop("study_id", None)

            if chunk_ids and filter_metadata:
                # Case 1: Delete specific PDF vectors by their chunk IDs with metadata validation
                # First, get the vectors to validate they match the filter
                results = index.fetch(ids=chunk_ids, namespace=namespace)
                valid_ids = []
                
                for chunk_id in chunk_ids:
                    if chunk_id in results.vectors:
                        vector_metadata = results.vectors[chunk_id].metadata
                        # Check if metadata matches the filter
                        matches_filter = True
                        for key, value in filter_metadata.items():
                            if key not in vector_metadata or vector_metadata[key] != value:
                                matches_filter = False
                                break
                        
                        if matches_filter:
                            valid_ids.append(chunk_id)
                        else:
                            logger.warning(f"Chunk {chunk_id} does not match filter criteria")
                
                if valid_ids:
                    delete_response = index.delete(ids=valid_ids, namespace=namespace)
                    deleted_count = len(valid_ids)
                    logger.info(f"Deleted {deleted_count} vectors from Pinecone by chunk IDs with validation: {valid_ids}")
                else:
                    deleted_count = 0
                    logger.warning("No chunks matched the filter criteria")
                    
            elif not chunk_ids and filter_metadata:
                # Case 2: Delete all vectors matching metadata filter (for study-level deletion)
                # Query Pinecone to find vectors with matching metadata
                query_result = index.query(
                    vector=[0.0] * self.dimension,  # Dummy vector
                    filter=filter_metadata,
                    top_k=10000,  # Get all matching vectors
                    include_metadata=True,
                    namespace=namespace
                )
                
                # Extract vector IDs from results
                matching_ids = [match.id for match in query_result.matches]
                
                if matching_ids:
                    index.delete(ids=matching_ids, namespace=namespace)
                    deleted_count = len(matching_ids)
                    logger.info(f"Deleted {deleted_count} vectors from Pinecone by metadata filter: {matching_ids}")
                else:
                    deleted_count = 0
                    logger.warning("No vectors matched the metadata filter criteria")
                    
            elif chunk_ids:
                # Case 3: Delete specific vectors without metadata validation
                index.delete(ids=chunk_ids, namespace=namespace)
                deleted_count = len(chunk_ids)
                logger.info(f"Deleted {deleted_count} vectors from Pinecone by chunk IDs: {chunk_ids}")
                
            else:
                raise ValueError("Either chunk_ids or filter_metadata must be provided")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting vectors from Pinecone: {str(e)}")
            raise 

    async def store_pdf_chunks(
        self,
        chunk_texts: List[str],
        base_metadata: Dict[str, Any],
        embeddings: List[List[float]],
        namespace: Optional[str] = None,
    ) -> List[str]:
        """
        Store multiple text chunks for a single document in Pinecone.

        Args:
            chunk_texts: List of chunk strings
            base_metadata: Shared metadata containing at least doc_id, org_id, project_id
            embeddings: Embedding per chunk (must match chunk_texts length)
            namespace: Optional namespace to isolate per org/project

        Returns:
            List[str]: Vector IDs stored for each chunk
        """
        try:
            if len(chunk_texts) != len(embeddings):
                raise ValueError("chunk_texts and embeddings must have the same length")

            index = self.get_index()

            doc_id = base_metadata.get("doc_id")
            if not doc_id:
                raise ValueError("doc_id is required in metadata to use as vector ID base")

            total_chunks = len(chunk_texts)
            vectors = []
            vector_ids: List[str] = []
            for i, (chunk, vector) in enumerate(zip(chunk_texts, embeddings)):
                vector_id = f"{doc_id}-{i}"
                vector_ids.append(vector_id)
                vector_metadata = {
                    "pdf_text": chunk[:7000],
                    "text_length": len(chunk),
                    "content_type": "doc_chunk",
                    "chunk_index": i,
                    "total_chunks": total_chunks,
                    **base_metadata,
                }
                vectors.append({
                    "id": vector_id,
                    "values": vector,
                    "metadata": vector_metadata,
                })

            # Upsert in a single call (or batch in reasonable sizes)
            index.upsert(vectors=vectors, namespace=namespace)
            logger.info(f"Successfully stored {len(vectors)} chunks in Pinecone (namespace={namespace})")
            return vector_ids
        except Exception as e:
            logger.error(f"Error storing PDF chunks in Pinecone: {str(e)}")
            raise

    async def document_exists(self, doc_id: str, org_id: str, project_id: str, namespace: Optional[str] = None) -> bool:
        """
        Check if a document exists in Pinecone by querying for any vectors with matching doc_id metadata.
        This method is robust and works regardless of which chunks exist or are deleted.
        
        Args:
            doc_id: The document ID to check
            org_id: Organization ID to verify document ownership
            project_id: Project ID to verify document ownership
            namespace: Optional namespace to check in
            
        Returns:
            bool: True if document exists and belongs to the org/project, False otherwise
        """
        try:
            index = self.get_index()
            
            # Query for any vectors with this doc_id in metadata
            query_result = index.query(
                vector=[0.0] * self.dimension,  # Dummy vector
                filter={
                    "doc_id": doc_id,
                    "org_id": org_id,
                    "project_id": project_id
                },
                top_k=1,  # We only need to know if ANY exist
                include_metadata=True,
                namespace=namespace
            )
            
            # If we found any matches, the document exists
            exists = len(query_result.matches) > 0
            
            if exists:
                logger.info(f"Document {doc_id} found with {len(query_result.matches)} chunks")
            else:
                logger.info(f"Document {doc_id} not found")
                
            return exists
            
        except Exception as e:
            logger.error(f"Error checking document existence for {doc_id}: {e}")
            # Fail-safe: treat as not existing to avoid false positives
            return False