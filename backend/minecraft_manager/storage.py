from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, TypeVar

from .config import settings
from .models import ServerState, UserRecord

T = TypeVar("T")


def ensure_data_dirs() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_path.mkdir(parents=True, exist_ok=True)
    settings.uploads_path.mkdir(parents=True, exist_ok=True)


def load_state() -> ServerState:
    ensure_data_dirs()
    if not settings.state_path.exists():
        state = ServerState()
        save_state(state)
        return state
    return ServerState.model_validate_json(settings.state_path.read_text(encoding="utf-8"))


def save_state(state: ServerState) -> None:
    settings.state_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")


def load_users() -> list[UserRecord]:
    ensure_data_dirs()
    if not settings.users_path.exists():
        return []
    raw = json.loads(settings.users_path.read_text(encoding="utf-8"))
    return [UserRecord.model_validate(item) for item in raw]


def save_users(users: Iterable[UserRecord]) -> None:
    payload = [user.model_dump(mode="json") for user in users]
    settings.users_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_log_line(line: str) -> None:
    ensure_data_dirs()
    log_file = settings.logs_path / "server.log"
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(f"{line.rstrip()}\n")
