from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import get_user_by_username, hash_password
from ..dependencies import require_role
from ..models import CreateUserRequest, UserPublic, UserRecord
from ..storage import load_users, save_users

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", dependencies=[Depends(require_role("owner", "admin"))])
def list_users():
    return [
        UserPublic(username=user.username, role=user.role, created_at=user.created_at, enabled=user.enabled)
        for user in load_users()
    ]


@router.post("", dependencies=[Depends(require_role("owner", "admin"))], status_code=status.HTTP_201_CREATED)
def create_user(payload: CreateUserRequest):
    users = load_users()
    if get_user_by_username(payload.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
    users.append(
        UserRecord(username=payload.username, password_hash=hash_password(payload.password), role=payload.role)
    )
    save_users(users)
    return {"created": payload.username}
