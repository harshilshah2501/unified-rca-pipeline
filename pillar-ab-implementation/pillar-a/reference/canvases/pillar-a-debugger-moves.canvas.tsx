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
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useCanvasState,
} from "cursor/canvas";

type MoveId = "how" | "m1" | "m2" | "m3";

const MOVES: { id: MoveId; label: string; blurb: string }[] = [
  { id: "how", label: "How to use", blurb: "Open this canvas beside chat" },
  { id: "m1", label: "Move 1 · Accumulate", blurb: "Three latencies in one 5m window" },
  { id: "m2", label: "Move 2 · Rejects", blurb: "stream.reject.jsonl outcomes" },
  { id: "m3", label: "Move 3 · Detect fire", blurb: "Prior season vs spike window" },
];

/** Observed 2026-08-27 from SketchWriter debugger session */
const M1_STEPS = [
  {
    label: "Sample step 1",
    added: "92.1 ms",
    running: "{92.1}",
    n: "1",
    p50: "92.1",
    p95: "92.1",
    buckets: "[0,1,0,0,0,0]",
    bucketNote: "One sample in [50, 100).",
  },
  {
    label: "Sample step 2",
    added: "+ 145.3 ms",
    running: "{92.1, 145.3}",
    n: "2",
    p50: "118.7",
    p95: "145.3",
    buckets: "[0,1,1,0,0,0]",
    bucketNote: "One in [50, 100), one in [100, 200).",
  },
  {
    label: "Sample step 3",
    added: "+ 88.0 ms",
    running: "{92.1, 145.3, 88.0}",
    n: "3",
    p50: "92.1",
    p95: "145.3",
    buckets: "[0,2,1,0,0,0]",
    bucketNote: "Two in [50, 100), one in [100, 200). p95 still 145.3 (tail).",
  },
];

const M2_LINES = [
  ["orphan-metric", "unattributed", "REJECT identity_unresolved"],
  ["synth-host", "synthesized", "REJECT identity_synthesized"],
  ["no-identity", "MISSING", "REJECT identity_unresolved"],
  ["alert-1 topo", "resolved", "SKIP (not metric_sample)"],
  ["CORRELATED_WITH topo", "resolved", "SKIP"],
  ["disk.queue_depth", "resolved", "REJECT unknown_metric_id"],
];

export default function PillarADebuggerMoves() {
  const [move, setMove] = useCanvasState<MoveId>("move", "how");
  const [m1Step, setM1Step] = useCanvasState<number>("m1Step", 0);
  const idx = MOVES.findIndex((m) => m.id === move);
  const meta = MOVES[idx] ?? MOVES[0];

  return (
    <Stack gap={16} style={{ padding: 16, maxWidth: 960 }}>
      <Stack gap={6}>
        <H1>Pillar A debugger — three moves</H1>
        <Text tone="secondary" size="small">
          Live numbers from pillar-ab-implementation/poc SketchWriter (2026-08-27).
          Click a move below. Companion walkthrough canvas covers admit/placement.
        </Text>
      </Stack>

      <Row gap={8} style={{ flexWrap: "wrap" }}>
        {MOVES.map((m) => (
          <span key={m.id}>
            <Pill
              active={m.id === move}
              tone={m.id === move ? "info" : "neutral"}
              onClick={() => setMove(m.id)}
            >
              {m.label}
            </Pill>
          </span>
        ))}
      </Row>

      <Row gap={12} style={{ alignItems: "center", justifyContent: "space-between" }}>
        <Stack gap={2}>
          <H2>{meta.label}</H2>
          <Text tone="secondary" size="small">
            {meta.blurb}
          </Text>
        </Stack>
        <Row gap={8}>
          <Button
            variant="secondary"
            disabled={idx === 0}
            onClick={() => setMove(MOVES[idx - 1].id)}
          >
            Previous
          </Button>
          <Button
            variant="primary"
            disabled={idx === MOVES.length - 1}
            onClick={() => setMove(MOVES[idx + 1].id)}
          >
            Next
          </Button>
        </Row>
      </Row>

      <Divider />

      {move === "how" && <HowPane />}
      {move === "m1" && (
        <Move1Pane step={m1Step} setStep={setM1Step} />
      )}
      {move === "m2" && <Move2Pane />}
      {move === "m3" && <Move3Pane />}
    </Stack>
  );
}

function HowPane() {
  return (
    <Stack gap={14}>
      <Callout tone="info" title="How to open this canvas in Cursor">
        In the chat panel, open the canvas attachment or Canvas panel and select
        pillar-a-debugger-moves. Keep it beside the chat while we step through.
        State (which move / which accumulate step) survives reload.
      </Callout>
      <Table
        headers={["Move", "What you will see", "PoC source"]}
        rows={[
          [
            "1 · Accumulate",
            "p50/p95/buckets after each of 3 lab latencies",
            "stream.resolved.jsonl checkout lines",
          ],
          [
            "2 · Rejects",
            "REJECT vs SKIP vs 0 sketch keys",
            "stream.reject.jsonl",
          ],
          [
            "3 · Detect fire",
            "prior Thu ~90 ms vs spike ~395 ms → would fire",
            "Simulated prior + spike through SketchWriter",
          ],
        ]}
        rowTone={["info", "warning", "success"]}
      />
      <Text size="small" tone="secondary">
        Related: pillar-a-poc-walkthrough canvas (placement, admit one-job, FP
        stages) · docs/PILLAR_A_PERCENTILES_DEEP_DIVE.md · FAQ Q26–Q30 in graph
        contract brief.
      </Text>
    </Stack>
  );
}

