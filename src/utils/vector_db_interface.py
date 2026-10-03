"""
Abstract interface for vector database operations
Supports both local (Chroma/FAISS) and Pinecone backends
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
import os
from dotenv import load_dotenv
load_dotenv()

class VectorDatabaseInterface(ABC):
    """Abstract base class for vector database operations"""
    
    @abstractmethod
    def store_documents(self, documents: List[Document], metadata: Dict[str, Any]) -> bool:
        """Store documents in the vector database"""
        pass
    
    @abstractmethod
    def search(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict] = None) -> List[Document]:
        """Search for similar documents"""
        pass
    
    @abstractmethod
    def delete_by_metadata(self, metadata_filter: Dict[str, Any]) -> bool:
        """Delete documents by metadata filter"""
        pass

class LocalVectorDatabase(VectorDatabaseInterface):
    """Local vector database implementation using Chroma"""
    
    def __init__(self, persist_directory: str, embeddings: OpenAIEmbeddings):
        from langchain_chroma import Chroma
        self.persist_directory = persist_directory
        self.embeddings = embeddings
        self.collection_name = f"pdf_collection_{os.path.basename(persist_directory)}"
        
    def store_documents(self, documents: List[Document], metadata: Dict[str, Any]) -> bool:
        """Store documents in local Chroma database"""
        try:
            from langchain_chroma import Chroma
            
            if os.path.exists(self.persist_directory):
                # Load existing database
                vector_db = Chroma(
                    collection_name=self.collection_name,
                    embedding_function=self.embeddings,
                    persist_directory=self.persist_directory,
                )
                # Add new documents
                vector_db.add_documents(documents)
            else:
                # Create new database
                vector_db = Chroma.from_documents(
                    documents=documents,
                    embedding=self.embeddings,
                    persist_directory=self.persist_directory,
                    collection_name=self.collection_name
                )
            
            # Persist the database
            vector_db.persist()
            return True
            
        except Exception as e:
            print(f"❌ Error storing documents in local database: {e}")
            return False
        
    def search(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict] = None) -> List[Document]:
        """Search local Chroma database"""
        try:
            from langchain_chroma import Chroma
            
            vector_db = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory,
            )
            
            # Search for relevant documents
            results = vector_db.similarity_search(query, k=top_k)
            return results
            
        except Exception as e:
            print(f"❌ Error searching local database: {e}")
            return []
        
    def delete_by_metadata(self, metadata_filter: Dict[str, Any]) -> bool:
        """Delete documents by metadata filter from local database"""
        try:
            from langchain_chroma import Chroma
            
            vector_db = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory,
            )
            
            # Chroma deletion by metadata
            vector_db.delete(where=metadata_filter)
            return True
            
        except Exception as e:
            print(f"❌ Error deleting from local database: {e}")
            return False

class PineconeVectorDatabase(VectorDatabaseInterface):
    """Pinecone vector database implementation"""
    
    def __init__(self, api_key: str, environment: str, index_name: str, embeddings):
        try:
            import pinecone
            from langchain_pinecone import PineconeVectorStore
            
            # Set the Pinecone API key in environment
            os.environ["PINECONE_API_KEY"] = api_key
            
            # Store the embeddings object properly
            self.embeddings = embeddings
            
            # Initialize Pinecone with new API pattern
            pc = pinecone.Pinecone()
            
            # Check if index exists
            existing_indexes = pc.list_indexes().names()
            print(f"Available Pinecone indexes: {existing_indexes}")
            
            if index_name not in existing_indexes:
                print(f"Creating Pinecone index: {index_name}")
                pc.create_index(
                    name=index_name,
                    spec=pinecone.Spec(
                        serverless=pinecone.ServerlessSpec(
                            cloud="aws",
                            region="us-east-1"
                        )
                    ),
                    dimension=1024,  # 1024 dimensions to match text-embedding-ada-002
                    metric="cosine"
                )
                print(f"✓ Created new Pinecone index: {index_name}")
            else:
                print(f"✓ Using existing Pinecone index: {index_name}")
            
            self.index_name = index_name
            self.pinecone = pc
            
        except ImportError:
            print("❌ Pinecone not installed. Please install with: pip install pinecone-client langchain-pinecone")
            raise
        except Exception as e:
            print(f"❌ Error initializing Pinecone: {e}")
            raise
        
    def store_documents(self, documents: List[Document], metadata: Dict[str, Any]) -> bool:
        """Store documents in Pinecone"""
        try:
            from langchain_pinecone import PineconeVectorStore
            
            # Ensure each document has the additional metadata
            enhanced_documents = []
            for doc in documents:
                # Merge the document's existing metadata with the additional metadata
                enhanced_metadata = {**doc.metadata, **metadata}
                enhanced_doc = Document(
                    page_content=doc.page_content,
                    metadata=enhanced_metadata
                )
                enhanced_documents.append(enhanced_doc)
            
            print(f"📄 Storing {len(enhanced_documents)} documents in Pinecone with metadata: {metadata}")
            
            # Create Pinecone vector store with API key
            vector_store = PineconeVectorStore.from_documents(
                documents=enhanced_documents,
                embedding=self.embeddings,
                index_name=self.index_name,
                # pinecone_api_key="pcsk_SgmHC_6J8AQGxgJtY3hxi5otMfJz4fE8xjJbCr5Mznc9GfzdLUWQGZpqvmgvqXXmpV2xE" # Pass the API key with correct parameter name
            )
            
            print(f"✅ Successfully stored {len(enhanced_documents)} documents in Pinecone")
            return True
            
        except Exception as e:
            print(f"❌ Error storing documents in Pinecone: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    def search(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict] = None) -> List[Document]:
        """Search Pinecone database"""
        try:
            from langchain_pinecone import PineconeVectorStore
            
            # Create Pinecone vector store for searching with API key
            vector_store = PineconeVectorStore.from_existing_index(
                index_name=self.index_name,
                embedding=self.embeddings,
                # pinecone_api_key="pcsk_SgmHC_6J8AQGxgJtY3hxi5otMfJz4fE8xjJbCr5Mznc9GfzdLUWQGZpqvmgvqXXmpV2xE"# Pass the API key with correct parameter name
            )
            
            # Search with optional metadata filter
            if filter_metadata:
                results = vector_store.similarity_search(
                    query, 
                    k=top_k,
                    filter=filter_metadata
                )
            else:
                results = vector_store.similarity_search(query, k=top_k)
                
            return results
            
        except Exception as e:
            print(f"❌ Error searching Pinecone: {e}")
            return []
        
    def delete_by_metadata(self, metadata_filter: Dict[str, Any]) -> bool:
        """Delete documents by metadata filter from Pinecone"""
        try:
            # Get the Pinecone index
            index = self.pinecone.Index(self.index_name)
            
            # Delete vectors matching metadata filter
            # In Pinecone v3+, use index.delete(filter=metadata_filter)
            print(f"🗑️ Deleting vectors from Pinecone with filter: {metadata_filter}")
            
            delete_response = index.delete(filter=metadata_filter)
            
            print(f"✅ Pinecone deletion completed successfully: {delete_response}")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting from Pinecone: {e}")
            return False

def get_vector_database(db_type: str, **kwargs) -> VectorDatabaseInterface:
    """Factory function to get the appropriate vector database implementation"""
    if db_type == "pinecone":
        return PineconeVectorDatabase(**kwargs)
    else:
        return LocalVectorDatabase(**kwargs)
