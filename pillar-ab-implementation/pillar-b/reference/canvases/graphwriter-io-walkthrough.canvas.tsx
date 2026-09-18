import {
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
  computeDAGLayout,
  useCanvasState,
  useHostTheme,
  useMemo,
} from "cursor/canvas";

type StepId =
  | "who"
  | "pipeline"
  | "example"
  | "admit"
  | "build"
  | "output"
  | "lab";

const STEPS: { id: StepId; label: string; blurb: string }[] = [
  { id: "who", label: "1 · Who", blurb: "Partners GraphWriter talks to" },
  { id: "pipeline", label: "2 · Pipeline", blurb: "Where it sits after Identity" },
  { id: "example", label: "3 · Example", blurb: "checkout-api topo line → edge" },
  { id: "admit", label: "4 · Admit", blurb: "Accept · skip · reject" },
  { id: "build", label: "5 · Build", blurb: "Seed + stream → GraphState" },
  { id: "output", label: "6 · Output", blurb: "What lands under map/" },
  { id: "lab", label: "7 · Lab", blurb: "make flush walkthrough" },
];

const PARTNER_ROWS = [
  {
    partner: "E1 Collect (upstream)",
    role: "Does not talk to GraphWriter directly",
    exchange:
      "Produces raw signals. Pillar B PoC never implements Collect; lab fixtures already look like post-Identity lines.",
  },
  {
    partner: "E2 Identity (upstream)",
    role: "Stamps identity on ingest.v1",
    exchange:
      "GraphWriter only admits identity.status = resolved. Unresolved / synthesized lines become rejects.",
  },
  {
    partner: "Shared ingest stream",
    role: "Same wire as Pillar A",
    exchange:
      "JSONL of ingest.v1. GraphWriter filters signal_class = topo_update; metric_sample is a silent skip.",
  },
  {
    partner: "topology.seed.json (lab)",
    role: "Optional bootstrap",
    exchange:
      "load_seed fills GraphState with declared nodes/edges before the stream runs.",
  },
  {
    partner: "ResolvedOnlyGate (ab_shared)",
    role: "Shared identity admit",
    exchange:
      "Same gate Pillar A uses. GraphWriter does not invent a second identity policy.",
  },
  {
    partner: "ci_qualify + edge_catalog",
    role: "Catalog checks inside GraphWriter",
    exchange:
      "May this ci_type be a vertex? Is relation in the fifteen-name catalog (or wave-1 skip)?",
  },
  {
    partner: "Dest / FileDest (Gate B)",
    role: "Publish target",
    exchange:
      'flush → Dest.put("map", …) → graph_snapshot.json, nodes.jsonl, edges.jsonl under poc/out/<tenant>/map/.',
  },
  {
    partner: "Pillar A SketchWriter",
    role: "Sibling, not a caller",
    exchange:
      "Parallel writer on the same stream. No A∪B merge. Later diagnose read-joins by tenant + ci_id.",
  },
  {
    partner: "Diagnose / neighbors (downstream)",
    role: "Readers of map/",
    exchange:
      "load_snapshot + neighbors walk the published graph. GraphWriter does not call Diagnose.",
  },
  {
    partner: "E5 maintain stub",
    role: "Optional after flush",
    exchange:
      "maintain_validity expires edges / drops stale corroborating; then republish a new snapshot version.",
  },
];

const PIPELINE_NODES = [
  { id: "collect", label: "E1 Collect", sub: "upstream · not in PoC" },
  { id: "identity", label: "E2 Identity", sub: "stamps identity.*" },
  { id: "stream", label: "ingest.v1 stream", sub: "shared wire" },
  { id: "gw", label: "GraphWriter", sub: "Pillar B · E3" },
  { id: "sw", label: "SketchWriter", sub: "Pillar A · E4" },
  { id: "map", label: "map/ Dest", sub: "snapshot · nodes · edges" },
  { id: "hist", label: "history/ Dest", sub: "sketches (A only)" },
  { id: "read", label: "Diagnose readers", sub: "load_snapshot · neighbors" },
];

