"""
Signup and Login API endpoints.

User registration and authentication for the dashboard.
"""

import datetime
import re
from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.crud import (
    get_user_by_email,
    get_user_by_username,
    get_organization_by_name,
    get_organization_by_id,
    create_organization_and_user,
)
from backend.models import Subscription
from backend.api.auth import (
    hash_password,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter()

_USERNAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{2,31}$")
_ORG_PUNCT = set("&.,'-()")

_ORG_BLOCKLIST = frozenset(
    {
        "test",
        "tests",
        "testing",
        "asdf",
        "qwerty",
        "qwer",
        "abc",
        "abcd",
        "abcdef",
        "xxx",
        "foo",
        "bar",
        "sample",
        "demo",
        "demos",
        "placeholder",
        "none",
        "null",
        "random",
        "organization",
        "organisation",
        "org",
        "orgs",
        "company",
        "companies",
        "default",
        "admin",
        "username",
        "user",
        "idk",
        "lol",
        "lorem",
        "ipsum",
        "hello",
        "hey",
        "hi",
        "yes",
        "no",
        "ok",
        "okay",
        "stuff",
        "things",
        "thing",
        "aaa",
        "zzz",
        "blah",
        "whatever",
        "something",
        "anything",
        "nothing",
        "myorg",
        "mycompany",
        "neworg",
        "newcompany",
        "temp",
        "temporary",
        "trial",
        "na",
        "inc",
        "llc",
        "ltd",
    }
)


def _collapse_org_whitespace(s: str) -> str:
    return " ".join((s or "").strip().split())


def _org_letters_only_lower(org: str) -> str:
    return "".join(c for c in org if c.isalpha()).lower()


def _org_max_consecutive_letter_run(org: str) -> int:
    run = 0
    max_run = 0
    for c in org:
        if c.isalpha():
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
    return max_run


def _org_letters_all_ascii(org: str) -> bool:
    for c in org:
        if c.isalpha() and ord(c) > 127:
            return False
    return True


def _normalize_organization_name(organization_name: str) -> str:
    """
    Validate organization name; return collapsed, trimmed name.
    Mirrors Frontend/src/utils/signupValidation.js isValidOrganizationName.
    """
    org = _collapse_org_whitespace(organization_name)
    if len(org) < 3 or len(org) > 80:
        raise HTTPException(
            status_code=400,
            detail="Invalid organization name: use 3–80 characters with a plausible company or team name.",
        )

    has_letter = False
    for c in org:
        if c.isalpha():
            has_letter = True
        elif c.isdigit():
            continue
        elif c == " " or c in _ORG_PUNCT:
            continue
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid organization name: use letters, numbers, spaces, and & . , ' - ( ).",
            )
    if not has_letter:
        raise HTTPException(
            status_code=400,
            detail="Invalid organization name: include at least one letter.",
        )

    if _org_max_consecutive_letter_run(org) < 3:
        raise HTTPException(
            status_code=400,
            detail="Invalid organization name: include a word with at least three letters.",
        )

    slug = org.lower()
    if slug in _ORG_BLOCKLIST:
        raise HTTPException(
            status_code=400,
            detail="Invalid organization name: that name is too generic or looks like a placeholder.",
        )

    compact = _org_letters_only_lower(org)
    if compact and compact in _ORG_BLOCKLIST:
        raise HTTPException(
            status_code=400,
            detail="Invalid organization name: that name is too generic or looks like a placeholder.",
        )

    if len(compact) >= 3 and len(set(compact)) == 1:
        raise HTTPException(
            status_code=400,
            detail="Invalid organization name: repeated characters are not allowed.",
        )

    letter_count = len(compact)
    if _org_letters_all_ascii(org) and letter_count >= 4:
        if not re.search(r"[aeiouyAEIOUY]", org):
            raise HTTPException(
                status_code=400,
                detail="Invalid organization name: use recognizable words (not random letters).",
            )

    return org


