"""Human narration for Incident Analysis (plain-language, paragraph-grade)."""

from __future__ import annotations

from typing import Any

_ECOM_ISOLATION_SNIPPET = "Healthy siblings (pricing/inventory"

_SIGNAL_PLAIN = {
    "request.p95_latency_ms": "slow requests (p95 latency)",
    "tcp.timeouts": "TCP timeouts",
    "error_rate_5xx": "HTTP 5xx errors",
    "http.error_rate": "HTTP error rate",
    "http.error_rate_4xx": "HTTP 4xx error rate",
    "cpu.usage": "CPU usage",
    "cpu.ready": "CPU ready time (VMs waiting for CPU)",
    "linkDown": "link-down",
    "ifOutDiscards": "outbound packet discards",
    "vmnic.dropped_packets": "dropped packets on the host NIC",
    "filesystem.used_pct": "disk nearly full",
    "oom_killer_event": "out-of-memory kill",
    "jvm.heap.used_pct": "JVM heap nearly full",
    "db.conn_pool.active_ratio": "database connection pool saturation",
    "davg_latency_ms": "datastore average latency",
    "gavg_latency_ms": "datastore guest latency",
    "virtualDisk.iops": "virtual-disk IOPS",
    "virtualDisk.totalLatency_ms": "virtual-disk latency",
    "disk.iowait_pct": "disk I/O wait",
    "ping.latency.ms": "ping latency",
    "ping.max.latency.ms": "max ping latency",
    "ping.packet.lost.percent": "ping packet loss",
    "host_cpu_saturation": "host CPU saturation",
    "ping_degradation": "ping degradation",
    "app_error_rate": "application error rate",
}


def plain(s: str | None) -> str:
    if not s:
        return ""
    return str(s).replace("`", "").strip()


def fmt_ts(ts: str | None) -> str:
    if not ts:
        return ""
    s = str(ts).replace("T", " ").replace("+00:00", "Z")
    return s[:19] + (" UTC" if "Z" not in s[:20] and "UTC" not in s else "")


def signal_plain(sig: str | None) -> str:
    if not sig:
        return "an anomaly"
    return _SIGNAL_PLAIN.get(sig, sig.replace("_", " ").replace(".", " "))


def _fmt_val(val: Any, sig: str = "") -> str:
    if val is None:
        return ""
    try:
        f = float(val)
    except (TypeError, ValueError):
        return str(val)
    low = (sig or "").lower()
    if "pct" in low or "percent" in low or "ratio" in low:
        # values sometimes already 0–1, sometimes 0–100
        if 0 < f <= 1.5 and ("ratio" in low or "error_rate" in low):
            return f"{f * 100:.1f}%"
        return f"{f:.1f}%"
    if f == int(f) and abs(f) < 1e6:
        return str(int(f))
    if abs(f) >= 100:
        return f"{f:.0f}"
    return f"{f:.2f}".rstrip("0").rstrip(".")


def human_deps(
    *,
    path: list[str] | None,
    path_s: str,
    root: str,
    seed: dict | None,
    gt: dict | None,
    corpus: str,
    isolation_note: str | None = None,
) -> dict:
    seed = seed or {}
    gt = gt or {}
    chain = [c for c in (path or []) if c]
    if not chain and path_s and path_s != "—":
        chain = [p.strip() for p in path_s.split("→") if p.strip()]
    seed_ci = seed.get("ci") or ""
    seed_sig = signal_plain(seed.get("signal"))
    title = gt.get("fault_title") or gt.get("signature") or root

    note_in = plain(isolation_note)
    if note_in.startswith(_ECOM_ISOLATION_SNIPPET) or "payment-provider as a decoy" in note_in:
        note_in = ""

    if corpus == "motadata":
        prose = (
            f"This Motadata incident was cut from a real telemetry export, so the "
            f"service map is a thin neighborhood around the labeled fault"
            f"{f' (“{title}”)' if title else ''} — not a full CMDB."
        )
        if chain and len(chain) > 1:
            prose += (
                f" Even on that thin slice, the engine’s blast path reads "
                f"{' → '.join(chain)}"
                f"{f', ending where operators first noticed trouble on {seed_ci} ({seed_sig})' if seed_ci else ''}."
            )
        elif root:
            prose += (
                f" Human ground truth points at {root} as the CI to mitigate; "
                f"neighbor edges may be incomplete compared with ObserveOps UC packs."
            )
        return {
            "critical_path": path_s or " → ".join(chain) or root or "—",
            "note": note_in or prose,
            "plain": prose,
        }

    if len(chain) >= 2:
        start, end = chain[0], chain[-1]
        mid = " → ".join(chain[1:-1])
        prose = (
            f"Think of this pack’s topology as a short causal corridor, not a whole data center. "
            f"The failure begins at {start}"
            f"{f' ({title})' if title and title != start else ''}, "
            f"then travels downstream"
            f"{f' through {mid}' if mid else ''} "
            f"until customers feel it on {end}"
            f"{f' as {seed_sig}' if seed_ci and end == seed_ci else ''}."
            f" Full chain: {' → '.join(chain)}. "
            f"Other CIs on this small map are deliberately off that corridor — "
            f"they stay healthy while this path degrades, which is why Localize must walk "
            f"upstream from the loud symptom instead of trusting the app alone."
        )
    elif root:
        prose = (
            f"On this pack’s map the labeled root is {root}"
            f"{f' — {title}' if title and title != root else ''}. "
            f"{f'Customers first noticed pain on {seed_ci} ({seed_sig}), which is usually downstream of the true fault. ' if seed_ci else ''}"
            f"The topology slice is small and purpose-built for traversal; it is not a live inventory sync."
        )
    else:
        prose = (
            "This view does not include a dependency chain from the verdict. "
            "Open the pack’s topology.json if you need the full CI neighborhood."
        )

    return {
        "critical_path": path_s or " → ".join(chain) or root or "—",
        "note": note_in or prose,
        "plain": prose,
    }


