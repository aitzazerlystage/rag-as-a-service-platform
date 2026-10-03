from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import secrets
from backend.database import get_db
from backend.crud import (
    get_user_by_id,
    get_organization_by_id,
    get_project_by_id,
    get_project_by_name_in_org,
    create_project,
    get_current_user_from_id,
    list_user_projects,
)
from backend.api.auth import decode_access_token
from backend.models import Api_key, ProjectUpload, Subscription, Tokens
from services.service_factory import create_pinecone_service, get_namespace_from_auth

router = APIRouter()


def _user_id_for_dashboard_delete(
    authorization: Optional[str], user_id_query: Optional[str]
) -> str:
    """Prefer valid JWT; otherwise accept user_id query (same trust model as GET .../uploads)."""
    if authorization:
        raw = authorization.strip()
        if raw.lower().startswith("bearer "):
            raw = raw[7:].strip()
        if raw:
            payload = decode_access_token(raw)
            if payload and payload.get("sub"):
                return str(payload["sub"])
    if user_id_query and user_id_query.strip():
        return user_id_query.strip()
    raise HTTPException(
        status_code=401,
        detail="Invalid or expired token — sign in again, or pass user_id.",
    )


@router.get("/projects")
async def list_projects_endpoint(user_id: str, db: Session = Depends(get_db)):
    """List projects owned by the user (same auth model as create: trusted user_id)."""
    if not user_id:
        raise HTTPException(status_code=401, detail="user_id is required")
    current_user = get_current_user_from_id(user_id, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid user: User not found")
    user_record = get_user_by_id(db, user_id)
    if not user_record or not user_record.org_id:
        raise HTTPException(status_code=403, detail="User is not assigned to an organization")
    projects = list_user_projects(db, user_id)
    return {"projects": projects, "org_id": user_record.org_id}


@router.get("/projects/{project_id}/uploads")
async def list_project_uploads(project_id: str, user_id: str, db: Session = Depends(get_db)):
    """Files recorded for this project from vectors/upload (newest first)."""
    if not user_id:
        raise HTTPException(status_code=401, detail="user_id is required")
    current_user = get_current_user_from_id(user_id, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid user: User not found")
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_user_id != user_id:
        raise HTTPException(status_code=403, detail="Not allowed to view this project")
    rows = (
        db.query(ProjectUpload)
        .filter(ProjectUpload.project_id == project_id)
        .order_by(ProjectUpload.created_at.desc())
        .all()
    )
    return {
        "project_id": project_id,
        "uploads": [
            {
                "id": r.id,
                "original_filename": r.original_filename,
                "doc_id": r.doc_id,
                "rag_inserted": r.rag_inserted,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.delete("/projects/{project_id}/uploads/{upload_id}")
async def delete_project_upload(
    project_id: str,
    upload_id: str,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Remove upload log row; if doc_id exists, delete vectors from Pinecone (same as /vectors/delete)."""
    uid = _user_id_for_dashboard_delete(authorization, user_id)
    current_user = get_current_user_from_id(uid, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid user: User not found")

    user_id = uid
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_user_id != user_id:
        raise HTTPException(status_code=403, detail="Not allowed to modify this project")

    row = (
        db.query(ProjectUpload)
        .filter(ProjectUpload.id == upload_id, ProjectUpload.project_id == project_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Upload not found")

    doc_id = row.doc_id
    rag_inserted = row.rag_inserted
    deleted_from_rag = 0

    if doc_id and rag_inserted:
        api_key_row = (
            db.query(Api_key)
            .filter(Api_key.project_id == project_id, Api_key.user_id == user_id)
            .first()
        )
        if not api_key_row:
            raise HTTPException(
                status_code=400,
                detail="No API key found for this project — create an API key to manage vectors.",
            )
        sub = (
            db.query(Subscription)
            .filter(Subscription.org_id == project.org_id)
            .first()
        )
        if not sub:
            raise HTTPException(status_code=500, detail="Subscription not found for organization")

        auth = {"api_key": api_key_row, "subscription": sub}
        pinecone_service = create_pinecone_service(auth=auth)
        namespace = get_namespace_from_auth(auth)
        filter_metadata = {
            "org_id": str(api_key_row.org_id),
            "project_id": str(api_key_row.project_id),
            "doc_id": doc_id,
        }
        try:
            deleted_from_rag = await pinecone_service.delete_pdf_vectors(
                chunk_ids=[],
                filter_metadata=filter_metadata,
                namespace=namespace,
            )
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to delete vectors from index: {str(e)}",
            ) from e
    elif doc_id and not rag_inserted:
        # No vectors were stored; only remove DB row
        pass

    db.delete(row)
    db.commit()
    return {
        "ok": True,
        "deleted_upload_id": upload_id,
        "deleted_from_rag": int(deleted_from_rag),
        "doc_id": doc_id,
    }


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Delete project: remove Pinecone vectors per distinct doc_id (RAG uploads), then DB rows."""
    uid = _user_id_for_dashboard_delete(authorization, user_id)
    current_user = get_current_user_from_id(uid, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid user: User not found")

    user_id = uid
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_user_id != user_id:
        raise HTTPException(status_code=403, detail="Not allowed to modify this project")

    upload_rows = (
        db.query(ProjectUpload)
        .filter(ProjectUpload.project_id == project_id)
        .order_by(ProjectUpload.created_at.desc())
        .all()
    )
    rag_rows = [r for r in upload_rows if r.doc_id and r.rag_inserted]
    doc_ids_ordered: list[str] = []
    seen_doc: set[str] = set()
    for r in rag_rows:
        if r.doc_id not in seen_doc:
            seen_doc.add(r.doc_id)
            doc_ids_ordered.append(r.doc_id)

    deleted_vectors_total = 0
    if doc_ids_ordered:
        api_key_row = (
            db.query(Api_key)
            .filter(Api_key.project_id == project_id, Api_key.user_id == user_id)
            .first()
        )
        if not api_key_row:
            raise HTTPException(
                status_code=400,
                detail="No API key found for this project — create an API key to delete RAG vectors.",
            )
        sub = (
            db.query(Subscription)
            .filter(Subscription.org_id == project.org_id)
            .first()
        )
        if not sub:
            raise HTTPException(status_code=500, detail="Subscription not found for organization")

        auth = {"api_key": api_key_row, "subscription": sub}
        pinecone_service = create_pinecone_service(auth=auth)
        namespace = get_namespace_from_auth(auth)
        for doc_id in doc_ids_ordered:
            filter_metadata = {
                "org_id": str(api_key_row.org_id),
                "project_id": str(api_key_row.project_id),
                "doc_id": doc_id,
            }
            try:
                deleted_vectors_total += await pinecone_service.delete_pdf_vectors(
                    chunk_ids=[],
                    filter_metadata=filter_metadata,
                    namespace=namespace,
                )
            except Exception as e:
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to delete vectors from index: {str(e)}",
                ) from e

    api_keys_for_project = (
        db.query(Api_key).filter(Api_key.project_id == project_id).all()
    )
    for key_row in api_keys_for_project:
        db.query(Tokens).filter(Tokens.api_key_id == key_row.id).delete(
            synchronize_session=False
        )
        db.delete(key_row)

    db.delete(project)
    db.commit()
    return {
        "ok": True,
        "project_id": project_id,
        "doc_ids_deleted": doc_ids_ordered,
        "deleted_vectors_total": int(deleted_vectors_total),
    }


@router.post("/projects/create")
async def create_project_endpoint(request: Dict[str, Any], db: Session = Depends(get_db)):
    """Create a new project under the caller's organization.

    Input: { "user_id" : "user_123" , "org_id": "org_123", "project_name": "AI Research", "description": "optional" }
    Output: { "project_id": "proj_456", "project_key": "abc123xyz" }
    """
    try:
        # Validate input
        org_id = request.get("org_id")
        project_name = request.get("project_name")
        description = request.get("description", None)

        if not org_id or not project_name:
            raise HTTPException(status_code=400, detail="org_id and project_name are required")

        # Auth: ensure requester is valid and belongs to the org
        user_token = request.get("access_token")
        user_id = request.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="user_id is required")
        
        current_user = get_current_user_from_id(user_id, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Invalid user: User not found")

        user_record = get_user_by_id(db, user_id)
        if not user_record or not user_record.org_id:
            raise HTTPException(status_code=403, detail="User is not assigned to an organization")

        if user_record.org_id != org_id:
            raise HTTPException(status_code=403, detail="org_id does not match the user's organization")

        # Check org exists
        org = get_organization_by_id(db, org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Enforce unique name in org
        if get_project_by_name_in_org(db, org_id, project_name):
            raise HTTPException(status_code=400, detail="Project name already exists in this organization")

        # Generate a project key (short, random, URL-safe)
        project_key = secrets.token_urlsafe(16)

        # Create project
        project = create_project(
            db=db,
            org_id=org_id,
            owner_user_id=user_id,
            name=project_name,
            description=description,
            project_key=project_key,
        )

        
        return {
            "project_id": project.id,
            "project_key": project.project_key,
            "name": project.name,
            "org_id": project.org_id,
            "owner_user_id": project.owner_user_id,
            "created_at": project.created_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")
