# Dashboard systemd

Install the PoC console so it starts on boot (port **8765**).

```bash
# From repo root
sudo cp benchmarking/dashboard/deploy/unified-rca-dashboard.service \
  /etc/systemd/system/unified-rca-dashboard.service
# or symlink:
# sudo ln -sf "$PWD/benchmarking/dashboard/deploy/unified-rca-dashboard.service" \
#   /etc/systemd/system/unified-rca-dashboard.service

sudo systemctl daemon-reload
sudo systemctl enable --now unified-rca-dashboard.service
sudo systemctl status unified-rca-dashboard.service
```

Open: http://127.0.0.1:8765/

```bash
sudo systemctl restart unified-rca-dashboard.service   # after code updates
journalctl -u unified-rca-dashboard.service -f
```
