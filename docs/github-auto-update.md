# GitHub Deployment And Auto-Update

The Linux host deploys from the `main` branch of this repository. Runtime state, worlds, logs, uploads, and secrets remain outside Git.

## Initial setup on the Linux host

Run these commands once as a user with `sudo` access. Replace the repository URL only if the project is moved.

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-full
sudo mkdir -p /home/scorpion
sudo chown scorpion:scorpion /home/scorpion
sudo -u scorpion git clone https://github.com/rinkerforever/Project-Minecraft.git /home/scorpion/minecraft
sudo -u scorpion python3 -m venv /home/scorpion/minecraft/backend/.venv
sudo -u scorpion /home/scorpion/minecraft/backend/.venv/bin/python -m pip install -r /home/scorpion/minecraft/backend/requirements.txt
```

Create `/home/scorpion/minecraft/backend/.env` with the production secret and host settings. Do not commit this file.

## Enable services

```bash
sudo cp /home/scorpion/minecraft/deploy/systemd/minecraft-control-plane.service /etc/systemd/system/
sudo cp /home/scorpion/minecraft/deploy/systemd/minecraft-control-plane-update.service /etc/systemd/system/
sudo cp /home/scorpion/minecraft/deploy/systemd/minecraft-control-plane-update.timer /etc/systemd/system/
sudo chmod 755 /home/scorpion/minecraft/deploy/update-from-github.sh
sudo systemctl daemon-reload
sudo systemctl enable --now minecraft-control-plane.service
sudo systemctl enable --now minecraft-control-plane-update.timer
```

After every push to `main`, the host checks GitHub within five minutes. It applies only fast-forward updates from a clean checkout, installs backend requirements, and restarts the API. Check the timer with:

```bash
systemctl status minecraft-control-plane-update.timer
journalctl -u minecraft-control-plane-update.service -n 50 --no-pager
```
