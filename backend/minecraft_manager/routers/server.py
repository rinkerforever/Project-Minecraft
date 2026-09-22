from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import zipfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from ..dependencies import current_user, require_role
from ..models import BackupRequest, CommandRequest, CreateProfileRequest, CreateRuntimeRequest, ModRecord, NotesRequest, ServerProfile
from ..services.server_manager import server_manager
from ..storage import load_state, save_state
from ..config import settings

router = APIRouter(prefix="/api/server", tags=["server"])


def ensure_profile_directory(working_directory: str) -> None:
    try:
        Path(working_directory).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not create working directory '{working_directory}'. Check that the backend service has permission to write there.",
        ) from exc


def active_profile_root() -> Path:
    state = load_state()
    if not state.active_profile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active profile configured")
    profile = next((item for item in state.profiles if item.name == state.active_profile), None)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active profile is missing")
    root = Path(profile.working_directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def profile_path(relative_path: str, *, allow_root: bool = True) -> Path:
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Paths must be relative to the active server folder")
    root = active_profile_root()
    target = (root / candidate).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path is outside the active server folder") from exc
    if not allow_root and target == root:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose a file or folder inside the active server folder")
    return target


def display_path(root: Path, item: Path) -> str:
    return item.relative_to(root).as_posix()


@router.get("/state", dependencies=[Depends(current_user)])
def get_state():
    return server_manager.get_state()


@router.post("/java-runtimes", dependencies=[Depends(require_role("owner", "admin"))], status_code=status.HTTP_201_CREATED)
def create_java_runtime(payload: CreateRuntimeRequest):
    state = load_state()
    state.java_runtimes = [runtime for runtime in state.java_runtimes if runtime.name != payload.name]
    state.java_runtimes.append(payload)
    save_state(state)
    return state


@router.post("/profiles", dependencies=[Depends(require_role("owner", "admin"))], status_code=status.HTTP_201_CREATED)
def create_profile(payload: CreateProfileRequest):
    state = load_state()
    ensure_profile_directory(payload.working_directory)
    profile = ServerProfile(
        name=payload.name,
        server_jar=payload.server_jar,
        working_directory=payload.working_directory,
        java_runtime=payload.java_runtime,
        jvm_args=payload.jvm_args or ["-Xms2G", "-Xmx4G"],
        server_args=payload.server_args or ["nogui"],
        mod_directory=payload.mod_directory,
    )
    state.profiles = [item for item in state.profiles if item.name != profile.name]
    state.profiles.append(profile)
    state.active_profile = state.active_profile or profile.name
    save_state(state)
    return state


@router.post("/profiles/{profile_name}/activate", dependencies=[Depends(require_role("owner", "admin"))])
def activate_profile(profile_name: str):
    try:
        return server_manager.switch_profile(profile_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/profiles/{profile_name}", dependencies=[Depends(require_role("owner", "admin"))])
def update_profile(profile_name: str, payload: CreateProfileRequest):
    if payload.name != profile_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile name cannot be changed")

    state = load_state()
    if state.server_status != "stopped":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stop the server before editing a profile")
    if not any(profile.name == profile_name for profile in state.profiles):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Profile '{profile_name}' does not exist")
    ensure_profile_directory(payload.working_directory)

    updated_profile = ServerProfile(
        name=payload.name,
        server_jar=payload.server_jar,
        working_directory=payload.working_directory,
        java_runtime=payload.java_runtime,
        jvm_args=payload.jvm_args or ["-Xms2G", "-Xmx4G"],
        server_args=payload.server_args or ["nogui"],
        mod_directory=payload.mod_directory,
    )
    state.profiles = [profile if profile.name != profile_name else updated_profile for profile in state.profiles]
    save_state(state)
    return state


@router.post("/start", dependencies=[Depends(require_role("owner", "admin", "operator"))])
def start_server():
    try:
        return server_manager.start_server()
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/stop", dependencies=[Depends(require_role("owner", "admin", "operator"))])
def stop_server():
    try:
        return server_manager.stop_server()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/restart", dependencies=[Depends(require_role("owner", "admin", "operator"))])
def restart_server():
    try:
        return server_manager.restart_server()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/command", dependencies=[Depends(require_role("owner", "admin", "operator"))])
def send_command(payload: CommandRequest):
    try:
        return server_manager.send_command(payload.command)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/mods", dependencies=[Depends(require_role("owner", "admin"))], status_code=status.HTTP_201_CREATED)
async def upload_mod(user=Depends(current_user), file: UploadFile = File(...)):
    state = load_state()
    if not state.active_profile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active profile configured")
    profile = next((item for item in state.profiles if item.name == state.active_profile), None)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active profile is missing")
    target_dir = Path(profile.working_directory) / profile.mod_directory
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / file.filename
    contents = await file.read()
    target_path.write_bytes(contents)
    mod = ModRecord(filename=file.filename, stored_path=str(target_path), uploaded_by=user.username)
    return server_manager.register_mod(mod)


@router.get("/mods/{filename}/download", dependencies=[Depends(current_user)])
def download_mod(filename: str):
    """Download a mod from the active profile without exposing its host path."""
    name = Path(filename).name
    if name != filename or not name.lower().endswith(".jar"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose a mod JAR from the active profile")
    state = load_state()
    if not state.active_profile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active profile configured")
    profile = next((item for item in state.profiles if item.name == state.active_profile), None)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active profile is missing")
    target = Path(profile.working_directory) / profile.mod_directory / name
    if not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mod file does not exist")
    return FileResponse(target, filename=name, media_type="application/java-archive")


@router.post("/server-jar", dependencies=[Depends(require_role("owner", "admin"))], status_code=status.HTTP_201_CREATED)
async def upload_server_jar(file: UploadFile = File(...)):
    state = load_state()
    if not state.active_profile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active profile configured")
    profile = next((item for item in state.profiles if item.name == state.active_profile), None)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active profile is missing")
    if state.server_status != "stopped":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stop the server before updating the server jar")
    if not file.filename.lower().endswith(".jar"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Server jar upload must be a .jar file")

    working_dir = Path(profile.working_directory)
    working_dir.mkdir(parents=True, exist_ok=True)
    target_path = working_dir / file.filename
    contents = await file.read()
    target_path.write_bytes(contents)

    updated_profile = profile.model_copy(update={"server_jar": file.filename})
    state.profiles = [item if item.name != profile.name else updated_profile for item in state.profiles]
    save_state(state)
    return state


@router.get("/logs", dependencies=[Depends(current_user)])
def get_logs(lines: int = 200):
    log_file = settings.logs_path / "server.log"
    if not log_file.exists():
        return {"lines": []}
    content = log_file.read_text(encoding="utf-8").splitlines()
    return {"lines": content[-lines:]}


@router.get("/players", dependencies=[Depends(current_user)])
def get_players():
    """Infer current players from the chronological join/leave events in the server log."""
    state = load_state()
    if state.online_players:
        now = datetime.utcnow()
        return {
            "players": [
                {
                    "name": player.name,
                    "joined_at": player.joined_at.isoformat(),
                    "online_seconds": max(0, int((now - player.joined_at).total_seconds())),
                }
                for player in state.online_players
            ]
        }
    log_file = settings.logs_path / "server.log"
    if not log_file.exists():
        return {"players": []}

    online: dict[str, tuple[str, int | None]] = {}
    joined = re.compile(r"\b([A-Za-z0-9_]{3,16}) joined the game\b")
    left = re.compile(r"\b([A-Za-z0-9_]{3,16}) (?:left the game|lost connection)\b")
    now = datetime.now()
    for line in log_file.read_text(encoding="utf-8", errors="replace").splitlines()[-3000:]:
        if match := joined.search(line):
            timestamp = line[:24].strip("[] ")
            clock = re.search(r"\b(\d{2}):(\d{2}):(\d{2})\b", line)
            seconds = None
            if clock:
                joined_at = now.replace(hour=int(clock.group(1)), minute=int(clock.group(2)), second=int(clock.group(3)), microsecond=0)
                if joined_at > now:
                    joined_at -= timedelta(days=1)
                seconds = int((now - joined_at).total_seconds())
            online[match.group(1)] = (timestamp, seconds)
        elif match := left.search(line):
            online.pop(match.group(1), None)
    return {"players": [{"name": name, "joined_at": data[0], "online_seconds": data[1]} for name, data in online.items()]}


@router.get("/health", dependencies=[Depends(current_user)])
def get_health():
    state = load_state()
    metrics = server_manager.process_metrics()
    tick_rate = None
    tick_source = "not reported by the server"
    log_file = settings.logs_path / "server.log"
    if state.server_status == "running":
        # Vanilla servers only log lag timing rather than an exact TPS metric. Use the
        # newest warning when present, otherwise report nominal TPS as an estimate.
        tick_rate = 20.0
        tick_source = "estimated: no recent lag warning"
        if log_file.exists():
            for line in reversed(log_file.read_text(encoding="utf-8", errors="replace").splitlines()[-300:]):
                match = re.search(r"Running\s+(\d+)ms\s+or\s+(\d+)\s+ticks behind", line)
                if match:
                    elapsed_ms, ticks = int(match.group(1)), int(match.group(2))
                    if ticks:
                        tick_rate = round(min(20.0, 20.0 * (ticks * 50) / elapsed_ms), 1)
                    tick_source = "estimated from latest lag warning"
                    break
    return {**metrics, "tick_rate": tick_rate, "tick_source": tick_source}


@router.get("/files", dependencies=[Depends(current_user)])
def list_files(path: str = ""):
    target = profile_path(path)
    if not target.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder does not exist")
    if not target.is_dir():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path must be a folder")
    root = active_profile_root()
    items = []
    for item in sorted(target.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name.lower())):
        stat = item.stat()
        items.append({
            "name": item.name,
            "path": display_path(root, item),
            "kind": "folder" if item.is_dir() else "file",
            "size": stat.st_size if item.is_file() else None,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        })
    return {"path": display_path(root, target) if target != root else "", "items": items}


@router.get("/files/download", dependencies=[Depends(current_user)])
def download_file(path: str):
    target = profile_path(path, allow_root=False)
    if not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File does not exist")
    return FileResponse(target, filename=target.name)


@router.post("/files", dependencies=[Depends(require_role("owner", "admin"))], status_code=status.HTTP_201_CREATED)
async def upload_file(directory: str = Form(""), file: UploadFile = File(...)):
    target_dir = profile_path(directory)
    if not target_dir.is_dir():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload destination must be a folder")
    filename = Path(file.filename or "").name
    if not filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A file name is required")
    target = profile_path((Path(directory) / filename).as_posix(), allow_root=False)
    target.write_bytes(await file.read())
    return {"path": display_path(active_profile_root(), target), "filename": filename}


@router.delete("/files", dependencies=[Depends(require_role("owner", "admin"))])
def delete_file(path: str):
    target = profile_path(path, allow_root=False)
    if not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Only existing files can be deleted")
    target.unlink()
    return {"deleted": path}


@router.get("/backups", dependencies=[Depends(current_user)])
def list_backups():
    root = active_profile_root()
    backup_dir = root / "backups"
    backup_dir.mkdir(exist_ok=True)
    backups = []
    for item in sorted(backup_dir.glob("*.zip"), key=lambda entry: entry.stat().st_mtime, reverse=True):
        stat = item.stat()
        backups.append({"name": item.name, "size": stat.st_size, "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()})
    return {"backups": backups}


@router.post("/backups", dependencies=[Depends(require_role("owner", "admin"))], status_code=status.HTTP_201_CREATED)
def create_backup(payload: BackupRequest):
    root = active_profile_root()
    backup_dir = root / "backups"
    backup_dir.mkdir(exist_ok=True)
    label = re.sub(r"[^A-Za-z0-9_-]+", "-", payload.label.strip()).strip("-") or "snapshot"
    name = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{label}.zip"
    archive = backup_dir / name
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for item in root.rglob("*"):
            if not item.is_file() or backup_dir in item.parents:
                continue
            # Do not dereference an in-folder symlink into an unrelated host path.
            try:
                item.resolve().relative_to(root)
            except ValueError:
                continue
            bundle.write(item, item.relative_to(root))
    return {"name": name, "size": archive.stat().st_size}


@router.get("/backups/download", dependencies=[Depends(current_user)])
def download_backup(name: str):
    target = profile_path(f"backups/{Path(name).name}", allow_root=False)
    if not target.is_file() or target.suffix.lower() != ".zip":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup does not exist")
    return FileResponse(target, filename=target.name, media_type="application/zip")


@router.delete("/backups", dependencies=[Depends(require_role("owner", "admin"))])
def delete_backup(name: str):
    target = profile_path(f"backups/{Path(name).name}", allow_root=False)
    if not target.is_file() or target.suffix.lower() != ".zip":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup does not exist")
    target.unlink()
    return {"deleted": target.name}


@router.put("/notes", dependencies=[Depends(require_role("owner", "admin"))])
def update_notes(payload: NotesRequest):
    state = load_state()
    state.notes = payload.notes
    save_state(state)
    return state
