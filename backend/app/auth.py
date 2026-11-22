"""Authentication: bcrypt password hashing + JWT sessions in an HttpOnly cookie.

- The first account ever registered becomes the admin.
- The session cookie is HttpOnly + SameSite=Lax, so page scripts can't read it and
  the PDF viewer / report links (plain <iframe>/<a>) are authenticated automatically.
- A `Authorization: Bearer <token>` header is also accepted (API clients, tests).
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import BACKEND_DIR, get_settings
from app.db import get_db
from app.models import User

COOKIE_NAME = "cl_session"
ALGORITHM = "HS256"


@lru_cache
def _secret() -> str:
    """JWT signing key: SECRET_KEY from .env, else a random key persisted locally (gitignored)."""
    configured = get_settings().secret_key
    if configured:
        return configured
    path: Path = BACKEND_DIR / ".secret_key"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    key = secrets.token_urlsafe(48)
    path.write_text(key, encoding="utf-8")
    return key


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode())
    except ValueError:
        return False


def create_token(user: User) -> str:
    hours = get_settings().session_hours
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": datetime.now(UTC) + timedelta(hours=hours),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=get_settings().session_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=get_settings().backend_url.startswith("https"),
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def _token_from_request(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.cookies.get(COOKIE_NAME)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    token = _token_from_request(request)
    if not token:
        raise unauthorized
    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized from None
    if user is None or not user.is_active:
        raise unauthorized
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user