const PIPELINE_EDGES = [
  { from: "collect", to: "identity" },
  { from: "identity", to: "stream" },
  { from: "stream", to: "gw" },
  { from: "stream", to: "sw" },
  { from: "gw", to: "map" },
  { from: "sw", to: "hist" },
  { from: "map", to: "read" },
];

const EXAMPLE_LINE = `{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:00Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "signal_class": "topo_update",
  "relation": "runs_on",
  "src_ci_id": "checkout-api",
  "dst_ci_id": "linux-server-app-01",
  "identity": {
    "status": "resolved",
    "bind_source": "topology_lookup"
  }
}`;

const EXAMPLE_EDGE = `{
  "schema_version": "graph_edge.v1",
  "tenant": "default",
  "edge_id": "e_checkout-api_runs_on_linux-server-app-01",
  "src_ci_id": "checkout-api",
  "dst_ci_id": "linux-server-app-01",
  "relation": "runs_on",
  "discovered_via": {
    "evidence_type": "…from bind_source",
    "telemetry_source": "topology_lookup"
  },
  "valid_from": "2026-08-20T03:30:00Z",
  "valid_to": null
}`;

const ADMIT_ROWS = [
  {
    case: "Happy topo",
    signal: "topo_update",
    identity: "resolved",
    relation: "runs_on",
    outcome: "Admit → upsert node(s) + edge",
    tone: "success" as const,
  },
  {
    case: "Metric on same stream",
    signal: "metric_sample",
    identity: "resolved",
    relation: "—",
    outcome: "Silent skip (Pillar A’s job)",
    tone: "neutral" as const,
  },
  {
    case: "Unresolved identity",
    signal: "topo_update",
    identity: "unattributed",
    relation: "runs_on",
    outcome: "Reject · identity_unresolved",
    tone: "danger" as const,
  },
  {
    case: "Synthesized identity",
    signal: "topo_update",
    identity: "synthesized",
    relation: "runs_on",
    outcome: "Reject · identity_synthesized",
    tone: "danger" as const,
  },
  {
    case: "Never-CI type",
    signal: "topo_update",
    identity: "resolved",
    relation: "runs_on",
    outcome: "Reject · never_ci_vertex (Alert/Incident/…)",
    tone: "danger" as const,
  },
  {
    case: "Unknown relation",
    signal: "topo_update",
    identity: "resolved",
    relation: "CALLS_FREE_TEXT",
    outcome: "Reject · unknown_relation",
    tone: "danger" as const,
  },
  {
    case: "Catalog but not wave-1",
    signal: "topo_update",
    identity: "resolved",
    relation: "owned_by (example)",
    outcome: "Phased skip (legal enum, emitter not ready)",
    tone: "warning" as const,
  },
];

const BUILD_STEPS = [
  {
    step: "1",
    api: "load_seed(topology.seed.json)",
    does: "Creates GraphState. Qualifies each seed CI type. Declared seed edges get evidence_type declared, telemetry_source topology.seed.",
  },
  {
    step: "2",
    api: "ingest(JsonlIngestSource)",
    does: "For each topo_update: identity gate → ci_qualify → classify_relation → ensure endpoint nodes → upsert edge with provenance from identity.bind_source.",
  },
  {
    step: "3",
    api: "flush(FileDest)",
    does: "build_snapshot(version) validates packaged graph_snapshot.v1, then publish_snapshot writes the three map keys (overwrite).",
  },
  {
    step: "4",
    api: "maintain_validity (optional)",
    does: "E5 stub: expire valid_to / drop stale corroborating; flush again with a new version (lab CLI --maintain-validity).",
  },
];

