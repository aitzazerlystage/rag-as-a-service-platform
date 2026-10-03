# """
# CRUD operations for the PDF Chatbot application
# Database-agnostic operations using SQLAlchemy ORM
# """

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Dict, Any, Optional
import json
import uuid
from .models import User, PDF, Thread, Message, Organization, Project, Tokens, Api_key, UserTokenUsage

from backend.database import SessionLocal   # ✅ ADD THIS IMPORT
from backend.models import Subscription

from datetime import datetime, timedelta

# ================================
# User Operations
# ================================

def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, username: str, full_name: str, email: str, password_hash: bytes) -> User:
    """Create a new user"""
    user = User(
        id=str(uuid.uuid4()),
        username=username,
        full_name=full_name,
        email=email,
        password_hash=password_hash
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# def create_organization(
#     db: Session,
#     org_name: str,
#     created_by_user_id: str,
#     plan_type: str = "free",
#     max_users: int = 5,
# ) -> Organization:
#     """Create a new organization with defaults and owner."""
#     organization = Organization(
#         org_name=org_name,
#         plan_type=plan_type,
#         max_users=max_users,
#         created_by=created_by_user_id,
#     )
#     db.add(organization)
#     db.commit()
#     db.refresh(organization)
#     return organization




from sqlalchemy.orm import Session
from fastapi import HTTPException

# def create_organization_and_user(
#     db: Session,
#     username: str,
#     full_name: str,
#     email: str,
#     hashed_password: str,
#     org_name: str
# ):
#     # 1. Create user
#     user = User(
#         username=username,
#         full_name=full_name,
#         email=email,
#         password_hash=hashed_password,
#     )
#     db.add(user)
#     db.flush()  # user.id available

#     # 2. Create organization
#     org = Organization(
#         org_name=org_name,
#         created_by=user.id,
#         plan_type="free"
#     )
#     db.add(org)
#     db.flush()  # org.id available

#     # 3. Attach user to org
#     user.org_id = org.id
#     db.add(user)   # update user with org_id

#     # 4. Create subscription
#     subscription = Subscription(
#         org_id=org.id,
#         plan=PlanEnum.free_trial,
#         monthly_limit_queries=100,
#         monthly_limit_ingest=50,
#         monthly_limit_tokens=50000,  # 50k tokens for free trial
#         end_date=datetime.utcnow() + timedelta(days=30),  # trial for 30 days
#     )
#     db.add(subscription)

#     db.commit()
#     db.refresh(user)
#     db.refresh(org)
#     db.refresh(subscription)

#     return user, org, subscription


from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models import User, Organization, Subscription
from backend.enum.enum import PlanEnum, StatusEnum
from utils.subscription_limits import set_plan_limits  # import helper

def create_organization_and_user(
    db: Session,
    username: str,
    full_name: str,
    email: str,
    hashed_password: str,
    org_name: str
):
    # 1. Create user
    user = User(
        username=username,
        full_name=full_name,
        email=email,
        password_hash=hashed_password,
    )
    db.add(user)
    db.flush()  # so user.id is available

    # 2. Create organization
    org = Organization(
        org_name=org_name,
        created_by=user.id,
        plan_type="free"  # still matches your current structure
    )
    db.add(org)
    db.flush()

    # 3. Attach user to organization
    user.org_id = org.id
    db.add(user)

    # 4. Create subscription (default tier: quotas only; keys from env)
    subscription = Subscription(
        org_id=org.id,
        plan=PlanEnum.free_trial,
        status=StatusEnum.active,
        end_date=None,
    )

    set_plan_limits(subscription)

    db.add(subscription)

    db.commit()
    db.refresh(user)
    db.refresh(org)
    db.refresh(subscription)

    return user, org, subscription


def set_user_organization(db: Session, user_id: str, org_id: str) -> None:
    """Link a user to an organization by setting org_id."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")
    user.org_id = org_id
    db.commit()





def get_organization_by_name(db: Session, org_name: str) -> Optional[Organization]:
    """Fetch organization by name."""
    return db.query(Organization).filter(Organization.org_name == org_name).first()

def delete_user(db: Session, user_id: str) -> None:
    """Delete a user by id (used for rollback on failed signup)."""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()

def get_user_info(db: Session, user_id: str) -> Optional[Dict[str, Any]]:
    """Get user information as dictionary"""
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email
    }

def get_current_user_from_id(user_id: str, db: Session) -> dict:
    """Get current user from user ID."""
    return get_user_info(db, user_id)




# ================================
# Subscription Operations
# ================================


def create_subscription(db: Session, org_id: str) -> Subscription:
    """Create default subscription for an organization (free_trial tier, env keys)."""
    subscription = Subscription(
        org_id=org_id,
        plan=PlanEnum.free_trial,
        status=StatusEnum.active,
        end_date=None,
    )
    set_plan_limits(subscription)
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription
# ================================
# PDF Operations
# ================================

def check_pdf_exists(db: Session, filename: str, user_id: str) -> bool:
    """Check if a user already uploaded a PDF with this filename"""
    pdf = db.query(PDF).filter(
        and_(PDF.filename == filename, PDF.user_id == user_id)
    ).first()
    return pdf is not None

def get_existing_pdf_data(db: Session, filename: str, user_id: str) -> Dict[str, Any]:
    """Get full data for an existing PDF by filename and user_id"""
    pdf = db.query(PDF).filter(
        and_(PDF.filename == filename, PDF.user_id == user_id)
    ).first()
    
    if not pdf:
        return {}
    
    return {
        "pdf_id": pdf.id,
        "filename": pdf.filename,
        "vector_database_path": pdf.vector_db_path,
        "processing_time": pdf.processing_time,
        "stats": {
            "text_length": pdf.text_length or 0,
            "table_count": pdf.table_count or 0,
            "image_count": pdf.image_count or 0,
            "chunks_stored": pdf.chunks_stored or 0,
            "processing_time": pdf.processing_time or "0:00:00"
        },
        "upload_time": pdf.upload_time
    }

def save_pdf_to_db(
    pdf_id: str, 
    filename: str, 
    vector_db_path: str, 
    processing_time: str, 
    stats: Dict[str, Any], 
    user_id: str, 
    base64_content: str = None, 
    mime_type: str = None, 
    processed_by_llm: bool = False
) -> PDF:
    """Save PDF metadata to the database"""
    db = SessionLocal()
    pdf = PDF(
        id=pdf_id,
        filename=filename,
        vector_db_path=vector_db_path,
        user_id=user_id,
        processing_time=processing_time,
        text_length=stats.get("text_length", 0),
        table_count=stats.get("table_count", 0),
        image_count=stats.get("image_count", 0),
        chunks_stored=stats.get("chunks_stored", 0),
        base64_content=base64_content,
        mime_type=mime_type,
        processed_by_llm=processed_by_llm
    )
    db.add(pdf)
    db.commit()
    db.refresh(pdf)
    return pdf

def validate_user_pdf(db: Session, pdf_id: str, user_id: str) -> bool:
    """Check if a PDF belongs to the specified user"""
    pdf = db.query(PDF).filter(
        and_(PDF.id == pdf_id, PDF.user_id == user_id)
    ).first()
    return pdf is not None

def get_user_pdfs(db: Session, user_id: str):
    # return ORM list — usable by other backend code
    return db.query(PDF).filter(PDF.user_id == user_id).all()




def filter_unprocessed_pdf_ids(db: Session, pdf_ids: List[str], user_id: str) -> List[str]:
    """Return only those IDs from pdf_ids whose processed_by_llm flag is FALSE for this user"""
    if not pdf_ids:
        return []
    
    unprocessed_pdfs = db.query(PDF.id).filter(
        and_(
            PDF.id.in_(pdf_ids),
            PDF.user_id == user_id,
            PDF.processed_by_llm == False
        )
    ).order_by(PDF.upload_time.desc()).all()
    
    return [pdf.id for pdf in unprocessed_pdfs]

def mark_pdfs_as_processed(db: Session, pdf_ids: List[str], user_id: str) -> int:
    """Set processed_by_llm = TRUE for provided pdf_ids owned by user. Returns count updated"""
    if not pdf_ids:
        return 0
    
    updated_count = db.query(PDF).filter(
        and_(
            PDF.id.in_(pdf_ids),
            PDF.user_id == user_id,
            PDF.processed_by_llm == False
        )
    ).update({"processed_by_llm": True}, synchronize_session=False)
    
    db.commit()
    return updated_count

def get_pdf_info(db: Session, pdf_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get PDF information by ID and user"""
    pdf = db.query(PDF).filter(
        and_(PDF.id == pdf_id, PDF.user_id == user_id)
    ).first()
    
    if not pdf:
        return None
    
    return {
        "id": pdf.id,
        "filename": pdf.filename,
        "vector_db_path": pdf.vector_db_path,
        "user_id": pdf.user_id,
        "upload_time": pdf.upload_time,
        "processing_time": pdf.processing_time,
        "text_length": pdf.text_length,
        "table_count": pdf.table_count,
        "image_count": pdf.image_count,
        "chunks_stored": pdf.chunks_stored,
        "base64_content": pdf.base64_content,
        "mime_type": pdf.mime_type,
        "processed_by_llm": pdf.processed_by_llm
    }

def update_pdf_llm_processed_flag(db: Session, pdf_id: str, user_id: str, processed: bool = True) -> bool:
    """Update the processed_by_llm flag for a PDF"""
    pdf = db.query(PDF).filter(
        and_(PDF.id == pdf_id, PDF.user_id == user_id)
    ).first()
    
    if not pdf:
        return False
    
    pdf.processed_by_llm = processed
    db.commit()
    return True

def delete_pdf(db: Session, pdf_id: str, user_id: str) -> bool:
    """Delete a PDF if it belongs to the user"""
    pdf = db.query(PDF).filter(
        and_(PDF.id == pdf_id, PDF.user_id == user_id)
    ).first()
    
    if not pdf:
        return False
    
    db.delete(pdf)
    db.commit()
    return True

# ================================
# Thread Operations
# ================================

def create_thread_id() -> str:
    """Generate a unique thread ID"""
    return str(uuid.uuid4())

def save_thread_to_db(
    db: Session, 
    thread_id: str, 
    pdf_id: Optional[str], 
    user_id: str, 
    title: str = "New Chat", 
    selected_pdf_ids: Optional[List[str]] = None
) -> Thread:
    """Save a new thread to the database with PDF associations"""
    # Create metadata with PDF associations
    if selected_pdf_ids:
        pdf_list = selected_pdf_ids
    elif pdf_id:
        pdf_list = [pdf_id]
    else:
        pdf_list = []
    
    metadata = {"selected_pdf_ids": pdf_list}
    metadata_json = json.dumps(metadata)
    
    thread = Thread(
        id=thread_id,
        pdf_id=pdf_id,
        user_id=user_id,
        title=title,
        metadata_json=metadata_json
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread

def update_thread_title(db: Session, thread_id: str, title: str, user_id: str) -> bool:
    """Update the title of a thread if the user owns it"""
    thread = db.query(Thread).filter(
        and_(Thread.id == thread_id, Thread.user_id == user_id)
    ).first()
    
    if not thread:
        return False
    
    thread.title = title
    db.commit()
    return True

def get_thread_by_id(db: Session, thread_id: str, user_id: str) -> Optional[Thread]:
    """Get thread by ID if user owns it"""
    return db.query(Thread).filter(
        and_(Thread.id == thread_id, Thread.user_id == user_id)
    ).first()

def get_user_threads(db: Session, user_id: str) -> List[Dict[str, Any]]:
    """Get all threads for a user"""
    threads = db.query(Thread).filter(Thread.user_id == user_id).order_by(Thread.last_activity.desc()).all()
    
    formatted_threads = []
    for thread in threads:
        # Parse metadata to get PDF count
        pdf_count = 0
        if thread.metadata_json:
            try:
                metadata = json.loads(thread.metadata_json)
                pdf_count = len(metadata.get('selected_pdf_ids', []))
            except json.JSONDecodeError:
                pass
        
        formatted_threads.append({
            "thread_id": thread.id,
            "title": thread.title,
            "created_time": thread.created_time,
            "last_activity": thread.last_activity,
            "pdf_count": pdf_count
        })
    
    return formatted_threads

def get_thread_pdfs(db: Session, thread_id: str, user_id: str) -> List[str]:
    """Get all PDF IDs associated with a specific thread"""
    thread = get_thread_by_id(db, thread_id, user_id)
    if not thread or not thread.metadata_json:
        return []
    
    try:
        metadata = json.loads(thread.metadata_json)
        pdf_ids = metadata.get('selected_pdf_ids', [])
        
        # Validate that these PDFs actually belong to this user
        valid_pdf_ids = []
        for pdf_id in pdf_ids:
            if validate_user_pdf(db, pdf_id, user_id):
                valid_pdf_ids.append(pdf_id)
        
        return valid_pdf_ids
    except json.JSONDecodeError:
        return []

def validate_thread_pdf_access(db: Session, thread_id: str, pdf_id: str, user_id: str) -> bool:
    """Check if a user can access a PDF in a specific thread"""
    thread = get_thread_by_id(db, thread_id, user_id)
    if not thread or not thread.metadata_json:
        return False
    
    try:
        metadata = json.loads(thread.metadata_json)
        selected_pdf_ids = metadata.get('selected_pdf_ids', [])
        return pdf_id in selected_pdf_ids
    except json.JSONDecodeError:
        return False

def update_thread_pdfs(db: Session, thread_id: str, user_id: str, selected_pdf_ids: List[str]) -> bool:
    """Update the selected PDFs for a thread"""
    thread = get_thread_by_id(db, thread_id, user_id)
    if not thread:
        return False
    
    # Validate that all PDFs belong to the user
    for pdf_id in selected_pdf_ids:
        if not validate_user_pdf(db, pdf_id, user_id):
            return False
    
    metadata = {"selected_pdf_ids": selected_pdf_ids}
    thread.metadata_json = json.dumps(metadata)
    db.commit()
    return True

def remove_pdf_from_thread(db: Session, thread_id: str, pdf_id: str, user_id: str) -> bool:
    """Remove a PDF from a thread's selected PDFs"""
    thread = get_thread_by_id(db, thread_id, user_id)
    if not thread or not thread.metadata_json:
        return False
    
    try:
        metadata = json.loads(thread.metadata_json)
        selected_pdf_ids = metadata.get('selected_pdf_ids', [])
        
        if pdf_id in selected_pdf_ids:
            selected_pdf_ids.remove(pdf_id)
            metadata["selected_pdf_ids"] = selected_pdf_ids
            thread.metadata_json = json.dumps(metadata)
            db.commit()
            return True
        return False
    except json.JSONDecodeError:
        return False

# ================================
# Message Operations
# ================================

def save_message_to_db(db: Session, thread_id: str, message_type: str, content: str) -> Message:
    """Save a message to the database"""
    message = Message(
        thread_id=thread_id,
        message_type=message_type,
        content=content
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

def get_thread_messages(db: Session, thread_id: str, user_id: str) -> Dict[str, Any]:
    """Retrieve all messages for a thread if the user has access"""
    # Verify user owns the thread
    thread = get_thread_by_id(db, thread_id, user_id)
    if not thread:
        raise ValueError("Access denied to this thread")
    
    messages = db.query(Message).filter(Message.thread_id == thread_id).order_by(Message.timestamp.asc()).all()
    
    formatted_messages = []
    for message in messages:
        formatted_messages.append({
            "type": message.message_type,
            "content": message.content,
            "timestamp": message.timestamp
        })
    
    return {
        "thread_id": thread_id,
        "title": thread.title,
        "messages": formatted_messages
    }



# ================================
# API Key Operations
# ================================

# from fastapi import HTTPException, Depends, Header
# from sqlalchemy.orm import Session
# from backend.models import Api_key
# from backend.database import get_db
# from fastapi import FastAPI, Security
# from fastapi.security.api_key import APIKeyHeader
# api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# def get_current_api_key(x_api_key:str= Security(api_key_header),db: Session = Depends(get_db)) -> Api_key:

#     api_key_obj = db.query(Api_key).filter(Api_key.api_key == x_api_key).first()
#     if not api_key_obj:
#         raise HTTPException(status_code=401, detail="Invalid or missing API key")
#     return api_key_obj








# ================================
# Project Operations
# ================================

def get_organization_by_id(db: Session, org_id: str) -> Optional[Organization]:
    """Fetch organization by id."""
    return db.query(Organization).filter(Organization.id == org_id).first()

def get_project_by_id(db: Session, project_id: str) -> Optional[Project]:
    """Fetch project by id."""
    return db.query(Project).filter(Project.id == project_id).first()

def get_project_by_name_in_org(db: Session, org_id: str, name: str) -> Optional[Project]:
    """Fetch a project by name within an organization."""
    return db.query(Project).filter(
        Project.org_id == org_id,
        Project.name == name
    ).first()

def create_project(
    db: Session,
    org_id: str,
    owner_user_id: str,
    name: str,
    description: Optional[str],
    project_key: str
) -> Project:
    """Create a new project within an organization owned by a user."""
    # Uniqueness enforced also by DB constraint, but check early for better error messages
    existing = get_project_by_name_in_org(db, org_id, name)
    if existing:
        raise ValueError("Project name already exists in this organization")

    project = Project(
        id=str(uuid.uuid4()),
        org_id=org_id,
        owner_user_id=owner_user_id,
        name=name,
        description=description,
        project_key=project_key,
        is_active=True
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

def list_user_projects(db: Session, user_id: str) -> List[Dict[str, Any]]:
    """List projects owned by a user (within their organization)."""
    projects = db.query(Project).filter(Project.owner_user_id == user_id).order_by(Project.created_at.desc()).all()
    return [
        {
            "project_id": p.id,
            "name": p.name,
            "description": p.description,
            "org_id": p.org_id,
            "project_key": p.project_key,
            "is_active": p.is_active,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        }
        for p in projects
    ]


# ================================
# Token Usage Tracking Operations
# ================================

def count_tokens_with_tiktoken(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Count tokens using Tiktoken for accurate token counting.
    
    Args:
        text: Text to count tokens for
        model: OpenAI model name (default: gpt-3.5-turbo)
    
    Returns:
        Number of tokens in the text
    """
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        print(f"WARNING: Failed to count tokens with tiktoken: {e}")
        # Fallback to character counting if tiktoken fails
        return len(text)

def record_token_usage(
    db: Session,
    api_key_id: str,
    endpoint: str,
    operation_type: str,
    input_text: str = "",
    output_text: str = "",
    model: str = "gpt-3.5-turbo"
) -> None:
    """Record token usage for API key monitoring using Tiktoken.
    
    Args:
        db: Database session
        api_key_id: ID of the API key used
        endpoint: API endpoint called (e.g., "vectors/insert", "vectors/query")
        operation_type: Type of operation (e.g., "insert", "query", "generate")
        input_text: Input text to count tokens for
        output_text: Output text to count tokens for
        model: OpenAI model name for tokenization
    """
    try:
        # Count tokens using Tiktoken
        input_tokens = count_tokens_with_tiktoken(input_text, model)
        output_tokens = count_tokens_with_tiktoken(output_text, model)
        total_tokens = input_tokens + output_tokens
        
        # Update cumulative total in api_keys table first
        api_key_record = db.query(Api_key).filter(Api_key.id == api_key_id).first()
        if api_key_record:
            api_key_record.total_tokens_used += total_tokens
            cumulative_total = api_key_record.total_tokens_used
            print(f"DEBUG: Updated API key {api_key_id} total_tokens_used to {cumulative_total}")
            
            # ✅ Update user-level token usage
            user_token_usage = db.query(UserTokenUsage).filter(UserTokenUsage.user_id == api_key_record.user_id).first()
            if user_token_usage:
                user_token_usage.total_user_token_usage += total_tokens
                print(f"DEBUG: Updated user {api_key_record.user_id} total_user_token_usage to {user_token_usage.total_user_token_usage}")
            else:
                # Create new UserTokenUsage record if it doesn't exist
                user_token_usage = UserTokenUsage(
                    user_id=api_key_record.user_id,
                    total_user_token_usage=total_tokens
                )
                db.add(user_token_usage)
                print(f"DEBUG: Created new UserTokenUsage record for user {api_key_record.user_id} with {total_tokens} tokens")
            
            # ✅ Update subscription token usage
            subscription = db.query(Subscription).filter(Subscription.org_id == api_key_record.org_id).first()
            if subscription:
                subscription.used_tokens += total_tokens
                print(f"DEBUG: Updated subscription {subscription.id} used_tokens to {subscription.used_tokens}")
            else:
                print(f"WARNING: No subscription found for org_id {api_key_record.org_id}")
        else:
            print(f"WARNING: API key {api_key_id} not found for total_tokens_used update")
            cumulative_total = total_tokens  # Fallback to just this call's total
        
        # Create token usage record with cumulative total
        token_record = Tokens(
            api_key_id=api_key_id,
            endpoint=endpoint,
            operation_type=operation_type,
            input_characters=input_tokens,  # Now storing actual tokens, not characters
            output_characters=output_tokens,  # Now storing actual tokens, not characters
            total_characters=total_tokens,  # Now storing actual tokens, not characters
            total_usage=cumulative_total  # Cumulative total up to this point
        )
        
        db.add(token_record)
        
        db.commit()
        print(f"DEBUG: Recorded token usage - API Key: {api_key_id}, Endpoint: {endpoint}, Input tokens: {input_tokens}, Output tokens: {output_tokens}, Total tokens: {total_tokens}")
        return total_tokens


        
    except Exception as e:
        print(f"ERROR: Failed to record token usage: {e}")
        db.rollback()


def record_aggregated_token_usage(
    db: Session,
    api_key_id: str,
    endpoint: str,
    operation_type: str,
    total_tokens: int
) -> None:
    """Record aggregated token usage for operations that use multiple LLM calls.
    
    Args:
        db: Database session
        api_key_id: ID of the API key used
        endpoint: API endpoint called
        operation_type: Type of operation
        total_tokens: Total tokens used across all LLM calls
    """
    try:
        # Update cumulative total in api_keys table first
        api_key_record = db.query(Api_key).filter(Api_key.id == api_key_id).first()
        if api_key_record:
            api_key_record.total_tokens_used += total_tokens
            cumulative_total = api_key_record.total_tokens_used
            print(f"DEBUG: Updated API key {api_key_id} total_tokens_used to {cumulative_total}")
            
            # ✅ Update user-level token usage
            user_token_usage = db.query(UserTokenUsage).filter(UserTokenUsage.user_id == api_key_record.user_id).first()
            if user_token_usage:
                user_token_usage.total_user_token_usage += total_tokens
                print(f"DEBUG: Updated user {api_key_record.user_id} total_user_token_usage to {user_token_usage.total_user_token_usage}")
            else:
                # Create new UserTokenUsage record if it doesn't exist
                user_token_usage = UserTokenUsage(
                    user_id=api_key_record.user_id,
                    total_user_token_usage=total_tokens
                )
                db.add(user_token_usage)
                print(f"DEBUG: Created new UserTokenUsage record for user {api_key_record.user_id} with {total_tokens} tokens")
            
            # ✅ Update subscription token usage
            subscription = db.query(Subscription).filter(Subscription.org_id == api_key_record.org_id).first()
            if subscription:
                subscription.used_tokens += total_tokens
                print(f"DEBUG: Updated subscription {subscription.id} used_tokens to {subscription.used_tokens}")
            else:
                print(f"WARNING: No subscription found for org_id {api_key_record.org_id}")
        else:
            print(f"WARNING: API key {api_key_id} not found for total_tokens_used update")
            cumulative_total = total_tokens  # Fallback to just this call's total
        
        # Create token usage record with aggregated total
        token_record = Tokens(
            api_key_id=api_key_id,
            endpoint=endpoint,
            operation_type=operation_type,
            input_characters=0,  # No direct input for aggregated usage
            output_characters=total_tokens,  # All tokens are considered "output" from processing
            total_characters=total_tokens,
            total_usage=cumulative_total  # Cumulative total up to this point
        )
        
        db.add(token_record)
        
        db.commit()
        print(f"DEBUG: Recorded aggregated token usage - API Key: {api_key_id}, Endpoint: {endpoint}, Total tokens: {total_tokens}")
        
    except Exception as e:
        print(f"ERROR: Failed to record aggregated token usage: {e}")
        db.rollback()




from fastapi import Security, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.models import Api_key, Subscription
from backend.database import get_db
from backend.enum.enum import StatusEnum

# Your existing header definition
from fastapi.security import APIKeyHeader
api_key_header = APIKeyHeader(name="x-api-key", auto_error=True)


def get_current_api_key(
    x_api_key: str = Security(api_key_header),
    db: Session = Depends(get_db)
) -> Api_key:
    """
    Validates API key and ensures subscription is active.
    Returns Api_key object + linked subscription for quota checks.
    """

    # 1. Validate API key
    api_key_obj = db.query(Api_key).filter(Api_key.api_key == x_api_key).first()
    if not api_key_obj:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    # 2. Fetch subscription via org_id
    subscription = db.query(Subscription).filter(Subscription.org_id == api_key_obj.org_id).first()
    if not subscription:
        raise HTTPException(status_code=403, detail="No subscription found for organization")

    # 3. Check subscription status
    if subscription.status != StatusEnum.active:
        raise HTTPException(status_code=403, detail=f"Subscription is {subscription.status}")

    # 4. Check token quota
    if subscription.monthly_limit_tokens is not None:
        if subscription.used_tokens >= subscription.monthly_limit_tokens:
            raise HTTPException(status_code=402, detail="Token quota exceeded.")

    # ✅ return API key + subscription together
    return {"api_key": api_key_obj, "subscription": subscription}


# ================================
# User Token Management Helper Functions
# ================================

def get_user_total_tokens(db: Session, user_id: str) -> int:
    """
    Get the total token usage for a user across all their API keys.
    
    Args:
        db: Database session
        user_id: User ID to get token usage for
    
    Returns:
        Total tokens used by the user
    """
    user_token_usage = db.query(UserTokenUsage).filter(UserTokenUsage.user_id == user_id).first()
    if user_token_usage:
        return user_token_usage.total_user_token_usage
    return 0


def get_user_token_usage_details(db: Session, user_id: str) -> Dict[str, Any]:
    """
    Get detailed token usage information for a user.
    
    Args:
        db: Database session
        user_id: User ID to get details for
    
    Returns:
        Dictionary with token usage details
    """
    # Get user's API keys
    api_keys = db.query(Api_key).filter(Api_key.user_id == user_id).all()
    
    # Get user's total token usage
    user_total = get_user_total_tokens(db, user_id)
    
    # Get subscription info
    user = db.query(User).filter(User.id == user_id).first()
    subscription = None
    if user and user.org_id:
        subscription = db.query(Subscription).filter(Subscription.org_id == user.org_id).first()
    
    # Calculate API key totals (for verification)
    api_key_totals = [api_key.total_tokens_used for api_key in api_keys]
    calculated_total = sum(api_key_totals)
    
    return {
        "user_id": user_id,
        "total_tokens_used": user_total,
        "calculated_total": calculated_total,
        "is_consistent": user_total == calculated_total,
        "api_keys": [
            {
                "api_key_id": api_key.id,
                "tokens_used": api_key.total_tokens_used,
                "created_at": api_key.created_at
            }
            for api_key in api_keys
        ],
        "subscription": {
            "used_tokens": subscription.used_tokens if subscription else 0,
            "token_limit": subscription.monthly_limit_tokens if subscription else 0,
            "remaining_tokens": (
                subscription.monthly_limit_tokens - subscription.used_tokens
                if subscription and subscription.monthly_limit_tokens is not None
                else 0
            )
        } if subscription else None
    }


def sync_user_token_totals(db: Session, user_id: str) -> bool:
    """
    Sync user token totals by recalculating from all API keys.
    Useful for fixing data inconsistencies.
    
    Args:
        db: Database session
        user_id: User ID to sync
    
    Returns:
        True if sync was successful, False otherwise
    """
    try:
        # Calculate total from all API keys
        api_keys = db.query(Api_key).filter(Api_key.user_id == user_id).all()
        calculated_total = sum(api_key.total_tokens_used for api_key in api_keys)
        
        # Update or create UserTokenUsage record
        user_token_usage = db.query(UserTokenUsage).filter(UserTokenUsage.user_id == user_id).first()
        if user_token_usage:
            user_token_usage.total_user_token_usage = calculated_total
            print(f"DEBUG: Synced user {user_id} total_user_token_usage to {calculated_total}")
        else:
            user_token_usage = UserTokenUsage(
                user_id=user_id,
                total_user_token_usage=calculated_total
            )
            db.add(user_token_usage)
            print(f"DEBUG: Created UserTokenUsage record for user {user_id} with {calculated_total} tokens")
        
        db.commit()
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to sync user token totals for {user_id}: {e}")
        db.rollback()
        return False


def get_user_remaining_tokens(db: Session, user_id: str) -> int:
    """
    Get the remaining tokens available for a user.
    
    Args:
        db: Database session
        user_id: User ID to check
    
    Returns:
        Number of tokens remaining, or -1 if no limit
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.org_id:
        return -1
    
    subscription = db.query(Subscription).filter(Subscription.org_id == user.org_id).first()
    if not subscription:
        return -1
    
    used_tokens = get_user_total_tokens(db, user_id)
    if subscription.monthly_limit_tokens is None:
        return -1
    remaining = subscription.monthly_limit_tokens - used_tokens
    return max(0, remaining)


def check_user_token_quota(db: Session, user_id: str, required_tokens: int = 0) -> Dict[str, Any]:
    """
    Check if a user has enough tokens remaining for an operation.
    
    Args:
        db: Database session
        user_id: User ID to check
        required_tokens: Number of tokens needed for the operation
    
    Returns:
        Dictionary with quota check results
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.org_id:
        return {
            "has_quota": False,
            "reason": "User not found or not in organization",
            "remaining_tokens": 0,
            "required_tokens": required_tokens
        }
    
    subscription = db.query(Subscription).filter(Subscription.org_id == user.org_id).first()
    if not subscription:
        return {
            "has_quota": False,
            "reason": "No subscription found",
            "remaining_tokens": 0,
            "required_tokens": required_tokens
        }
    
    used_tokens = get_user_total_tokens(db, user_id)
    if subscription.monthly_limit_tokens is None:
        return {
            "has_quota": True,
            "reason": "No token limit",
            "remaining_tokens": -1,
            "required_tokens": required_tokens,
            "used_tokens": used_tokens,
            "token_limit": None,
            "subscription_status": subscription.status.value if subscription.status else "unknown",
        }

    remaining_tokens = subscription.monthly_limit_tokens - used_tokens
    return {
        "has_quota": remaining_tokens >= required_tokens,
        "remaining_tokens": max(0, remaining_tokens),
        "required_tokens": required_tokens,
        "used_tokens": used_tokens,
        "token_limit": subscription.monthly_limit_tokens,
        "subscription_status": subscription.status.value if subscription.status else "unknown",
    }


def reset_user_token_usage(db: Session, user_id: str) -> bool:
    """
    Reset all token usage for a user (useful for testing or manual resets).
    
    Args:
        db: Database session
        user_id: User ID to reset
    
    Returns:
        True if reset was successful, False otherwise
    """
    try:
        # Reset all API key totals
        api_keys = db.query(Api_key).filter(Api_key.user_id == user_id).all()
        for api_key in api_keys:
            api_key.total_tokens_used = 0
        
        # Reset user total
        user_token_usage = db.query(UserTokenUsage).filter(UserTokenUsage.user_id == user_id).first()
        if user_token_usage:
            user_token_usage.total_user_token_usage = 0
        
        # Reset subscription total
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.org_id:
            subscription = db.query(Subscription).filter(Subscription.org_id == user.org_id).first()
            if subscription:
                subscription.used_tokens = 0
        
        db.commit()
        print(f"DEBUG: Reset all token usage for user {user_id}")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to reset token usage for user {user_id}: {e}")
        db.rollback()
        return False


