import threading
from datetime import datetime
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, delete, insert, literal, select

from lugnut.auth.deps import (
    COOKIE,
    DB,
    SESSION_TTL,
    Scope,
    hash_secret,
    new_secret,
    require,
    set_session_cookie,
    utcnow,
)
from lugnut.auth.models import ApiToken, LoginSession, User

router = APIRouter(prefix="/api")
_hasher = PasswordHasher()
# Verified against when the username is unknown, so both cases take the same time.
_DUMMY_HASH = _hasher.hash("lugnut-dummy-password")
# ponytail: one lock serialises every login so parallel guesses can't outrun the
# backoff. Fine for a single-user app; per-IP locks if login throughput ever matters.
_login_lock = threading.Lock()

Reader = Annotated[User, Depends(require("read"))]
Writer = Annotated[User, Depends(require("write"))]


class SetupIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=12, max_length=1024)


class LoginIn(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=1024)


class UserOut(BaseModel):
    id: int
    username: str


class TokenIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    scope: Scope


class TokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    scope: Scope
    created_at: datetime
    last_used_at: datetime | None


class TokenCreated(BaseModel):
    id: int
    name: str
    scope: Scope
    token: str


def _start_session(request: Request, response: Response, db: DB, user: User) -> UserOut:
    raw = new_secret()
    now = utcnow()
    db.execute(delete(LoginSession).where(LoginSession.expires_at <= now))
    db.add(
        LoginSession(
            token_hash=hash_secret(raw),
            user_id=user.id,
            created_at=now,
            expires_at=now + SESSION_TTL,
        )
    )
    db.commit()
    set_session_cookie(request, response, raw)
    return UserOut(id=user.id, username=user.username)


@router.post("/setup", status_code=201)
def setup(body: SetupIn, request: Request, response: Response, db: DB) -> UserOut:
    if db.scalar(select(User.id)) is not None:
        raise HTTPException(409, "Already set up")
    # One INSERT ... WHERE NOT EXISTS, so two racing setups can't both create a user.
    row = select(
        literal(body.username),
        literal(_hasher.hash(body.password)),
        literal(utcnow(), DateTime),
    ).where(~select(User.id).exists())
    result = db.execute(
        insert(User).from_select(["username", "password_hash", "created_at"], row)
    )
    if result.rowcount != 1:  # type: ignore[attr-defined]
        db.rollback()
        raise HTTPException(409, "Already set up")
    user = db.scalars(select(User).where(User.username == body.username)).one()
    return _start_session(request, response, db, user)


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response, db: DB) -> UserOut:
    limiter = request.app.state.login_limiter
    ip = request.client.host if request.client else ""
    with _login_lock:
        if not limiter.allowed(ip):
            raise HTTPException(429, "Too many failed logins, try again later")
        user = db.scalar(select(User).where(User.username == body.username))
        try:
            _hasher.verify(user.password_hash if user else _DUMMY_HASH, body.password)
            ok = user is not None
        except VerificationError:
            ok = False
        if not ok:
            limiter.failed(ip)
            raise HTTPException(401, "Wrong username or password")
        limiter.succeeded(ip)
    assert user is not None
    return _start_session(request, response, db, user)


@router.post("/auth/logout", status_code=204)
def logout(_: Writer, request: Request, response: Response, db: DB) -> None:
    raw = request.cookies.get(COOKIE)
    if raw:
        db.execute(delete(LoginSession).where(LoginSession.token_hash == hash_secret(raw)))
        db.commit()
    response.delete_cookie(
        COOKIE,
        httponly=True,
        samesite="strict",
        secure=request.app.state.settings.secure_cookies,
    )


@router.get("/auth/me")
def me(user: Reader) -> UserOut:
    return UserOut(id=user.id, username=user.username)


@router.get("/tokens")
def list_tokens(_: Reader, db: DB) -> list[TokenOut]:
    return [TokenOut.model_validate(t) for t in db.scalars(select(ApiToken).order_by(ApiToken.id))]


@router.post("/tokens", status_code=201)
def create_token(body: TokenIn, _: Writer, db: DB) -> TokenCreated:
    raw = new_secret("lgn_")
    token = ApiToken(
        name=body.name, token_hash=hash_secret(raw), scope=body.scope, created_at=utcnow()
    )
    db.add(token)
    db.commit()
    return TokenCreated(id=token.id, name=token.name, scope=body.scope, token=raw)


@router.delete("/tokens/{token_id}", status_code=204)
def delete_token(token_id: int, _: Writer, db: DB) -> None:
    token = db.get(ApiToken, token_id)
    if token is None:
        raise HTTPException(404, "No such token")
    db.delete(token)
    db.commit()