const OUTPUT_ROWS = [
  {
    key: "graph_snapshot.json",
    schema: "graph_snapshot.v1",
    meaning: "Packaged read unit: tenant, version, nodes[], edges[]",
  },
  {
    key: "nodes.jsonl",
    schema: "graph_node.v1 per line",
    meaning: "Same vertices as the snapshot, one object per line for inspection",
  },
  {
    key: "edges.jsonl",
    schema: "graph_edge.v1 per line",
    meaning: "Same typed relations as the snapshot, one object per line",
  },
];

const LAB_SEED_NODES = [
  "bs-checkout (BusinessService)",
  "checkout-api (Service)",
  "linux-server-app-01 (Host)",
  "app-runtime-jvm (Runtime)",
  "payments-db (Database)",
];

const LAB_EDGES = [
  { from: "checkout-api", to: "linux-server-app-01", relation: "runs_on" },
  { from: "app-runtime-jvm", to: "linux-server-app-01", relation: "runs_on" },
  { from: "checkout-api", to: "payments-db", relation: "depends_on" },
  { from: "checkout-api", to: "bs-checkout", relation: "part_of" },
  { from: "checkout-api", to: "payments-db", relation: "communicates_with" },
];

function PipelineDag() {
  const theme = useHostTheme();
  const layout = useMemo(
    () =>
      computeDAGLayout({
        nodes: PIPELINE_NODES.map((n) => ({ id: n.id })),
        edges: PIPELINE_EDGES,
        direction: "horizontal",
        nodeWidth: 132,
        nodeHeight: 48,
        rankGap: 56,
        nodeGap: 28,
        padding: 12,
      }),
    [],
  );
  const labelOf = (id: string) => PIPELINE_NODES.find((n) => n.id === id);

  return (
    <Stack gap={8}>
      <svg
        width="100%"
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        style={{ maxWidth: layout.width, display: "block" }}
      >
        {layout.edges.map((e) => (
          <line
            key={`${e.from}-${e.to}`}
            x1={e.sourceX}
            y1={e.sourceY}
            x2={e.targetX}
            y2={e.targetY}
            stroke={theme.stroke.secondary}
            strokeWidth={1.5}
            markerEnd="url(#gw-arrow)"
          />
        ))}
        <defs>
          <marker
            id="gw-arrow"
            viewBox="0 0 10 10"
            refX={9}
            refY={5}
            markerWidth={6}
            markerHeight={6}
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill={theme.stroke.secondary} />
          </marker>
        </defs>
        {layout.nodes.map((n) => {
          const meta = labelOf(n.id);
          const isGw = n.id === "gw";
          return (
            <g key={n.id} transform={`translate(${n.x}, ${n.y})`}>
              <rect
                width={132}
                height={48}
                rx={4}
                fill={isGw ? theme.fill.tertiary : theme.fill.secondary}
                stroke={isGw ? theme.accent.primary : theme.stroke.secondary}
              />
              <text
                x={66}
                y={20}
                textAnchor="middle"
                fill={theme.text.primary}
                fontSize={11}
                fontWeight={isGw ? 600 : 500}
              >
                {meta?.label}
              </text>
              <text
                x={66}
                y={36}
                textAnchor="middle"
                fill={theme.text.secondary}
                fontSize={9}
              >
                {meta?.sub}
              </text>
            </g>
          );
        })}
      </svg>
      <Text tone="secondary" size="small">
        Source: pillar-ab-implementation pipeline layout · GraphWriter is the
        only node that writes map/. SketchWriter is a sibling on the same
        stream, not an input to GraphWriter.
      </Text>
    </Stack>
  );
}

