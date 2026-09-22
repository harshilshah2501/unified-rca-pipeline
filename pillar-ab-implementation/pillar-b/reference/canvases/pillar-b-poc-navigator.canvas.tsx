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
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useCanvasState,
  useHostTheme,
} from "cursor/canvas";

type LayerId =
  | "overview"
  | "orchestrator"
  | "entry"
  | "write-core"
  | "shared"
  | "read"
  | "prod";

type FileRow = {
  file: string;
  job: string;
  callers: string;
};

const LAYERS: {
  id: LayerId;
  title: string;
  readOrder: number;
  blurb: string;
  relates: string;
  files: FileRow[];
}[] = [
  {
    id: "overview",
    title: "Spine",
    readOrder: 1,
    blurb:
      "Two use cases only: (1) build + maintain the knowledge graph into Dest map/, (2) walk-through a published snapshot. Detect / Curate / Identify / Package / sketches are assumed or stubbed — not the PoC mission.",
    relates:
      "Parent frame for every other tab. Write path left → publish_map → Dest map/ → walk APIs right. Nothing below invents a second write path or a ServiceOps product surface.",
    files: [],
  },
  {
    id: "orchestrator",
    title: "Public orchestrator",
    readOrder: 2,
    blurb:
      "Sole library API the lab CLI, unit tests, and a future Topology writer call for map writes.",
    relates:
      "Sits under Lab entry (and future workers). Calls Write core + Shared glue; publishes through Dest (Production surfaces). Read helpers never call it for writes.",
    files: [
      {
        file: "graph/graph_writer.py",
        job: "load_estate_bootstrap → write_topo_stream → publish_map → maintain_map",
        callers: "cli_publish_map, tests, future Topology writer",
      },
    ],
  },
  {
    id: "entry",
    title: "Lab entry",
    readOrder: 3,
    blurb:
      "Human / Make entry that wires sample-estate files into GraphWriter + FileDest. Not a production HTTP server.",
    relates:
      "Thin caller only: sample estate files → Public orchestrator → FileDest. Skip in production mental model; use it to run the PoC once.",
    files: [
      {
        file: "graph/cli_publish_map.py",
        job: "Wire sample-estate files into GraphWriter + FileDest",
        callers: "make publish-map",
      },
    ],
  },
  {
    id: "write-core",
    title: "Write core",
    readOrder: 4,
    blurb:
      "Internal to GraphWriter: admit triage, mutate GraphState, validate, publish, E5 maintain. Do not import from Diagnose.",
    relates:
      "Owned exclusively by Public orchestrator. Depends on Shared glue (gate, Dest, schema, reject codes). Downstream readers use Dest, not these modules.",
    files: [
      {
        file: "graph/graph_builder.py",
        job: "GraphState; load_estate_bootstrap_state; apply_topo_stream (admit triage)",
        callers: "graph_writer only",
      },
      {
        file: "graph/ci_qualify.py",
        job: "Never-CI types → DROP",
        callers: "graph_builder",
      },
      {
        file: "graph/edge_catalog.py",
        job: "Relation emit / skip / reject",
        callers: "graph_builder",
      },
      {
        file: "graph/provenance.py",
        job: "discovered_via evidence blocks",
        callers: "graph_builder",
      },
      {
        file: "graph/snapshot.py",
        job: "build / publish / load graph_snapshot.v1",
        callers: "graph_writer",
      },
      {
        file: "graph/maintain.py",
        job: "E5 expire, stale corroborating, declared 7d/30d",
        callers: "graph_writer.maintain_map",
      },
    ],
  },
  {
    id: "shared",
    title: "Shared glue (ab_shared)",
    readOrder: 5,
    blurb: "Post-Identity utilities. Pillar B does not reimplement Collect.",
    relates:
      "Horizontal support under Write core and Lab entry (paths, JSONL sources). Same patterns as Pillar A. Not a Motadata stage by itself.",
    files: [
      {
        file: "ab_shared/identity_gate.py",
        job: "ResolvedOnlyGate — E2 door into writers",
        callers: "graph_writer / apply_topo_stream",
      },
      {
        file: "ab_shared/dest.py",
        job: "MemoryDest / FileDest put-get for map/",
        callers: "snapshot publish + tests",
      },
      {
        file: "ab_shared/ingest_source.py",
        job: "JSONL / list stream sources",
        callers: "CLI + tests",
      },
      {
        file: "ab_shared/schema.py",
        job: "Validate against contracts/schemas mirrors",
        callers: "snapshot",
      },
      {
        file: "ab_shared/reject_codes.py",
        job: "Stable DROP reason strings",
        callers: "gate / catalog / qualify",
      },
    ],
  },
  {
    id: "read",
    title: "Read helpers",
    readOrder: 6,
    blurb:
      "Use case 2 — walk-through: hops, direction, relation filters, reachable set, paths, confidence-bearing filter over a published snapshot. case_path/ drivers are optional harnesses that call these APIs.",
    relates:
      "Opposite side of the spine (use case 2): after publish_map, readers load Dest map/ via load_snapshot — they do not call write_topo_stream. compare.py is tests-only (build proof).",
    files: [
      {
        file: "graph/neighbors.py",
        job: "neighbors / reachable_ci_ids / find_paths",
        callers: "test_map_walk; case_path stubs",
      },
      {
        file: "graph/read_api.py",
        job: "load_snapshot + confidence_bearing filter",
        callers: "test_map_walk; case_path stubs",
      },
      {
        file: "graph/compare.py",
        job: "SAMPLE_IO spine equality",
        callers: "tests only",
      },
      {
        file: "graph/case_path/*",
        job: "Stub Detect→Package drivers (not PoC core)",
        callers: "test_case_path; test_identify_package",
      },
    ],
  },
  {
    id: "prod",
    title: "Production surfaces",
    readOrder: 7,
    blurb:
      "No frozen third-party GraphWriter REST/gRPC. Other Motadata stages use Dest rooms + the ingest stream.",
    relates:
      "What replaces Lab entry in product: ingest.v1 topo stream in, Dest map/ out. Vortex/S3 are encodings of the same Dest keys — not a second schema. Read last so the PoC folders do not look like product APIs.",
    files: [
      {
        file: "Dest put/get map/",
        job: "Write/read graph_snapshot + nodes/edges JSON(L)",
        callers: "GraphWriter write; Scope/Diagnose/E5 read",
      },
      {
        file: "ingest.v1 topo_update stream",
        job: "Continuous Topology input after Identity",
        callers: "Topology writer → write_topo_stream",
      },
      {
        file: "Vortex + S3 adapters",
        job: "Same logical keys; hot/cold encodings",
        callers: "Design / later Dest profiles",
      },
    ],
  },
];