def human_logs(raw_lines: list[str], *, corpus: str = "observeops") -> list[str]:
    out: list[str] = []
    for line in raw_lines or []:
        s = plain(line)
        if not s:
            continue
        low = s.lower()
        if ("linkdown" in low and "ifdescr" in low) or low.startswith("snmp trap linkdown"):
            out.append(
                "Network gear raised an SNMP link-down trap on the core-switch uplink — "
                "the interface that should have been carrying traffic went operationally down."
            )
        elif "ifoutdiscards" in low:
            out.append(
                "Soon after, the same uplink showed climbing outbound discards: packets were "
                "being thrown away on the wire path, not just “slow somewhere in the app.”"
            )
        elif "vmnic" in low or "packet drop" in low:
            out.append(
                "The ESXi host mirrored that network pain — dropped packets / link trouble on "
                "its uplink — which is the bridge between the switch fault and the VMs above it."
            )
        elif "tcp timeout" in low or "elevated error rate behind" in low:
            out.append(
                "Only later did orders-api start timing out. That is the customer-visible end of "
                "the chain, not where the cable actually failed."
            )
        elif "network change window" in low or "uplink maintenance" in low:
            out.append(
                "Change context mattered: an uplink maintenance window was recorded on the core "
                "switch, which helps explain why a link fault appeared in that interval."
            )
        elif "no space left" in low or ("filesystem" in low and "full" in low):
            out.append(
                "The guest OS disk filled up — log writes started failing with “no space left,” "
                "which is a hard local resource failure on the VM, not an upstream network blip."
            )
        elif "out of memory" in low or ("oom" in low and "killed" in low):
            out.append(
                "The kernel’s OOM-killer then stopped the orders-api process. Once memory and disk "
                "are exhausted, the app cannot stay healthy even if the host and network look fine."
            )
        elif "cpu.ready" in low or "cpu ready" in low:
            out.append(
                "Virtual machines spent unusual time waiting for CPU (elevated ready time) — a "
                "classic sign the ESXi host was oversubscribed and starving guests."
            )
        elif "cpu.usage" in low:
            out.append(
                "The ESXi host itself was running very hot on CPU usage, which lines up with "
                "scheduler contention rather than a single noisy guest inventing the whole outage."
            )
        elif ("p95 latency" in low or "latency" in low) and "slo" in low:
            out.append(
                "Application latency crossed the SLO — that is what customers felt, and it is "
                "usually the symptom seed, not the CI you should reboot first."
            )
        elif "drs" in low or "vcpu-heavy" in low:
            out.append(
                "A capacity / DRS-style change packed additional busy VMs onto the same host, "
                "raising the odds of CPU contention before anyone touched the application tier."
            )
        elif "load average" in low or "loadavg" in low:
            out.append(
                "Guest OS load average spiked, showing a run-queue backlog inside the VM after "
                "the host could no longer schedule vCPU promptly."
            )
        elif "datastore" in low or "iowait" in low or "storage" in low:
            out.append(
                "Storage-path signals showed elevated latency / I/O wait — the kind of noisy-neighbor "
                "or datastore contention that slows databases and then the apps that depend on them."
            )
        elif "heap" in low or "conn_pool" in low or "pool-size" in low or "deploy" in low:
            out.append(
                "Application-tier evidence pointed at resource exhaustion inside the service itself "
                "(heap / connection pool / deploy config) while upstream infrastructure stayed healthy."
            )
        elif corpus == "motadata":
            out.append(
                s if len(s) >= 60 else f"Motadata event evidence: {s}."
            )
        else:
            out.append(s if len(s) >= 50 else f"Pack event: {s}.")
        if len(out) >= 6:
            break

    seen: set[str] = set()
    uniq: list[str] = []
    for x in out:
        if x in seen:
            continue
        seen.add(x)
        uniq.append(x)
    return uniq


