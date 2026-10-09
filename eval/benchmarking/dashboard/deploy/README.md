# Docs hub systemd (port 8765)

Install the PoC console / docs hub so it starts whenever this WSL distro boots — independent of Cursor.

Requires WSL systemd (`/etc/wsl.conf` → `[boot] systemd=true`). This machine already has that.

```bash
# From repo root
sudo cp eval/benchmarking/dashboard/deploy/unified-rca-dashboard.service \
  /etc/systemd/system/unified-rca-dashboard.service
# or keep a live symlink to the repo copy:
# sudo ln -sf "$PWD/eval/benchmarking/dashboard/deploy/unified-rca-dashboard.service" \
#   /etc/systemd/system/unified-rca-dashboard.service

sudo systemctl daemon-reload
sudo systemctl enable --now unified-rca-dashboard.service
sudo systemctl status unified-rca-dashboard.service --no-pager
```

Open: http://127.0.0.1:8765/ · docs index: http://127.0.0.1:8765/docs.html

```bash
sudo systemctl restart unified-rca-dashboard.service   # after code updates
journalctl -u unified-rca-dashboard.service -f
sudo systemctl disable --now unified-rca-dashboard.service   # stop + un-boot
```

If a one-off Cursor/`start-poc-dash.sh` process already holds `:8765`, stop it before enabling the unit (`./start-poc-dash.sh stop` or kill that PID).
