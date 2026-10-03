"""
Database configuration and session management for SQLAlchemy
Supports both SQLite and PostgreSQL databases
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
from config.settings import get_database_url

# Get database URL from configuration
DATABASE_URL = get_database_url()

# Determine if we're using SQLite or PostgreSQL
is_sqlite = DATABASE_URL.startswith("sqlite")

# Create engine with appropriate configuration
if is_sqlite:
    # SQLite-specific configuration
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # Only for SQLite
        poolclass=StaticPool,  # SQLite doesn't support connection pooling
        echo=False  # Set to True for SQL query debugging
    )
else:
    # PostgreSQL configuration
    engine = create_engine(
        DATABASE_URL,
        echo=False,  # Set to True for SQL query debugging
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=300  # Recycle connections every 5 minutes
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

def get_db():
    """
    Dependency to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _ensure_sqlite_project_uploads_doc_id():
    """ALTER existing SQLite tables; Base.metadata.create_all does not add new columns."""
    if not is_sqlite:
        return
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='project_uploads' LIMIT 1"
            )
        ).fetchone()
        if not row:
            return
        cols = conn.execute(text("PRAGMA table_info(project_uploads)")).fetchall()
        names = {c[1] for c in cols}
        if "doc_id" not in names:
            conn.execute(text("ALTER TABLE project_uploads ADD COLUMN doc_id TEXT"))
            print("SQLite: added column project_uploads.doc_id")


def create_tables():
    """
    Create all tables in the database
    """
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_project_uploads_doc_id()

def drop_tables():
    """
    Drop all tables in the database (use with caution!)
    """
    Base.metadata.drop_all(bind=engine)
