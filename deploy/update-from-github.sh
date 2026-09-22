#!/usr/bin/env bash
set -euo pipefail

APP_USER="scorpion"
REPO_DIR="/home/scorpion/minecraft"
BRANCH="main"
SERVICE="minecraft-control-plane.service"
RESTART_MARKER="$REPO_DIR/.restart-required"

run_as_app_user() {
  runuser -u "$APP_USER" -- "$@"
}

if ! run_as_app_user git -C "$REPO_DIR" diff --quiet || ! run_as_app_user git -C "$REPO_DIR" diff --cached --quiet; then
  echo "Refusing to update: the deployment checkout has local changes."
  exit 1
fi

run_as_app_user git -C "$REPO_DIR" fetch --quiet origin "$BRANCH"
local_revision="$(run_as_app_user git -C "$REPO_DIR" rev-parse HEAD)"
remote_revision="$(run_as_app_user git -C "$REPO_DIR" rev-parse "origin/$BRANCH")"

if [[ "$local_revision" == "$remote_revision" ]]; then
  exit 0
fi

run_as_app_user git -C "$REPO_DIR" merge --ff-only "origin/$BRANCH"
run_as_app_user "$REPO_DIR/backend/.venv/bin/python" -m pip install --quiet -r "$REPO_DIR/backend/requirements.txt"
touch "$RESTART_MARKER"
echo "Updated Minecraft Control Plane to $remote_revision; restart $SERVICE after Minecraft is stopped."
