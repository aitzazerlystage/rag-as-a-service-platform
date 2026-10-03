"""
Configuration file for the PDF Processing API
"""

import os
from typing import Optional

# OpenAI API Configuration
# OPENAI_API_KEY = ""
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# LLM Configuration (local Ollama)
LLM_MODEL = "qwen3:4b-instruct"
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 4000
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
# LLM_MODEL = "gpt-4o"  # OpenAI (replaced by Ollama)

# Embedding Configuration — Pinecone index dimension (all stored vectors)
PINECONE_INDEX_DIMENSIONS = 1024
EMBEDDING_MODEL = "nomic-embed-text-v1.5"
EMBEDDING_DIMENSIONS = PINECONE_INDEX_DIMENSIONS

# Multiple Embedding Provider Configuration
# "model_dimensions" = native API output; "dimensions" = Pinecone index size (after align)
EMBEDDING_PROVIDERS = {
    "nomic": {
        "models": ["nomic-embed-text-v1.5", "nomic-embed-text-v1"],
        "default": "nomic-embed-text-v1.5",
        "model_dimensions": 768,
        "dimensions": PINECONE_INDEX_DIMENSIONS,
    },
    "ollama": {
        "models": ["nomic-embed-text", "mxbai-embed-large"],
        "default": "nomic-embed-text",
        "model_dimensions": 768,
        "dimensions": PINECONE_INDEX_DIMENSIONS,
    },
    "openai": {
        "models": ["text-embedding-3-small", "text-embedding-3-large"],
        "default": "text-embedding-3-small",
        "model_dimensions": 1024,
        "dimensions": PINECONE_INDEX_DIMENSIONS,
    },
    "voyageai": {
        "models": ["voyage-3", "voyage-3.5"],
        "default": "voyage-3.5",
        "model_dimensions": 1024,
        "dimensions": PINECONE_INDEX_DIMENSIONS,
    },
    "cohere": {
        "models": ["embed-english-v3.0"],
        "default": "embed-english-v3.0",
        "model_dimensions": 1024,
        "dimensions": PINECONE_INDEX_DIMENSIONS,
    },
}

# Default embedding provider and model (Nomic cloud API — no local GPU)
DEFAULT_EMBEDDING_PROVIDER = "nomic"
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text-v1.5"

SUPPORTED_EMBEDDING_PROVIDERS = list(EMBEDDING_PROVIDERS.keys())

# Additional API Keys for other providers
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")
NOMIC_API_KEY = os.getenv("NOMIC_API_KEY", "")

# Vector Database Configuration
VECTOR_DB_CHUNK_SIZE = 2500
VECTOR_DB_CHUNK_OVERLAP = 400

# Pinecone Configuration (Optional - for cloud vector database)
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "nil")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "nil")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "nil")
VECTOR_DB_TYPE = os.getenv("VECTOR_DB_TYPE", "pinecone")  # "local" or "pinecone"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "nil")
ANTHROPIC_API_KEY=os.getenv("ANTHROPIC_API_KEY", "nil")
# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chatbot.db")
# DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dcs:12345@localhost:5432/chatbot")
CHATBOT_DB_PATH = "chatbot.db"  # Keep for backward compatibility

# Server Configuration
HOST = "0.0.0.0"
PORT = 8001

# File Processing Configuration
MAX_CONCURRENT_PDFS = 3
MAX_IMAGE_WORKERS = 4
TEMP_DIR_PREFIX = "pdf_processing_"

# Output Configuration
OUTPUT_DIR = "extracted_outputs"
VECTOR_DB_DIR = "vector_db"
IMG_DIR = "images"

def get_OPENAI_API_KEY() -> str:
    """Get OpenAI API key from environment or config"""
    return os.getenv("OPENAI_API_KEY", OPENAI_API_KEY)

def get_llm_model() -> str:
    """Get LLM model from environment or config"""
    return os.getenv("LLM_MODEL", LLM_MODEL)

def get_llm_temperature() -> float:
    """Get LLM temperature from environment or config"""
    return float(os.getenv("LLM_TEMPERATURE", LLM_TEMPERATURE))

def get_llm_max_tokens() -> int:
    """Get LLM max tokens from environment or config"""
    return int(os.getenv("LLM_MAX_TOKENS", LLM_MAX_TOKENS))

def get_ollama_base_url() -> str:
    """Get Ollama API base URL from environment or config"""
    return os.getenv("OLLAMA_BASE_URL", OLLAMA_BASE_URL)

def get_embedding_model() -> str:
    """Get embedding model from environment or config"""
    return os.getenv("EMBEDDING_MODEL", EMBEDDING_MODEL)

