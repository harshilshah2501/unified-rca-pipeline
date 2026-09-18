import {
  Button,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Divider,
  Grid,
  H1,
  H2,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useCanvasState,
  useEffect,
  useHostTheme,
} from "cursor/canvas";

type TabId =
  | "animate"
  | "overview"
  | "map"
  | "history"
  | "ops"
  | "physical"
  | "join";

const TABS: { id: TabId; label: string }[] = [
  { id: "animate", label: "0 · Animate" },
  { id: "overview", label: "1 · Overview" },
  { id: "map", label: "2 · map/" },
  { id: "history", label: "3 · history/" },
  { id: "ops", label: "4 · Who R/W" },
  { id: "physical", label: "5 · Vortex / S3" },
  { id: "join", label: "6 · Join (no sync)" },
];

const PHASES = [
  {
    title: "1 · Admit + bind",
    body: "E1 Collect admits raw signals. E2 Identity stamps tenant + ci_id with identity.status = resolved. Bind/LUT-like work lives here — not as a third store room.",
  },
  {
    title: "2 · Fan-out (parallel writers)",
    body: "The resolved stream branches. Pillar B (E3) builds topology. Pillar A (E4) builds metric sketches. They do not wait on each other.",
  },
  {
    title: "3 · Write map/",
    body: "E3 writes graph_node.v1 / graph_edge.v1 as a GraphSnapshot into map/ (Smartscape-like). Provenance + validity live on edges.",
  },
  {
    title: "4 · Write history/",
    body: "E4 writes sketch.v1 (T-Digest + buckets + baseline) into history/. entity_id is the same string as map ci_id. No edges inside sketches.",
  },
  {
    title: "5 · No sync between rooms",
    body: "There is no job that copies map ↔ history. E5 may refresh baselines (A) and validity (B) as separate writers — still not merging rooms.",
  },
  {
    title: "6 · Join at read (WorkingSet)",
    body: "Detect reads history (digest vs baseline). Scope/Localize/Identify build a WorkingSet: neighbors from map + sketches from history for the same ids.",
  },
];

export default function MapHistoryStorageBlocks() {
  const [tab, setTab] = useCanvasState<TabId>("tab", "animate");
  const idx = TABS.findIndex((t) => t.id === tab);

  return (
    <Stack gap={16} style={{ padding: 16, maxWidth: 960 }}>
      <Stack gap={6}>
        <H1>map/ and history/ — storage remapped</H1>
        <Text tone="secondary" size="small">
          Motadata Pillar B → map/ · Pillar A → history/. Same identity after E2.
          No continuous sync. HTML twins: docs/map-history-storage-animation.html ·
          docs/map-history-storage-blocks.html
        </Text>
      </Stack>

      <Row gap={8} style={{ flexWrap: "wrap" }}>
        {TABS.map((t) => (
          <span key={t.id}>
            <Pill
              active={t.id === tab}
              tone={t.id === tab ? "info" : "neutral"}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </Pill>
          </span>
        ))}
      </Row>

      <Row gap={8} style={{ justifyContent: "space-between" }}>
        <Text size="small" weight="semibold">
          {TABS[idx]?.label}
        </Text>
        <Row gap={8}>
          <Button
            variant="secondary"
            disabled={idx === 0}
            onClick={() => setTab(TABS[idx - 1].id)}
          >
            Previous
          </Button>
          <Button
            variant="primary"
            disabled={idx === TABS.length - 1}
            onClick={() => setTab(TABS[idx + 1].id)}
          >
            Next
          </Button>
        </Row>
      </Row>

      <Divider />

      {tab === "animate" && <AnimateFlow />}
      {tab === "overview" && <Overview />}
      {tab === "map" && <MapRoom />}
      {tab === "history" && <HistoryRoom />}
      {tab === "ops" && <Ops />}
      {tab === "physical" && <PhysicalDest />}
      {tab === "join" && <Join />}
    </Stack>
  );
}

