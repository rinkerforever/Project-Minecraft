from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from .auth import decode_token
from .models import UserPublic


def current_user(authorization: str = Header(default="")) -> UserPublic:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    return decode_token(token)


def require_role(*allowed_roles: str):
    def dependency(user: UserPublic = Depends(current_user)) -> UserPublic:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return dependency
