
"""PDF Processing API with FAISS/Pinecone Vector Database and LangGraph-Powered Chat

This FastAPI application enables users to:
- Register/Login with full name, email, password
- Upload PDFs and extract text, tables, images
- Process PDF content using an advanced NLP pipeline
- Store document chunks in FAISS or Pinecone vector databases
- Perform semantic search and chat using LangChain and LangGraph
- Manage user-specific threads, messages, and permissions
- Support multi-PDF unified querying and selective PDF chat
- Handle multiple document types (PDF, DOC, DOCX) via Docling
- Provide system status checks

The system integrates with OpenAI embeddings, uses SQLite for metadata persistence,
and supports scalable, thread-safe operations with UUID-based identifiers.


- Register/Login with full name, email, password
- Upload PDFs and extract text, tables, images
- Process PDF content using an NLP pipeline
- Store chunks in FAISS vector databases
- Perform semantic search and chat (single/multi/unified PDF)
- Support per-thread PDF selection
- Full JWT-based authentication and access control
- Thread and data encapsulation (no cross-user access)

Uses: SQLite, OpenAI embeddings, LangChain, LangGraph, bcrypt, JWT
"""


from dotenv import load_dotenv
load_dotenv()

# ================================
# Core Imports and Configuration
# ================================

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import tempfile
import shutil
from typing import List, Dict, Any, Optional
import json
import datetime
import uuid
import base64
import mimetypes
import io
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session
from backend.models import Thread
from backend.models import PDF
from services.embedding_service import EmbeddingService
from services.pinecone_service import PineconeService

# Import API modules to register their endpoints
# from backend.api import insert

# Import the existing PDF processing functions
from utils.pdf_processor import (
    run_single_pdf_pipeline,
    VECTOR_DB_DIR,
    OUTPUT_DIR,
    cleanup_images_folder,
)

# LangChain & Vector Store for vector storage and retrieval
from langchain.text_splitter import RecursiveCharacterTextSplitter
from config.chunking_embeddings import get_chunking_embeddings
# from langchain_openai import OpenAIEmbeddings  # default via get_chunking_embeddings()
# from langchain_openai import ChatOpenAI  # replaced by local Ollama via config.llm_factory
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
# Import Pinecone components
try:
    from langchain_pinecone import PineconeVectorStore
    PINECONE_AVAILABLE = True
except ImportError:
    PineconeVectorStore = None
    PINECONE_AVAILABLE = False

# Import LangGraph workflow functions for stateful conversational AI
from backend.core.langgraph_workflow import (
    create_chat_workflow,
    create_unified_chat_workflow,
    create_llm_only_chat_workflow,
    get_checkpointer,
    get_unified_pinecone_vector_store,
    get_unified_faiss_vector_store
)

# Import configuration constants (e.g., API keys, chunk sizes)
from config.settings import (
    OPENAI_API_KEY,
    VECTOR_DB_CHUNK_SIZE,
    VECTOR_DB_CHUNK_OVERLAP,
    get_vector_db_type,
    get_pinecone_api_key,
    get_pinecone_environment,
    get_pinecone_index_name,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS
)

# Import database and CRUD functions (lazy import to avoid circular dependency)
def get_db():
    """Lazy import to avoid circular dependency"""
    from backend.database import get_db as _get_db
    yield from _get_db()

def create_tables():
    """Lazy import to avoid circular dependency"""
    from backend.database import create_tables as _create_tables
    return _create_tables()
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
    record_token_usage, record_aggregated_token_usage, get_current_api_key
) 

from backend.models import Api_key, Tokens

# Import document processing functions
from utils.document_processor import (
    process_non_pdf_file,
    initialize_document_processor
)

# Optional Docling import for non-PDF (DOC/DOCX) conversion
try:
    from docling.document_converter import DocumentConverter
    try:
        from docling_core.types.doc import PictureItem
    except Exception:
        PictureItem = None
    DOC_CONVERTER = DocumentConverter()
except Exception:
    # If docling is unavailable, ensure both are defined to avoid NameError
    PictureItem = None
    DOC_CONVERTER = None

# Database initialization will be handled by SQLAlchemy



# Import random for filename generation
import random

# ================================
# Recency Filtering Configuration
# ================================

# Recency filtering configuration for chat endpoint
RECENCY_FILTER_ENABLED = True
MAX_DOCUMENTS_PER_CHAT = 2
PRIORITIZE_RESUMES = True