function AnimateFlow() {
  const theme = useHostTheme();
  const [phase, setPhase] = useCanvasState<number>("animPhase", 0);
  const [playing, setPlaying] = useCanvasState<boolean>("animPlaying", false);
  const p = Math.max(0, Math.min(PHASES.length - 1, phase));
  const meta = PHASES[p];

  useEffect(() => {
    if (!playing) return;
    if (p >= PHASES.length - 1) {
      setPlaying(false);
      return;
    }
    const t = setTimeout(() => setPhase(p + 1), 1600);
    return () => clearTimeout(t);
  }, [playing, p, setPhase, setPlaying]);

  const a = theme.diff.insertedLine;
  const b = theme.diff.removedLine;
  const j = theme.accent.primary;
  const warn = theme.diff.removedLine;
  const stroke = theme.stroke.secondary;
  const text = theme.text.primary;
  const muted = theme.text.secondary;
  const faint = theme.text.tertiary;
  const surface = theme.bg.elevated;
  const fill = theme.fill.tertiary;

  const wire = (active: boolean, color: string) => ({
    fill: "none" as const,
    stroke: color,
    strokeWidth: active ? 2.4 : 1.4,
    opacity: active ? 1 : 0.22,
    strokeLinecap: "round" as const,
  });

  const node = (active: boolean, color: string, dashed = false) => ({
    fill: active ? fill : surface,
    stroke: color,
    strokeWidth: active ? 2 : 1.4,
    strokeDasharray: dashed ? "5 3" : undefined,
    opacity: active ? 1 : 0.55,
  });

  return (
    <Stack gap={14}>
      <Row gap={8} style={{ flexWrap: "wrap", alignItems: "center" }}>
        <Button
          variant="secondary"
          disabled={p === 0}
          onClick={() => {
            setPlaying(false);
            setPhase(p - 1);
          }}
        >
          Step back
        </Button>
        <Button
          variant="primary"
          onClick={() => {
            if (playing) {
              setPlaying(false);
              return;
            }
            if (p >= PHASES.length - 1) setPhase(0);
            setPlaying(true);
          }}
        >
          {playing ? "Pause" : "Play"}
        </Button>
        <Button
          variant="secondary"
          disabled={p === PHASES.length - 1}
          onClick={() => {
            setPlaying(false);
            setPhase(p + 1);
          }}
        >
          Step forward
        </Button>
        <Row gap={6} style={{ flexWrap: "wrap", marginLeft: "auto" }}>
          {PHASES.map((_, i) => (
            <span key={i}>
              <Pill
                size="sm"
                active={i === p}
                onClick={() => {
                  setPlaying(false);
                  setPhase(i);
                }}
              >
                {String(i + 1)}
              </Pill>
            </span>
          ))}
        </Row>
      </Row>

      <Callout tone="info" title={meta.title}>
        {meta.body}
      </Callout>

      <div
        style={{
          border: `1px solid ${stroke}`,
          borderRadius: 12,
          padding: 12,
          background: surface,
        }}
      >
        <Text size="small" tone="tertiary" style={{ marginBottom: 8 }}>
          Remap animation · write fan-out → two rooms → read join
        </Text>
        <svg
          viewBox="0 0 1000 520"
          width="100%"
          height="auto"
          role="img"
          aria-label="Animated map and history remapping"
        >
          {/* E1 */}
          <rect x={20} y={210} width={120} height={70} rx={10} {...node(p >= 0, j)} />
          <text x={36} y={232} fill={faint} fontSize={10} fontFamily="monospace">
            E1
          </text>
          <text x={36} y={252} fill={text} fontSize={13} fontWeight={600}>
            Collect
          </text>
          <text x={36} y={268} fill={muted} fontSize={10} fontFamily="monospace">
            raw signals
          </text>

          {/* E2 */}
          <rect x={200} y={210} width={140} height={70} rx={10} {...node(p >= 0, j)} />
          <text x={216} y={232} fill={faint} fontSize={10} fontFamily="monospace">
            E2
          </text>
          <text x={216} y={252} fill={text} fontSize={13} fontWeight={600}>
            Identity
          </text>
          <text x={216} y={268} fill={muted} fontSize={10} fontFamily="monospace">
            ci_id · resolved
          </text>
          {p >= 0 && (
            <text x={270} y={200} fill={j} fontSize={10} fontFamily="monospace" textAnchor="middle">
              tenant+ci_id
            </text>
          )}

          <path d="M140 245 L200 245" {...wire(p >= 0, j)} />

          {/* B branch */}
          <path d="M340 230 C390 230 390 100 430 100" {...wire(p >= 1, b)} />
          <rect
            x={430}
            y={55}
            width={150}
            height={90}
            rx={10}
            {...node(p >= 1, b)}
          />
          <text x={446} y={76} fill={faint} fontSize={9} fontFamily="monospace">
            E3 · PILLAR B
          </text>
          <text x={446} y={98} fill={text} fontSize={13} fontWeight={600}>
            Topology
          </text>
          <text x={446} y={116} fill={muted} fontSize={10} fontFamily="monospace">
            nodes · edges
          </text>
          <text x={446} y={132} fill={faint} fontSize={10} fontFamily="monospace">
            GraphSnapshot
          </text>

          <path d="M580 100 L640 100" {...wire(p >= 2, b)} />
          <rect
            x={640}
            y={65}
            width={130}
            height={70}
            rx={10}
            {...node(p >= 2, b, true)}
          />
          <text
            x={705}
            y={95}
            textAnchor="middle"
            fill={p >= 2 ? b : muted}
            fontSize={14}
            fontWeight={700}
          >
            map/
          </text>
          <text
            x={705}
            y={114}
            textAnchor="middle"
            fill={muted}
            fontSize={10}
            fontFamily="monospace"
          >
            ≈ Smartscape
          </text>
          {p >= 2 && <circle cx={620} cy={100} r={6} fill={b} />}

          {/* A branch */}
          <path d="M340 260 C390 260 390 390 430 390" {...wire(p >= 1, a)} />
          <rect
            x={430}
            y={345}
            width={150}
            height={90}
            rx={10}
            {...node(p >= 1, a)}
          />
          <text x={446} y={366} fill={faint} fontSize={9} fontFamily="monospace">
            E4 · PILLAR A
          </text>
          <text x={446} y={388} fill={text} fontSize={13} fontWeight={600}>
            Stores sketches
          </text>
          <text x={446} y={406} fill={muted} fontSize={10} fontFamily="monospace">
            digest · buckets
          </text>
          <text x={446} y={422} fill={faint} fontSize={10} fontFamily="monospace">
            baseline
          </text>

          <path d="M580 390 L640 390" {...wire(p >= 3, a)} />
          <rect
            x={640}
            y={355}
            width={130}
            height={70}
            rx={10}
            {...node(p >= 3, a, true)}
          />
          <text
            x={705}
            y={385}
            textAnchor="middle"
            fill={p >= 3 ? a : muted}
            fontSize={14}
            fontWeight={700}
          >
            history/
          </text>
          <text
            x={705}
            y={404}
            textAnchor="middle"
            fill={muted}
            fontSize={10}
            fontFamily="monospace"
          >
            ≈ Grail history
          </text>
          {p >= 3 && <circle cx={620} cy={390} r={6} fill={a} />}

          {/* Forbidden sync */}
          <path
            d="M705 135 L705 355"
            fill="none"
            stroke={warn}
            strokeWidth={1.5}
            strokeDasharray="4 4"
            opacity={p >= 4 ? 0.7 : 0.12}
          />
          {p >= 4 && (
            <>
              <line
                x1={685}
                y1={230}
                x2={725}
                y2={270}
                stroke={warn}
                strokeWidth={2.5}
              />
              <line
                x1={725}
                y1={230}
                x2={685}
                y2={270}
                stroke={warn}
                strokeWidth={2.5}
              />
              <text
                x={760}
                y={255}
                fill={warn}
                fontSize={11}
                fontFamily="monospace"
                fontWeight={600}
              >
                NO SYNC
              </text>
            </>
          )}

          {/* WorkingSet */}
          <path
            d="M770 100 C860 100 860 245 820 245"
            {...wire(p >= 5, j)}
          />
          <path
            d="M770 390 C860 390 860 245 820 245"
            {...wire(p >= 5, j)}
          />
          <rect
            x={820}
            y={210}
            width={150}
            height={70}
            rx={10}
            {...node(p >= 5, j)}
            opacity={p >= 5 ? 1 : 0.28}
          />
          <text x={836} y={232} fill={faint} fontSize={10} fontFamily="monospace">
            E8+
          </text>
          <text x={836} y={252} fill={text} fontSize={13} fontWeight={600}>
            WorkingSet
          </text>
          <text x={836} y={268} fill={muted} fontSize={10} fontFamily="monospace">
            join at read
          </text>
          {p >= 5 && (
            <>
              <circle cx={790} cy={170} r={5} fill={j} />
              <circle cx={790} cy={320} r={5} fill={j} />
            </>
          )}
        </svg>

        <Row gap={14} style={{ marginTop: 10, flexWrap: "wrap" }}>
          <Text size="small" tone="secondary">
            Pillar B → map/
          </Text>
          <Text size="small" tone="secondary">
            Pillar A → history/
          </Text>
          <Text size="small" tone="secondary">
            Read join (WorkingSet)
          </Text>
          <Text size="small" tone="secondary">
            No map↔history sync
          </Text>
        </Row>
      </div>
    </Stack>
  );
}

