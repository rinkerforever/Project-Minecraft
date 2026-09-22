from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Role = Literal["owner", "admin", "operator", "viewer"]
ServerStatus = Literal["stopped", "starting", "running", "stopping", "error"]


class UserRecord(BaseModel):
    username: str
    password_hash: str
    role: Role = "viewer"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    enabled: bool = True


class UserPublic(BaseModel):
    username: str
    role: Role
    created_at: datetime
    enabled: bool


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: Role


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: Role = "viewer"


class JavaRuntime(BaseModel):
    name: str
    java_path: str
    version: str


class ServerProfile(BaseModel):
    name: str
    server_jar: str
    working_directory: str
    java_runtime: str
    jvm_args: list[str] = Field(default_factory=lambda: ["-Xms2G", "-Xmx4G"])
    server_args: list[str] = Field(default_factory=lambda: ["nogui"])
    mod_directory: str = "mods"
    enabled: bool = True


class ModRecord(BaseModel):
    filename: str
    stored_path: str
    uploaded_by: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    enabled: bool = True


class OnlinePlayer(BaseModel):
    name: str
    joined_at: datetime = Field(default_factory=datetime.utcnow)


class ServerState(BaseModel):
    active_profile: str | None = None
    server_status: ServerStatus = "stopped"
    java_runtimes: list[JavaRuntime] = Field(default_factory=list)
    profiles: list[ServerProfile] = Field(default_factory=list)
    mods: list[ModRecord] = Field(default_factory=list)
    online_players: list[OnlinePlayer] = Field(default_factory=list)
    last_command: str | None = None
    last_started_at: datetime | None = None
    last_stopped_at: datetime | None = None
    notes: str = ""


class CreateRuntimeRequest(BaseModel):
    name: str
    java_path: str
    version: str


class CreateProfileRequest(BaseModel):
    name: str
    server_jar: str
    working_directory: str
    java_runtime: str
    jvm_args: list[str] = Field(default_factory=list)
    server_args: list[str] = Field(default_factory=list)
    mod_directory: str = "mods"


class SwitchProfileRequest(BaseModel):
    profile_name: str


class CommandRequest(BaseModel):
    command: str


class NotesRequest(BaseModel):
    notes: str


class BackupRequest(BaseModel):
    label: str = ""