# ================================
# FastAPI App Initialization
# ================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="PDF Chatbot API",
    description="API for uploading PDFs, processing content, and chatting with documents.",
    version="1.0.0"
)

# ✅ List of allowed origins
origins = [
    "https://chatbot-frontend-updated.onrender.com",  # Your deployed frontend
    "http://localhost:3000",                      # For local development
    "http://localhost:5173/"
]

# ✅ Configure CORS properly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
from backend.api.insert import router as insert_router
from backend.api.query import router as query_router
from backend.api.generate_api_key import router as generate_api_key_router
from backend.api.upload import router as upload_router
from backend.api.delete import router as delete_router
from backend.api.projects_create import router as projects_create_router
from backend.api.signup_login import router as signup_login_router
from backend.api.dashboard_usage import router as dashboard_usage_router

app.include_router(signup_login_router, tags=["Auth"])
app.include_router(insert_router, prefix="/api", tags=["Vectors"])
app.include_router(query_router, prefix="/api", tags=["Vectors"])
app.include_router(generate_api_key_router, prefix="/api", tags=["Vectors"])
app.include_router(upload_router, prefix="/api", tags=["Vectors"])
app.include_router(delete_router, prefix="/api", tags=["Vectors"])
app.include_router(projects_create_router, prefix="/api", tags=["Projects"])
app.include_router(dashboard_usage_router, prefix="/api", tags=["Dashboard"])



# ================================
# Global Embedding and Text Splitter Configuration
# ================================

embeddings = get_chunking_embeddings()

from langchain_experimental.text_splitter import SemanticChunker
text_splitter = SemanticChunker(
    embeddings=embeddings,
    buffer_size=1,  # Number of sentences to combine
    add_start_index=True
)

# Initialize document processor with dependencies
initialize_document_processor(
    text_splitter, DOC_CONVERTER, PictureItem, 
    LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, OPENAI_API_KEY
)

# ================================
# Utility Functions: Database Management
# ================================

# Initialize database tables using SQLAlchemy
create_tables()

# Verify vector database configuration
vector_db_type = get_vector_db_type()
print(f"DEBUG: System configured to use vector database type: {vector_db_type}")

if vector_db_type == "pinecone":
    if not PINECONE_AVAILABLE:
        print("WARNING: Pinecone is configured but not available. Install 'langchain-pinecone' to use Pinecone.")
        print("ERROR: System cannot start with Pinecone configuration but no Pinecone support.")
        print("Please either:")
        print("  1. Install 'langchain-pinecone' package, or")
        print("  2. Set VECTOR_DB_TYPE=local in your environment")
        import sys
        sys.exit(1)
    else:
        print(f"DEBUG: Pinecone is available and configured")
        print(f"DEBUG: Pinecone index: {get_pinecone_index_name()}")
        print(f"DEBUG: Pinecone environment: {get_pinecone_environment()}")
        print(f"DEBUG: Pinecone API key: {get_pinecone_api_key()[:10]}..." if get_pinecone_api_key() else "Not set")
        
        # Verify Pinecone index exists
        try:
            import pinecone
            pc = pinecone.Pinecone(api_key=get_pinecone_api_key())
            index_name = get_pinecone_index_name()
            if index_name not in [idx.name for idx in pc.list_indexes()]:
                print(f"ERROR: Pinecone index '{index_name}' does not exist!")
                print(f"Available indexes: {[idx.name for idx in pc.list_indexes()]}")
                print("Please create the index or update PINECONE_INDEX_NAME in your configuration.")
                import sys
                sys.exit(1)
            else:
                print(f"✅ Pinecone index '{index_name}' verified and accessible")
        except Exception as e:
            print(f"ERROR verifying Pinecone index: {e}")
            import sys
            sys.exit(1)
else:
    print(f"DEBUG: Using local FAISS vector database")

# ================================
# Utility Functions: Authentication
# ================================

from backend.api.auth import SECRET_KEY, ALGORITHM, decode_access_token

def get_current_user(request: Request, db: Session = Depends(get_db)) -> dict:
    """Extract current user from JWT token in Authorization header."""
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = token.split(" ")[1]
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_info = get_user_info(db, user_id)
    if not user_info:
        raise HTTPException(status_code=401, detail="User not found")
    return user_info

