"""Change facts — linked to a CI by id and time; never graph vertices."""

from __future__ import annotations

import json
from typing import Any

from ab_shared.dest import Dest
from ab_shared.schema import validate


def make_change_fact(
    *,
    tenant: str,
    change_id: str,
    ci_id: str,
    occurred_at: str,
    change_kind: str,
    summary: str = "",
    source: str = "lab",
    labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    fact = {
        "schema_version": "change_fact.v1",
        "tenant": tenant,
        "change_id": change_id,
        "ci_id": ci_id,
        "occurred_at": occurred_at,
        "change_kind": change_kind,
        "summary": summary,
        "source": source,
        "labels": labels or {},
    }
    validate("change_fact_v1.schema.json", fact)
    return fact


def append_change_fact(dest: Dest, fact: dict[str, Any]) -> None:
    validate("change_fact_v1.schema.json", fact)
    existing = dest.get("history", "change_facts.jsonl") or b""
    dest.put("history", "change_facts.jsonl", existing + (json.dumps(fact) + "\n").encode("utf-8"))
