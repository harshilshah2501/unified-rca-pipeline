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
      "P1 write path only: estate bootstrap + topo stream → GraphWriter → map/. Diagnose reads map/; it does not call write methods.",
    relates:
      "Parent frame for every other tab. Read this once, then drill down. Nothing below invents a second write path.",
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
      "Case-path style reads over a published snapshot (PoC stubs for Scope/Diagnose).",
    relates:
      "Opposite side of the spine: after publish_map, readers load Dest map/ — they do not call write_topo_stream. compare.py is tests-only.",
    files: [
      {
        file: "graph/neighbors.py",
        job: "Outbound neighbor walk",
        callers: "tests; later Scope",
      },
      {
        file: "graph/read_api.py",
        job: "load_snapshot helpers",
        callers: "tests",
      },
      {
        file: "graph/compare.py",
        job: "SAMPLE_IO spine equality",
        callers: "tests only",
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

const VERB_STEPS: {
  id: string;
  method: string;
  means: string;
  optional?: boolean;
}[] = [
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
    optional: true,
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

          {/* Read helpers → Dest room */}
          <line
            x1={readX}
            y1={readY + READ_H / 2}
            x2={destX + DEST_W}
            y2={destY + DEST_H / 2}
            stroke={theme.stroke.secondary}
            strokeWidth={1.5}
            markerEnd="url(#flow-arrow)"
          />
          <text
            x={(readX + destX + DEST_W) / 2}
            y={destY + DEST_H / 2 - 10}
            textAnchor="middle"
            fill={theme.text.tertiary}
            fontSize={10}
          >
            reads
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
            snapshot · nodes · edges
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
            neighbors · load
          </span>
        </button>
      </div>

      <Text size="small" tone="secondary">
        Click a box or the Dest room for detail below. Lab entry maps to
        Topology writer in product.
      </Text>
    </Stack>
  );
}

function CallSequenceFlow() {
  const theme = useHostTheme();
  const happy = VERB_STEPS.filter((s) => !s.optional);
  const optional = VERB_STEPS.find((s) => s.optional);

  return (
    <Stack gap={12}>
      <Text weight="medium">Happy path (required)</Text>
      <Row gap={8} align="center" wrap>
        {happy.map((step, i) => (
          <Row key={step.id} gap={8} align="center">
            <Card style={{ minWidth: 180, flex: "0 1 auto" }}>
              <CardBody>
                <Stack gap={6}>
                  <Row gap={6} align="center">
                    <Pill tone="info" size="sm">
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
            {i < happy.length - 1 ? (
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

      {optional ? (
        <Stack gap={8}>
          <Text weight="medium">Optional E5 loop (after first publish)</Text>
          <Row gap={8} align="center" wrap>
            <Card style={{ minWidth: 180 }}>
              <CardBody>
                <Stack gap={6}>
                  <Row gap={6} align="center">
                    <Pill tone="neutral" size="sm">
                      3
                    </Pill>
                    <Text weight="semibold" size="small">
                      publish_map
                    </Text>
                  </Row>
                  <Text size="small" tone="secondary">
                    Snapshot already on Dest
                  </Text>
                </Stack>
              </CardBody>
            </Card>
            <Text
              weight="semibold"
              style={{ color: theme.text.tertiary, fontSize: 18 }}
            >
              →
            </Text>
            <Card style={{ minWidth: 180 }}>
              <CardBody>
                <Stack gap={6}>
                  <Row gap={6} align="center">
                    <Pill tone="warning" size="sm">
                      4
                    </Pill>
                    <Text weight="semibold" size="small">
                      {optional.method}
                    </Text>
                  </Row>
                  <Text size="small" tone="secondary">
                    {optional.means}
                  </Text>
                </Stack>
              </CardBody>
            </Card>
            <Text
              weight="semibold"
              style={{ color: theme.text.tertiary, fontSize: 18 }}
            >
              →
            </Text>
            <Card style={{ minWidth: 180 }}>
              <CardBody>
                <Stack gap={6}>
                  <Row gap={6} align="center">
                    <Pill tone="info" size="sm">
                      5
                    </Pill>
                    <Text weight="semibold" size="small">
                      publish_map
                    </Text>
                  </Row>
                  <Text size="small" tone="secondary">
                    Re-flush after maintain marks
                  </Text>
                </Stack>
              </CardBody>
            </Card>
          </Row>
        </Stack>
      ) : null}
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
            <Text tone="secondary" size="small">
              Guides: docs/MAP_P1_FABRIC_EVAL.md · docs/Codebase-go-through.md
            </Text>
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
  6: "After publish",
  7: "Product honesty",
};

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
          Interactive index for pillar-ab-implementation/pillar-b/poc. Open
          beside chat; use Pylance F12 in the editor for symbol jumps.
        </Text>
      </Stack>

      <Grid columns={4} gap={12}>
        <Stat value="P1" label="Always-on fabric E1–E5" />
        <Stat value="map/" label="Sole GraphWriter room" />
        <Stat value="4" label="Public write verbs" />
        <Stat value="Dest" label="Prod integration surface" tone="info" />
      </Grid>

      <Callout tone="info" title="Start in code">
        Open graph/graph_writer.py → F12 into apply_topo_stream → Shift+F12 on
        GraphWriter for every caller (CLI + tests).
      </Callout>

      <H2>How the layers relate</H2>
      <Text tone="secondary" size="small">
        Write path left-to-right; publish_map drops into Dest map/; readers
        load that room. Click for detail below.
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

      <H2>GraphWriter call sequence</H2>
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
          Package README · docs/README.md (doc map) · SAMPLE_IO Case A/B · slice
          contracts/MAP_WRITE_READ_RECORD.md ·
          reference/canvases/pillar-b-poc-navigator.canvas.tsx
        </Text>
        <Text size="small" style={{ color: theme.text.tertiary }}>
          Canvas state remembers your last layer selection across reloads.
        </Text>
      </Stack>
    </Stack>
  );
}
