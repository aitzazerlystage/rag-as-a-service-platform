"""
Auth utilities: password hashing and JWT tokens.

Uses bcrypt (bytes) for compatibility with LargeBinary password_hash column.
"""

import os
import datetime
from datetime import timedelta
from typing import Optional

import bcrypt
import jwt
from jwt import PyJWTError

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def hash_password(password: str) -> bytes:
    """Hash a password using bcrypt. Returns bytes for LargeBinary storage."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def verify_password(plain_password: str, hashed_password: bytes) -> bool:
    """Verify a plain password against a bcrypt hashed password (bytes)."""
    try:
        if not isinstance(hashed_password, bytes):
            return False
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password)
    except Exception:
        return False


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except PyJWTError:
        return None
