"""
Configuration package for PDF Processing API
"""

from .settings import *

__all__ = [
    'OPENAI_API_KEY',
    'LLM_MODEL',
    'LLM_TEMPERATURE',
    'LLM_MAX_TOKENS',
    'VECTOR_DB_CHUNK_SIZE',
    'VECTOR_DB_CHUNK_OVERLAP',
    'CHATBOT_DB_PATH',
    'HOST',
    'PORT',
    'MAX_CONCURRENT_PDFS',
    'MAX_IMAGE_WORKERS',
    'TEMP_DIR_PREFIX',
    'OUTPUT_DIR',
    'VECTOR_DB_DIR',
    'IMG_DIR',
    'get_OPENAI_API_KEY',
    'get_llm_model',
    'get_llm_temperature',
    'get_llm_max_tokens',
    'get_vector_db_chunk_size',
    'get_vector_db_chunk_overlap',
    'get_chatbot_db_path',
    'get_host',
    'get_port',
    'get_temp_dir_prefix',
    'get_max_concurrent_pdfs',
    'get_max_image_workers',
    'get_output_dir',
    'get_vector_db_dir',
    'get_img_dir'
]
