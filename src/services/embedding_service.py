import os
import logging
from typing import List, Optional
from openai import OpenAI
import voyageai
import cohere

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self, model_provider: str = None, model_name: str = None, openai_key: str = None):
        # Use defaults if not specified
        self.model_provider = model_provider or "openai"
        self.model_name = model_name or self._get_default_model()
        self.dimensions = 1536  # All models produce 1024D
        self.openai_key = openai_key
        # Initialize appropriate client
        self._initialize_client()
    
    def _get_default_model(self) -> str:
        """Get default model for the provider"""
        from config.settings import EMBEDDING_PROVIDERS, DEFAULT_EMBEDDING_PROVIDER
        
        if self.model_provider in EMBEDDING_PROVIDERS:
            return EMBEDDING_PROVIDERS[self.model_provider]["default"]
        return "text-embedding-3-small"
    
    def _initialize_client(self):
        """Initialize the appropriate embedding client"""
        if self.model_provider == "openai":
            api_key = self.openai_key
            if not api_key:
                raise ValueError("OPENAI_API_KEY is required")
            self.client = OpenAI(api_key=api_key)
            
        elif self.model_provider == "voyageai":
            api_key = os.getenv("VOYAGE_API_KEY")
            if not api_key:
                raise ValueError("VOYAGE_API_KEY environment variable is required")
            self.client = voyageai.Client(api_key=api_key)
            
        elif self.model_provider == "cohere":
            api_key = os.getenv("COHERE_API_KEY")
            if not api_key:
                raise ValueError("COHERE_API_KEY environment variable is required")
            self.client = cohere.Client(api_key=api_key)
            
        else:
            raise ValueError(f"Unsupported embedding provider: {self.model_provider}")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for the given text
        
        Args:
            text: The text to embed
            
        Returns:
            List[float]: The embedding vector
        """
        try:
            # Truncate text if it's too long
            max_tokens = 8191
            if len(text) > max_tokens * 4:
                text = text[:max_tokens * 4]
                logger.warning(f"Text truncated to {max_tokens * 4} characters for embedding")
            
            if self.model_provider == "openai":
                return await self._generate_openai_embedding(text)
            elif self.model_provider == "voyageai":
                return await self._generate_voyage_embedding(text)
            elif self.model_provider == "cohere":
                return await self._generate_cohere_embedding(text)
                
        except Exception as e:
            logger.error(f"Error generating embedding with {self.model_provider}: {str(e)}")
            raise
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List[List[float]]: List of embedding vectors
        """
        try:
            # Truncate texts if needed
            processed_texts = []
            for text in texts:
                max_tokens = 8191
                if len(text) > max_tokens * 4:
                    text = text[:max_tokens * 4]
                processed_texts.append(text)
            
            if self.model_provider == "openai":
                return await self._generate_openai_embeddings_batch(processed_texts)
            elif self.model_provider == "voyageai":
                return await self._generate_voyage_embeddings_batch(processed_texts)
            elif self.model_provider == "cohere":
                return await self._generate_cohere_embeddings_batch(processed_texts)
                
        except Exception as e:
            logger.error(f"Error generating batch embeddings with {self.model_provider}: {str(e)}")
            raise
    
    # Provider-specific methods
    async def _generate_openai_embedding(self, text: str) -> List[float]:
        """Generate OpenAI embedding"""
        response = self.client.embeddings.create(
            model=self.model_name,
            input=text,
            dimensions=1024
        )
        return response.data[0].embedding
    
    async def _generate_voyage_embedding(self, text: str) -> List[float]:
        """Generate Voyage AI embedding"""
        result = self.client.embed(
            texts=[text],
            model=self.model_name,
            input_type="document"
        )
        return result.embeddings[0]
    
    async def _generate_cohere_embedding(self, text: str) -> List[float]:
        """Generate Cohere embedding"""
        response = self.client.embed(
            texts=[text],
            model=self.model_name,
            input_type="search_document"
        )
        return response.embeddings[0]
    
    # Batch methods for each provider
    async def _generate_openai_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate OpenAI embeddings in batch"""
        response = self.client.embeddings.create(
            model=self.model_name,
            input=texts,
            dimensions=1024
        )
        return [data.embedding for data in response.data]
    
    async def _generate_voyage_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate Voyage AI embeddings in batch"""
        result = self.client.embed(
            texts=texts,
            model=self.model_name,
            input_type="document"
        )
        return result.embeddings
    
    async def _generate_cohere_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate Cohere embeddings in batch"""
        response = self.client.embed(
            texts=texts,
            model=self.model_name,
            input_type="search_document"
        )
        return response.embeddings 