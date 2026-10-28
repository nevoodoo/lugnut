import base64
import hashlib
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from lugnut import timeutil
from lugnut.auth.models import ApiToken, LoginSession, User
from lugnut.db import get_session

COOKIE = "lugnut_session"
SESSION_TTL = timedelta(days=30)
TOUCH_EVERY = timedelta(hours=1)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

Scope = Literal["read", "write"]
DB = Annotated[Session, Depends(get_session)]


def utcnow() -> datetime:
    # Columns are naive DateTime holding UTC; timeutil.UtcDatetime re-tags on the way out.
    return timeutil.utcnow().replace(tzinfo=None)


def new_secret(prefix: str = "") -> str:
    raw = base64.b32encode(secrets.token_bytes(32)).decode().rstrip("=").lower()
    return prefix + raw


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def set_session_cookie(request: Request, response: Response, value: str) -> None:
    response.set_cookie(
        COOKIE,
        value,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        samesite="strict",
        secure=request.app.state.settings.secure_cookies,
    )


def _unauthorized() -> HTTPException:
    return HTTPException(401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})


def _token_user(request: Request, db: Session, header: str, scope: Scope) -> User:
    kind, _, value = header.partition(" ")
    if kind.lower() != "bearer" or not value:
        raise _unauthorized()
    token = db.scalar(select(ApiToken).where(ApiToken.token_hash == hash_secret(value.strip())))
    if token is None:
        raise _unauthorized()
    if token.scope != "write" and (scope == "write" or request.method not in SAFE_METHODS):
        raise HTTPException(403, "Token is read-only")
    user: User | None = db.scalar(select(User))  # single-user app: tokens belong to the one user
    if user is None:
        raise _unauthorized()
    now = utcnow()
    if token.last_used_at is None or now - token.last_used_at >= TOUCH_EVERY:
        token.last_used_at = now
        db.commit()
    return user


def _cookie_user(request: Request, response: Response, db: Session) -> User:
    raw = request.cookies.get(COOKIE)
    if not raw:
        raise _unauthorized()
    now = utcnow()
    session = db.scalar(
        select(LoginSession).where(
            LoginSession.token_hash == hash_secret(raw), LoginSession.expires_at > now
        )
    )
    if session is None:
        raise _unauthorized()
    if request.method not in SAFE_METHODS and request.headers.get("x-lugnut") != "1":
        raise HTTPException(403, "Missing X-Lugnut header")
    user: User | None = db.get(User, session.user_id)
    if user is None:
        raise _unauthorized()
    if session.expires_at - now <= SESSION_TTL - TOUCH_EVERY:
        session.expires_at = now + SESSION_TTL
        db.commit()
        set_session_cookie(request, response, raw)
    return user


def require(scope: Scope) -> Callable[..., User]:
    """Dependency: the authenticated user, via Bearer token if sent, else the session cookie."""

    def dependency(request: Request, response: Response, db: DB) -> User:
        header = request.headers.get("authorization")
        if header is not None:
            return _token_user(request, db, header, scope)
        return _cookie_user(request, response, db)

    return dependency
