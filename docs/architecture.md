# Architecture

## Components

### Linux host service

The backend is a FastAPI application that owns:

- Authentication and role-based access
- Java runtime registration
- Server profile registration
- Minecraft process lifecycle management
- Mod upload placement
- Web dashboard rendering

The backend persists state in JSON files for this first pass so it is easy to understand and move around. A future production version should move to SQLite or PostgreSQL.

### Windows desktop client

The Windows application is a Python Tkinter client that authenticates against the backend API and exposes:

- Start, stop, and restart buttons
- Profile switching
- Admin command entry
- Mod uploads
- User creation for additional remote admins
- Log viewing

### Browser access

The web dashboard is intentionally lightweight. The backend already exposes the needed API, so a richer SPA can be added later without changing the control model.

## Deployment model

1. Linux machine runs the FastAPI service and the Minecraft server jar process.
2. Windows desktops run the client app and talk to the API over the network.
3. Multiple users authenticate with role-based permissions.

## Roadmap

- Add SQLite persistence and migrations
- Add HTTPS, refresh tokens, and password reset flows
- Add server file browser and modpack import workflows
- Add background tasks for backup scheduling
- Add live websocket log streaming
- Package the Windows client with PyInstaller or MSIX
