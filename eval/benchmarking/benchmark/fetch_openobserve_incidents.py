#!/usr/bin/env python3
"""Fetch OpenObserve v2 alerts + incidents into a local corpus snapshot."""

from __future__ import annotations

import argparse
import base64
import json
import os
import urllib.request
from pathlib import Path


def _auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, auth: str) -> dict | list:
    req = urllib.request.Request(
        url, headers={"Authorization": auth, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("datasets/openobserve_incidents/v1"),
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OPENOBSERVE_URL", "http://172.16.14.77:5080"),
    )
    parser.add_argument(
        "--org",
        default=os.environ.get("OPENOBSERVE_ORG", "default"),
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("OPENOBSERVE_USER", ""),
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("OPENOBSERVE_PASSWORD", ""),
    )
    args = parser.parse_args()
    if not args.user or not args.password:
        raise SystemExit(
            "Set OPENOBSERVE_USER and OPENOBSERVE_PASSWORD (or --user/--password)."
        )

    auth = _auth_header(args.user, args.password)
    base = args.base_url.rstrip("/")
    org = args.org
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "incidents").mkdir(exist_ok=True)

    alerts = get_json(f"{base}/api/v2/{org}/alerts", auth)
    incidents_list = get_json(f"{base}/api/v2/{org}/alerts/incidents", auth)
    (out / "alerts.json").write_text(json.dumps(alerts, indent=2) + "\n")
    (out / "list.json").write_text(json.dumps(incidents_list, indent=2) + "\n")

    incidents = incidents_list.get("incidents") or []
    for i, inc in enumerate(incidents, 1):
        iid = inc["id"]
        detail = get_json(f"{base}/api/v2/{org}/alerts/incidents/{iid}", auth)
        (out / "incidents" / f"{iid}.json").write_text(
            json.dumps(detail, indent=2) + "\n"
        )
        print(f"[{i}/{len(incidents)}] saved {iid} {detail.get('title')}")

    meta = {
        "base_url": base,
        "org": org,
        "alert_count": len(alerts.get("list") or []),
        "incident_count": len(incidents),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"Wrote {out} ({meta})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
