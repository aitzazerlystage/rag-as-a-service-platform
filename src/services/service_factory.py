"""
Service Factory - Centralized service initialization with automatic key management.

This module provides factory functions to create properly configured service instances
based on subscription information, eliminating the need to manually handle API keys
in every endpoint.
"""

from typing import Tuple, Optional
from services.embedding_service import EmbeddingService
from services.pinecone_service import PineconeService
from utils.get_api_key import get_key
from config.settings import get_default_embedding_provider


def create_services_from_auth(
    auth: dict,
    embedding_provider: Optional[str] = None,
    embedding_model: Optional[str] = None
) -> Tuple[EmbeddingService, PineconeService]:
    """
    Create embedding and Pinecone services from auth object.
    
    This factory function handles all the complexity of:
    - Extracting subscription from auth
    - Retrieving the correct API keys (cached/decrypted)
    - Initializing both services
    
    Args:
        auth: Authentication object containing subscription info
              Expected format: { "api_key": obj, "subscription": obj }
        embedding_provider: Provider to use ("ollama", "openai", "voyageai", "cohere")
        embedding_model: Optional specific model name
        
    Returns:
        Tuple of (EmbeddingService, PineconeService)
        
    Example:
        >>> embedding_service, pinecone_service = create_services_from_auth(auth)
        >>> # Services are ready to use!
    """
    subscription = auth["subscription"]
    embedding_provider = embedding_provider or get_default_embedding_provider()
    
    # Get all keys in one call (cached for efficiency)
    openai_api_key, pinecone_api_key, pinecone_index_name, pinecone_env = get_key(subscription)
    
    # Initialize embedding service
    embedding_service = EmbeddingService(
        model_provider=embedding_provider,
        model_name=embedding_model,
        openai_key=openai_api_key if embedding_provider == "openai" else None,
    )
    
    # Initialize Pinecone service
    pinecone_service = PineconeService(
        pinecone_api_key=pinecone_api_key,
        pinecone_index_name=pinecone_index_name,
        pinecone_env=pinecone_env
    )
    
    return embedding_service, pinecone_service


def create_embedding_service(
    auth: dict,
    embedding_provider: Optional[str] = None,
    embedding_model: Optional[str] = None
) -> EmbeddingService:
    """
    Create only an embedding service from auth object.
    
    Useful when you only need embeddings without Pinecone.
    
    Args:
        auth: Authentication object containing subscription info
        embedding_provider: Provider to use ("ollama", "openai", "voyageai", "cohere")
        embedding_model: Optional specific model name
        
    Returns:
        Configured EmbeddingService instance
    """
    subscription = auth["subscription"]
    embedding_provider = embedding_provider or get_default_embedding_provider()
    openai_api_key, _, _, _ = get_key(subscription)
    
    return EmbeddingService(
        model_provider=embedding_provider,
        model_name=embedding_model,
        openai_key=openai_api_key if embedding_provider == "openai" else None,
    )


def create_pinecone_service(auth: dict) -> PineconeService:
    """
    Create only a Pinecone service from auth object.
    
    Useful when you only need Pinecone without embeddings.
    
    Args:
        auth: Authentication object containing subscription info
        
    Returns:
        Configured PineconeService instance
    """
    subscription = auth["subscription"]
    _, pinecone_api_key, pinecone_index_name, pinecone_env = get_key(subscription)
    
    return PineconeService(
        pinecone_api_key=pinecone_api_key,
        pinecone_index_name=pinecone_index_name,
        pinecone_env=pinecone_env
    )


def get_namespace_from_auth(auth: dict) -> str:
    """
    Get the Pinecone namespace for the authenticated user.
    
    Args:
        auth: Authentication object containing api_key info
        
    Returns:
        Namespace string in format "{org_id}-{project_id}"
    """
    api_key_obj = auth["api_key"]
    return f"{api_key_obj.org_id}-{api_key_obj.project_id}"