def human_metric_line(ci: str, sig: str, val: Any = None, thr: Any = None) -> str:
    sp = signal_plain(sig)
    vs = _fmt_val(val, sig)
    ts = _fmt_val(thr, sig)
    if val is not None and thr is not None:
        return (
            f"On {ci}, {sp} reached {vs}, crossing the alert threshold of {ts}. "
            f"That reading is evidence on this CI — weigh it with onset time and topology, "
            f"not as a standalone “loudest metric wins” vote."
        )
    if val is not None:
        return (
            f"On {ci}, {sp} measured {vs}. Use this together with neighboring onsets on the pack map."
        )
    return f"On {ci}, {sp} crossed into an anomalous state during the incident window."


def human_metrics_from_anomalies(anoms: list[dict], *, limit: int = 6) -> list[str]:
    out = []
    for a in anoms[:limit]:
        out.append(
            human_metric_line(
                a.get("ci") or "?",
                a.get("signal") or "?",
                a.get("value"),
                a.get("threshold"),
            )
        )
    return out


def human_metrics_from_strings(lines: list[str]) -> list[str]:
    """Best-effort rewrite of 'ci: signal reached X (alert above Y)' strings."""
    import re

    out: list[str] = []
    pat = re.compile(
        r"^(?P<ci>.+?):\s*(?P<sig>\S+)\s+reached\s+(?P<val>[^\s(]+)(?:\s*\(alert above\s+(?P<thr>[^)]+)\))?$",
        re.I,
    )
    for line in lines or []:
        m = pat.match(plain(line))
        if m:
            out.append(
                human_metric_line(
                    m.group("ci"),
                    m.group("sig"),
                    m.group("val"),
                    m.group("thr"),
                )
            )
        elif plain(line):
            s = plain(line)
            out.append(s if len(s) >= 55 else f"Metric evidence: {s}.")
    return out[:6]


def human_customer_impact(
    *,
    raw: str | None,
    seed: dict | None,
    gt: dict | None,
    title: str,
    corpus: str,
) -> str:
    seed = seed or {}
    gt = gt or {}
    seed_ci = seed.get("ci") or ""
    seed_sig = signal_plain(seed.get("signal") or gt.get("signature"))
    raw_p = plain(raw)
    if raw_p.lower().startswith("symptom "):
        raw_p = ""

    if corpus == "motadata":
        return (
            f"Operators watching Motadata saw degradation on {seed_ci or 'the monitored CI'} "
            f"({seed_sig}). That is the customer-facing or monitor-facing pain — the investigation "
            f"seed — while human ground truth for this pack still labels "
            f"{gt.get('root_ci') or 'the root CI'} as the CI to score against"
            f"{f' ({title})' if title else ''}."
        )

    if seed_ci:
        base = (
            f"Customers experienced trouble on {seed_ci} — specifically {seed_sig}. "
            f"That symptom opens the case, but on classic-infra packs it is usually downstream "
            f"of the true fault"
            f"{f' ({title})' if title else ''}."
        )
    else:
        base = (
            f"Users felt service degradation consistent with {title or 'this pack’s fault class'}."
        )
    if raw_p and "checkout" in raw_p.lower():
        # keep useful ecom numbers if present
        return f"{base} Pack notes: {raw_p}"
    if raw_p and len(raw_p) > 40 and "symptom" not in raw_p.lower()[:20]:
        return f"{base} Additional context: {raw_p}"
    return base