def get_current_user_from_id(user_id: str, db: Session) -> dict:
    """Get current user from user ID."""
    return get_user_info(db, user_id)

# ================================
# Authentication Dependency
# ================================

def check_pdf_exists(filename: str, user_id: str, db: Session = Depends(get_db)) -> bool:
    """Check if a user already uploaded a PDF with this filename.
    Allows same filename for different users."""
    print(f"DEBUG: check_pdf_exists called with filename={filename}, user_id={user_id}")
    try:
        from backend.crud import check_pdf_exists as crud_check_pdf_exists
        exists = crud_check_pdf_exists(db, filename, user_id)
        print(f"DEBUG: check_pdf_exists returning {exists}")
        return exists
    except Exception as e:
        print(f"ERROR in check_pdf_exists: {e}")
        return False

def get_existing_pdf_data(filename: str, user_id: str, db: Session = Depends(get_db)) -> dict:
    """Get full data for an existing PDF by filename and user_id."""
    print(f"DEBUG: get_existing_pdf_data called with filename={filename}, user_id={user_id}")
    try:
        from backend.crud import get_existing_pdf_data as crud_get_existing_pdf_data
        pdf_data = crud_get_existing_pdf_data(db, filename, user_id)
        print(f"DEBUG: get_existing_pdf_data returning data: {bool(pdf_data)}")
        return pdf_data
    except Exception as e:
        print(f"ERROR in get_existing_pdf_data: {e}")
        return {}



def validate_user_pdf(pdf_id: str, user_id: str, db: Session = Depends(get_db)) -> bool:
    """Check if a PDF belongs to the specified user."""
    print(f"DEBUG: validate_user_pdf called with pdf_id={pdf_id}, user_id={user_id}")
    try:
        from backend.crud import validate_user_pdf as crud_validate_user_pdf
        is_valid = crud_validate_user_pdf(db, pdf_id, user_id)
        print(f"DEBUG: validate_user_pdf returning {is_valid}")
        return is_valid
    except Exception as e:
        print(f"ERROR in validate_user_pdf: {e}")
        return False

def validate_thread_pdf_access(thread_id: str, pdf_id: str, user_id: str, db: Session = Depends(get_db)) -> bool:
    """Check if a user can access a PDF in a specific thread."""
    print(f"DEBUG: validate_thread_pdf_access called with thread_id={thread_id}, pdf_id={pdf_id}, user_id={user_id}")
    try:
        from backend.crud import validate_thread_pdf_access as crud_validate_thread_pdf_access
        has_access = crud_validate_thread_pdf_access(db, thread_id, pdf_id, user_id)
        print(f"DEBUG: validate_thread_pdf_access returning {has_access}")
        return has_access
    except Exception as e:
        print(f"ERROR in validate_thread_pdf_access: {e}")
        return False


from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
import json

def get_thread_pdfs_with_recency_filter(
    db: Session,
    thread_id: str,
    user_id: str,
    max_documents: int = 2,
    prioritize_resumes: bool = True
) -> List[str]:
    """
    Get PDF IDs from a thread with recency filtering and optional resume prioritization.
    Uses SQLAlchemy instead of raw sqlite3.
    """

    print(f"🔍 RECENCY FILTER: Getting {max_documents} most recent documents from thread {thread_id}")

    # Step 1: Get all PDFs linked to the thread
    all_pdf_ids = get_thread_pdfs(db,thread_id, user_id)
    if not all_pdf_ids:
        print(f"🔒 No PDFs found in thread {thread_id}")
        return []

    # Step 2: Fetch PDF details from the database via SQLAlchemy
    pdf_details = db.query(PDF).filter(
        PDF.id.in_(all_pdf_ids),
        PDF.user_id == user_id
    ).order_by(desc(PDF.upload_time)).all()

    if not pdf_details:
        print(f"⚠️ No PDF details found for IDs: {all_pdf_ids}")
        return []

    print(f"📄 Found {len(pdf_details)} PDFs in thread, sorting by upload time")

    # Step 3: Prioritize resumes if requested
    if prioritize_resumes:
        resumes = []
        other_docs = []

        for pdf in pdf_details:
            filename_lower = pdf.filename.lower()
            is_resume = any(keyword in filename_lower for keyword in [
                "resume", "cv", "curriculum vitae", "bio", "profile"
            ]) or filename_lower.endswith(".pdf")

            if is_resume:
                resumes.append(pdf)
            else:
                other_docs.append(pdf)

        print(f"📋 Resumes found: {len(resumes)}, Other docs: {len(other_docs)}")

        # Take the most recent resumes first
        selected_pdfs = [pdf.id for pdf in resumes[:max_documents]]

        # If we still have slots, add other docs
        remaining_slots = max_documents - len(selected_pdfs)
        if remaining_slots > 0:
            selected_pdfs.extend([pdf.id for pdf in other_docs[:remaining_slots]])

        print(f"✅ Selected PDFs: {selected_pdfs}")
        return selected_pdfs

    # Step 4: Fallback: Simple recency-based selection
    selected_pdfs = [pdf.id for pdf in pdf_details[:max_documents]]
    print(f"✅ Selected {len(selected_pdfs)} most recent documents: {selected_pdfs}")
    return selected_pdfs