const READ_ORDER = [...LAYERS].sort((a, b) => a.readOrder - b.readOrder);

const API_ROWS = [
  {
    method: "load_estate_bootstrap",
    means: "Load optional starting estate (not CaseSeed)",
  },
  {
    method: "write_topo_stream",
    means: "Upsert admitted topo_update lines into GraphState (not Dest yet)",
  },
  {
    method: "publish_map",
    means: "Validate GraphState + write snapshot/nodes/edges to Dest map/",
  },
  {
    method: "maintain_map",
    means: "E5 validity marks — no new edges",
  },
];

/** Horizontal write-path packages (Dest room is laid out separately below Write core). */
const REL_PACKAGES: {
  id: string;
  label: string;
  sub: string;
  layer: LayerId;
}[] = [
  { id: "entry", label: "Lab entry", sub: "CLI / make", layer: "entry" },
  {
    id: "orch",
    label: "Public orchestrator",
    sub: "GraphWriter",
    layer: "orchestrator",
  },
  { id: "core", label: "Write core", sub: "builder · catalog", layer: "write-core" },
  { id: "shared", label: "Shared glue", sub: "ab_shared", layer: "shared" },
];

const PACKAGE_FLOW: { from: string; to: string; label: string }[] = [
  { from: "entry", to: "orch", label: "calls" },
  { from: "orch", to: "core", label: "uses" },
  { from: "core", to: "shared", label: "uses" },
];

const WRITE_STEPS: { id: string; method: string; means: string }[] = [
  {
    id: "boot",
    method: "load_estate_bootstrap",
    means: "Optional starting estate into memory",
  },
  {
    id: "stream",
    method: "write_topo_stream",
    means: "Admit topo lines → GraphState (not Dest yet)",
  },
  {
    id: "publish",
    method: "publish_map",
    means: "Validate + write snapshot / nodes / edges to Dest",
  },
  {
    id: "maintain",
    method: "maintain_map",
    means: "E5 validity marks — then publish_map again",
  },
];

