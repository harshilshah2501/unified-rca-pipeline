# Lean RCA API deployment

This deploys the product RCA API on port `8780`. The learning UI remains the
separate `federated-pipeline` service on port `8770`.

## Install with systemd

From the repository root:

```bash
chmod +x lean-pipeline/scripts/serve-rca.sh
sudo ln -sf "$PWD/lean-pipeline/deploy/systemd/lean-rca.service" \
  /etc/systemd/system/lean-rca.service
sudo ln -sf "$PWD/lean-pipeline/deploy/systemd/lean-rca.target" \
  /etc/systemd/system/lean-rca.target
sudo systemctl daemon-reload
sudo systemctl enable --now lean-rca.service
sudo systemctl status lean-rca.service
```

The service starts `lean_rca` through `lean-pipeline/scripts/serve-rca.sh`.
It uses the repository virtual environment when available, sets
`PYTHONPATH=lean-pipeline:.`, and defaults `OBSERVEOPS_CORPUS` to
`datasets/observeops`. Override the listening port with a systemd drop-in
that sets `Environment=PORT=<port>`.

## Verify the API

```bash
curl http://127.0.0.1:8780/health
curl http://127.0.0.1:8780/v1/diagnose/UC-1
curl -X POST http://127.0.0.1:8780/v1/diagnose \
  -H 'Content-Type: application/json' \
  -d '{"uc_id":"UC-1"}'
```

## Local smoke test

```bash
lean-pipeline/scripts/serve-rca.sh &
server_pid=$!
sleep 1
curl --fail http://127.0.0.1:8780/health
kill "$server_pid"
wait "$server_pid" 2>/dev/null || true
```