def validate_thread_context(db: Session,thread_id: Optional[str], user_id: str, strict_mode: bool = True) -> List[str]:
    """
    Validate thread context and return PDFs that should be accessible in this thread.
    
    Args:
        thread_id: Thread ID to validate (required for strict mode)
        user_id: User ID for access control
        strict_mode: If True (default), requires thread_id and enforces thread isolation
                    If False, falls back to all user PDFs when no thread_id provided
    
    Returns:
        List of PDF IDs that should be accessible in this context
        Empty list if no PDFs should be accessible (e.g., empty thread)
    """
    print(f"🔍 Validating thread context - Thread: {thread_id}, User: {user_id}, Strict: {strict_mode}")
    
    if not thread_id:
        if strict_mode:
            print("🚫 STRICT MODE: No thread context provided, denying access")
            return []
        else:
            # Legacy fallback mode - return all user PDFs (only for specific use cases)
            print("⚠️  LEGACY MODE: No thread context, returning all user PDFs")
            user_pdfs = get_user_pdfs(db,user_id)
            return [pdf["pdf_id"] for pdf in user_pdfs]
    
    # Thread context provided - only return PDFs associated with this thread
    thread_pdfs = get_thread_pdfs(db,thread_id, user_id)
    print(f"🔒 Thread isolation: Found {len(thread_pdfs)} PDFs for thread {thread_id}")
    return thread_pdfs



# ================================
# Utility Functions: Processing Flags (non-image files)
# ================================

def filter_unprocessed_pdf_ids(pdf_ids: List[str], user_id: str, db: Session) -> List[str]:
    """Return only those IDs from pdf_ids whose processed_by_llm flag is FALSE for this user."""
    try:
        from backend.crud import filter_unprocessed_pdf_ids as crud_filter_unprocessed_pdf_ids
        return crud_filter_unprocessed_pdf_ids(db, pdf_ids, user_id)
    except Exception as e:
        print(f"ERROR filtering unprocessed pdf ids: {e}")
        return []

def mark_pdfs_as_processed(pdf_ids: List[str], user_id: str, db: Session) -> int:
    """Set processed_by_llm = TRUE for provided pdf_ids owned by user. Returns count updated."""
    try:
        from backend.crud import mark_pdfs_as_processed as crud_mark_pdfs_as_processed
        updated = crud_mark_pdfs_as_processed(db, pdf_ids, user_id)
        print(f"✅ Marked {updated} PDFs as processed: {pdf_ids}")
        return updated
    except Exception as e:
        print(f"ERROR marking PDFs as processed: {e}")
        return 0

# ================================
# Utility Functions: Thread Management
# ================================

def create_thread_id() -> str:
    """Generate a unique thread ID."""
    return str(uuid.uuid4())


# ================================
# Utility Functions: Vector Database Management
# ================================