function StepBody({ step }: { step: StepId }) {
  if (step === "who") {
    return (
      <Stack gap={12}>
        <Callout tone="info">
          GraphWriter is an orchestrator, not a network service. It is called
          by the lab CLI (or a future Topology writer). It reads seed +
          ingest, writes Dest map/, and optionally runs the E5 maintain stub.
        </Callout>
        <Table
          headers={["Partner", "Role", "What is exchanged"]}
          rows={PARTNER_ROWS.map((r) => [r.partner, r.role, r.exchange])}
          rowTone={PARTNER_ROWS.map((r) =>
            r.partner.includes("GraphWriter") || r.partner.includes("Dest")
              ? "info"
              : undefined,
          )}
        />
      </Stack>
    );
  }

  if (step === "pipeline") {
    return (
      <Stack gap={12}>
        <H3>Where GraphWriter sits</H3>
        <PipelineDag />
        <Grid columns={3} gap={12}>
          <Stat value="E3" label="ObserveOps stage (Topology)" />
          <Stat value="map/" label="Only room GraphWriter writes" tone="info" />
          <Stat value="Parallel" label="With Pillar A after Identity" />
        </Grid>
        <Text tone="secondary" size="small">
          Normative I/O: E2_INPUT_FIXTURES.md (input) · MAP_WRITE_READ_RECORD.md
          (output) · IDENTIFIED_STREAM_REJECT.md (drop codes).
        </Text>
      </Stack>
    );
  }

  if (step === "example") {
    return (
      <Stack gap={12}>
        <Callout tone="neutral">
          Lab fixture line from
          pillar-b/poc/fixtures/lab_checkout/stream.resolved.jsonl — Service
          checkout-api runs_on Host linux-server-app-01.
        </Callout>
        <Grid columns={2} gap={12}>
          <Card>
            <CardHeader>Input · one ingest.v1 line</CardHeader>
            <CardBody>
              <Code>{EXAMPLE_LINE}</Code>
            </CardBody>
          </Card>
          <Card>
            <CardHeader>Output · one graph_edge.v1</CardHeader>
            <CardBody>
              <Code>{EXAMPLE_EDGE}</Code>
            </CardBody>
          </Card>
        </Grid>
        <H3>What happens inside apply_topo_updates</H3>
        <Table
          headers={["Check", "This line", "Result"]}
          rows={[
            ["signal_class", "topo_update", "Not skipped"],
            ["identity.status", "resolved", "Gate admits"],
            ["ci_type", "Service", "May emit vertex"],
            ["relation", "runs_on", "Wave-1 catalog · upsert edge"],
            ["Endpoints", "checkout-api → linux-server-app-01", "Ensure both nodes exist"],
            ["edge_id", "e_checkout-api_runs_on_linux-server-app-01", "Stable replace key"],
          ]}
        />
      </Stack>
    );
  }

  if (step === "admit") {
    return (
      <Stack gap={12}>
        <Text>
          Three outcomes matter: admit (mutate GraphState), silent skip
          (wrong signal for this writer), reject (recorded on
          writer.rejects with a shared reason code).
        </Text>
        <Table
          headers={["Case", "signal_class", "identity", "relation", "Outcome"]}
          rows={ADMIT_ROWS.map((r) => [
            r.case,
            r.signal,
            r.identity,
            r.relation,
            r.outcome,
          ])}
          rowTone={ADMIT_ROWS.map((r) => r.tone)}
        />
        <Text tone="secondary" size="small">
          Reason codes are locked in contracts/IDENTIFIED_STREAM_REJECT.md so
          Pillar A and Pillar B do not invent private drop vocabularies.
        </Text>
      </Stack>
    );
  }

  if (step === "build") {
    return (
      <Stack gap={12}>
        <Table
          headers={["Order", "GraphWriter API", "What it does"]}
          rows={BUILD_STEPS.map((s) => [s.step, s.api, s.does])}
        />
        <Card>
          <CardHeader>Internal helpers (not separate services)</CardHeader>
          <CardBody>
            <Text size="small">
              graph_builder.apply_topo_updates · ci_qualify.may_emit_vertex ·
              edge_catalog.classify_relation · provenance.build_discovered_via ·
              snapshot.build_snapshot / publish_snapshot · maintain.maintain_graph_validity
            </Text>
          </CardBody>
        </Card>
      </Stack>
    );
  }

  if (step === "output") {
    return (
      <Stack gap={12}>
        <H3>poc/out/&lt;tenant&gt;/map/</H3>
        <Table
          headers={["Dest key", "Schema", "Meaning"]}
          rows={OUTPUT_ROWS.map((r) => [r.key, r.schema, r.meaning])}
        />
        <Grid columns={3} gap={12}>
          <Stat value="(tenant, ci_id)" label="Node logical key" />
          <Stat value="(tenant, edge_id)" label="Edge logical key" />
          <Stat value="(tenant, version)" label="Snapshot generation" />
        </Grid>
        <Callout tone="warning">
          GraphWriter never writes history/sketches.jsonl. Computed blast-radius
          style edges from product briefs are not map rows — readers derive those
          later.
        </Callout>
      </Stack>
    );
  }

  // lab
  return (
    <Stack gap={12}>
      <Code>
        {`cd pillar-ab-implementation/pillar-b/poc
make install && make flush
# → poc/out/default/map/{graph_snapshot.json,nodes.jsonl,edges.jsonl}`}
      </Code>
      <Grid columns={2} gap={12}>
        <Card>
          <CardHeader>Seed vertices (topology.seed.json)</CardHeader>
          <CardBody>
            <Stack gap={4}>
              {LAB_SEED_NODES.map((n) => (
                <span key={n}>
                  <Text size="small">{n}</Text>
                </span>
              ))}
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader>Relations the lab emits</CardHeader>
          <CardBody>
            <Table
              headers={["from", "relation", "to"]}
              rows={LAB_EDGES.map((e) => [e.from, e.relation, e.to])}
            />
          </CardBody>
        </Card>
      </Grid>
      <Text tone="secondary" size="small">
        CLI path: GraphWriter.load_seed → ingest(stream.resolved.jsonl) →
        FileDest.flush. Same five relations appear both in seed and stream so
        the lab round-trips a small estate map.
      </Text>
    </Stack>
  );
}

