import os
import time
from pathlib import Path
from flask import Flask, abort
import requests

app = Flask("product")
FAULT_DIR = Path(os.getenv("FAULT_DIR", "/faults"))


def _flag(name, default="false"):
    path = FAULT_DIR / name
    if path.exists():
        return path.read_text().strip().lower()
    return default


def _latency():
    try:
        return float(_flag("product.latency", "0"))
    except ValueError:
        return 0.0


def _fail():
    return _flag("product.fail", "false") == "true"


@app.route("/product")
def product():
    latency = _latency()
    if latency > 0:
        time.sleep(latency)

    if _fail():
        abort(500)

    # 30s so code-level inventory SLOWDOWN stays HTTP 200 (not timeout→5xx)
    resp = requests.get("http://inventory:8082/inventory", timeout=60)
    resp.raise_for_status()
    inventory = resp.json()

    return {
        "product": "MacBook",
        "inventory": inventory,
    }


app.run(host="0.0.0.0", port=8081)