const WALK_STEPS: { id: string; method: string; means: string }[] = [
  {
    id: "load",
    method: "load_snapshot",
    means: "Read Dest map/ keys back into a snapshot dict",
  },
  {
    id: "neighbors",
    method: "get_neighbors",
    means: "1-hop / multi-hop edges via neighbors() — direction + filters",
  },
  {
    id: "reachable",
    method: "get_reachable",
    means: "Seed + neighborhood CI set via reachable_ci_ids()",
  },
  {
    id: "paths",
    method: "get_paths",
    means: "Simple paths to CI or leaf type via find_paths()",
  },
];

const PKG_W = 136;
const PKG_H = 52;
const PKG_GAP = 48;
const DIAGRAM_PAD = 16;
const DEST_W = 200;
const DEST_H = 72;
const READ_W = 136;
const READ_H = 52;

function LayerRelationDiagram({
  activeLayer,
  onSelect,
}: {
  activeLayer: LayerId;
  onSelect: (id: LayerId) => void;
}) {
  const theme = useHostTheme();

  const pkgXs = REL_PACKAGES.map(
    (_, i) => DIAGRAM_PAD + i * (PKG_W + PKG_GAP),
  );
  const pkgY = DIAGRAM_PAD;
  const coreIdx = REL_PACKAGES.findIndex((p) => p.id === "core");
  const coreCx = pkgXs[coreIdx] + PKG_W / 2;

  const arrowTop = pkgY + PKG_H;
  const destY = arrowTop + 56;
  const destX = coreCx - DEST_W / 2;
  const readX = destX + DEST_W + PKG_GAP;
  const readY = destY + (DEST_H - READ_H) / 2;

  const diagramW = Math.max(
    DIAGRAM_PAD * 2 + REL_PACKAGES.length * PKG_W + (REL_PACKAGES.length - 1) * PKG_GAP,
    readX + READ_W + DIAGRAM_PAD,
  );
  const diagramH = destY + DEST_H + DIAGRAM_PAD;

  const destSelected = activeLayer === "prod";
  const readSelected = activeLayer === "read";

  return (
    <Stack gap={10}>
      <div
        style={{
          position: "relative",
          width: diagramW,
          height: diagramH,
          maxWidth: "100%",
          overflow: "auto",
        }}
      >
        <svg
          width={diagramW}
          height={diagramH}
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            pointerEvents: "none",
            display: "block",
          }}
        >
          <defs>
            <marker
              id="flow-arrow"
              viewBox="0 0 10 10"
              refX={9}
              refY={5}
              markerWidth={7}
              markerHeight={7}
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill={theme.stroke.secondary} />
            </marker>
            <marker
              id="publish-arrow"
              viewBox="0 0 10 10"
              refX={9}
              refY={5}
              markerWidth={7}
              markerHeight={7}
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill={theme.accent.primary} />
            </marker>
          </defs>

          {PACKAGE_FLOW.map((e, i) => {
            const x1 = pkgXs[i] + PKG_W;
            const x2 = pkgXs[i + 1];
            const y = pkgY + PKG_H / 2;
            return (
              <g key={`${e.from}-${e.to}`}>
                <line
                  x1={x1}
                  y1={y}
                  x2={x2}
                  y2={y}
                  stroke={theme.stroke.secondary}
                  strokeWidth={1.5}
                  markerEnd="url(#flow-arrow)"
                />
                <text
                  x={(x1 + x2) / 2}
                  y={y - 8}
                  textAnchor="middle"
                  fill={theme.text.tertiary}
                  fontSize={10}
                >
                  {e.label}
                </text>
              </g>
            );
          })}

          {/* Write core → Dest room */}
          <line
            x1={coreCx}
            y1={arrowTop}
            x2={coreCx}
            y2={destY}
            stroke={theme.accent.primary}
            strokeWidth={2}
            markerEnd="url(#publish-arrow)"
          />
          <text
            x={coreCx + 10}
            y={(arrowTop + destY) / 2 + 4}
            fill={theme.accent.primary}
            fontSize={11}
            fontWeight={600}
          >
            publish_map
          </text>

          {/* Dest room → Read helpers (use case 2 · walk-through) */}
          <line
            x1={destX + DEST_W}
            y1={destY + DEST_H / 2}
            x2={readX}
            y2={readY + READ_H / 2}
            stroke={theme.accent.primary}
            strokeWidth={2}
            markerEnd="url(#publish-arrow)"
          />
          <text
            x={(readX + destX + DEST_W) / 2}
            y={destY + DEST_H / 2 - 12}
            textAnchor="middle"
            fill={theme.accent.primary}
            fontSize={10}
            fontWeight={600}
          >
            load_snapshot · walk
          </text>
        </svg>

        {REL_PACKAGES.map((p, i) => {
          const selected = activeLayer === p.layer;
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => onSelect(p.layer)}
              aria-pressed={selected}
              aria-label={`Open layer: ${p.label}`}
              style={{
                position: "absolute",
                left: pkgXs[i],
                top: pkgY,
                width: PKG_W,
                height: PKG_H,
                margin: 0,
                padding: "6px 8px",
                boxSizing: "border-box",
                borderRadius: 4,
                border: `${selected ? 2 : 1}px solid ${
                  selected ? theme.accent.primary : theme.stroke.secondary
                }`,
                background: selected
                  ? theme.fill.tertiary
                  : theme.fill.secondary,
                color: theme.text.primary,
                cursor: "pointer",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: 2,
                fontFamily: "inherit",
              }}
            >
              <span
                style={{
                  fontSize: 11,
                  fontWeight: selected ? 600 : 500,
                  lineHeight: 1.2,
                  textAlign: "center",
                }}
              >
                {p.label}
              </span>
              <span
                style={{
                  fontSize: 9,
                  color: theme.text.secondary,
                  lineHeight: 1.2,
                  textAlign: "center",
                }}
              >
                {p.sub}
              </span>
            </button>
          );
        })}

        {/* Dest room — oval / stadium, accent surface */}
        <button
          type="button"
          onClick={() => onSelect("prod")}
          aria-pressed={destSelected}
          aria-label="Open layer: Dest map/ room"
          style={{
            position: "absolute",
            left: destX,
            top: destY,
            width: DEST_W,
            height: DEST_H,
            margin: 0,
            padding: "8px 16px",
            boxSizing: "border-box",
            borderRadius: DEST_H / 2,
            border: `${destSelected ? 2 : 1}px solid ${theme.accent.primary}`,
            background: destSelected
              ? theme.accent.primary
              : theme.accent.control,
            color: theme.text.onAccent,
            cursor: "pointer",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 2,
            fontFamily: "inherit",
          }}
        >
          <span style={{ fontSize: 12, fontWeight: 600, lineHeight: 1.2 }}>
            Dest map/
          </span>
          <span
            style={{
              fontSize: 9,
              opacity: 0.9,
              lineHeight: 1.2,
              textAlign: "center",
            }}
          >
            UC1 publish · UC2 walk hub
          </span>
        </button>

        <button
          type="button"
          onClick={() => onSelect("read")}
          aria-pressed={readSelected}
          aria-label="Open layer: Read helpers"
          style={{
            position: "absolute",
            left: readX,
            top: readY,
            width: READ_W,
            height: READ_H,
            margin: 0,
            padding: "6px 8px",
            boxSizing: "border-box",
            borderRadius: 4,
            border: `${readSelected ? 2 : 1}px solid ${
              readSelected ? theme.accent.primary : theme.stroke.secondary
            }`,
            background: readSelected
              ? theme.fill.tertiary
              : theme.fill.secondary,
            color: theme.text.primary,
            cursor: "pointer",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 2,
            fontFamily: "inherit",
          }}
        >
          <span
            style={{
              fontSize: 11,
              fontWeight: readSelected ? 600 : 500,
              lineHeight: 1.2,
              textAlign: "center",
            }}
          >
            Read helpers
          </span>
          <span
            style={{
              fontSize: 9,
              color: theme.text.secondary,
              lineHeight: 1.2,
              textAlign: "center",
            }}
          >
            neighbors · walk
          </span>
        </button>
      </div>

      <Text size="small" tone="secondary">
        Two use cases on one spine. Use case 1 (build + maintain): Lab entry →
        GraphWriter → Write core → Dest map/ via publish_map. Use case 2
        (walk-through): Dest map/ → Read helpers via load_snapshot · walk.
        Click a box for detail below.
      </Text>
    </Stack>
  );
}

