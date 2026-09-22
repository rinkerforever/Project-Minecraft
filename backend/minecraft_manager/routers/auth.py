from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ..auth import create_token, verify_password
from ..models import LoginRequest
from ..storage import load_users

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest):
    user = next((item for item in load_users() if item.username == payload.username and item.enabled), None)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return create_token(user)
