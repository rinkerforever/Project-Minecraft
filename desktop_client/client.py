from __future__ import annotations

import tkinter as tk
import base64
import os
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import requests


class BlocksmithConsole(tk.Tk):
    """Native Windows companion for the authenticated Blocksmith web console."""

    COLORS = {"bg": "#101215", "panel": "#171a1e", "panel2": "#20252b", "line": "#343c46", "text": "#dce2eb", "muted": "#8d99a9", "blue": "#4b95ff", "green": "#62c454", "red": "#ef6258"}

    def __init__(self) -> None:
        super().__init__()
        self.title("Blocksmith Server Console")
        self.geometry("1180x760")
        self.minsize(780, 520)
        self.base_url = tk.StringVar(value="http://192.168.50.22:9090")
        self.username = tk.StringVar(value="owner")
        self.password = tk.StringVar(value="changeme")
        self.command = tk.StringVar()
        self.file_path = ""
        self.token: str | None = None
        self.state: dict = {}
        self.player_images: list[tk.PhotoImage] = []
        self.compact_layout = False
        self.view_name = "Console"
        self._style()
        self._build()
        self.bind("<Configure>", self._resize_layout)

    def _style(self) -> None:
        self.configure(bg=self.COLORS["bg"])
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("App.TFrame", background=self.COLORS["bg"])
        style.configure("Panel.TFrame", background=self.COLORS["panel"])
        style.configure("App.TLabel", background=self.COLORS["bg"], foreground=self.COLORS["text"])
        style.configure("Panel.TLabel", background=self.COLORS["panel"], foreground=self.COLORS["text"])
        style.configure("Muted.TLabel", background=self.COLORS["panel"], foreground=self.COLORS["muted"])
        style.configure("Title.TLabel", background=self.COLORS["panel"], foreground=self.COLORS["text"], font=("Segoe UI", 16, "bold"))
        style.configure("Header.TLabel", background=self.COLORS["panel"], foreground=self.COLORS["text"], font=("Segoe UI", 11, "bold"))
        style.configure("Primary.TButton", background="#2461b5", foreground="white", borderwidth=0, padding=(12, 8))
        style.map("Primary.TButton", background=[("active", "#2e70c9")])
        style.configure("Quiet.TButton", background=self.COLORS["panel2"], foreground=self.COLORS["text"], bordercolor=self.COLORS["line"], padding=(10, 7))
        style.configure("Nav.TButton", background=self.COLORS["panel"], foreground="#b5bfcc", borderwidth=0, anchor="w", padding=(18, 13))
        style.map("Nav.TButton", background=[("active", "#202833")], foreground=[("active", self.COLORS["blue"])])
        style.configure("Danger.TButton", background="#2a1a1a", foreground=self.COLORS["red"], bordercolor="#9f413d", padding=(12, 8))
        style.configure("Start.TButton", background="#17231a", foreground=self.COLORS["green"], bordercolor="#488842", padding=(12, 8))
        style.configure("Treeview", background="#15191d", fieldbackground="#15191d", foreground=self.COLORS["text"], rowheight=31, bordercolor=self.COLORS["line"])
        style.map("Treeview", background=[("selected", "#253a55")])

    def _build(self) -> None:
        root = ttk.Frame(self, style="App.TFrame")
        root.pack(fill="both", expand=True)
        toolbar = ttk.Frame(root, style="Panel.TFrame")
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text="Blocksmith", style="Header.TLabel").pack(side="left", padx=(14, 10), pady=9)
        for label in ("Console", "Files", "Mods", "Backups", "Settings"):
            ttk.Button(toolbar, text=label, style="Quiet.TButton", command=lambda name=label: self.show_view(name)).pack(side="left", padx=2, pady=6)
        self.connect_button = ttk.Button(toolbar, text="Connect", style="Primary.TButton", command=self.login)
        self.connect_button.pack(side="right", padx=(4, 12), pady=6)
        self.refresh_button = ttk.Button(toolbar, text="Refresh", style="Quiet.TButton", command=self.refresh)
        self.refresh_button.pack(side="right", padx=4, pady=6)
        self.server_note = ttk.Label(toolbar, text="● Connect to server", style="Muted.TLabel")
        self.server_note.pack(side="right", padx=12)

        titlebar = ttk.Frame(root, style="Panel.TFrame")
        titlebar.pack(fill="x", pady=(1, 0))
        self.title_label = ttk.Label(titlebar, text="Console", style="Header.TLabel")
        self.title_label.pack(side="left", padx=14, pady=8)
        self.profile_label = ttk.Label(titlebar, text="No profile selected", style="Muted.TLabel")
        self.profile_label.pack(side="left", pady=8)

        body = ttk.Frame(root, style="App.TFrame")
        body.pack(fill="both", expand=True)
        self.right = ttk.Frame(body, style="Panel.TFrame", width=220)
        self.right.pack(side="right", fill="y")
        self.right.pack_propagate(False)
        ttk.Label(self.right, text="ONLINE PLAYERS", style="Header.TLabel").pack(anchor="w", padx=18, pady=(22, 8))
        self.players_frame = ttk.Frame(self.right, style="Panel.TFrame")
        self.players_frame.pack(fill="x", padx=16)
        ttk.Separator(self.right).pack(fill="x", padx=16, pady=22)
        ttk.Label(self.right, text="SERVER HEALTH", style="Header.TLabel").pack(anchor="w", padx=18)
        self.health = ttk.Label(self.right, text="Status: stopped\nProfile: none\nLast command: none", style="Muted.TLabel", justify="left", wraplength=220)
        self.health.pack(anchor="w", padx=18, pady=13)
        self.content = ttk.Frame(body, style="App.TFrame")
        self.content.pack(side="left", fill="both", expand=True)
        self.show_view("Console")

    def _resize_layout(self, event: tk.Event | None = None) -> None:
        """Keep the primary controls visible when the window is narrower than the full dashboard."""
        if event is not None and event.widget is not self:
            return
        compact = self.winfo_width() < 980
        if compact == self.compact_layout:
            return
        self.compact_layout = compact
        if compact:
            self.right.pack_forget()
            self.server_note.pack_forget()
        else:
            self.right.pack(side="right", fill="y")
            self.server_note.pack(side="right", padx=12, before=self.refresh_button)

    def clear_content(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()

    def show_view(self, name: str) -> None:
        self.view_name = name
        self.title_label.configure(text=name)
        self.clear_content()
        if name == "Console": self.console_view()
        elif name == "Files": self.files_view()
        elif name == "Mods": self.mods_view()
        elif name == "Backups": self.backups_view()
        else: self.settings_view()

    def console_view(self) -> None:
        frame = ttk.Frame(self.content, style="App.TFrame", padding=22)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1); frame.rowconfigure(1, weight=1)
        command = ttk.Frame(frame, style="Panel.TFrame", padding=8)
        command.grid(row=0, column=0, sticky="ew", pady=(0, 15)); command.columnconfigure(1, weight=1)
        ttk.Label(command, text=">_", style="Panel.TLabel").grid(row=0, column=0, padx=(5, 10))
        entry = ttk.Entry(command, textvariable=self.command)
        entry.grid(row=0, column=1, sticky="ew"); entry.bind("<Return>", lambda _: self.send_command())
        ttk.Button(command, text="Send", style="Quiet.TButton", command=self.send_command).grid(row=0, column=2, padx=(10, 0))
        self.logs = tk.Text(frame, bg="#121518", fg="#b7c1cc", insertbackground="white", relief="flat", font=("Cascadia Mono", 10), wrap="word", state="disabled")
        self.logs.grid(row=1, column=0, sticky="nsew")
        actions = ttk.Frame(frame, style="App.TFrame")
        actions.grid(row=2, column=0, sticky="ew", pady=(15, 0))
        for col in range(3): actions.columnconfigure(col, weight=1)
        ttk.Button(actions, text="Start", style="Start.TButton", command=lambda: self.action("start")).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(actions, text="Restart", style="Quiet.TButton", command=lambda: self.action("restart")).grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(actions, text="Stop", style="Danger.TButton", command=lambda: self.action("stop")).grid(row=0, column=2, sticky="ew", padx=(5, 0))
        self.refresh_logs()

    def files_view(self) -> None:
        frame = self.list_view("Files", "Browse the active profile folder. Files cannot leave this directory.")
        actions = ttk.Frame(frame, style="App.TFrame"); actions.pack(fill="x", pady=(0, 10))
        ttk.Button(actions, text="Up one folder", style="Quiet.TButton", command=self.files_up).pack(side="left")
        ttk.Button(actions, text="Upload file", style="Primary.TButton", command=self.upload_file).pack(side="right")
        self.file_tree = self.tree(frame, ("Name", "Type", "Size", "Modified"))
        self.file_tree.bind("<Double-1>", self.open_file_item)
        ttk.Button(frame, text="Delete selected file", style="Danger.TButton", command=self.delete_file).pack(anchor="e", pady=(10, 0))
        self.list_files()

    def mods_view(self) -> None:
        frame = self.list_view("Mods", "Mod JARs uploaded to the active profile.")
        actions = ttk.Frame(frame, style="App.TFrame"); actions.pack(fill="x", pady=(0, 10))
        ttk.Button(actions, text="Sync server mods", style="Quiet.TButton", command=self.sync_server_mods).pack(side="right")
        ttk.Button(actions, text="Install selected mods", style="Quiet.TButton", command=self.install_selected_mods).pack(side="right")
        ttk.Button(actions, text="Upload mod", style="Primary.TButton", command=lambda: self.upload_file(mod=True)).pack(side="right", padx=(0, 8))
        self.mod_tree = self.tree(frame, ("Filename", "Uploaded by", "Uploaded at"))
        self.mod_tree.configure(selectmode="extended")
        for mod in self.state.get("mods", []): self.mod_tree.insert("", "end", iid=mod["filename"], values=(mod["filename"], mod["uploaded_by"], str(mod["uploaded_at"])))

    def install_selected_mods(self) -> None:
        selected = getattr(self, "mod_tree", None)
        if selected is None or not selected.selection():
            messagebox.showinfo("Install Mods", "Select one or more mods to install first.")
            return
        self.install_mods(list(selected.selection()), "Install Mods")

    def sync_server_mods(self) -> None:
        filenames = [mod["filename"] for mod in self.state.get("mods", [])]
        if not filenames:
            messagebox.showinfo("Sync Server Mods", "This server has no uploaded mods to sync.")
            return
        self.install_mods(filenames, "Sync Server Mods")

    def install_mods(self, filenames: list[str], title: str) -> None:
        mods_by_name = {mod["filename"]: mod for mod in self.state.get("mods", [])}
        target_dir = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / ".minecraft" / "mods"
        installed: list[str] = []
        skipped: list[str] = []
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            for filename in filenames:
                mod = mods_by_name[filename]
                destination = target_dir / filename
                uploaded_at = datetime.fromisoformat(mod["uploaded_at"].replace("Z", "+00:00"))
                server_timestamp = uploaded_at.replace(tzinfo=uploaded_at.tzinfo or timezone.utc).timestamp()
                if destination.exists() and destination.stat().st_mtime >= server_timestamp:
                    skipped.append(filename)
                    continue
                response = requests.get(self.endpoint(f"/api/server/mods/{filename}/download"), headers=self.headers(), timeout=120)
                response.raise_for_status()
                temporary = destination.with_suffix(destination.suffix + ".download")
                temporary.write_bytes(response.content)
                temporary.replace(destination)
                os.utime(destination, (server_timestamp, server_timestamp))
                installed.append(filename)
        except (OSError, KeyError, ValueError, requests.RequestException) as exc:
            self.error(f"{title} failed", exc)
            return
        summary = []
        if installed: summary.append(f"Installed: {', '.join(installed)}")
        if skipped: summary.append(f"Already current: {', '.join(skipped)}")
        messagebox.showinfo(title, "\n".join(summary) or "No mods changed.")

    def backups_view(self) -> None:
        frame = self.list_view("Backups", "ZIP snapshots of the active server folder.")
        actions = ttk.Frame(frame, style="App.TFrame"); actions.pack(fill="x", pady=(0, 10))
        ttk.Button(actions, text="Create backup", style="Primary.TButton", command=self.create_backup).pack(side="right")
        self.backup_tree = self.tree(frame, ("Name", "Size", "Created"))
        self.backup_tree.bind("<Double-1>", lambda _: self.download_backup())
        ttk.Button(frame, text="Download selected", style="Quiet.TButton", command=self.download_backup).pack(side="left", pady=(10, 0))
        ttk.Button(frame, text="Delete selected", style="Danger.TButton", command=self.delete_backup).pack(side="right", pady=(10, 0))
        self.list_backups()

    def settings_view(self) -> None:
        frame = self.list_view("Settings", "Profile changes require a stopped server.")
        form = ttk.Frame(frame, style="Panel.TFrame", padding=16); form.pack(fill="x")
        self.settings_profile = ttk.Combobox(form, state="readonly", values=[p["name"] for p in self.state.get("profiles", [])])
        self.settings_profile.set(self.state.get("active_profile") or ""); self.settings_profile.grid(row=0, column=1, sticky="ew", pady=4); self.settings_profile.bind("<<ComboboxSelected>>", lambda _: self.load_profile_form())
        self.settings_jar = tk.StringVar(); self.settings_dir = tk.StringVar(); self.settings_runtime = ttk.Combobox(form, state="readonly", values=[r["name"] for r in self.state.get("java_runtimes", [])]); self.settings_jvm = tk.StringVar(); self.settings_args = tk.StringVar(); self.settings_mod_dir = tk.StringVar()
        fields = [("Profile", self.settings_profile), ("Server JAR", self.settings_jar), ("Working directory", self.settings_dir), ("Java runtime", self.settings_runtime), ("JVM arguments", self.settings_jvm), ("Server arguments", self.settings_args), ("Mod directory", self.settings_mod_dir)]
        for row, (label, value) in enumerate(fields):
            ttk.Label(form, text=label, style="Muted.TLabel").grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
            widget = value if isinstance(value, ttk.Combobox) else ttk.Entry(form, textvariable=value)
            if row: widget.grid(row=row, column=1, sticky="ew", pady=5)
        form.columnconfigure(1, weight=1); ttk.Button(form, text="Save profile", style="Primary.TButton", command=self.save_profile).grid(row=7, column=1, sticky="e", pady=(12, 0))
        ttk.Label(frame, text="Operator notes", style="Header.TLabel").pack(anchor="w", pady=(20, 5))
        self.notes = tk.Text(frame, height=5, bg="#15191d", fg=self.COLORS["text"], insertbackground="white", relief="flat")
        self.notes.pack(fill="x"); self.notes.insert("1.0", self.state.get("notes", "")); ttk.Button(frame, text="Save notes", style="Quiet.TButton", command=self.save_notes).pack(anchor="e", pady=8)
        self.load_profile_form()

    def list_view(self, heading: str, description: str) -> ttk.Frame:
        frame = ttk.Frame(self.content, style="App.TFrame", padding=25); frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=heading, style="Title.TLabel").pack(anchor="w")
        ttk.Label(frame, text=description, style="Muted.TLabel").pack(anchor="w", pady=(2, 17))
        return frame

    def tree(self, parent: ttk.Frame, columns: tuple[str, ...]) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=columns, show="headings")
        for column in columns:
            tree.heading(column, text=column)
            tree.column(column, width=125, minwidth=80, stretch=True)
        tree.pack(fill="both", expand=True)
        return tree

    def headers(self) -> dict[str, str]: return {"Authorization": f"Bearer {self.token}"} if self.token else {}
    def endpoint(self, path: str) -> str: return f"{self.base_url.get().rstrip('/')}{path}"

    def login(self) -> None:
        if not self.token:
            self.username.set(simpledialog.askstring("Connect", "Username:", initialvalue=self.username.get(), parent=self) or "")
            self.password.set(simpledialog.askstring("Connect", "Password:", show="*", initialvalue=self.password.get(), parent=self) or "")
        if not self.username.get() or not self.password.get(): return
        try:
            response = requests.post(self.endpoint("/api/auth/login"), json={"username": self.username.get(), "password": self.password.get()}, timeout=15); response.raise_for_status()
            self.token = response.json()["access_token"]; self.refresh()
        except (requests.RequestException, KeyError) as exc: self.error("Connect failed", exc)

    def refresh(self) -> None:
        if not self.token: self.login(); return
        try:
            self.state = self.get_json("/api/server/state"); self.profile_label.configure(text=self.state.get("active_profile") or "No profile selected")
            self.server_note.configure(text=f"● Server {self.state.get('server_status', 'unknown')}")
            metrics = self.get_json("/api/server/health")
            cpu = "--" if metrics.get("cpu_percent") is None else f"{metrics['cpu_percent']:.1f}%"
            memory = self.memory_text(metrics.get("memory_bytes"))
            tps = "--" if metrics.get("tick_rate") is None else f"{metrics['tick_rate']:.1f} TPS"
            self.health.configure(text=f"CPU usage: {cpu}\nMemory: {memory}\nTick rate: {tps}\n{metrics.get('tick_source', '')}\n\nProfile: {self.state.get('active_profile') or 'none'}")
            self.refresh_players()
            self.show_view(self.view_name)
        except requests.RequestException as exc: self.error("Could not refresh", exc)

    def get_json(self, path: str) -> dict:
        response = requests.get(self.endpoint(path), headers=self.headers(), timeout=30); response.raise_for_status(); return response.json()

    @staticmethod
    def memory_text(value: int | None) -> str:
        if value is None:
            return "--"
        if value < 1024 * 1024 * 1024:
            return f"{value / 1024 / 1024:.0f} MB"
        return f"{value / 1024 / 1024 / 1024:.1f} GB"
    def action(self, action: str, payload: dict | None = None) -> None:
        try:
            response = requests.post(self.endpoint(f"/api/server/{action}"), headers=self.headers(), json=payload, timeout=90); response.raise_for_status(); self.refresh()
        except requests.RequestException as exc: self.error("Server action failed", exc)
    def send_command(self) -> None:
        value = self.command.get().strip()
        if value: self.action("command", {"command": value}); self.command.set("")
    def refresh_logs(self) -> None:
        if not hasattr(self, "logs") or not self.token: return
        try:
            lines = self.get_json("/api/server/logs?lines=500").get("lines", []); self.logs.configure(state="normal"); self.logs.delete("1.0", "end"); self.logs.insert("1.0", "\n".join(lines) or "No server output yet."); self.logs.see("end"); self.logs.configure(state="disabled")
        except requests.RequestException: pass
    def refresh_players(self) -> None:
        try: players = self.get_json("/api/server/players").get("players", [])
        except requests.RequestException: players = []
        for child in self.players_frame.winfo_children(): child.destroy()
        self.player_images.clear()
        if not players: ttk.Label(self.players_frame, text="No players currently detected.", style="Muted.TLabel").pack(anchor="w", pady=8)
        for player in players:
            row = ttk.Frame(self.players_frame, style="Panel.TFrame")
            row.pack(fill="x", pady=6)
            image = self.player_head(player["name"])
            if image:
                ttk.Label(row, image=image, style="Panel.TLabel").pack(side="left", padx=(0, 9))
            else:
                ttk.Label(row, text=player["name"][:2].upper(), style="Panel.TLabel", width=3).pack(side="left", padx=(0, 9))
            ttk.Label(row, text=f"{player['name']}\n{self.online_duration(player.get('online_seconds'))}", style="Panel.TLabel").pack(side="left")

    def player_head(self, name: str) -> tk.PhotoImage | None:
        try:
            response = requests.get(f"https://mc-heads.net/avatar/{name}/48", timeout=5)
            response.raise_for_status()
            image = tk.PhotoImage(data=base64.b64encode(response.content))
            self.player_images.append(image)
            return image
        except (requests.RequestException, tk.TclError):
            return None

    @staticmethod
    def online_duration(seconds: int | None) -> str:
        if seconds is None:
            return "Online"
        hours, remainder = divmod(seconds, 3600)
        minutes = remainder // 60
        return f"{hours}h {minutes}m online" if hours else f"{minutes}m online"

    def list_files(self) -> None:
        if not self.token: return
        try:
            data = self.get_json(f"/api/server/files?path={self.file_path}")
            self.file_path = data["path"]
            for row in self.file_tree.get_children(): self.file_tree.delete(row)
            for item in data["items"]: self.file_tree.insert("", "end", iid=item["path"], values=(item["name"], item["kind"], item.get("size") or "", item["modified_at"]))
        except requests.RequestException as exc: self.error("Could not load files", exc)
    def files_up(self) -> None: self.file_path = "/".join(self.file_path.split("/")[:-1]); self.list_files()
    def open_file_item(self, _event=None) -> None:
        selected = self.file_tree.selection()
        if not selected: return
        values = self.file_tree.item(selected[0], "values")
        if values[1] == "folder": self.file_path = selected[0]; self.list_files()
        else: self.download_file(selected[0])
    def upload_file(self, mod: bool = False) -> None:
        path = filedialog.askopenfilename(title="Choose mod JAR" if mod else "Choose file", filetypes=[("Java archive", "*.jar"), ("All files", "*.*")])
        if not path: return
        try:
            with open(path, "rb") as handle:
                target = "/api/server/mods" if mod else "/api/server/files"
                data = None if mod else {"directory": self.file_path}
                response = requests.post(self.endpoint(target), headers=self.headers(), data=data, files={"file": (Path(path).name, handle)}, timeout=120); response.raise_for_status()
            self.refresh()
        except (OSError, requests.RequestException) as exc: self.error("Upload failed", exc)
    def download_file(self, path: str) -> None:
        destination = filedialog.asksaveasfilename(initialfile=Path(path).name)
        if not destination: return
        try:
            response = requests.get(self.endpoint("/api/server/files/download"), headers=self.headers(), params={"path": path}, timeout=120); response.raise_for_status(); Path(destination).write_bytes(response.content)
        except (OSError, requests.RequestException) as exc: self.error("Download failed", exc)
    def delete_file(self) -> None:
        selected = self.file_tree.selection()
        if not selected or not messagebox.askyesno("Delete file", f"Delete {selected[0]}?"): return
        try: requests.delete(self.endpoint("/api/server/files"), headers=self.headers(), params={"path": selected[0]}, timeout=30).raise_for_status(); self.list_files()
        except requests.RequestException as exc: self.error("Delete failed", exc)
    def list_backups(self) -> None:
        if not self.token: return
        try:
            for row in self.backup_tree.get_children(): self.backup_tree.delete(row)
            for item in self.get_json("/api/server/backups")["backups"]: self.backup_tree.insert("", "end", iid=item["name"], values=(item["name"], item["size"], item["created_at"]))
        except requests.RequestException as exc: self.error("Could not load backups", exc)
    def create_backup(self) -> None:
        label = simpledialog.askstring("Create backup", "Backup label (optional):", initialvalue="snapshot", parent=self)
        if label is None: return
        self.action("backups", {"label": label}); self.list_backups()
    def download_backup(self) -> None:
        selected = self.backup_tree.selection()
        if not selected: return
        destination = filedialog.asksaveasfilename(initialfile=selected[0], defaultextension=".zip")
        if not destination: return
        try:
            response = requests.get(self.endpoint("/api/server/backups/download"), headers=self.headers(), params={"name": selected[0]}, timeout=120)
            response.raise_for_status()
            Path(destination).write_bytes(response.content)
        except (OSError, requests.RequestException) as exc: self.error("Download failed", exc)
    def delete_backup(self) -> None:
        selected = self.backup_tree.selection()
        if not selected or not messagebox.askyesno("Delete backup", f"Delete {selected[0]}?"): return
        try: requests.delete(self.endpoint("/api/server/backups"), headers=self.headers(), params={"name": selected[0]}, timeout=30).raise_for_status(); self.list_backups()
        except requests.RequestException as exc: self.error("Delete failed", exc)
    def load_profile_form(self) -> None:
        profile = next((p for p in self.state.get("profiles", []) if p["name"] == self.settings_profile.get()), None)
        if not profile: return
        self.settings_jar.set(profile["server_jar"]); self.settings_dir.set(profile["working_directory"]); self.settings_runtime.set(profile["java_runtime"]); self.settings_jvm.set(" ".join(profile["jvm_args"])); self.settings_args.set(" ".join(profile["server_args"])); self.settings_mod_dir.set(profile["mod_directory"])
    def save_profile(self) -> None:
        name = self.settings_profile.get()
        if not name: return
        payload = {"name": name, "server_jar": self.settings_jar.get(), "working_directory": self.settings_dir.get(), "java_runtime": self.settings_runtime.get(), "jvm_args": self.settings_jvm.get().split(), "server_args": self.settings_args.get().split(), "mod_directory": self.settings_mod_dir.get()}
        try: requests.put(self.endpoint(f"/api/server/profiles/{name}"), headers=self.headers(), json=payload, timeout=30).raise_for_status(); self.refresh()
        except requests.RequestException as exc: self.error("Could not save profile", exc)
    def save_notes(self) -> None:
        try: requests.put(self.endpoint("/api/server/notes"), headers=self.headers(), json={"notes": self.notes.get("1.0", "end-1c")}, timeout=30).raise_for_status(); messagebox.showinfo("Notes", "Notes saved.")
        except requests.RequestException as exc: self.error("Could not save notes", exc)
    def error(self, title: str, error: Exception) -> None:
        detail = str(error)
        if isinstance(error, requests.HTTPError) and error.response is not None:
            try: detail = error.response.json().get("detail", detail)
            except ValueError: pass
        messagebox.showerror(title, detail)


if __name__ == "__main__":
    BlocksmithConsole().mainloop()