def get_embedding_dimensions() -> int:
    """Vector dimension stored in Pinecone (index size)."""
    return int(os.getenv("EMBEDDING_DIMENSIONS", EMBEDDING_DIMENSIONS))

def get_pinecone_index_dimensions() -> int:
    """Pinecone index dimension — all providers align vectors to this size."""
    return int(os.getenv("PINECONE_INDEX_DIMENSIONS", PINECONE_INDEX_DIMENSIONS))

def get_provider_model_dimensions(provider: str) -> int:
    """Native embedding length for a provider's default model."""
    cfg = EMBEDDING_PROVIDERS.get(provider, {})
    return int(cfg.get("model_dimensions", cfg.get("dimensions", get_pinecone_index_dimensions())))

def get_vector_db_chunk_size() -> int:
    """Get vector database chunk size from environment or config"""
    return int(os.getenv("VECTOR_DB_CHUNK_SIZE", VECTOR_DB_CHUNK_SIZE))

def get_vector_db_chunk_overlap() -> int:
    """Get vector database chunk overlap from environment or config"""
    return int(os.getenv("VECTOR_DB_CHUNK_OVERLAP", VECTOR_DB_CHUNK_OVERLAP))

def get_pinecone_api_key() -> str:
    """Get Pinecone API key from environment or config"""
    return os.getenv("PINECONE_API_KEY", PINECONE_API_KEY)

def get_pinecone_environment() -> str:
    """Get Pinecone environment from environment or config"""
    return os.getenv("PINECONE_ENVIRONMENT", PINECONE_ENVIRONMENT)

def get_pinecone_index_name() -> str:
    """Get Pinecone index name from environment or config"""
    return os.getenv("PINECONE_INDEX_NAME", PINECONE_INDEX_NAME)

def get_vector_db_type() -> str:
    """Get vector database type from environment or config"""
    return os.getenv("VECTOR_DB_TYPE", VECTOR_DB_TYPE)

def get_chatbot_db_path() -> str:
    """Get chatbot database path from environment or config"""
    return os.getenv("CHATBOT_DB_PATH", CHATBOT_DB_PATH)

def get_host() -> str:
    """Get server host from environment or config"""
    return os.getenv("HOST", HOST)

def get_port() -> int:
    """Get server port from environment or config"""
    return int(os.getenv("PORT", PORT))

def get_temp_dir_prefix() -> str:
    """Get temporary directory prefix from environment or config"""
    return os.getenv("TEMP_DIR_PREFIX", TEMP_DIR_PREFIX)

def get_max_concurrent_pdfs() -> int:
    """Get maximum concurrent PDFs from environment or config"""
    return int(os.getenv("MAX_CONCURRENT_PDFS", MAX_CONCURRENT_PDFS))

def get_max_image_workers() -> int:
    """Get maximum image workers from environment or config"""
    return int(os.getenv("MAX_IMAGE_WORKERS", MAX_IMAGE_WORKERS))

def get_output_dir() -> str:
    """Get output directory from environment or config"""
    return os.getenv("OUTPUT_DIR", OUTPUT_DIR)

def get_vector_db_dir() -> str:
    """Get vector database directory from environment or config"""
    return os.getenv("VECTOR_DB_DIR", VECTOR_DB_DIR)

def get_img_dir() -> str:
    """Get image directory from environment or config"""
    return os.getenv("IMG_DIR", IMG_DIR)

def get_database_url() -> str:
    """Get database URL from environment or config"""
    return os.getenv("DATABASE_URL", DATABASE_URL)

# New embedding provider helper functions
def get_embedding_providers() -> dict:
    """Get embedding providers configuration"""
    return EMBEDDING_PROVIDERS

def get_default_embedding_provider() -> str:
    """Get default embedding provider from environment or config"""
    return os.getenv("DEFAULT_EMBEDDING_PROVIDER", DEFAULT_EMBEDDING_PROVIDER)

def get_default_embedding_model() -> str:
    """Get default embedding model from environment or config"""
    return os.getenv("DEFAULT_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)

def get_voyage_api_key() -> str:
    """Get Voyage AI API key from environment or config"""
    return os.getenv("VOYAGE_API_KEY", VOYAGE_API_KEY)


def get_cohere_api_key() -> str:
    """Get Cohere API key from environment or config"""
    return os.getenv("COHERE_API_KEY", COHERE_API_KEY)

def get_nomic_api_key() -> str:
    """Get Nomic Atlas API key from environment or config"""
    return os.getenv("NOMIC_API_KEY", NOMIC_API_KEY)
