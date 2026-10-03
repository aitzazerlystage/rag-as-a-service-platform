from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import os
import tempfile
import shutil
import random
import uuid
import datetime
import asyncio
import json

from backend.crud import get_current_api_key, record_aggregated_token_usage
from backend.database import get_db
from backend.crud import (
    get_user_by_id, get_organization_by_id, get_project_by_id
)
from backend.models import ProjectUpload
from services.rag_insert_service import insert_text_into_rag
from config.settings import get_default_embedding_provider

router = APIRouter()

@router.post("/vectors/upload")
async def upload_files_for_processing(
    files: List[UploadFile] = File(...),
    insert_to_rag: bool = Form(True),
    metadata: Optional[str] = Form(None),
    embedding_provider: str = Form(get_default_embedding_provider()),
    embedding_model: Optional[str] = Form(None),
    auth=Depends(get_current_api_key),
    db: Session = Depends(get_db)
):
    """Upload, process, and optionally insert files into RAG.
    Requires API key authentication via x-api-key header.

    Organization and project scope are taken from the API key (same as /vectors/insert).

    Parameters:
    - files: List of files to process
    - insert_to_rag: If True (default), insert extracted text into RAG (Pinecone) after processing
    - metadata: Optional JSON string for RAG metadata (e.g. {"title":"My Doc","authors":"..."})
    - embedding_provider: "nomic", "openai", "voyageai", or "cohere" (default: nomic)
    - embedding_model: Optional model name (uses provider default if not specified)

    Supports: PDF, TXT, DOC, DOCX.
    File size limit: 10MB per file.

    Returns processing results, and when insert_to_rag=True, RAG insert results per file.
    """
    # Extract API key and subscription from auth dict
    api_key_obj = auth["api_key"]
    subscription = auth["subscription"]
    user_id = api_key_obj.user_id
    organization_id = api_key_obj.org_id
    project_id = api_key_obj.project_id
    print(f"DEBUG: vectors/upload called with {len(files)} files, user_id={user_id}, org_id={organization_id}, project_id={project_id} (from API key)")
    
    # Validate organization_id exists under user_id
    try:
        user_record = get_user_by_id(db, user_id)
        if not user_record or not user_record.org_id:
            raise HTTPException(
                status_code=403, 
                detail=f"User {user_id} is not assigned to an organization"
            )
        
        if user_record.org_id != organization_id:
            raise HTTPException(
                status_code=403, 
                detail=f"Organization {organization_id} does not match user's organization {user_record.org_id}"
            )
        
        # Verify organization exists
        org = get_organization_by_id(db, organization_id)
        if not org:
            raise HTTPException(
                status_code=404, 
                detail=f"Organization {organization_id} not found"
            )
        
        print(f"✅ Organization {organization_id} validated for user {user_id}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error validating organization: {e}")
        raise HTTPException(status_code=500, detail=f"Error validating organization: {str(e)}")
    
    # Validate project_id exists under organization_id
    try:
        project = get_project_by_id(db, project_id)
        if not project:
            raise HTTPException(
                status_code=404, 
                detail=f"Project {project_id} not found"
            )
        
        if project.org_id != organization_id:
            raise HTTPException(
                status_code=403, 
                detail=f"Project {project_id} does not belong to organization {organization_id}"
            )
        
        print(f"✅ Project {project_id} validated under organization {organization_id}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error validating project: {e}")
        raise HTTPException(status_code=500, detail=f"Error validating project: {str(e)}")

    # Parse optional metadata JSON
    extra_metadata: Dict[str, Any] = {}
    if metadata:
        try:
            extra_metadata = json.loads(metadata) if isinstance(metadata, str) else metadata
        except json.JSONDecodeError:
            print("❌ Upload rejected: metadata must be valid JSON")
            raise HTTPException(status_code=400, detail="metadata must be valid JSON")
    
    if not files:
        print("❌ Upload rejected: No files provided (use multipart field name 'files')")
        raise HTTPException(status_code=400, detail="No files provided")
    
    # File size limit: 10MB
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
    
    # Supported file extensions
    allowed_exts = {".pdf", ".txt", ".doc", ".docx"}
    
    # Validate files
    for file in files:
        # Check file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE:
            detail = (
                f"File {file.filename} exceeds 10MB limit. "
                f"Size: {file_size / (1024*1024):.2f}MB"
            )
            print(f"❌ Upload rejected: {detail}")
            raise HTTPException(status_code=400, detail=detail)
        
        # Check file extension
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in allowed_exts:
            detail = (
                f"File {file.filename} has unsupported type '{ext or '(none)'}'. "
                f"Allowed: {', '.join(sorted(allowed_exts))}"
            )
            print(f"❌ Upload rejected: {detail}")
            raise HTTPException(status_code=400, detail=detail)
    
    results = []
    
    # Enable bounded parallel processing of files
    max_concurrency = int(os.environ.get("UPLOAD_MAX_CONCURRENCY", "3"))
    semaphore = asyncio.Semaphore(max_concurrency)
    
    # Extract the existing per-file logic into a sync helper so we can run it in a thread
    def _process_single_file_sync(file: UploadFile):
        try:
            print(f"DEBUG: Processing file: {file.filename}")
            
            # Generate unique filename
            random_digits = str(random.randint(1000, 9999))
            original_filename = file.filename
            name, ext = os.path.splitext(original_filename)
            new_filename = f"{name}_{random_digits}{ext}"
            
            # Create temporary file
            temp_dir = tempfile.mkdtemp(prefix="file_processing_")
            temp_file_path = os.path.join(temp_dir, new_filename)
            
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            start_time = datetime.datetime.now()
            ext = os.path.splitext(new_filename)[1].lower()
            
            # Import processing functions dynamically to avoid circular imports
            from utils.pdf_processor import run_single_pdf_pipeline
            from utils.document_processor import (
                process_non_pdf_file,
                initialize_document_processor
            )
            
            # Initialize processors with dependencies from fastapi_app
            from backend.api.fastapi_app import (
                text_splitter, OPENAI_API_KEY, LLM_MAX_TOKENS, PINECONE_AVAILABLE,
                DOC_CONVERTER, PictureItem, LLM_MODEL, LLM_TEMPERATURE
            )
            initialize_document_processor(
                text_splitter, DOC_CONVERTER, PictureItem, 
                LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, OPENAI_API_KEY
            )
            
            # Process file based on type
            if ext == ".pdf":
                result = run_single_pdf_pipeline(temp_file_path, max_workers=4, pdf_id=str(uuid.uuid4()), user_id=user_id)
            else:
                print("Running Non-PDF Chain")
                result = process_non_pdf_file(temp_file_path, new_filename)
            
            if not result or not result.get("success", False):
                error_msg = result.get("error", "Unknown processing error") if result else "Processing failed"
                raise Exception(f"Document processing failed: {error_msg}")
            
            end_time = datetime.datetime.now()
            processing_time = end_time - start_time
            
            # Format result (without vector database operations)
            formatted_result = {
                "filename": new_filename,
                "original_filename": original_filename,
                "file_type": ext[1:].upper(),  # Remove dot and uppercase
                "status": "completed",
                "processing_time": str(processing_time),
                "file_size_bytes": os.path.getsize(temp_file_path),
                "stats": {
                    "text_length": result.get("stats", {}).get("text_length", 0),
                    "table_count": result.get("stats", {}).get("table_count", 0),
                    "image_count": result.get("stats", {}).get("image_count", 0),
                    "llm_tokens": result.get("llm_tokens", 0) if "llm_tokens" in result else result.get("stats", {}).get("llm_tokens", 0),  # Check result root first, then stats
                    "processing_time": str(processing_time)
                },
                "extracted_text": result.get("final_text", ""),
                "full_text_length": len(result.get("final_text", ""))
            }
            
            print(f"DEBUG: Successfully processed {new_filename}")
            return formatted_result
            
        except Exception as e:
            print(f"ERROR processing {file.filename}: {e}")
            error_result = {
                "filename": file.filename,
                "original_filename": file.filename,
                "file_type": os.path.splitext(file.filename)[1][1:].upper() if os.path.splitext(file.filename)[1] else "UNKNOWN",
                "status": "failed",
                "error": str(e),
                "processing_time": "0:00:00",
                "file_size_bytes": 0,
                "stats": {
                    "text_length": 0,
                    "table_count": 0,
                    "image_count": 0,
                    "processing_time": "0:00:00"
                },
                "extracted_text": "",
                "full_text_length": 0
            }
            return error_result
        
        finally:
            # Cleanup temporary files
            try:
                if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                if 'temp_dir' in locals() and os.path.exists(temp_dir) and os.path.isdir(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as cleanup_error:
                print(f"WARNING: Could not clean up temp file: {cleanup_error}")
    
    # Async wrapper for the sync function with semaphore control
    async def _process_file_with_limit(file: UploadFile):
        async with semaphore:
            # Run the sync function in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _process_single_file_sync, file)
    
    # Process all files in parallel with concurrency limit
    print(f"DEBUG: Starting parallel processing of {len(files)} files with max concurrency: {max_concurrency}")
    tasks = [asyncio.create_task(_process_file_with_limit(file)) for file in files]
    task_results = await asyncio.gather(*tasks, return_exceptions=False)
    results.extend(task_results)
    
    # Insert into RAG for each successfully processed file (when insert_to_rag=True)
    if insert_to_rag:
        for result in results:
            if result.get("status") == "completed" and result.get("extracted_text"):
                pdf_text = result["extracted_text"]
                original_filename = result.get("original_filename", result.get("filename", "document"))
                doc_id = str(uuid.uuid4())
                file_metadata = {
                    "doc_id": doc_id,
                    "filename": original_filename,
                    "title": original_filename,
                    **extra_metadata,
                }
                try:
                    insert_result = await insert_text_into_rag(
                        pdf_text=pdf_text,
                        metadata=file_metadata,
                        auth=auth,
                        db=db,
                        embedding_provider=embedding_provider,
                        embedding_model=embedding_model,
                        endpoint_suffix="vectors/upload",
                    )
                    result["insert_result"] = insert_result
                    if insert_result and isinstance(insert_result, dict) and "error" not in insert_result:
                        result["doc_id"] = doc_id
                except HTTPException:
                    raise
                except Exception as e:
                    result["insert_result"] = {"error": str(e), "status": "failed"}
                    result["status"] = "completed_with_insert_error"
                    print(f"WARNING: Insert into RAG failed for {original_filename}: {e}")
    
    print(f"DEBUG: vectors/upload completed with {len(results)} results")
    
    # Aggregate token usage from all processing results
    total_llm_tokens = 0
    for result in results:
        if result.get("status") == "completed":
            # Check for LLM tokens in stats first, then in result root
            stats = result.get("stats", {})
            if "llm_tokens" in stats:
                total_llm_tokens += stats["llm_tokens"]
                print(f"📊 File {result.get('filename', 'unknown')} used {stats['llm_tokens']} LLM tokens (from stats)")
            elif "llm_tokens" in result:
                total_llm_tokens += result["llm_tokens"]
                print(f"📊 File {result.get('filename', 'unknown')} used {result['llm_tokens']} LLM tokens (from result)")
    
    # Record total token usage for the entire upload operation
    if total_llm_tokens > 0:
        try:
            record_aggregated_token_usage(
                db=db,
                api_key_id=api_key_obj.id,
                endpoint="vectors/upload",
                operation_type="upload_processing",
                total_tokens=total_llm_tokens
            )
            print(f"📊 Total LLM tokens used in upload processing: {total_llm_tokens}")
        except Exception as e:
            print(f"WARNING: Failed to record token usage for upload: {e}")
    
    insert_count = sum(
        1 for r in results
        if r.get("insert_result") and "error" not in r.get("insert_result", {})
    )

    for result in results:
        if result.get("status") != "completed":
            continue
        orig = result.get("original_filename") or result.get("filename") or "unknown"
        ir = result.get("insert_result") or {}
        rag_ok = bool(insert_to_rag and ir and "error" not in ir)
        try:
            db.add(
                ProjectUpload(
                    project_id=project_id,
                    org_id=organization_id,
                    user_id=user_id,
                    original_filename=orig,
                    doc_id=result.get("doc_id"),
                    rag_inserted=rag_ok,
                )
            )
        except Exception as log_err:
            print(f"WARNING: project_upload log failed for {orig}: {log_err}")
    try:
        db.commit()
    except Exception as commit_err:
        print(f"WARNING: project_upload commit: {commit_err}")
        db.rollback()

    return {
        "results": results,
        "total_files": len(files),
        "successful_files": len([r for r in results if r["status"] == "completed"]),
        "failed_files": len([r for r in results if r["status"] == "failed"]),
        "inserted_to_rag": insert_count,
        "total_llm_tokens": total_llm_tokens,
        "status": "completed",
        "validated_ids": {
            "user_id": user_id,
            "organization_id": organization_id,
            "project_id": project_id
        }
    }