function Overview() {
  return (
    <Stack gap={14}>
      <Callout tone="info" title="Two rooms after one fan-out">
        E2 Identity stamps tenant + ci_id. E3 writes map/. E4 writes history/.
        Dynatrace analogy: map ≈ Smartscape, history ≈ Grail-like history (sketches).
        Bind/LUT-like work is E2 — not a third store room.
      </Callout>
      <Grid columns={3} gap={12}>
        <Stat value="map/" label="Pillar B topology" tone="info" />
        <Stat value="history/" label="Pillar A sketches" tone="success" />
        <Stat value="ci_id≡entity_id" label="Join at read" tone="warning" />
      </Grid>
      <Text size="small">
        Flow: Collect → Identity → (Topology → map/) ∥ (Stores → history/) →
        Detect reads history; Scope/Localize/Identify join both into WorkingSet.
        Use tab 0 · Animate for the stepped remapping.
      </Text>
    </Stack>
  );
}

function MapRoom() {
  return (
    <Stack gap={14}>
      <Card>
        <CardHeader trailing={<Pill tone="info">Pillar B</Pill>}>
          map/ sub-blocks
        </CardHeader>
        <CardBody>
          <Table
            headers={["Sub-block", "Contents", "Key"]}
            rows={[
              ["graph_node.v1", "CI vertices", "tenant + ci_id"],
              ["graph_edge.v1", "Typed arcs + discovered_via + validity", "tenant + edge_id"],
              ["GraphSnapshot", "Versioned nodes+edges package", "tenant + snapshot version"],
            ]}
          />
        </CardBody>
      </Card>
      <Text size="small" tone="secondary">
        Writes: E3 Topology (inventory/catalog/telemetry → relation enum). Reads:
        E8/E9/E10 query_graph / neighbor walk. Not metric digests.
      </Text>
    </Stack>
  );
}

