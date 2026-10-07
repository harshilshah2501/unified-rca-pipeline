# Motadata candidate windows (A1 — no GT yet)

Automation **proposed** these from threshold crossings. A human must pick a story and write `ground_truth.json`.

- Source: `/root/Harshil-PoCs/Unified-RCA/datasets/ingest_samples/jsonl_resolved/metric_numeric.jsonl`
- Lines scanned: all
- CI cards with ≥1 crossing: 392
- Already packed: `dlink-48`→motadata-ping-001, `Fluentbit`→motadata-cpu-001

## PoC curated picks (start here)

Aim: **1 clear network variant** + **1 harder multi-signal** (leave the 3-smoke comfort zone). Skip chronic-only hosts for GT.

| Priority | CI | Why | Caution |
|----------|----|-----|---------|
| 1 | `Netgear Switch` | Clear infra network variant (packet loss) — same class as ping-001, different CI. Good regression breadth. |  |
| 2 | `proxmox-ve-129` | Clear ping/packet-loss host — second network smoke if Netgear topology is thin. |  |
| 3 | `localhost.localdomain` | Highest pure-network crossing count — may be noisy/lab; verify before GT. | Short 2h window at 100% loss — verify story before GT |
| 4 | `linux-host-2` | Only pure high-CPU CI besides Fluentbit — check if chronic (bad GT) vs episodic. | Likely **chronic** CPU (~24h hot) — weak as a discrete incident |
| 5 | `HB1-2328-26-4992-4512-4320-4869-76-735.hb1.com` | Harder multi-signal (CPU + network) — leaves comfort zone; GT may need contributors. | Multi-cause possible — GT may need `contributor_cis` |

### Suggested first cut (eng after you confirm GT draft)

1. **`Netgear Switch`** → `motadata-ping-002` — signature draft `ping_degradation` (packet loss; root=`Netgear Switch` if you agree).
2. **`HB1-…-735.hb1.com`** → `motadata-multi-001` — harder pack; draft root + contributors after you inspect peaks (CPU/mem/ping).

**Hold:** `linux-host-2` until you confirm it is not chronically pegged junk.

## Diversity shortlist

| # | CI | Class | Role hint | Crossings | Primary metric | Monitors | Window |
|---|----|-------|-----------|-----------|----------------|----------|--------|
| 1 | `localhost.localdomain` | network | infra_network_variant | 116 | `ping.packet.lost.percent` | 24 | 2026-07-21T04:02:38 → 2026-07-21T05:57:38 |
| 2 | `proxmox-ve-129` | network | infra_network_variant | 46 | `ping.packet.lost.percent` | 129 | 2026-07-20T07:36:46 → 2026-07-21T05:15:38 |
| 3 | `HB1-2328-26-4992-4512-4320-4869-76-566.hb1.com` | network | infra_network_variant | 45 | `ping.packet.lost.percent` | 378 | 2026-07-20T08:08:56 → 2026-07-21T05:16:38 |
| 4 | `linux-host-2` | resource | infra_resource_variant | 8662 | `system.cpu.percent` | 2 | 2026-07-20T06:54:28 → 2026-07-21T05:57:43 |
| 5 | `HB1-2328-26-4992-4512-4320-4869-76-735.hb1.com` | resource | harder_multi_signal | 837 | `system.1min.avg.cpu.percent` | 391 | 2026-07-20T07:29:56 → 2026-07-21T05:55:38 |
| 6 | `HB1-2328-26-4992-4512-4320-4869-76-750.hb1.com` | resource | harder_multi_signal | 828 | `system.1min.avg.cpu.percent` | 286 | 2026-07-20T07:29:56 → 2026-07-21T05:55:38 |
| 7 | `HB1-2328-26-4992-4512-4320-4869-76-541.hb1.com` | resource | harder_multi_signal | 822 | `system.1min.avg.cpu.percent` | 182 | 2026-07-20T07:29:46 → 2026-07-21T05:55:38 |
| 8 | `HB1-2328-26-4992-4512-4320-4869-76-668.hb1.com` | resource | harder_multi_signal | 820 | `system.1min.avg.cpu.percent` | 303 | 2026-07-20T07:29:56 → 2026-07-21T05:55:38 |
| 9 | `HB1-2328-26-4992-4512-4320-4869-76-606.hb1.com` | resource | harder_multi_signal | 819 | `system.1min.avg.cpu.percent` | 259 | 2026-07-20T07:29:46 → 2026-07-21T05:55:38 |
| 10 | `HB1-2328-26-4992-4512-4320-4869-76-701.hb1.com` | resource | harder_multi_signal | 812 | `system.1min.avg.cpu.percent` | 407 | 2026-07-20T07:29:56 → 2026-07-21T05:55:38 |

### Your next actions

1. Confirm **1–2** curated picks (or swap from diversity table).
2. For each: draft `root_ci` + `signature` (+ optional `contributor_cis`).
3. Eng cuts packs → Motadata bakeoff → you verify on `#samples`.

## Top fresh CI cards (by crossings)

| CI | Crossings | Classes | Primary metric | Role |
|----|-----------|---------|----------------|------|
| `linux-host-2` | 8662 | resource | `system.cpu.percent` | infra_resource_variant |
| `HB1-2328-26-4992-4512-4320-4869-76-735.hb1.com` | 837 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-750.hb1.com` | 828 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-541.hb1.com` | 822 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-668.hb1.com` | 820 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-606.hb1.com` | 819 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-701.hb1.com` | 812 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-719.hb1.com` | 573 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-686.hb1.com` | 572 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-623.hb1.com` | 570 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-700.hb1.com` | 569 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-687.hb1.com` | 568 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-688.hb1.com` | 568 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-573.hb1.com` | 568 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-624.hb1.com` | 567 | network,resource | `system.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-608.hb1.com` | 567 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-575.hb1.com` | 564 | network,resource | `system.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-685.hb1.com` | 560 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-544.hb1.com` | 559 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-736.hb1.com` | 557 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-752.hb1.com` | 555 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-716.hb1.com` | 555 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-767.hb1.com` | 554 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-765.hb1.com` | 554 | network,resource | `system.cpu.percent` | harder_multi_signal |
| `HB1-2328-26-4992-4512-4320-4869-76-620.hb1.com` | 553 | network,resource | `system.1min.avg.cpu.percent` | harder_multi_signal |
