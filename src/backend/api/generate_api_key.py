from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import secrets
from backend.database import get_db
from backend.crud import get_user_by_id, get_organization_by_id, get_current_user_from_id
from backend.models import Api_key, Project

router = APIRouter()


def _validate_dashboard_project_access(
    db: Session, org_id: str, user_id: str, project_id: str
) -> Project:
    """Shared checks for dashboard project routes (trusted user_id + org_id query params)."""
    if not org_id or not user_id:
        raise HTTPException(status_code=400, detail="org_id and user_id are required")

    current_user = get_current_user_from_id(user_id, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid user: User not found")

    user_record = get_user_by_id(db, user_id)
    if not user_record or not user_record.org_id:
        raise HTTPException(status_code=403, detail="User is not assigned to an organization")

    if user_record.org_id != org_id:
        raise HTTPException(status_code=403, detail="org_id does not match the user's organization")

    org = get_organization_by_id(db, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.org_id == org_id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=404, detail="Project not found or does not belong to this organization"
        )
    return project


@router.get("/projects/{project_id}/api_keys")
async def list_project_api_keys(
    project_id: str, org_id: str, user_id: str, db: Session = Depends(get_db)
):
    """List API keys for a project (full key values for dashboard owners; stored server-side)."""
    _validate_dashboard_project_access(db, org_id, user_id, project_id)

    keys = (
        db.query(Api_key)
        .filter(Api_key.project_id == project_id, Api_key.org_id == org_id)
        .order_by(Api_key.created_at.desc())
        .all()
    )

    return {
        "project_id": project_id,
        "api_keys": [
            {
                "id": k.id,
                "api_key": k.api_key,
                "created_at": k.created_at.isoformat() if k.created_at else None,
            }
            for k in keys
        ],
    }


@router.post("/projects/{project_id}/generate_api_key")
async def generate_api_key(project_id: str, org_id: str, user_id: str, db: Session = Depends(get_db)):
    """Generate an API key for a project.
    
    Input: project_id, org_id, user_id as URL parameters
    Output: { "api_key": "abc123...", "project_id": "proj_456", "org_id": "org_123" }
    """
    try:
        _validate_dashboard_project_access(db, org_id, user_id, project_id)

        # Generate API key
        api_key = secrets.token_hex(32)
        new_api_key = Api_key(
            org_id=org_id,
            project_id=project_id,
            api_key=api_key,
            user_id=user_id
        )
        db.add(new_api_key)
        db.commit()
        db.refresh(new_api_key)
        
        return {
            "api_key": new_api_key.api_key,
            "project_id": project_id,
            "org_id": org_id,
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate API key: {str(e)}")