function HistoryRoom() {
  return (
    <Stack gap={14}>
      <Card>
        <CardHeader trailing={<Pill tone="success">Pillar A</Pill>}>
          history/ sub-blocks
        </CardHeader>
        <CardBody>
          <Table
            headers={["Sub-block", "Contents", "Key"]}
            rows={[
              [
                "sketch.v1",
                "T-Digest + buckets + seasonal baseline",
                "tenant, entity_id, metric_id, window, season_key, window_start",
              ],
              ["Lab file", "sketches.jsonl", "FileDest history/ room"],
              [
                "Motadata-shaped",
                "S3 cold objects + Vortex hot index",
                "Same logical key; two temperatures",
              ],
            ]}
          />
        </CardBody>
      </Card>
      <Text size="small" tone="secondary">
        entity_id = same string as map ci_id after Identity. Sketches never carry
        src_ci_id / relation.
      </Text>
    </Stack>
  );
}

function Ops() {
  return (
    <Stack gap={14}>
      <H2>Writes</H2>
      <Table
        headers={["Who", "Room", "Op"]}
        rows={[
          ["E3 Topology", "map/", "put GraphSnapshot / nodes+edges"],
          ["E4 Sketch writer", "history/", "put sketch.v1 rows"],
          ["E5 Maintain", "both (separate)", "baselines → A; validity/decay → B"],
        ]}
      />
      <H2>Reads</H2>
      <Table
        headers={["Who", "Room", "Need"]}
        rows={[
          ["E6 Detect door C", "history/", "digest p95 vs baseline"],
          ["Dashboards", "history/ hot", "latest p95 / trend"],
          ["E8 Scope", "both", "WorkingSet: neighbors + sketches"],
          ["E9 Localize", "map/", "typed walk"],
          ["E10 Identify", "both", "query_graph + get_metric_baseline"],
          ["Pillar C (opt)", "WorkingSet", "tools only — no S3 dump"],
        ]}
        rowTone={["info", "neutral", "warning", "neutral", "neutral", "neutral"]}
      />
    </Stack>
  );
}