function SequenceCards({
  steps,
  pillTone = "info",
}: {
  steps: { id: string; method: string; means: string }[];
  pillTone?: "info" | "neutral" | "warning";
}) {
  const theme = useHostTheme();
  return (
    <Row gap={8} align="center" wrap>
      {steps.map((step, i) => (
        <Row key={step.id} gap={8} align="center">
          <Card style={{ minWidth: 180, flex: "0 1 auto" }}>
            <CardBody>
              <Stack gap={6}>
                <Row gap={6} align="center">
                  <Pill tone={pillTone} size="sm">
                    {String(i + 1)}
                  </Pill>
                  <Text weight="semibold" size="small">
                    {step.method}
                  </Text>
                </Row>
                <Text size="small" tone="secondary">
                  {step.means}
                </Text>
              </Stack>
            </CardBody>
          </Card>
          {i < steps.length - 1 ? (
            <Text
              weight="semibold"
              style={{ color: theme.text.tertiary, fontSize: 18 }}
            >
              →
            </Text>
          ) : null}
        </Row>
      ))}
    </Row>
  );
}

function CallSequenceFlow() {
  return (
    <Stack gap={16}>
      <Stack gap={8}>
        <Text weight="medium">GraphWriter — use case 1 · build + maintain</Text>
        <Text size="small" tone="secondary">
          Estate bootstrap + topo stream → Dest map/. maintain_map is E5 on an
          already-published map; call publish_map again to re-flush marks.
        </Text>
        <SequenceCards steps={WRITE_STEPS} pillTone="info" />
      </Stack>
      <Stack gap={8}>
        <Text weight="medium">Walk-through — use case 2 · read published map/</Text>
        <Text size="small" tone="secondary">
          After publish_map. read_api thin wrappers delegate into neighbors.py.
          Proof: test_map_walk. Does not call write verbs.
        </Text>
        <SequenceCards steps={WALK_STEPS} pillTone="neutral" />
      </Stack>
    </Stack>
  );
}

