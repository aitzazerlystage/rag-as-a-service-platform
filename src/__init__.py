"""
PDF Processing API - A comprehensive solution for extracting, processing, and chatting with PDF documents
"""

__version__ = "1.0.0"
__author__ = "PDF Processing Team"

from .config import *
# from .backend import *  # Removed to avoid circular import
from .utils import *

__all__ = [
    # Configuration
    'OPENAI_API_KEY',
    'LLM_MODEL',
    'LLM_TEMPERATURE',
    'LLM_MAX_TOKENS',
    'VECTOR_DB_CHUNK_SIZE',
    'VECTOR_DB_CHUNK_OVERLAP',
    'PINECONE_API_KEY',
    'PINECONE_ENVIRONMENT',
    'PINECONE_INDEX_NAME',
    'VECTOR_DB_TYPE',
    'CHATBOT_DB_PATH',
    'HOST',
    'PORT',
    'MAX_CONCURRENT_PDFS',
    'MAX_IMAGE_WORKERS',
    'TEMP_DIR_PREFIX',
    'OUTPUT_DIR',
    'VECTOR_DB_DIR',
    'IMG_DIR',
    
    # Backend
    'app',
    'create_chat_workflow',
    'create_unified_chat_workflow',
    'get_checkpointer',
    'close_connection',
    
    # Utils
    'run_single_pdf_pipeline',
    'process_multiple_pdfs_async',
    'search_vector_db',
    'find_pdf_files',
    'save_results',
    'generate_summary_report',
    'get_vector_database',
    'VectorDatabaseInterface',
    'LocalVectorDatabase',
    'PineconeVectorDatabase'
]
