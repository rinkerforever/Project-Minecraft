from __future__ import annotations

import subprocess
import threading
import re
from datetime import datetime
from pathlib import Path

try:
    import psutil
except ImportError:  # The API remains usable if metrics support is not installed yet.
    psutil = None

from ..models import ModRecord, OnlinePlayer, ServerProfile, ServerState
from ..storage import append_log_line, load_state, save_state


class ServerManager:
    def __init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None
        self._stdout_thread: threading.Thread | None = None
        # stop_server calls send_command while holding this lock. An RLock prevents
        # that controlled re-entry from deadlocking health checks and new logins.
        self._lock = threading.RLock()

    def get_state(self) -> ServerState:
        return load_state()

    def process_metrics(self) -> dict[str, float | int | None]:
        """Return measurements for the managed JVM without inspecting unrelated processes."""
        with self._lock:
            if not self._process or self._process.poll() is not None or psutil is None:
                return {"cpu_percent": None, "memory_bytes": None}
            try:
                process = psutil.Process(self._process.pid)
                return {
                    "cpu_percent": round(process.cpu_percent(interval=0.1), 1),
                    "memory_bytes": process.memory_info().rss,
                }
            except (psutil.Error, OSError):
                return {"cpu_percent": None, "memory_bytes": None}

    def save_state(self, state: ServerState) -> ServerState:
        save_state(state)
        return state

    def _active_profile(self, state: ServerState) -> ServerProfile:
        if not state.active_profile:
            raise ValueError("No active profile is configured.")
        profile = next((item for item in state.profiles if item.name == state.active_profile), None)
        if profile is None:
            raise ValueError(f"Active profile '{state.active_profile}' no longer exists.")
        return profile

    def _java_path_for_profile(self, state: ServerState, profile: ServerProfile) -> str:
        runtime = next((item for item in state.java_runtimes if item.name == profile.java_runtime), None)
        if runtime is None:
            raise ValueError(f"Java runtime '{profile.java_runtime}' is not registered.")
        return runtime.java_path

    def start_server(self) -> ServerState:
        with self._lock:
            state = load_state()
            if self._process and self._process.poll() is None:
                raise ValueError("Server is already running.")

            profile = self._active_profile(state)
            java_path = self._java_path_for_profile(state, profile)
            working_dir = Path(profile.working_directory)
            if not working_dir.is_dir():
                raise ValueError(
                    f"Working directory '{working_dir}' does not exist. Edit the active profile to use a valid folder on the backend host."
                )
            server_jar = working_dir / profile.server_jar
            if not server_jar.is_file():
                raise ValueError(
                    f"Server jar '{server_jar}' does not exist. Use Update Server Jar after correcting the profile."
                )
            if server_jar.name == "run.sh":
                # Modern Forge installers use run.sh to supply their generated classpath.
                # Keep the profile memory settings in the file consumed by that launcher.
                (working_dir / "user_jvm_args.txt").write_text("\n".join(profile.jvm_args) + "\n", encoding="utf-8")
                command = ["bash", profile.server_jar, *profile.server_args]
            else:
                command = [java_path, *profile.jvm_args, "-jar", profile.server_jar, *profile.server_args]

            state.server_status = "starting"
            state.online_players = []
            state.last_command = " ".join(command)
            state.last_started_at = datetime.utcnow()
            save_state(state)
            append_log_line(f"[manager] starting with command: {state.last_command}")

            self._process = subprocess.Popen(
                command,
                cwd=working_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self._stdout_thread = threading.Thread(target=self._pump_logs, daemon=True)
            self._stdout_thread.start()
            state.server_status = "running"
            save_state(state)
            return state

    def _pump_logs(self) -> None:
        if not self._process or not self._process.stdout:
            return
        for line in self._process.stdout:
            append_log_line(line)
            self._record_player_event(line)

        state = load_state()
        state.server_status = "stopped"
        state.last_stopped_at = datetime.utcnow()
        save_state(state)
        append_log_line("[manager] server process exited")

    def _record_player_event(self, line: str) -> None:
        """Persist player presence while the process is running for accurate session duration."""
        joined = re.search(r"\b([A-Za-z0-9_]{3,16}) joined the game\b", line)
        left = re.search(r"\b([A-Za-z0-9_]{3,16}) (?:left the game|lost connection)\b", line)
        if not joined and not left:
            return
        state = load_state()
        if joined:
            name = joined.group(1)
            state.online_players = [player for player in state.online_players if player.name != name]
            state.online_players.append(OnlinePlayer(name=name))
        else:
            state.online_players = [player for player in state.online_players if player.name != left.group(1)]
        save_state(state)

    def stop_server(self) -> ServerState:
        with self._lock:
            state = load_state()
            if not self._process or self._process.poll() is not None:
                state.server_status = "stopped"
                save_state(state)
                return state

            state.server_status = "stopping"
            save_state(state)
            self.send_command("stop")
            try:
                self._process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                append_log_line("[manager] graceful stop timed out, terminating process")
                self._process.terminate()
                self._process.wait(timeout=10)
            state.server_status = "stopped"
            state.last_stopped_at = datetime.utcnow()
            save_state(state)
            return state

    def restart_server(self) -> ServerState:
        self.stop_server()
        return self.start_server()

    def send_command(self, command: str) -> ServerState:
        with self._lock:
            state = load_state()
            if not self._process or self._process.poll() is not None or not self._process.stdin:
                raise ValueError("Server is not running.")
            self._process.stdin.write(f"{command}\n")
            self._process.stdin.flush()
            state.last_command = command
            save_state(state)
            append_log_line(f"[admin] {command}")
            return state

    def switch_profile(self, profile_name: str) -> ServerState:
        state = load_state()
        if not any(profile.name == profile_name for profile in state.profiles):
            raise ValueError(f"Profile '{profile_name}' does not exist.")
        if self._process and self._process.poll() is None:
            raise ValueError("Stop the server before switching profiles.")
        state.active_profile = profile_name
        save_state(state)
        return state

    def register_mod(self, mod: ModRecord) -> ServerState:
        state = load_state()
        state.mods = [item for item in state.mods if item.filename != mod.filename]
        state.mods.append(mod)
        save_state(state)
        return state


server_manager = ServerManager()