def human_one_liner(
    *,
    title: str,
    root: str,
    change: str | None,
    note: str | None,
    corpus: str,
) -> str:
    ch = plain(change)
    nt = plain(note)
    if ch and not ch.lower().startswith("symptom"):
        return (
            f"{title or 'This incident'} centers on {root or 'the labeled root CI'}. "
            f"A useful change / context clue in the pack: {ch}."
        )
    if nt and len(nt) > 40:
        return nt if len(nt) > 80 else (
            f"{title or 'Labeled fault'} at {root}. {nt}"
        )
    if corpus == "motadata":
        return (
            f"{title or 'Motadata L1 pack'}: human-confirmed root {root}. "
            f"This slice came from a real Motadata export; Lean and Federated are scored "
            f"against that label, not against a synthetic lab story."
        )
    return (
        f"Pack story: {title or 'classic-infra fault'} with root CI {root}. "
        f"Shared Detect starts at the customer symptom; Localize walks upstream on the "
        f"pack topology until the earliest consistent fault CI wins."
    )


def human_actions(
    raw: list | None,
    *,
    title: str,
    root: str,
    corpus: str,
) -> tuple[list[str], list[str]]:
    now = [plain(x) for x in (raw or []) if plain(x)]
    # Expand terse bullets
    expanded: list[str] = []
    for a in now[:4]:
        if len(a) < 50:
            expanded.append(
                f"{a} Focus mitigation on {root or 'the labeled root CI'}"
                f"{f' ({title})' if title else ''} before chasing downstream symptoms."
            )
        else:
            expanded.append(a)
    if not expanded:
        if corpus == "motadata":
            expanded = [
                f"Open the Motadata views for {root or 'the labeled CI'} and confirm the "
                f"same signals that crossed threshold in this pack, then mitigate that CI first "
                f"rather than restarting every noisy neighbor.",
                f"After recovery, keep this pack’s human ground truth ({title or root}) "
                f"authoritative for Samples scoring — do not auto-generate new labels.",
            ]
        else:
            expanded = [
                f"Mitigate {root or 'the root CI'} first"
                f"{f' — {title}' if title else ''} — then re-check the customer symptom CI "
                f"to confirm the blast path is clearing from upstream to downstream.",
            ]
    later = (
        [
            "After the immediate fix, review whether change windows, capacity moves, or "
            "config deploys lined up with onset — that is how Identify depth improves next time.",
            "Keep Lean/Federated compared on the same Detect seed so bakeoff scoring stays fair.",
        ]
        if corpus != "motadata"
        else [
            "Expand Motadata coverage only after Samples confirm on existing L1 packs.",
            "Prefer another real-export slice over synthetic generators for the next Motadata case.",
        ]
    )
    return expanded[:4], later[:3]


def human_executive(
    *,
    title: str,
    root: str,
    impact: str,
    fix: str,
    corpus: str,
) -> dict:
    if corpus == "motadata":
        cause = (
            f"Human-confirmed Motadata L1 labels this pack as {title or 'the fault'} "
            f"with root CI {root}. Lean/Federated are scored against that label after "
            f"shared Detect on the Motadata symptom seed."
        )
    else:
        cause = (
            f"Likely cause on this pack: {title or 'classic-infra fault'} at {root}. "
            f"That is the CI Localize named after walking upstream from the customer "
            f"symptom on the pack topology."
        )
    impact_out = impact if len(impact) >= 80 else (
        f"{impact} Treat the symptom CI as the customer pain surface while repairing "
        f"the root CI first, then confirm the blast path clears downstream."
    )
    fix_out = fix if len(fix) >= 70 else (
        f"{fix} After mitigation, re-check the original symptom metric so you know "
        f"the corridor from root to customer actually recovered."
    )
    return {"cause": cause, "impact": impact_out, "fix": fix_out}


_SIGNAL_SHORT = {
    "cpu.ready": "CPU ready",
    "cpu.usage": "CPU usage",
    "request.p95_latency_ms": "p95 latency",
    "tcp.timeouts": "TCP timeouts",
    "error_rate_5xx": "5xx errors",
    "linkDown": "link-down",
    "ifOutDiscards": "outbound discards",
    "vmnic.dropped_packets": "NIC drops",
    "filesystem.used_pct": "disk used %",
    "oom_killer_event": "OOM kill",
    "jvm.heap.used_pct": "JVM heap %",
    "db.conn_pool.active_ratio": "DB pool active",
    "davg_latency_ms": "datastore latency",
    "gavg_latency_ms": "guest disk latency",
    "disk.iowait_pct": "disk I/O wait",
    "ping.latency.ms": "ping latency",
    "ping.max.latency.ms": "max ping latency",
    "ping.packet.lost.percent": "ping loss %",
}


