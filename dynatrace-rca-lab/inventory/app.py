import os
import time
from pathlib import Path
from flask import Flask, abort

app = Flask("inventory")
FAULT_DIR = Path(os.getenv("FAULT_DIR", "/faults"))


def _flag(name, default="false"):
    path = FAULT_DIR / name
    if path.exists():
        return path.read_text().strip().lower()
    return default


def _latency():
    try:
        return float(_flag("inventory.latency", "0"))
    except ValueError:
        return 0.0


def _fail():
    return _flag("inventory.fail", "false") == "true"


@app.route("/inventory")
def inventory():
    latency = _latency()
    if latency > 0:
        time.sleep(latency)

    if _fail():
        abort(500)

    return {"stock": 100}


app.run(host="0.0.0.0", port=8082)