function Move1Pane({
  step,
  setStep,
}: {
  step: number;
  setStep: (n: number | ((p: number) => number)) => void;
}) {
  const s = M1_STEPS[Math.min(step, M1_STEPS.length - 1)];
  return (
    <Stack gap={14}>
      <Callout tone="info" title="Sample steps ≠ pipeline stages">
        Buttons 1 / 2 / 3 mean “after adding the next latency into this same 5m
        sketch key” — not Collect / Identity / Topology. “After” = after that
        sample updates digest + buckets in-window. Not after merging digests
        across hosts or days.
      </Callout>
      <Text>
        Key: <Code>checkout-api</Code> · <Code>request.latency_ms</Code> ·{" "}
        <Code>5m</Code> · <Code>Thu-03:00</Code> · <Code>03:30:00Z</Code>
      </Text>
      <Row gap={8} style={{ alignItems: "center", flexWrap: "wrap" }}>
        <Text size="small" weight="semibold">
          Sample step:
        </Text>
        {[0, 1, 2].map((i) => (
          <span key={i}>
            <Pill
              active={step === i}
              tone={step === i ? "info" : "neutral"}
              onClick={() => setStep(i)}
            >
              {i + 1}: {M1_STEPS[i].added}
            </Pill>
          </span>
        ))}
        <Button
          variant="secondary"
          disabled={step >= 2}
          onClick={() => setStep((p) => Math.min(2, p + 1))}
        >
          Add next sample
        </Button>
      </Row>
      <Grid columns={4} gap={12}>
        <Stat value={s.n} label="n in this window" tone="info" />
        <Stat value={s.p50} label="p50 from T-Digest (ms)" />
        <Stat value={s.p95} label="p95 from T-Digest (ms)" tone="info" />
        <Stat value={s.added} label="just added" />
      </Grid>
      <Card>
        <CardHeader>{s.label} — running set {s.running}</CardHeader>
        <CardBody>
          <Stack gap={6}>
            <Text size="small">
              p50 / p95 come from <Code>TDigestAdapter.quantile(0.50 / 0.95)</Code>{" "}
              on the running sample set — not from bucket midpoints. With n=1–3
              the digest is nearly exact on those points.
            </Text>
            <Text size="small">
              Buckets (separate leftover): bounds [0, 50, 100, 200, 500, 1000,
              2000] → counts <Code>{s.buckets}</Code>. {s.bucketNote}
            </Text>
            {step === 2 && (
              <Text size="small" tone="secondary">
                p95 stayed 145.3 at steps 2 and 3 because 145.3 is still the
                slowest sample. Baseline still self-seeds in one flush — no
                Detect fire yet (see Move 3).
              </Text>
            )}
          </Stack>
        </CardBody>
      </Card>
      <Table
        headers={[
          "Sample step",
          "Just added",
          "Running set",
          "n",
          "p50",
          "p95",
          "buckets",
        ]}
        rows={M1_STEPS.map((r) => [
          r.label,
          r.added,
          r.running,
          r.n,
          r.p50,
          r.p95,
          r.buckets,
        ])}
        rowTone={M1_STEPS.map((_, i) => (i === step ? "info" : "neutral"))}
      />
    </Stack>
  );
}

function Move2Pane() {
  return (
    <Stack gap={14}>
      <Row gap={12} style={{ flexWrap: "wrap" }}>
        <Stat value="4" label="rejects recorded" tone="danger" />
        <Stat value="0" label="sketch keys" tone="success" />
        <Stat value="3" label="topo skipped" />
      </Row>
      <Table
        headers={["Line", "identity", "Outcome"]}
        rows={M2_LINES}
        rowTone={["danger", "danger", "danger", "neutral", "neutral", "warning"]}
      />
      <Callout tone="success" title="Teaching">
        Junk never becomes sketch.v1. REJECT goes to SketchWriter.rejects; SKIP
        is silent (None, None) for non-metric_sample — same as FAQ Q28–Q29.
      </Callout>
    </Stack>
  );
}

function Move3Pane() {
  return (
    <Stack gap={14}>
      <Callout tone="warning" title="Why move 1 could not fire Detect">
        One flush self-seeds baseline (expected ≈ current). Fire needs prior
        same season_key history — E5’s job to keep that honest.
      </Callout>
      <Grid columns={2} gap={12}>
        <Card>
          <CardHeader trailing={<Pill tone="neutral">Prior Thu</Pill>}>
            2026-08-13 (simulated history)
          </CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text size="small">Samples 85, 90, 88 ms · n=3</Text>
              <Stat value="~90" label="expected_p95 (self-seed)" />
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Pill tone="warning">Spike Thu</Pill>}>
            2026-08-20 (current)
          </CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text size="small">Samples 380, 410, 395 ms · n=3</Text>
              <Stat value="~395" label="digest p95" tone="danger" />
            </Stack>
          </CardBody>
        </Card>
      </Grid>
      <Card>
        <CardHeader trailing={<Pill tone="info">E6 door C</Pill>}>
          Detect compare
        </CardHeader>
        <CardBody>
          <Stack gap={8}>
            <Text>
              current p95 ≈ <Code>395</Code> vs baseline expected ≈{" "}
              <Code>90</Code> → <strong>would fire</strong> (abnormal for season).
            </Text>
            <Text size="small" tone="secondary">
              Hot-bin buckets [0,0,0,3,0,0] → all three samples in [200, 500) ms.
              Investigate after fire uses that range; optional exemplars not in
              wave-1 writer.
            </Text>
          </Stack>
        </CardBody>
      </Card>
    </Stack>
  );
}
