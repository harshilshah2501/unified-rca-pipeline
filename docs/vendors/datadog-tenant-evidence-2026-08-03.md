# Datadog tenant evidence — 2026-08-03

**Org:** Self (`d6223052-8f1c-11f1-94b2-66515ec82cb8`)  
**Site:** `datadoghq.com`  
**User:** Harshil Shah (`harshilshah25@gmail.com`) via OAuth  
**Method:** Datadog MCP (`plugin-datadog-datadog`) after loading skills `datadog/metrics`, `datadog/traces`, `datadog/logs`, `datadog/incidents-and-alerting`, `datadog/services-and-infrastructure`

This appendix grounds **Observed** claims in [`DATADOG_PRODUCTION_PIPELINE.md`](./DATADOG_PRODUCTION_PIPELINE.md). It is a snapshot, not a product specification.

---

## 1. Hosts (`search_datadog_hosts`)

| hostname | os | agent_version | env |
|----------|-----|---------------|-----|
| `DESKTOP-MBPAQK1` | GNU/Linux | 7.81.3 | `dev` |

**Count:** 1 host.

---

## 2. Services (`search_datadog_services`)

Sample catalog names (not a deliberate microservices estate):

`bash`, `dashboard`, `installer`, `motadata-context-layer`, `node`, `npm`, `oneagentebpfdiscovery`, `oneagenteventstracer`, `oneagentextensions`, `oneagenthelper`, `oneagentloganalytics`, `oneagentos`, `oneagentwatchdog`, `peer.hostname:api2.cursor.sh`, `peer.hostname:docs.mcp.cloudflare.com`, `peer.hostname:mcp.datadoghq.com`, `rsyslogd`

**Reading:** Process / auto-instrumentation / peer-hostname discovery — **not** `frontend → product → inventory`.

---

## 3. Service dependencies (`search_datadog_service_dependencies`)

For `service:node` (downstream / peers observed):

| name | display_name |
|------|----------------|
| `peer.hostname:api2.cursor.sh` | api2.cursor.sh |
| `peer.hostname:mcp.datadoghq.com` | mcp.datadoghq.com |
| `peer.hostname:docs.mcp.cloudflare.com` | docs.mcp.cloudflare.com |

**Reading:** APM-derived outbound peers from auto-instrumented `node` (Cursor / MCP traffic), not typed CI graph.

---

## 4. Metrics (`get_datadog_metric`, scalar, last ~2h)

| Query | Aggregated value (avg) |
|-------|-------------------------|
| `avg:system.mem.pct_usable{host:DESKTOP-MBPAQK1}` | ~0.45 (45% usable) |
| `avg:system.load.norm.1{host:DESKTOP-MBPAQK1}` | ~0.27 |
| `avg:system.cpu.user{host:DESKTOP-MBPAQK1}` | ~5.0 |

Host metrics intake is live.

---

## 5. APM spans (`search_datadog_spans`, `*`, last ~6h)

- **Count:** ~899 spans in window (truncated sample returned)
- Dominant `service:` **`node`**, `env:dev`, `host:DESKTOP-MBPAQK1`
- Example operations: `command_execution` (`resource: sh`), `http.request` / `undici.request` to `docs.mcp.cloudflare.com`, `dns.lookup`
- Tags include `svc.auto:node`, `entrypoint.workdir:cursor`, `source:apm`

**Reading:** Auto APM from local Node/Cursor processes — not an app lab.

---

## 6. Logs (`search_datadog_logs`, `*`, last ~6h)

- **Count:** ~106k log lines in window
- Services seen: `rsyslogd`, `oneagentloganalytics`, …
- Example: systemd / `h100-backup.service` failures; Dynatrace OneAgent log-analytics debug on same host; WSL pro-service warnings

**Reading:** Host syslog + co-resident OneAgent log shipper noise — logs product is active.

---

## 7. Monitors (`search_datadog_monitors`)

| id | name (short) | type | status | Detect door |
|----|--------------|------|--------|-------------|
| 310485027 | Watchdog Anomaly for `{{service}}` | `event-v2 alert` | **Alert** | Watchdog → events |
| 310484616 | Memory space is low | `query alert` | OK | Metric threshold |
| 310484608 | Disk latency is high | `query alert` | OK | Metric threshold |
| 310484609 | Disk usage is high (forecast) | `query alert` | OK | Metric forecast |
| 310484611 | System load is high | `query alert` | OK | Metric threshold |
| 310484607 | CPU usage is high | `query alert` | OK | Metric threshold |
| 310484614 | Network traffic (received) high | `query alert` | OK | Metric threshold |
| 310484615 | Network traffic (sent) high | `query alert` | OK | Metric threshold |
| 310485843 | High Error Rate on `web.request` | `query alert` | OK | APM trace metrics |

Watchdog monitor query (verbatim):

```text
events("source:watchdog (story_category:apm)").rollup("count").by("story_key").last("30m") > 0
```

Created by **Datadog Support** during Agent onboarding (~2026-08-03T09:50Z).

---

## 8. Watchdog events (`search_datadog_events`, `source:watchdog`)

Example titles (repeated ~09:51–10:05Z):

> Error rate increased on the `/bin/bash` resource in **node**

Tags include: `source:watchdog`, `story_category:apm`, `story_type:error_rate`, `service:node`, `env:dev`, `story_key:0ca0cc19-cb24-583d-9573-3352bbf01be0`, `resource_name:/bin/bash`

UI path referenced in event text: `/watchdog/story/0ca0cc19-cb24-583d-9573-3352bbf01be0`

---

## 9. Incidents (`search_datadog_incidents`)

**0** matching incidents (`state:(active OR stable OR resolved)`).

No packaged Incident card observed in this tenant at snapshot time.

---

## 10. Absences (honest)

| Expected in a rich APM lab | This tenant |
|----------------------------|-------------|
| Deliberate `frontend` / `inventory` services | Absent |
| Typed microservice call graph | Absent (peer hostnames only) |
| Operator-opened Incident | Absent |
| Hand-authored custom monitors beyond Support defaults | Not required for evidence; defaults + Watchdog suffice |

---

## 11. How to cite

In the pipeline doc:

- **Observed (MCP)** → cite § of this appendix
- **Observed (agent)** → local Agent install / `datadog-agent status` on WSL
- **Public framing** → Datadog product docs / marketing
- **Inferred** → reasonable model, not vendor-internal
- **Teaching** → pedagogical estate, **not** this tenant