function LayerDetailPanel({ active }: { active: (typeof LAYERS)[number] }) {
  return (
    <Card>
      <CardHeader
        trailing={
          <Row gap={6}>
            <Pill tone="neutral" size="sm">
              Read #{active.readOrder}
            </Pill>
            <Pill tone="info" active>
              {active.title}
            </Pill>
          </Row>
        }
      >
        {active.title}
      </CardHeader>
      <CardBody>
        <Stack gap={12}>
          <Text>{active.blurb}</Text>
          <Stack gap={4}>
            <Text weight="medium">Related how</Text>
            <Text size="small" tone="secondary">
              {active.relates}
            </Text>
          </Stack>
          {active.id === "overview" ? (
            <Stack gap={8}>
              <Text tone="secondary" size="small">
                Eval detail: docs/MAP_P1_FABRIC_EVAL.md · code tour:
                docs/Codebase-go-through.md · call graphs:
                docs/pillar-b-callgraph.png (build) ·
                docs/pillar-b-walk-callgraph.png (walk)
              </Text>
              <Stack gap={4}>
                <Text weight="medium">How to judge success</Text>
                <Text size="small" tone="secondary">
                  1. Case A/B map spines match SAMPLE_IO after build. 2. Walk
                  tests show multi-hop / inbound / confidence-bearing behavior
                  on published map/. 3. Maintain changes what a walk is allowed
                  to see (expire / hard-downgrade). If a change does not improve
                  build, maintain, or walk, it is out of focus.
                </Text>
              </Stack>
            </Stack>
          ) : null}
          {active.files.length > 0 ? (
            <Table
              headers={["File / surface", "Job", "Who calls"]}
              rows={active.files.map((f) => [f.file, f.job, f.callers])}
            />
          ) : null}
        </Stack>
      </CardBody>
    </Card>
  );
}

const READ_BLURBS: Record<number, string> = {
  1: "Big picture",
  2: "Only write API",
  3: "How to run once",
  4: "Internals",
  5: "Supporting stubs",
  6: "Walk-through",
  7: "Product honesty",
};

const USE_CASE_ROWS = [
  {
    useCase: "1 · Build + maintain",
    owns: "Admit topo_update, upsert nodes/edges, publish GraphSnapshot, E5 validity marks",
    proof: "test_p1_map_fabric, test_maintain, test_graph_writer, test_sample_io",
  },
  {
    useCase: "2 · Walk-through",
    owns: "Read published snapshot: hops, direction, relation filters, reachable set, paths, confidence-bearing",
    proof: "test_map_walk",
  },
];

const STUB_ROWS = [
  {
    concern: "E1 Collect / E2 Identity",
    stance: "Assumed done — fixtures look like post-E2 ingest.v1",
  },
  {
    concern: "Pillar A sketches / history/",
    stance: "Out of package; optional sketch_provider hook only",
  },
  {
    concern: "Detect Signal storm",
    stance: "Stub JSON under cases/increment2/",
  },
  {
    concern: "CaseSeed / WorkingSet / LeafClaim",
    stance: "Thin drivers that call walk APIs — not a second product",
  },
  {
    concern: "EvidenceBundle / VerdictCard",
    stance: "Lab stubs for a diagnose-shaped close — not ServiceOps",
  },
  {
    concern: "Live Vortex / S3 / discovery crawler",
    stance: "Dest is files.v1; discovery = Design",
  },
];