def create_faiss_vector_db(text: str, filename: str, pdf_id: str, processing_time: str, stats: dict, user_id: str, org_id: str) -> Optional[str]:
    """Create a FAISS vector database from extracted text content."""
    print(f"DEBUG: create_faiss_vector_db called for {filename}")
    
    # Check if system is configured for Pinecone
    vector_db_type = get_vector_db_type()
    if vector_db_type == "pinecone":
        print(f"ERROR: System is configured for Pinecone but create_faiss_vector_db was called!")
        print(f"This should not happen. Please check your configuration.")
        return None
    
    try:
        # Split text into chunks
        chunks = text_splitter.split_text(text)
        print(f"DEBUG: Split text into {len(chunks)} chunks")
        
        # Create Document objects with metadata
        documents = []
        for i, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk,
                metadata={
                    "pdf_id": pdf_id,
                    "user_id": user_id,  # ✅ Add user_id for isolation
                    "org_id": org_id,    # ✅ Add org_id for multi-tenancy
                    "filename": filename,
                    "chunk_id": f"{pdf_id}_chunk_{i}",
                    "text_length": len(chunk),
                    "processing_time": processing_time,
                    **stats
                }
            )
            documents.append(doc)
        
        if not documents:
            print(f"DEBUG: No valid documents created for {filename}")
            return None
        
        # Create FAISS vector store
        vector_store = FAISS.from_documents(documents, embeddings)
        vector_db_path = f"vector_db_{pdf_id}"
        print(f"DEBUG: About to save FAISS vector database to {vector_db_path}")
        print(f"DEBUG: Current working directory: {os.getcwd()}")
        vector_store.save_local(vector_db_path)
        print(f"DEBUG: Saved FAISS vector database to {vector_db_path}")
        print(f"DEBUG: Path exists after save: {os.path.exists(vector_db_path)}")
        print(f"DEBUG: Directory contents: {os.listdir('.') if os.path.exists('.') else 'No current directory'}")
        return vector_db_path
    except Exception as e:
        print(f"ERROR creating FAISS vector database: {e}")
        return None

