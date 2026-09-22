# Minecraft Control Plane

This repository scaffolds a Python-based Minecraft server manager designed for a Linux host plus Windows desktop administration clients.

## What it does

- Runs a Python API on Linux that can start, stop, restart, and send console commands to a Minecraft server process.
- Lets you register multiple Java runtimes and multiple server profiles so different server jars can run against different Java versions.
- Supports authenticated users with roles so multiple people can install the Windows client and manage the same server.
- Accepts mod `.jar` uploads from the Windows client and places them into the active profile's `mods` folder.
- Includes a lightweight web dashboard backed by the same API.

## Project layout

- `backend/`: Linux-hosted FastAPI service and web dashboard.
- `desktop_client/`: Windows desktop client built with Tkinter.
- `docs/`: deployment and architecture notes.

## Quick start

### Linux host

1. Install Python 3.11+ and Java runtimes you want to offer. On Debian or Ubuntu:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-full
```

2. Create a virtual environment and install backend dependencies:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python run_server.py
```

If the server reports a `bcrypt`/`passlib` startup error after an earlier install, repair the virtual environment with:

```bash
python -m pip install --upgrade --force-reinstall "bcrypt>=4.1,<5" "passlib[bcrypt]==1.7.4"
```

3. Sign in with the bootstrap owner account:

- Username: `owner`
- Password: `changeme`

4. Immediately create a real owner/admin account and rotate the bootstrap password.

### Windows client

You can either run from source during development or install a packaged desktop app.

#### Install the packaged app

1. On a build machine, install [Inno Setup 6](https://jrsoftware.org/isinfo.php).
2. From PowerShell in the repository root, create the installer:

```powershell
.\desktop_client\build_installer.ps1
```

3. Distribute `installer-output\Minecraft-Control-Plane-Setup-0.1.0.exe`. It installs the app without requiring Python, adds a Start Menu entry, and offers a desktop shortcut during setup. The AIMNET Minecraft icon is embedded in the installer, app executable, and created shortcuts automatically.

#### Run from source

1. Install Python 3.11+ on Windows.
2. Install the client dependency:

```powershell
cd desktop_client
py -m pip install -r requirements.txt
py client.py
```

3. Point the app at your Linux host, for example `http://192.168.1.50:9090`.

## Important next steps

- Put the API behind HTTPS and a reverse proxy before exposing it outside your LAN.
- Replace the default secret key using `MCM_SECRET_KEY`.
- Add stronger audit logging, backups, and staged mod/profile validation before production use.

## GitHub deployment

See [GitHub deployment and auto-update](docs/github-auto-update.md) to deploy the Linux host from GitHub and automatically apply new `main` branch updates.