export default function PillarBPocNavigator() {
  const theme = useHostTheme();
  const [layer, setLayer] = useCanvasState<LayerId>(
    "pillar-b-nav-layer",
    "overview",
  );
  const active = LAYERS.find((l) => l.id === layer) ?? LAYERS[0];

  return (
    <Stack gap={20} style={{ padding: 20, maxWidth: 980 }}>
      <Stack gap={6}>
        <H1>Pillar B map PoC navigator</H1>
        <Text tone="secondary">
          Interactive index for pillar-ab-implementation/pillar-b/poc. This
          package proves a knowledge graph / topology PoC — two use cases only.
          Open beside chat; use Pylance F12 in the editor for symbol jumps.
        </Text>
      </Stack>

      <Grid columns={4} gap={12}>
        <Stat value="2" label="Use cases (build · walk)" tone="info" />
        <Stat value="map/" label="Sole GraphWriter room" />
        <Stat value="4" label="Public write verbs" />
        <Stat value="Dest" label="Prod integration surface" />
      </Grid>

      <Callout tone="info" title="PoC focus lock">
        Build/maintain and walk-through own the mission. case_path/ under Read
        helpers is optional harness only. Start in code: graph/graph_writer.py →
        F12 into apply_topo_stream → Shift+F12 on GraphWriter for every caller.
      </Callout>

      <H2>The only two use cases that matter</H2>
      <Text tone="secondary" size="small">
        Build/maintain → GraphState → publish_map → Dest map/ ← walk-through
        (neighbors / reachable / paths). maintain_map (optional E5) sits on the
        write side.
      </Text>
      <Table
        headers={["Use case", "What we own", "Proof"]}
        rows={USE_CASE_ROWS.map((r) => [r.useCase, r.owns, r.proof])}
      />

      <H3>What we stub or assume (not PoC core)</H3>
      <Table
        headers={["Concern", "Stance in this PoC"]}
        rows={STUB_ROWS.map((r) => [r.concern, r.stance])}
      />
      <Text size="small" tone="secondary">
        Stub harness docs: docs/MAP_P2_CASE_PATH.md · docs/MAP_P3_DIAGNOSE_CLOSE.md
        — optional, not the knowledge-graph mission.
      </Text>

      <H2>How the layers relate</H2>
      <Text tone="secondary" size="small">
        Use case 1 — write path left-to-right, then publish_map into Dest map/.
        Use case 2 — Dest map/ rightward into Read helpers (load_snapshot ·
        walk). Click for detail below.
      </Text>
      <LayerRelationDiagram activeLayer={layer} onSelect={setLayer} />

      <Row gap={8} wrap>
        {READ_ORDER.map((l) => (
          <Button
            key={l.id}
            variant={l.id === layer ? "primary" : "secondary"}
            onClick={() => setLayer(l.id)}
          >
            {l.readOrder}. {l.title}
          </Button>
        ))}
      </Row>
      <Text size="small" tone="secondary">
        Same selection as the diagram. Read order:{" "}
        {READ_BLURBS[active.readOrder] ?? ""} ·{" "}
        {READ_ORDER.map((l) => l.title).join(" → ")}
      </Text>

      <LayerDetailPanel active={active} />

      <Divider />

      <H2>Call sequences</H2>
      <CallSequenceFlow />

      <Divider />

      <H2>Public GraphWriter verbs</H2>
      <Table
        headers={["Method", "Plain meaning"]}
        rows={API_ROWS.map((r) => [r.method, r.means])}
      />

      <H3>Docs</H3>
      <Stack gap={4}>
        <Text size="small" tone="secondary">
          Package README · docs/README.md (doc map) · MAP_P1_FABRIC_EVAL ·
          Codebase-go-through · SAMPLE_IO Case A/B ·
          contracts/MAP_WRITE_READ_RECORD.md
        </Text>
        <Text size="small" style={{ color: theme.text.tertiary }}>
          This canvas is the framing home (two use cases + layer index). State
          remembers your last layer selection across reloads.
        </Text>
      </Stack>
    </Stack>
  );
}