function PhysicalDest() {
  return (
    <Stack gap={14}>
      <Callout tone="info" title="Rooms ≠ temperature">
        map/ and history/ are content rooms (what fact). Vortex and S3 are
        temperature tiers (how hot the same row is) when the Motadata-shaped E4
        destination is chosen. Vortex is not map/; S3 is not history/. Both rooms
        can live hot in Vortex and age cold into S3.
      </Callout>

      <Grid columns={2} gap={12}>
        <Stat value="S3" label="Cold — remember / retain / rebuild" tone="warning" />
        <Stat value="Vortex" label="Hot — Detect, dashboards, WorkingSet" tone="info" />
      </Grid>

      <H2>Three encodings of the same Dest</H2>
      <Table
        headers={["Profile", "Where bytes land", "When"]}
        rows={[
          [
            "files.v1 (lab today)",
            "poc/out/<tenant>/map/… and history/sketches.jsonl",
            "PoC — FileDest.put(room, key, bytes)",
          ],
          [
            "S3 (cold)",
            "Partitioned objects; same logical keys; append/replace immutable sketch + snapshot objects",
            "Motadata-shaped retention",
          ],
          [
            "Vortex (hot)",
            "Analytical tables / index over same fields (JSON now; protobuf later)",
            "Interactive query — Motadata DDL not frozen yet",
          ],
        ]}
      />

      <H2>Write shapes</H2>
      <Table
        headers={["Writer", "Room", "Logical op", "Motadata-shaped physical"]}
        rows={[
          [
            "E3 Topology",
            "map/",
            'Dest.put("map", "nodes.jsonl" | "edges.jsonl" | "graph_snapshot.json", …)',
            "Upsert node/edge rows into Vortex graph tables; append/replace GraphSnapshot object on S3",
          ],
          [
            "E4 Sketch writer",
            "history/",
            'Dest.put("history", "sketches.jsonl", sketch.v1 row)',
            "Append sketch object on S3 (partitioned); upsert / load same key into Vortex hot index",
          ],
          [
            "E5 Maintain",
            "both, separate",
            "Refresh baseline fields (A); validity/decay on edges (B)",
            "Still two writers — no copy map↔history",
          ],
        ]}
      />

      <Text size="small" tone="secondary">
        Sketch cold path (teaching): tenant=…/metric_id=…/window=5m/date=…/
        &lt;key-hash&gt;__window_start=….json — one immutable object per closed window.
      </Text>

      <H2>Read shapes (always via hot / retrieval)</H2>
      <Table
        headers={["Caller", "API shape", "Hits"]}
        rows={[
          [
            "E6 Detect door C",
            "get_sketch(tenant, entity_id, metric_id, window, season_key, window_start) → compare digest p95 vs baseline",
            "Vortex (not S3 dump)",
          ],
          [
            "Dashboards",
            "latest p95 / prior N windows for entity+metric",
            "Vortex",
          ],
          [
            "E8–E10 WorkingSet",
            "query_graph(neighbors of ci_id) + get_metric_baseline / sketches for those ids",
            "Vortex may federate cold S3; returns bounded WorkingSet",
          ],
          [
            "Optional Pillar C",
            "Same tools only",
            "No open-S3; no raw Vortex hop-scan",
          ],
        ]}
        rowTone={["info", "neutral", "warning", "neutral"]}
      />

      <Callout tone="warning" title="Product rule">
        Diagnose never browses S3 as a dump. Cold is for retention, rebuild, and
        backfill into Vortex. Logical keys stay fixed when the profile changes:
        node (tenant, ci_id); edge (tenant, edge_id); sketch (tenant, entity_id,
        metric_id, window, season_key, window_start).
      </Callout>

      <Text size="small">
        Deep dive §7.3–7.4 · FAQ Q30 / Q36 · vortex-s3-interaction.html ·
        GATE_B_DEST_PROFILE.md
      </Text>
    </Stack>
  );
}

function Join() {
  return (
    <Stack gap={14}>
      <Callout tone="warning" title="No map↔history sync">
        Rooms stay separate. Join = read-time WorkingSet keyed by tenant +
        ci_id/entity_id. Integration may assert sketched entities exist as nodes —
        a consistency check, not replication.
      </Callout>
      <Table
        headers={["Myth", "Fact"]}
        rows={[
          ["history syncs into map", "Never — different schemas"],
          ["map embeds digests", "No — sketches are history rows"],
          ["join_key column", "Concept only = tenant + shared id"],
          ["LUT in map/", "Bind is E2 Identity, not a third room"],
          ["Vortex = map/, S3 = history/", "No — both rooms can be hot+cold"],
        ]}
      />
      <Text size="small">
        Animation: docs/map-history-storage-animation.html · Blocks:
        docs/map-history-storage-blocks.html · FAQ Q36 in contract brief.
      </Text>
    </Stack>
  );
}
