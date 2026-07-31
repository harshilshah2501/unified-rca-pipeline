import os
import time
from pathlib import Path
from flask import Flask, abort
import requests

app = Flask("frontend")
FAULT_DIR = Path(os.getenv("FAULT_DIR", "/faults"))


def _flag(name, default="false"):
    path = FAULT_DIR / name
    if path.exists():
        return path.read_text().strip().lower()
    return default


def _latency():
    try:
        return float(_flag("frontend.latency", "0"))
    except ValueError:
        return 0.0


def _fail():
    return _flag("frontend.fail", "false") == "true"


@app.route("/")
def home():
    latency = _latency()
    if latency > 0:
        time.sleep(latency)

    if _fail():
        abort(500)

    resp = requests.get("http://product:8081/product", timeout=5)
    resp.raise_for_status()
    return resp.json()


app.run(host="0.0.0.0", port=8080)
