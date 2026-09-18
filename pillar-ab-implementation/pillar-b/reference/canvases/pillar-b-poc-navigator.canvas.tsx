import {
  Button,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Code,
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
  /** 1-based cold-reader order */
  readOrder: number;
  blurb: string;
  /** How this layer sits relative to the others */
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
      "Sole library API the lab CLI, unit tests, and a future Topology worker call for map writes.",
    relates:
      "Sits under Lab entry (and future workers). Calls Write core + Shared glue; publishes through Dest (Production surfaces). Read helpers never call it for writes.",
    files: [
      {
        file: "graph/graph_writer.py",
        job: "load_estate_bootstrap → write_topo_stream → publish_map → maintain_map",
        callers: "cli_publish_map, tests, future Topology worker",
      },
    ],
  },
  {
    id: "entry",
    title: "Lab entry",
    readOrder: 3,
    blurb: "Human / Make entry that wires sample-estate files into GraphWriter + FileDest. Not a production HTTP server.",
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
    blurb: "Internal to GraphWriter: admit triage, mutate GraphState, validate, publish, E5 maintain. Do not import from Diagnose.",
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
    blurb: "Case-path style reads over a published snapshot (PoC stubs for Scope/Diagnose).",
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
        callers: "Topology worker → write_topo_stream",
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

export default function PillarBPocNavigator() {
  const theme = useHostTheme();
  const [layer, setLayer] = useCanvasState<LayerId>("pillar-b-nav-layer", "overview");
  const active = LAYERS.find((l) => l.id === layer) ?? LAYERS[0];

  return (
    <Stack gap={20} style={{ padding: 20, maxWidth: 960 }}>
      <Stack gap={6}>
        <H1>Pillar B map PoC navigator</H1>
        <Text tone="secondary">
          Interactive index for pillar-ab-implementation/pillar-b/poc. Open beside
          chat; use Pylance F12 in the editor for symbol jumps.
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
        Call / dependency direction for the PoC. Arrows mean “uses” or “feeds.”
      </Text>
      <Code>
        {`Lab entry  ──calls──►  Public orchestrator  ──uses──►  Write core
                                      │                         │
                                      │                         └──uses──►  Shared glue
                                      │
                                      └──publish_map──►  Dest map/  ◄──read──  Read helpers

Production surfaces = same Dest map/ + ingest.v1 stream (product), not a GraphWriter HTTP API.
Spine = the whole write story above (not a separate package).`}
      </Code>

      <H2>Read in this order</H2>
      <Text tone="secondary" size="small">
        Click a step to open that layer. Same order as docs/Codebase-go-through.md
        clarifications.
      </Text>
      <Stack gap={6}>
        {READ_ORDER.map((l) => (
          <Row key={l.id} gap={10} align="center">
            <Pill tone={l.id === layer ? "info" : "neutral"} size="sm">
              {String(l.readOrder)}
            </Pill>
            <Button
              variant={l.id === layer ? "primary" : "secondary"}
              onClick={() => setLayer(l.id)}
            >
              {l.title}
            </Button>
            <Text size="small" tone="secondary">
              {l.readOrder === 1
                ? "Big picture"
                : l.readOrder === 2
                  ? "Only write API"
                  : l.readOrder === 3
                    ? "How to run once"
                    : l.readOrder === 4
                      ? "Internals"
                      : l.readOrder === 5
                        ? "Supporting stubs"
                        : l.readOrder === 6
                          ? "After publish"
                          : "Product honesty"}
            </Text>
          </Row>
        ))}
      </Stack>

      <Divider />

      <H2>Choose a layer</H2>
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

      <Card>
        <CardHeader
          trailing={
            <Row gap={6}>
              <Pill tone="neutral" size="sm">
                Read #{active.readOrder}
              </Pill>
              <Pill tone="info">{active.title}</Pill>
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
                <Text weight="medium">Call sequence</Text>
                <Code>
                  load_estate_bootstrap → write_topo_stream → publish_map →
                  [maintain_map → publish_map]
                </Code>
                <Text tone="secondary" size="small">
                  Guides: docs/MAP_P1_FABRIC_EVAL.md · docs/Codebase-go-through.md
                </Text>
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
          contracts/MAP_WRITE_READ_RECORD.md
        </Text>
        <Text size="small" style={{ color: theme.text.tertiary }}>
          Canvas state remembers your last layer selection across reloads.
        </Text>
      </Stack>
    </Stack>
  );
}