def create_pinecone_vector_db(text: str, filename: str, pdf_id: str, processing_time: str, stats: dict, user_id: str, org_id: str) -> Optional[str]:
    """Create a Pinecone vector database from processed text."""
    if not PINECONE_AVAILABLE:
        print("ERROR: Pinecone is not available")
        return None
        
    print(f"DEBUG: create_pinecone_vector_db called for {filename}")
    print(f"DEBUG: PINECONE_AVAILABLE: {PINECONE_AVAILABLE}")
    print(f"DEBUG: PineconeVectorStore: {PineconeVectorStore}")
    
    try:
        # Split text into chunks
        chunks = text_splitter.split_text(text)
        print(f"DEBUG: Split text into {len(chunks)} chunks")
        
        # Create Document objects with metadata for Pinecone
        documents = []
        for i, chunk in enumerate(chunks):
            # ADD extention to the chunck
            extension = os.path.splitext(filename)[1].lower()
            chunk = f"File Type: {extension}\n{chunk}\nFile Type: {extension}"
            # Convert processing_time to string for Pinecone compatibility
            processing_time_str = str(processing_time) if processing_time else "0:00:00"
            
            # Create metadata with all Pinecone-compatible types
            # Note: stats are already cleaned before calling this function
            metadata = {
                "pdf_id": pdf_id,
                "user_id": user_id,  # ✅ Add user_id for isolation
                "org_id": org_id,    # ✅ Add org_id for multi-tenancy
                "filename": filename,
                "chunk_id": f"{pdf_id}_chunk_{i}",
                "text_length": len(chunk),
                "processing_time": processing_time_str,
                **stats
            }
            
            # Debug: Log metadata types
            print(f"DEBUG: Metadata types for chunk {i}:")
            for key, value in metadata.items():
                print(f"  {key}: {type(value)} = {value}")
            
            doc = Document(
                page_content=chunk,
                metadata=metadata
            )
            documents.append(doc)
        
        if not documents:
            print(f"DEBUG: No valid documents created for {filename}")
            return None
            
        # Get Pinecone configuration
        index_name = get_pinecone_index_name()
        api_key = get_pinecone_api_key()
        environment = get_pinecone_environment()
        
        print(f"DEBUG: Pinecone config - index_name: {index_name}, api_key: {api_key[:10]}..., environment: {environment}")
        
        # Verify Pinecone index exists
        try:
            import pinecone
            pc = pinecone.Pinecone(api_key=api_key)
            if index_name not in [idx.name for idx in pc.list_indexes()]:
                print(f"ERROR: Pinecone index '{index_name}' does not exist")
                return None
        except Exception as e:
            print(f"ERROR verifying Pinecone index: {e}")
            return None
        
        # Create Pinecone vector store
        print(f"DEBUG: About to create Pinecone vector store with {len(documents)} documents")
        vector_store = PineconeVectorStore.from_documents(documents, embeddings, index_name=index_name)
        print(f"DEBUG: Successfully created Pinecone vector store")
        print(f"DEBUG: Saved documents to Pinecone index {index_name}")
        
        # Return a consistent path format for Pinecone
        result_path = f"pinecone_{index_name}_{pdf_id}"
        print(f"DEBUG: create_pinecone_vector_db returning: {result_path}")
        return result_path
    except Exception as e:
        print(f"ERROR creating Pinecone vector database: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_vector_database_exists(pdf_id: str, db_type: str) -> bool:
    """Check if a vector database exists for a given PDF ID."""
    if db_type == "pinecone":
        if not PINECONE_AVAILABLE:
            print(f"DEBUG: Pinecone not available, cannot check database for PDF {pdf_id}")
            return False
        try:
            # Get Pinecone configuration
            api_key = get_pinecone_api_key()
            environment = get_pinecone_environment()
            index_name = get_pinecone_index_name()
            
            print(f"DEBUG: Checking Pinecone database for PDF {pdf_id}")
            print(f"DEBUG: Using index: {index_name}, environment: {environment}")
            
            # Check if index exists
            import pinecone
            pc = pinecone.Pinecone(api_key=api_key)
            
            # Try to search for documents with this PDF ID to verify they exist
            vector_store = PineconeVectorStore.from_existing_index(index_name=index_name, embedding=embeddings)
            results = vector_store.similarity_search("test", k=1, filter={"pdf_id": pdf_id})
            exists = len(results) > 0
            print(f"DEBUG: Pinecone database check for PDF {pdf_id}: {exists}")
            return exists
        except Exception as e:
            print(f"ERROR checking Pinecone database for PDF {pdf_id}: {e}")
            return False
    else:  # FAISS
        vector_db_path = f"vector_db_{pdf_id}"
        exists = os.path.exists(vector_db_path)
        print(f"DEBUG: FAISS database check for PDF {pdf_id}: {exists} (path: {vector_db_path})")
        return exists

def get_selected_pdfs_vector_store(db: Session, selected_pdf_ids: List[str], user_id: str):

    """Create a unified vector store from selected PDFs."""
    print(f"DEBUG: get_selected_pdfs_vector_store called with selected_pdf_ids={selected_pdf_ids}, user_id={user_id}")
    vector_db_type = get_vector_db_type()
    print(f"DEBUG: Vector DB type: {vector_db_type}")
    
    if vector_db_type == "pinecone":
        if not PINECONE_AVAILABLE:
            raise HTTPException(status_code=500, detail="Pinecone is not available")
        try:
            # Filter by user's PDFs
            user_pdf_ids = [pdf.id for pdf in get_user_pdfs(db, user_id)]
            filtered_ids = [pid for pid in selected_pdf_ids if pid in user_pdf_ids]
            
            if not filtered_ids:
                return None
                
            # Get unified Pinecone vector store with user isolation
            vector_store = get_unified_pinecone_vector_store(filtered_ids, embeddings, user_id)
            if vector_store is None:
                raise Exception("Failed to create unified Pinecone vector store")
            return vector_store
        except Exception as e:
            print(f"ERROR creating unified Pinecone vector store: {e}")
            # Don't fall back to FAISS when Pinecone is configured
            raise HTTPException(status_code=500, detail=f"Failed to create Pinecone vector store: {str(e)}")
    else:  # FAISS
        # Double-check that we're actually supposed to use FAISS
        if vector_db_type == "pinecone":
            print(f"ERROR: System is configured for Pinecone but FAISS fallback was attempted!")
            print(f"This should not happen. Please check your configuration.")
            raise HTTPException(status_code=500, detail="System configuration error: Pinecone configured but FAISS fallback attempted")
            
        try:
            print(f"DEBUG: Using FAISS vector store")
            print(f"DEBUG: Current working directory: {os.getcwd()}")
            all_docs = []
            for pdf_id in selected_pdf_ids:
                print(f"DEBUG: Processing PDF ID: {pdf_id}")
                if not validate_user_pdf(pdf_id, user_id):
                    print(f"DEBUG: PDF {pdf_id} validation failed")
                    continue
                vector_db_path = f"vector_db_{pdf_id}"
                print(f"DEBUG: Looking for vector DB at: {vector_db_path}")
                print(f"DEBUG: Path exists: {os.path.exists(vector_db_path)}")
                if os.path.exists(vector_db_path):
                    try:
                        store = FAISS.load_local(vector_db_path, embeddings, allow_dangerous_deserialization=True)
                        if hasattr(store, 'docstore') and store.docstore:
                            for doc_id, doc in store.docstore._dict.items():
                                all_docs.append(doc)
                        print(f"DEBUG: Successfully loaded docs from {vector_db_path}")
                    except Exception as e:
                        print(f"WARNING: Could not load {vector_db_path}: {e}")
                else:
                    print(f"WARNING: Vector DB path does not exist: {vector_db_path}")
            
            if not all_docs:
                print("DEBUG: No documents found for selected PDFs")
                return None
                
            print(f"DEBUG: Creating FAISS store with {len(all_docs)} documents")
            vector_store = FAISS.from_documents(all_docs, embeddings)
            return vector_store
        except Exception as e:
            print(f"ERROR creating unified FAISS vector store: {e}")
            return None



def update_pdf_llm_processed_flag_wrapper(pdf_id: str, user_id: str, processed: bool = True, db: Session = Depends(get_db)) -> bool:
    """Update the LLM processing flag for a PDF."""
    success = update_pdf_llm_processed_flag(db, pdf_id, user_id, processed)
    
    if success:
        print(f"✅ Updated LLM processing flag for PDF {pdf_id} to {processed}")
    else:
        print(f"⚠️ No rows updated for PDF {pdf_id} (user_id: {user_id})")
    
    return success


# ================================
# API Endpoint: System Status
# ================================

@app.get("/status")
async def get_system_status():
    """Get the current status of the system including vector database and service health."""
    status_info = {
        "server_time": datetime.datetime.utcnow().isoformat(),
        "openai_configured": bool(OPENAI_API_KEY),
        "docling_available": DOC_CONVERTER is not None
    }
    
    # Check vector database status
    vector_db_type = get_vector_db_type()
    
    if vector_db_type == "pinecone":
        status_info["vector_db_type"] = "pinecone"
        api_key = get_pinecone_api_key()
        status_info["pinecone_config"] = {
            "api_key": api_key[:10] + "..." if api_key else "Not set"
        }
        
        if not PINECONE_AVAILABLE:
            status_info["pinecone_status"] = "not_available"
            status_info["pinecone_error"] = "Pinecone library not installed"
        else:
            try:
                import pinecone
                pc = pinecone.Pinecone(api_key=api_key)
                
                # Check if index exists
                index_name = get_pinecone_index_name()
                if index_name in [idx.name for idx in pc.list_indexes()]:
                    status_info["pinecone_status"] = "accessible"
                    try:
                        index = pc.Index(index_name)
                        stats = index.describe_index_stats()
                        status_info["pinecone_stats"] = {
                            "dimension": stats.get("dimension"),
                            "index_fullness": stats.get("index_fullness"),
                            "namespaces": list(stats.get("namespaces", {}).keys()),
                            "total_vector_count": stats.get("total_vector_count")
                        }
                    except Exception as e:
                        status_info["pinecone_stats"] = {"error": str(e)}
                else:
                    status_info["pinecone_status"] = "index_not_found"
                    status_info["pinecone_error"] = f"Index '{index_name}' not found"
            except Exception as e:
                status_info["pinecone_status"] = "error"
                status_info["pinecone_error"] = str(e)
    else:
        # FAISS check
        try:
            # Double-check that we're actually supposed to use FAISS
            if vector_db_type == "pinecone":
                print(f"ERROR: System is configured for Pinecone but FAISS status check was attempted!")
                status_info.update({
                    "vector_db_type": "faiss",
                    "faiss_status": "error",
                    "faiss_error": "System configuration error: Pinecone configured but FAISS status check attempted"
                })
            else:
                vector_dbs = []
                for item in os.listdir("."):
                    if item.startswith("vector_db_") and os.path.isdir(item):
                        vector_dbs.append(item)
                status_info.update({
                    "vector_db_type": "faiss",
                    "faiss_status": "available",
                    "local_vector_dbs": vector_dbs,
                    "total_local_dbs": len(vector_dbs)
                })
        except Exception as e:
            status_info["faiss_status"] = "error"
            status_info["faiss_error"] = str(e)
    
    return status_info







# ================================
# Run Server
# ================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
