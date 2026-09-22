from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .auth import hash_password
from .config import settings
from .routers import auth, server, users
from .storage import ensure_data_dirs, load_users, save_users
from .web import router as web_router
from .models import UserRecord


def bootstrap_owner() -> None:
    users_list = load_users()
    if users_list:
        return
    users_list.append(UserRecord(username="owner", password_hash=hash_password("changeme"), role="owner"))
    save_users(users_list)


def create_app() -> FastAPI:
    ensure_data_dirs()
    bootstrap_owner()
    app = FastAPI(title="Minecraft Control Plane", version="0.1.0")
    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.include_router(web_router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(server.router)
    return app


app = create_app()
