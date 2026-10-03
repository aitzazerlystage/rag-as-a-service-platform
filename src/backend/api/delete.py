from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from backend.crud import get_current_api_key
from services.service_factory import create_pinecone_service, get_namespace_from_auth

router = APIRouter()

@router.post("/vectors/delete")
async def delete_vectors(
    request: Dict[str, Any],
    auth=Depends(get_current_api_key)  # returns { "api_key": obj, "subscription": obj }
):
    """Delete vectors from Pinecone by their IDs, study_id, or doc_id with optional namespace.

    This uses the existing PineconeService.delete_pdf_vectors which validates
    the provided IDs against a metadata filter before deletion.
    
    org_id and project_id are extracted from the authenticated API key.

    Input:
    {
      "chunk_ids": ["doc_001", "doc_001-0", "doc_001-1"],  # Optional: specific chunk IDs to delete
      "study_id": "68d19b117f6d452ef5943f92",  # Optional: delete all vectors with this study_id
      "doc_id": "doc_001",  # Optional: delete all chunks belonging to this document
      "knowledge_base_id": "68d1984d7f6d452ef5943f91",  # Optional: knowledge base ID to filter by
      "filter_metadata": { "additional": "metadata" },  # Optional additional metadata
      "delete_all": false  # when true, deletes all vectors in that project's namespace
    }

    Note: Either chunk_ids, study_id, or doc_id is required when delete_all is false.
    If chunk_ids are provided, they take precedence over study_id/doc_id.
    study_id and doc_id are mutually exclusive - only one can be provided.

    Output:
    { "deleted_count": 2, "namespace": "org_001-proj_001", "study_id": "68d19b117f6d452ef5943f92" }
    """
    try:
        chunk_ids = request.get("chunk_ids") or []
        knowledge_base_id = request.get("knowledge_base_id")
        filter_metadata = request.get("filter_metadata") or {}
        delete_all = bool(request.get("delete_all", False))
        study_id = request.get("study_id")
        doc_id = request.get("doc_id")

        # knowledge_base_id is optional - only add to filter if provided

        if not delete_all:
            if not isinstance(chunk_ids, list):
                raise HTTPException(status_code=400, detail="chunk_ids must be a list")
            if not chunk_ids and not study_id and not doc_id:
                raise HTTPException(status_code=400, detail="Either chunk_ids, study_id, or doc_id is required when delete_all is false")
            
            # Validate that study_id and doc_id are not both provided
            if study_id and doc_id:
                raise HTTPException(status_code=400, detail="study_id and doc_id are mutually exclusive - only one can be provided")

        # Extract org_id and project_id from API key (like insert endpoint)
        api_key_obj = auth["api_key"]
        org_id = api_key_obj.org_id
        project_id = api_key_obj.project_id

        # Derive namespace from API key
        namespace = get_namespace_from_auth(auth)

        # Add knowledge_base_id to filter metadata only if provided
        if knowledge_base_id:
            filter_metadata["knowledge_base_id"] = knowledge_base_id
        
        # Add org_id and project_id to filter metadata for additional scoping
        # This ensures deletion is always scoped to the authenticated user's org/project
        filter_metadata["org_id"] = str(org_id)
        filter_metadata["project_id"] = str(project_id)
        
        # Add study_id or doc_id to filter metadata if provided and no chunk_ids are specified
        if study_id and not chunk_ids:
            filter_metadata["study_id"] = study_id
        elif doc_id and not chunk_ids:
            filter_metadata["doc_id"] = doc_id

        # ✨ Initialize Pinecone service using factory (handles all key management automatically)
        try:
            pinecone_service = create_pinecone_service(auth=auth)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Service initialization failed: {str(e)}")

        # If delete_all flag is set, delete everything in namespace
        if delete_all:
            try:
                index = pinecone_service.get_index()
                # Delete all vectors in the derived namespace
                index.delete(deleteAll=True, namespace=namespace)
                return {
                    "deleted_all": True,
                    "namespace": namespace,
                    "message": f"All vectors deleted in namespace '{namespace}'"
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to delete all vectors in namespace {namespace}: {str(e)}")

        # Otherwise delete specific chunk_ids with metadata validation
        # If chunk_ids are provided, ignore study_id/doc_id and delete specific chunks
        # If only study_id or doc_id is provided, use empty chunk_ids and let metadata filtering handle it
        chunk_ids_to_delete = chunk_ids if chunk_ids else []
        
        deleted_count = await pinecone_service.delete_pdf_vectors(
            chunk_ids=chunk_ids_to_delete,
            filter_metadata=filter_metadata,
            namespace=namespace,
        )

        return {
            "deleted_all": False,
            "deleted_count": int(deleted_count),
            "namespace": namespace,
            "study_id": study_id if study_id else None,
            "doc_id": doc_id if doc_id else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete vectors: {str(e)}")