def _normalize_and_validate_signup(
    username: str,
    full_name: str,
    email: str,
    password: str,
    organization_name: str,
) -> tuple[str, str, str, str, str]:
    """
    Validate signup fields; return normalized username, full_name, email, password, org_name.
    Rules mirror Frontend/src/utils/signupValidation.js.
    """
    u = (username or "").strip()
    if not _USERNAME_RE.match(u):
        raise HTTPException(
            status_code=400,
            detail="Invalid username: 3–32 characters, must start with a letter; "
            "only letters, numbers, underscore, and hyphen.",
        )

    fn = (full_name or "").strip()
    if len(fn) < 2 or len(fn) > 100:
        raise HTTPException(
            status_code=400,
            detail="Invalid full name: use 2–100 characters.",
        )
    has_letter = False
    for c in fn:
        if c.isalpha():
            has_letter = True
        elif c in " -'.":
            continue
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid full name: letters, spaces, hyphen, apostrophe, or period only; "
                "include at least one letter.",
            )
    if not has_letter:
        raise HTTPException(
            status_code=400,
            detail="Invalid full name: include at least one letter.",
        )

    org = _normalize_organization_name(organization_name)

    em = (email or "").strip().lower()
    if len(em) > 254 or not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", em):
        raise HTTPException(status_code=400, detail="Invalid email address.")
    at = em.index("@")
    local, domain = em[:at], em[at + 1 :]
    if len(local) > 64 or len(domain) > 253:
        raise HTTPException(status_code=400, detail="Invalid email address.")
    if domain.startswith(".") or domain.endswith(".") or ".." in domain:
        raise HTTPException(status_code=400, detail="Invalid email address.")

    if len(password) < 8 or len(password) > 128:
        raise HTTPException(
            status_code=400,
            detail="Invalid password: use 8–128 characters with at least one letter and one number.",
        )
    if password != password.strip():
        raise HTTPException(status_code=400, detail="Invalid password: no leading or trailing spaces.")
    if not all(32 <= ord(c) <= 126 for c in password):
        raise HTTPException(
            status_code=400,
            detail="Invalid password: use only printable ASCII characters.",
        )
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise HTTPException(
            status_code=400,
            detail="Invalid password: include at least one letter and one number.",
        )

    return u, fn, em, password, org


@router.post("/signup")
async def signup(
    username: str = Form(...),
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    organization_name: str = Form(...),
    db: Session = Depends(get_db),
):
    """Register a new user, organization, and subscription atomically."""
    username, full_name, email, password, organization_name = _normalize_and_validate_signup(
        username, full_name, email, password, organization_name
    )
    print(f"DEBUG: signup called with username={username}, email={email}")

    existing_org = get_organization_by_name(db, organization_name)
    if existing_org:
        raise HTTPException(status_code=400, detail="Organization name already exists")

    existing_user_by_username = get_user_by_username(db, username)
    existing_user_by_email = get_user_by_email(db, email)
    if existing_user_by_username or existing_user_by_email:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    hashed_password = hash_password(password)
    print(f"DEBUG: Password hashed successfully, type={type(hashed_password)}, length={len(hashed_password)}")

    try:
        user, org, subscription = create_organization_and_user(
            db=db,
            username=username,
            full_name=full_name,
            email=email,
            hashed_password=hashed_password,
            org_name=organization_name.strip(),
        )
    except Exception as e:
        print(f"ERROR during signup: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete signup")

    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
        },
        "organization": {
            "id": org.id,
            "name": org.org_name,
            "plan_type": org.plan_type,
            "max_users": org.max_users,
        },
        "subscription": {
            "id": subscription.id,
            "plan": subscription.plan.value,
            "limit_queries": subscription.monthly_limit_queries,
            "limit_ingest": subscription.monthly_limit_ingest,
        },
    }


@router.post("/login")
async def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Authenticate a user and return a JWT token."""
    print(f"DEBUG: login called with email={email}")

    user = get_user_by_email(db, email)
    if not user:
        print(f"DEBUG: No user found with email: {email}")
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    print(f"DEBUG: Found user with ID: {user.id}")

    if not verify_password(password, user.password_hash):
        print(f"DEBUG: Password verification failed for user with email: {email}")
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    print(f"DEBUG: Password verification successful for user with email: {email}")

    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    organization = None
    subscription_payload = None
    if user.org_id:
        org = get_organization_by_id(db, user.org_id)
        if org:
            organization = {
                "id": org.id,
                "name": org.org_name,
                "plan_type": org.plan_type,
                "max_users": org.max_users,
            }
        sub = (
            db.query(Subscription)
            .filter(Subscription.org_id == user.org_id)
            .first()
        )
        if sub:
            subscription_payload = {
                "id": sub.id,
                "plan": sub.plan.value,
                "limit_queries": sub.monthly_limit_queries,
                "limit_ingest": sub.monthly_limit_ingest,
            }

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
        },
        "organization": organization,
        "subscription": subscription_payload,
    }
