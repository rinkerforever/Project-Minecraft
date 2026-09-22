from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext

from .config import settings
from .models import TokenResponse, UserPublic, UserRecord
from .storage import load_users

# Passlib 1.7.4 probes a module attribute removed by bcrypt 4.1+.
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type("_About", (), {"__version__": bcrypt.__version__})()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_token(user: UserRecord) -> TokenResponse:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.token_expire_minutes)
    payload = {"sub": user.username, "role": user.role, "exp": expires}
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return TokenResponse(access_token=token, username=user.username, role=user.role)


def get_user_by_username(username: str) -> UserRecord | None:
    return next((user for user in load_users() if user.username == username), None)


def decode_token(token: str) -> UserPublic:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = get_user_by_username(payload["sub"])
    if user is None or not user.enabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer active")

    return UserPublic(
        username=user.username,
        role=user.role,
        created_at=user.created_at,
        enabled=user.enabled,
    )
