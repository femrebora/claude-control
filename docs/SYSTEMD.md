# Run claude-control on boot (Linux / systemd)

Useful if you want the dashboard always available on a home server (Beelink, NUC, Raspberry Pi).

## 1. User-level systemd unit

Create `~/.config/systemd/user/claude-control.service` (replace `YOUR_USERNAME` with your actual username):

```ini
[Unit]
Description=claude-control local dashboard
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/YOUR_USERNAME/claude-control
ExecStart=/home/YOUR_USERNAME/claude-control/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1
# If you want to manage a non-default CLAUDE_HOME:
# Environment=CLAUDE_HOME=%h/.claude

[Install]
WantedBy=default.target
```

Then:

```bash
systemctl --user daemon-reload
systemctl --user enable --now claude-control
systemctl --user status claude-control
```

To make it survive logouts (so it runs even when you're not logged in):

```bash
sudo loginctl enable-linger $USER
```

## 2. Logs

```bash
journalctl --user -u claude-control -f
```

## 3. Stop / disable

```bash
systemctl --user stop claude-control
systemctl --user disable claude-control
```

## 4. Firewall

The default `--host 127.0.0.1` binding means the port is **not** reachable from your LAN. If you've set up UFW (recommended):

```bash
sudo ufw status
# claude-control needs no inbound rule because it's loopback-only
```

If you want to access the dashboard from another machine on your LAN, do **not** rebind to `0.0.0.0`. Instead use SSH port forwarding from your laptop:

```bash
ssh -L 8765:127.0.0.1:8765 user@beelink.local
```

Then open <http://127.0.0.1:8765> on your laptop.