export default function GraphWriterIoWalkthrough() {
  const [step, setStep] = useCanvasState<StepId>("step", "who");
  const idx = STEPS.findIndex((s) => s.id === step);
  const meta = STEPS[idx] ?? STEPS[0];

  return (
    <Stack gap={16} style={{ padding: 16, maxWidth: 980 }}>
      <Stack gap={6}>
        <H1>GraphWriter — who it talks to, and a concrete example</H1>
        <Text tone="secondary" size="small">
          Pillar B Topology orchestrator under pillar-ab-implementation/pillar-b/poc.
          Input: post-E2 ingest.v1 topo_update (+ optional seed). Output: Gate B
          files.v1 under map/. OneOps/Fusion HTML briefs are catalog reference only
          — they are not GraphWriter callers.
        </Text>
      </Stack>

      <Row gap={8} style={{ flexWrap: "wrap" }}>
        {STEPS.map((s) => (
          <span key={s.id}>
            <Pill
              active={s.id === step}
              tone={s.id === step ? "info" : "neutral"}
              onClick={() => setStep(s.id)}
            >
              {s.label}
            </Pill>
          </span>
        ))}
      </Row>

      <Stack gap={4}>
        <H2>{meta.label}</H2>
        <Text tone="secondary">{meta.blurb}</Text>
      </Stack>

      <Divider />

      <StepBody step={step} />

      <Row gap={8} justify="space-between">
        <Pill
          tone="neutral"
          onClick={() => idx > 0 && setStep(STEPS[idx - 1].id)}
        >
          Previous
        </Pill>
        <Text tone="secondary" size="small">
          {idx + 1} / {STEPS.length}
        </Text>
        <Pill
          tone="info"
          onClick={() =>
            idx < STEPS.length - 1 && setStep(STEPS[idx + 1].id)
          }
        >
          Next
        </Pill>
      </Row>
    </Stack>
  );
}
