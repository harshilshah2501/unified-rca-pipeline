#!/usr/bin/env python3
"""Export e-commerce RCA scenario tables from PostgreSQL to JSON.

Reads the three tables created by datasets/dump_scenario_postgres.sh and writes:
  <out>/metrics.json
  <out>/logs.json
  <out>/spans.json
  <out>/manifest.json

Requires: psycopg2 OR psql + python3 stdlib (psql COPY path).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _iso(ts) -> str:
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    s = str(ts).replace(" ", "T")
    if s.endswith("+00"):
        s = s[:-3] + "Z"
    elif "+" not in s and not s.endswith("Z"):
        s += "Z"
    return s


def export_via_psycopg2(args: argparse.Namespace, out: Path) -> dict:
    import psycopg2
    import psycopg2.extras

    conn = psycopg2.connect(
        host=args.host,
        port=args.port,
        dbname=args.db,
        user=args.user,
        password=args.password,
    )
    schema = args.schema
    tenant = args.tenant
    counts: dict[str, int] = {}
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            f"SELECT ts, metric_name, value, labels FROM {schema}.otel_metrics "
            "WHERE tenant_id = %s ORDER BY ts, metric_name",
            (tenant,),
        )
        metrics = [
            {
                "ts": _iso(r["ts"]),
                "metric_name": r["metric_name"],
                "value": float(r["value"]) if r["value"] is not None else None,
                "labels": r["labels"] or {},
            }
            for r in cur.fetchall()
        ]
        cur.execute(
            f"SELECT ts, stream, level, logger, message, attributes FROM {schema}.otel_logs "
            "WHERE tenant_id = %s ORDER BY ts",
            (tenant,),
        )
        logs = [
            {
                "ts": _iso(r["ts"]),
                "stream": r["stream"],
                "level": r["level"],
                "logger": r["logger"],
                "message": r["message"],
                "attributes": r["attributes"] or {},
            }
            for r in cur.fetchall()
        ]
        cur.execute(
            f"SELECT trace_id, span_id, parent_span_id, service_name, span_name, span_kind, "
            f"start_time, end_time, duration_ms, attributes FROM {schema}.otel_spans "
            "WHERE tenant_id = %s ORDER BY start_time, span_id",
            (tenant,),
        )
        spans = [
            {
                "trace_id": r["trace_id"],
                "span_id": r["span_id"],
                "parent_span_id": r["parent_span_id"],
                "service_name": r["service_name"],
                "span_name": r["span_name"],
                "span_kind": r["span_kind"],
                "start_time": _iso(r["start_time"]),
                "end_time": _iso(r["end_time"]),
                "duration_ms": float(r["duration_ms"]) if r["duration_ms"] is not None else None,
                "attributes": r["attributes"] or {},
            }
            for r in cur.fetchall()
        ]
    conn.close()
    counts = {"metrics": len(metrics), "logs": len(logs), "spans": len(spans)}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    (out / "logs.json").write_text(json.dumps(logs, indent=2) + "\n")
    (out / "spans.json").write_text(json.dumps(spans, indent=2) + "\n")
    return counts


def export_via_psql(args: argparse.Namespace, out: Path) -> dict:
    """Fallback when psycopg2 is unavailable — use psql JSON aggregation."""
    env = os.environ.copy()
    env["PGPASSWORD"] = args.password
    base = [
        "psql",
        "-h",
        args.host,
        "-p",
        str(args.port),
        "-U",
        args.user,
        "-d",
        args.db,
        "-v",
        "ON_ERROR_STOP=1",
        "-t",
        "-A",
    ]

    def q(sql: str) -> str:
        r = subprocess.run(
            base + ["-c", sql],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        return r.stdout.strip()

    schema = args.schema
    tenant = args.tenant.replace("'", "''")
    metrics_sql = f"""
SELECT COALESCE(json_agg(row_to_json(t) ORDER BY ts, metric_name), '[]'::json)
FROM (
  SELECT to_char(ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS ts,
         metric_name, value, labels
  FROM {schema}.otel_metrics WHERE tenant_id = '{tenant}'
) t;
"""
    logs_sql = f"""
SELECT COALESCE(json_agg(row_to_json(t) ORDER BY ts), '[]'::json)
FROM (
  SELECT to_char(ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS ts,
         stream, level, logger, message, attributes
  FROM {schema}.otel_logs WHERE tenant_id = '{tenant}'
) t;
"""
    spans_sql = f"""
SELECT COALESCE(json_agg(row_to_json(t) ORDER BY start_time, span_id), '[]'::json)
FROM (
  SELECT trace_id, span_id, parent_span_id, service_name, span_name, span_kind,
         to_char(start_time AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS start_time,
         to_char(end_time AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS end_time,
         duration_ms, attributes
  FROM {schema}.otel_spans WHERE tenant_id = '{tenant}'
) t;
"""
    metrics = json.loads(q(metrics_sql) or "[]")
    logs = json.loads(q(logs_sql) or "[]")
    spans = json.loads(q(spans_sql) or "[]")
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    (out / "logs.json").write_text(json.dumps(logs, indent=2) + "\n")
    (out / "spans.json").write_text(json.dumps(spans, indent=2) + "\n")
    return {"metrics": len(metrics), "logs": len(logs), "spans": len(spans)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default=os.environ.get("PGHOST", "localhost"))
    p.add_argument("--port", type=int, default=int(os.environ.get("PGPORT", "5432")))
    p.add_argument("--db", default=os.environ.get("PGDATABASE", "observability"))
    p.add_argument("--user", default=os.environ.get("PGUSER", "rca"))
    p.add_argument("--password", default=os.environ.get("PGPASSWORD", "rca"))
    p.add_argument("--schema", default="public")
    p.add_argument("--tenant", default="acme")
    p.add_argument(
        "--out",
        type=Path,
        default=Path("datasets/ecom_checkout/raw"),
    )
    args = p.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    try:
        counts = export_via_psycopg2(args, args.out)
        method = "psycopg2"
    except ImportError:
        counts = export_via_psql(args, args.out)
        method = "psql"
    except Exception as first:
        try:
            counts = export_via_psql(args, args.out)
            method = "psql"
        except Exception as second:
            print(f"ERROR: psycopg2 path failed: {first}", file=sys.stderr)
            print(f"ERROR: psql path failed: {second}", file=sys.stderr)
            return 1

    manifest = {
        "source": "postgres",
        "export_method": method,
        "tenant_id": args.tenant,
        "schema": args.schema,
        "host": args.host,
        "db": args.db,
        "counts": counts,
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