def onset_lines(evidence: list | None, *, limit: int = 5) -> list[str]:
    """Compact onset bullets: '10:00:05 · esxi-host-01 — CPU ready 12, CPU usage 92%'."""
    # group signal snippets by (ts, ci)
    groups: dict[tuple[str, str], list[str]] = {}
    order: list[tuple[str, str]] = []
    seen_sig: set[str] = set()
    for ev in sorted(evidence or [], key=lambda e: (e.get("timestamp") or "", e.get("ci") or "")):
        ci = ev.get("ci") or "?"
        sig = ev.get("signal") or "?"
        key = f"{ci}|{sig}"
        if key in seen_sig:
            continue
        seen_sig.add(key)
        # skip long SNMP message duplicates when metric already present
        if isinstance(ev.get("value"), str) and len(str(ev.get("value"))) > 60:
            continue
        ts = ev.get("timestamp") or ""
        when = fmt_ts(ts)
        # short clock for display
        clock = when[11:19] if len(when) >= 19 else when
        gkey = (clock or when, ci)
        snippet = _SIGNAL_SHORT.get(sig) or signal_plain(sig)
        if ev.get("value") is not None and not isinstance(ev.get("value"), str):
            snippet = f"{snippet} {_fmt_val(ev.get('value'), sig)}"
        if gkey not in groups:
            groups[gkey] = []
            order.append(gkey)
        groups[gkey].append(snippet)
        if len(order) >= limit:
            break
    lines = []
    for clock, ci in order:
        signals = ", ".join(groups[(clock, ci)])
        lines.append(f"{clock}  ·  {ci} — {signals}")
    return lines


def onset_prose(evidence: list | None, *, limit: int = 5) -> str:
    lines = onset_lines(evidence, limit=limit)
    if not lines:
        return ""
    return "\n".join(f"• {ln}" for ln in lines)


