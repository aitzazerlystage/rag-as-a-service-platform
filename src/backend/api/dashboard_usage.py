"""Dashboard usage metrics for JWT-authenticated web console (aggregates all API keys for the user)."""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.api.auth import decode_access_token
from backend.database import get_db
from backend.models import Api_key, Project, Subscription, Tokens, User

router = APIRouter()


def _each_calendar_day(start: datetime, end: datetime) -> List[date]:
    """Inclusive UTC calendar days from start through end (date parts)."""
    d0 = start.date() if isinstance(start, datetime) else start
    d1 = end.date() if isinstance(end, datetime) else end
    out: List[date] = []
    cur = d0
    while cur <= d1:
        out.append(cur)
        cur = cur + timedelta(days=1)
    return out


def _build_usage_payload(
    *,
    user_id: str,
    days: int,
    db: Session,
    key_ids: Optional[List[str]] = None,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Build usage JSON for either all keys for user (key_ids=None) or a filtered subset.
    Returns (payload, error_message). error_message set if key_ids invalid for user.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    api_keys: List[Api_key] = (
        db.query(Api_key).filter(Api_key.user_id == user_id).all()
    )
    if key_ids is not None:
        allowed = {k.id for k in api_keys}
        if not key_ids or any(k not in allowed for k in key_ids):
            return {}, "API key not found or not owned by user"
        api_keys = [k for k in api_keys if k.id in key_ids]

    key_ids_list = [k.id for k in api_keys]

    user = db.query(User).filter(User.id == user_id).first()
    subscription_payload = None
    if user and user.org_id:
        sub = (
            db.query(Subscription)
            .filter(Subscription.org_id == user.org_id)
            .first()
        )
        if sub:
            subscription_payload = {
                "id": sub.id,
                "plan": sub.plan.value if sub.plan else None,
                "status": sub.status.value if sub.status else None,
                "monthly_limit_tokens": sub.monthly_limit_tokens,
                "used_tokens": sub.used_tokens,
                "monthly_limit_queries": sub.monthly_limit_queries,
                "used_queries": sub.used_queries,
                "monthly_limit_ingest": sub.monthly_limit_ingest,
                "used_ingest": sub.used_ingest,
            }

    if not key_ids_list:
        empty_daily = [
            {
                "date": d.isoformat(),
                "requests": 0,
                "tokens": 0,
                "total_chars_legacy": 0,
            }
            for d in _each_calendar_day(start_date, end_date)
        ]
        return (
            {
                "user_id": user_id,
                "period_days": days,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "subscription": subscription_payload,
                "summary": {
                    "total_requests": 0,
                    "total_input_characters": 0,
                    "total_output_characters": 0,
                    "total_characters": 0,
                    "total_tokens": 0,
                    "average_chars_per_request": 0,
                },
                "api_keys": [],
                "endpoint_breakdown": {},
                "daily_usage": {},
                "daily_series": empty_daily,
            },
            None,
        )

    token_records = (
        db.query(Tokens)
        .filter(
            and_(
                Tokens.api_key_id.in_(key_ids_list),
                Tokens.created_at >= start_date,
                Tokens.created_at <= end_date,
            )
        )
        .all()
    )

    total_input = sum(r.input_characters for r in token_records)
    total_output = sum(r.output_characters for r in token_records)
    total_chars = sum(r.total_characters for r in token_records)
    n = len(token_records)

    endpoint_stats: Dict[str, Dict[str, Any]] = {}
    for record in token_records:
        ep = record.endpoint
        if ep not in endpoint_stats:
            endpoint_stats[ep] = {
                "count": 0,
                "input_chars": 0,
                "output_chars": 0,
                "total_chars": 0,
                "tokens": 0,
            }
        endpoint_stats[ep]["count"] += 1
        endpoint_stats[ep]["input_chars"] += record.input_characters
        endpoint_stats[ep]["output_chars"] += record.output_characters
        endpoint_stats[ep]["total_chars"] += record.total_characters
        endpoint_stats[ep]["tokens"] = endpoint_stats[ep]["total_chars"]

    calendar_days = _each_calendar_day(start_date, end_date)
    daily_stats: Dict[str, Dict[str, Any]] = {}
    for d in calendar_days:
        ds = d.isoformat()
        daily_stats[ds] = {"count": 0, "total_chars": 0, "tokens": 0}

    for record in token_records:
        date_str = record.created_at.date().isoformat()
        if date_str not in daily_stats:
            daily_stats[date_str] = {"count": 0, "total_chars": 0, "tokens": 0}
        daily_stats[date_str]["count"] += 1
        daily_stats[date_str]["total_chars"] += record.total_characters
        daily_stats[date_str]["tokens"] += record.total_characters

    daily_series: List[Dict[str, Any]] = []
    for d in calendar_days:
        ds = d.isoformat()
        row = daily_stats.get(ds, {"count": 0, "total_chars": 0, "tokens": 0})
        daily_series.append(
            {
                "date": ds,
                "requests": row["count"],
                "tokens": row["tokens"],
                "total_chars_legacy": row["total_chars"],
            }
        )

    project_names: Dict[str, str] = {}
    for k in api_keys:
        proj = db.query(Project).filter(Project.id == k.project_id).first()
        project_names[k.project_id] = proj.name if proj else k.project_id

    per_key: List[Dict[str, Any]] = []
    for k in api_keys:
        kr = [r for r in token_records if r.api_key_id == k.id]
        per_key.append(
            {
                "api_key_id": k.id,
                "project_id": k.project_id,
                "project_name": project_names.get(k.project_id, k.project_id),
                "masked_key": f"…{k.api_key[-8:]}" if len(k.api_key) >= 8 else "••••",
                "total_tokens_used_cumulative": k.total_tokens_used,
                "period_requests": len(kr),
                "period_total_characters": sum(r.total_characters for r in kr),
                "period_tokens": sum(r.total_characters for r in kr),
            }
        )

    payload: Dict[str, Any] = {
        "user_id": user_id,
        "period_days": days,
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "subscription": subscription_payload,
        "summary": {
            "total_requests": n,
            "total_input_characters": total_input,
            "total_output_characters": total_output,
            "total_characters": total_chars,
            "total_tokens": total_chars,
            "average_chars_per_request": (total_chars / n) if n else 0,
        },
        "api_keys": per_key,
        "endpoint_breakdown": endpoint_stats,
        "daily_usage": daily_stats,
        "daily_series": daily_series,
    }
    return payload, None


def _user_id_for_dashboard(
    authorization: Optional[str], user_id_query: Optional[str]
) -> str:
    """Prefer valid JWT; else accept user_id query (same pattern as project dashboard APIs)."""
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


@router.get("/dashboard/usage")
async def get_dashboard_usage(
    days: int = Query(30, ge=1, le=365),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Token usage across all API keys owned by the logged-in user,
    plus subscription quota snapshot. Includes `daily_series` (day-by-day tokens).
    """
    uid = _user_id_for_dashboard(authorization, user_id)
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    payload, err = _build_usage_payload(user_id=uid, days=days, db=db, key_ids=None)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return payload


@router.get("/dashboard/usage/key/{api_key_id}")
async def get_dashboard_usage_for_key(
    api_key_id: str,
    days: int = Query(30, ge=1, le=365),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Usage for a single API key (must belong to the logged-in user)."""
    uid = _user_id_for_dashboard(authorization, user_id)
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    payload, err = _build_usage_payload(
        user_id=uid, days=days, db=db, key_ids=[api_key_id]
    )
    if err:
        raise HTTPException(status_code=404, detail=err)
    key_row = db.query(Api_key).filter(Api_key.id == api_key_id).first()
    if not key_row:
        raise HTTPException(status_code=404, detail="API key not found")
    proj = (
        db.query(Project).filter(Project.id == key_row.project_id).first()
        if key_row
        else None
    )
    payload["api_key"] = {
        "api_key_id": api_key_id,
        "masked_key": f"…{key_row.api_key[-8:]}" if key_row and len(key_row.api_key) >= 8 else "••••",
        "project_id": key_row.project_id if key_row else None,
        "project_name": proj.name if proj else None,
    }
    return payload
