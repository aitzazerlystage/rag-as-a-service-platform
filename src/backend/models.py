"""
SQLAlchemy ORM models for the PDF Chatbot application
Compatible with both SQLite and PostgreSQL
"""

from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, LargeBinary, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import uuid
from datetime import datetime
from backend.enum.enum import PlanEnum, StatusEnum
from enum import Enum as PyEnum  # Python Enum
from sqlalchemy import Enum      # SQLAlchemy Enum
from enum import Enum as PyEnum  # Python Enum
from sqlalchemy import Enum      # SQLAlchemy Enum

class Organization(Base):
    """Organization model for grouping users and enforcing plans"""
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_name = Column(String, nullable=False, unique=True)
    plan_type = Column(String, nullable=False, default="free")
    max_users = Column(Integer, nullable=False, default=5)
    created_at = Column(DateTime, default=func.current_timestamp())
    created_by = Column(String, ForeignKey("users.id"), nullable=True)  # Filled after user creation

    # Relationships
    users = relationship("User", back_populates="organization", foreign_keys="User.org_id")
    creator = relationship("User", foreign_keys=[created_by])
    projects = relationship("Project", back_populates="organization", cascade="all, delete-orphan")

class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(LargeBinary, nullable=False)  # Compatible with both SQLite and PostgreSQL
    created_at = Column(DateTime, default=func.current_timestamp())
    org_id = Column(String, ForeignKey("organizations.id"), nullable=True)
    
    # Relationships
    pdfs = relationship("PDF", back_populates="user", cascade="all, delete-orphan")
    threads = relationship("Thread", back_populates="user", cascade="all, delete-orphan")
    organization = relationship("Organization", back_populates="users", foreign_keys=[org_id])
    organizations_owned = relationship("Organization", foreign_keys="Organization.created_by")
    projects_owned = relationship("Project", back_populates="owner")
    user_token_usage = relationship("UserTokenUsage", back_populates="user", uselist=False)


class Project(Base):
    """Project model scoped to an Organization and owned by a User

    Multi-tenant constraints:
    - name is unique per organization
    - project_key is globally unique (used for API access/integration)
    """
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    owner_user_id = Column(String, ForeignKey("users.id"), nullable=False)

    name = Column(String, nullable=False)
    description = Column(Text)

    # A short secret/token-like key for client usage; rotate if compromised
    project_key = Column(String, nullable=False, unique=True)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())

    # Constraints and indexes for performance and tenancy guarantees
    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_projects_org_id_name"),
        Index("ix_projects_org_id", "org_id"),
        Index("ix_projects_owner_user_id", "owner_user_id"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="projects")
    owner = relationship("User", back_populates="projects_owned")
    uploads = relationship(
        "ProjectUpload",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectUpload(Base):
    """Files ingested via vectors/upload scoped to a project (API key)."""

    __tablename__ = "project_uploads"
    __table_args__ = (Index("ix_project_uploads_project_id", "project_id"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    original_filename = Column(String, nullable=False)
    # Same UUID embedded in Pinecone metadata when insert_to_rag succeeds
    doc_id = Column(String, nullable=True, index=True)
    rag_inserted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())

    project = relationship("Project", back_populates="uploads")


class PDF(Base):
    """PDF model for tracking uploaded documents"""
    __tablename__ = "pdfs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    vector_db_path = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    upload_time = Column(DateTime, default=func.current_timestamp())
    processing_time = Column(String)
    text_length = Column(Integer)
    table_count = Column(Integer)
    image_count = Column(Integer)
    chunks_stored = Column(Integer)
    base64_content = Column(Text)
    mime_type = Column(String)
    processed_by_llm = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="pdfs")

class Thread(Base):
    """Thread model for chat sessions"""
    __tablename__ = "threads"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    pdf_id = Column(String)  # Optional, for backward compatibility
    title = Column(String)
    created_time = Column(DateTime, default=func.current_timestamp())
    last_activity = Column(DateTime, default=func.current_timestamp())
    metadata_json = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="threads")
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")

class Message(Base):
    """Message model for chat history"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(String, ForeignKey("threads.id"), nullable=False)
    message_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    thread = relationship("Thread", back_populates="messages")


from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
import uuid

from backend.database import Base

class Api_key(Base):
    __tablename__ = "api_keys"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    api_key = Column(String, unique=True,nullable=False)
    total_tokens_used = Column(Integer, default=0, nullable=False)  # Cumulative total tokens used
    created_at = Column(DateTime, default=func.current_timestamp())

class Tokens(Base):
    """Tokens model for tracking API usage by character count"""
    __tablename__ = "tokens"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    api_key_id = Column(String, ForeignKey("api_keys.id"), nullable=False)
    endpoint = Column(String, nullable=False)  # e.g., "vectors/insert", "vectors/query", "response/generate"
    operation_type = Column(String, nullable=False)  # e.g., "insert", "query", "generate"
    input_characters = Column(Integer, default=0)  # Characters in input/request
    output_characters = Column(Integer, default=0)  # Characters in output/response
    total_characters = Column(Integer, nullable=False)  # Total characters used for this call
    total_usage = Column(Integer, default=0)  # Cumulative total usage for this API key
    created_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    api_key = relationship("Api_key")



class Subscription(Base):
    """
    Subscription model:
    - Scoped to an Organization (all users/projects in that org share the subscription).
    - Tracks plan, status, quotas, and usage.
    """

    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, unique=True)

    plan = Column(Enum(PlanEnum), default=PlanEnum.free_trial, nullable=False)
    status = Column(Enum(StatusEnum), default=StatusEnum.active, nullable=False)



    start_date = Column(DateTime, default=func.current_timestamp())
    end_date = Column(DateTime, nullable=True)  # trial expiry or billing cycle end

    

    # Quota limits (per billing cycle)
    monthly_limit_queries = Column(Integer, default=4)
    monthly_limit_ingest = Column(Integer, default=100)
    monthly_limit_storage_mb = Column(Integer, default=500)
    monthly_limit_tokens = Column(Integer, default=5000)  # Token quota limit

    # Usage counters (reset on renewal)
    used_queries = Column(Integer, default=0)
    used_ingest = Column(Integer, default=0)
    used_storage_mb = Column(Integer, default=0)
    used_tokens = Column(Integer, default=0)  # Token usage counter


       # 🧩 Dedicated or Blackbox credentials
    openai_api_key = Column(String, nullable=True)
    pinecone_api_key = Column(String, nullable=True)
    pinecone_env = Column(String, nullable=True)
    pinecone_index = Column(String, nullable=True)

    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    organization = relationship("Organization", backref="subscription")


class UserTokenUsage(Base):
    """User-level token usage tracking to prevent quota bypass via multiple API keys"""
    __tablename__ = "user_token_usage"
    
    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    total_user_token_usage = Column(Integer, default=0, nullable=False)
    last_updated = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    user = relationship("User", back_populates="user_token_usage")