def deduction_steps(
    engine: str,
    verd: dict,
    *,
    seed: dict | None = None,
    gt: dict | None = None,
    corpus: str = "observeops",
) -> list[str]:
    seed = seed or {}
    gt = gt or {}
    root = verd.get("root_ci") or gt.get("root_ci") or ""
    sig = verd.get("signature") or gt.get("signature") or ""
    title = gt.get("fault_title") or sig or root
    seed_ci = seed.get("ci") or ""
    seed_sig = signal_plain(seed.get("signal"))
    chain = verd.get("causal_chain") or []
    evidence = verd.get("evidence") or []
    onset = onset_prose(evidence)
    steps: list[str] = []

    if seed_ci:
        steps.append(
            f"Detect (shared for both engines): thresholds lit up on {seed_ci} as "
            f"{seed_sig}. That alert is the investigation seed — where pain showed up — "
            f"and it is usually not the root CI. Lean and Federated both start from this "
            f"same Detect output so the bakeoff compares Localize, not detector luck."
        )
    else:
        steps.append(
            "Detect (shared): a threshold crossing produced the symptom seed that both "
            "engines consume. The fair scoreboard does not give Federated a separate "
            "Panorama detector on these packs."
        )

    if engine == "lean":
        steps.append(
            "Localize · Traverse: Lean walks the typed CI / service map upstream from that "
            "symptom. The walk is best-first (follow promising edges), not a blind breadth-first "
            "flood of every node on the pack topology."
        )
        obs = verd.get("observations")
        bfs = verd.get("naive_bfs_expansions")
        if obs is not None and bfs is not None:
            steps.append(
                f"Localize · Prioritize: on this run Lean spent {obs} high-value observations "
                f"to converge. A naive BFS-style expansion on the same pack would touch about "
                f"{bfs} nodes — the gap is information-gain prioritization (ask the check that "
                f"best separates “loud symptom” from “true root”)."
            )
        else:
            steps.append(
                "Localize · Prioritize: Lean prefers checks with high information gain — "
                "signals that cleanly separate upstream faults from downstream symptoms — "
                "instead of expanding every neighbor equally."
            )
        if onset:
            steps.append(
                "Localize · Order (temporal onset & Δt)\n"
                "Earlier upstream onsets outrank later customer symptoms when the topology "
                "connects those CIs.\n"
                f"{onset}"
            )
        else:
            steps.append(
                "Localize · Order: Lean compares onset times so an earlier upstream fault "
                "beats a later downstream symptom when both look “bad” in the metrics panel."
            )
        if verd.get("fallback_fired"):
            steps.append(
                "Escalate (CARE): several candidate CIs lit up close together in time, so Lean "
                "did not trust “earliest CI” alone. CARE ranked shared-upstream suspects and "
                "kept the audit trail explicit (this is Lean’s ambiguity path, not a Federated hop)."
            )
            clog = verd.get("causal_log") or []
            if verd.get("causal_verified") and clog:
                checks = ", ".join(
                    c.get("check") for c in clog if c.get("check") and c.get("passed")
                )
                steps.append(
                    f"Verify (Tier 3): scoped causal checks then passed ({checks}). "
                    f"Only at this tier does Lean allow stronger cause-and-effect language — "
                    f"still on a tiny candidate set, not a fleet-wide counterfactual."
                )
            elif verd.get("evidentiary_tier") == 2:
                steps.append(
                    "Verify (Tier 2): CARE produced a correlational ranking. That is stronger "
                    "than a raw symptom guess, but Lean still does not claim full Causal Validity "
                    "until a scoped Tier-3 check passes."
                )
        else:
            tier = verd.get("evidentiary_tier") or 1
            steps.append(
                f"Verify (Tier {tier}): temporal order and topology rules produced a clear "
                f"winner, so CARE did not need to fire. The evidentiary claim stays on the "
                f"main path — auditable, without a heavy causal side quest."
            )
        if root:
            steps.append(
                f"Conclusion: Lean named {root} as the root CI"
                f"{f' with signature “{sig}”' if sig else ''}"
                f"{f' — {title}' if title and title != root else ''}. "
                f"That is the CI an SRE should mitigate first."
            )
        if chain and len(chain) > 1:
            steps.append(
                f"Blast path after the root: {' → '.join(chain)}. Read this as "
                f"“how pain reached the customer,” not as a second competing root."
            )

    elif engine == "federated":
        steps.append(
            "Localize · Murphy: Federated does not replay Lean’s best-first walk. It ranks "
            "candidate CIs with a Murphy / Gibbs-style posterior over the dependency graph and "
            "metrics, then fuses that ranking into a root pick."
        )
        post = verd.get("murphy_posterior")
        if post is not None and root:
            try:
                steps.append(
                    f"On this run the strongest posterior mass sat on {root} "
                    f"(≈ {float(post):.0%}). Treat that as soft ranking confidence, not a "
                    f"Lean evidentiary tier label."
                )
            except (TypeError, ValueError):
                steps.append(
                    f"Murphy favored {root} (posterior={post}) among the candidates it scored."
                )
        if onset:
            steps.append(
                "Onset evidence fed into Murphy ranking (same Detect seed as Lean):\n"
                f"{onset}"
            )
        if verd.get("fallback_fired"):
            reason = verd.get("fallback_reason") or "helper path"
            try:
                strong = post is not None and float(post) >= 0.7
            except (TypeError, ValueError):
                strong = False
            if strong and root:
                steps.append(
                    f"Fusion also recorded a helper path ({reason}). On this pack it agreed "
                    f"with Murphy’s pick ({root}) — useful audit detail, not a disagreement."
                )
            else:
                steps.append(
                    f"Fusion fallback: Murphy ranking alone was weak, so helper rules applied "
                    f"({reason}). That is Federated’s rescue path for this run."
                )
        else:
            steps.append(
                "Fusion: the Murphy path held without falling back to lean-rule rescue on "
                "this run — Federated’s “main path” in bakeoff terms."
            )
        if root:
            steps.append(
                f"Conclusion: Federated fused to {root}"
                f"{f' with signature “{sig}”' if sig else ''}. "
                f"Compare this root to Lean’s on the same Detect seed for the fair scoreboard."
            )
        if chain and len(chain) > 1:
            steps.append(
                f"Associated chain: {' → '.join(chain)}."
            )

    else:
        steps.append(
            "OpenObserve’s Analysis narrative is a third-party baseline. It is not Lean’s "
            "topology walk and not Federated’s Murphy ranking — score it honestly against pack GT."
        )

    if corpus == "motadata":
        steps.append(
            f"Motadata scoring note: human ground truth on this pack labels "
            f"{gt.get('root_ci') or root} "
            f"({gt.get('fault_title') or gt.get('signature') or 'see Samples'}). "
            f"Automation only scores; it does not invent that label."
        )
    return steps
