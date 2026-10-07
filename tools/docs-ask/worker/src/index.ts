/**
 * Unified-RCA documentation Q&A — retrieval + optional Workers AI synthesis.
 * Index: /docs-index.json (built by tools/docs-ask/index/build_index.py)
 */

export interface Env {
  AI: Ai;
  ASSETS: Fetcher;
  DOCS_ASK_TOKEN?: string;
}

interface IndexChunk {
  id: string;
  path: string;
  title: string;
  heading: string;
  start_line: number;
  text: string;
  cite_url: string;
}

interface DocsIndex {
  meta: { chunk_count: number; generated_at: string };
  chunks: IndexChunk[];
}

let indexCache: { at: number; data: DocsIndex } | null = null;
const INDEX_TTL_MS = 5 * 60 * 1000;

function tokenize(q: string): string[] {
  return q
    .toLowerCase()
    .replace(/[^\w\s-]/g, " ")
    .split(/\s+/)
    .filter((t) => t.length > 2);
}

function scoreChunk(chunk: IndexChunk, terms: string[]): number {
  if (terms.length === 0) return 0;
  const hay = `${chunk.title} ${chunk.heading} ${chunk.path} ${chunk.text}`.toLowerCase();
  let score = 0;
  for (const t of terms) {
    const re = new RegExp(t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g");
    const hits = hay.match(re);
    if (hits) score += hits.length;
    if (chunk.title.toLowerCase().includes(t)) score += 4;
    if (chunk.path.toLowerCase().includes(t)) score += 2;
  }
  return score;
}

async function loadIndex(env: Env, url: URL): Promise<DocsIndex> {
  const now = Date.now();
  if (indexCache && now - indexCache.at < INDEX_TTL_MS) {
    return indexCache.data;
  }
  // Prefer gzipped index (smaller Worker asset); fall back to plain JSON.
  const gzUrl = new URL("/docs-index.json.gz", url.origin);
  let res = await env.ASSETS.fetch(gzUrl);
  let data: DocsIndex;
  if (res.ok) {
    const ds = new DecompressionStream("gzip");
    const stream = res.body!.pipeThrough(ds);
    const text = await new Response(stream).text();
    data = JSON.parse(text) as DocsIndex;
  } else {
    const indexUrl = new URL("/docs-index.json", url.origin);
    res = await env.ASSETS.fetch(indexUrl);
    if (!res.ok) {
      throw new Error(`Index missing (${res.status}). Run build_index.py before deploy.`);
    }
    data = (await res.json()) as DocsIndex;
  }
  indexCache = { at: now, data };
  return data;
}

function retrieve(index: DocsIndex, query: string, k: number): IndexChunk[] {
  const terms = tokenize(query);
  const scored = index.chunks
    .map((c) => ({ c, s: scoreChunk(c, terms) }))
    .filter((x) => x.s > 0)
    .sort((a, b) => b.s - a.s);
  if (scored.length === 0 && terms.length > 0) {
    // fallback: any term partial match
    const partial = index.chunks
      .map((c) => {
        const hay = `${c.text}`.toLowerCase();
        let s = 0;
        for (const t of terms) if (hay.includes(t)) s += 1;
        return { c, s };
      })
      .filter((x) => x.s > 0)
      .sort((a, b) => b.s - a.s);
    return partial.slice(0, k).map((x) => x.c);
  }
  return scored.slice(0, k).map((x) => x.c);
}

function unauthorized(): Response {
  return new Response(JSON.stringify({ error: "Unauthorized" }), {
    status: 401,
    headers: { "Content-Type": "application/json" },
  });
}

function checkAuth(request: Request, env: Env): boolean {
  const required = env.DOCS_ASK_TOKEN?.trim();
  if (!required) return true;
  const header = request.headers.get("X-Docs-Ask-Token");
  const url = new URL(request.url);
  const q = url.searchParams.get("token");
  return header === required || q === required;
}

async function handleSearch(request: Request, env: Env): Promise<Response> {
  if (!checkAuth(request, env)) return unauthorized();
  const url = new URL(request.url);
  const q = url.searchParams.get("q")?.trim() ?? "";
  const k = Math.min(20, Math.max(1, parseInt(url.searchParams.get("k") ?? "8", 10) || 8));
  if (!q) {
    return Response.json({ error: "Missing q" }, { status: 400 });
  }
  const index = await loadIndex(env, url);
  const hits = retrieve(index, q, k).map((c, i) => ({
    rank: i + 1,
    id: c.id,
    path: c.path,
    title: c.title,
    heading: c.heading,
    start_line: c.start_line,
    cite_url: c.cite_url,
    snippet: c.text.slice(0, 400) + (c.text.length > 400 ? "…" : ""),
  }));
  return Response.json({ query: q, hits, index_generated_at: index.meta.generated_at });
}

async function handleAsk(request: Request, env: Env): Promise<Response> {
  if (!checkAuth(request, env)) return unauthorized();
  let body: { question?: string; k?: number };
  try {
    body = (await request.json()) as { question?: string; k?: number };
  } catch {
    return Response.json({ error: "Invalid JSON body" }, { status: 400 });
  }
  const question = body.question?.trim();
  if (!question) {
    return Response.json({ error: "Missing question" }, { status: 400 });
  }
  const k = Math.min(12, Math.max(3, body.k ?? 8));
  const url = new URL(request.url);
  const index = await loadIndex(env, url);
  const chunks = retrieve(index, question, k);

  if (chunks.length === 0) {
    return Response.json({
      question,
      answer:
        "I could not find matching passages in the indexed documentation. Try different keywords or check that the index was rebuilt after your last doc push.",
      citations: [],
    });
  }

  const contextBlocks = chunks
    .map(
      (c, i) =>
        `[${i + 1}] ${c.title} — ${c.heading}\npath: ${c.path}\ncite: ${c.cite_url}\n---\n${c.text.slice(0, 1800)}`,
    )
    .join("\n\n");

  const system = `You answer questions about the Unified-RCA / ObserveOps / Motadata documentation.
Use ONLY the provided sources. If the sources do not contain enough information, say so clearly.
Every factual claim must cite one or more sources using [1], [2], etc. matching the numbered blocks.
At the end, list "Sources" as markdown links using the cite URLs from the blocks.`;

  const prompt = `${system}\n\nSources:\n${contextBlocks}\n\nQuestion: ${question}\n\nAnswer:`;

  let answer: string;
  try {
    const result = await env.AI.run("@cf/meta/llama-3.1-8b-instruct", {
      messages: [{ role: "user", content: prompt }],
      max_tokens: 1024,
    });
    const msg = result as { response?: string };
    answer = msg.response?.trim() ?? "No response from model.";
  } catch (e) {
    // Retrieval-only fallback when AI unavailable
    answer =
      "Workers AI is unavailable in this environment. Here are the most relevant passages:\n\n" +
      chunks
        .map(
          (c, i) =>
            `**[${i + 1}] ${c.title}** (${c.path})\n${c.text.slice(0, 500)}…\n→ ${c.cite_url}`,
        )
        .join("\n\n");
  }

  const citations = chunks.map((c, i) => ({
    n: i + 1,
    path: c.path,
    title: c.title,
    heading: c.heading,
    cite_url: c.cite_url,
  }));

  return Response.json({
    question,
    answer,
    citations,
    index_generated_at: index.meta.generated_at,
  });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/api/health") {
      return Response.json({ ok: true, service: "unified-rca-docs-ask" });
    }
    if (url.pathname === "/api/search" && request.method === "GET") {
      return handleSearch(request, env);
    }
    if (url.pathname === "/api/ask" && request.method === "POST") {
      return handleAsk(request, env);
    }

    return env.ASSETS.fetch(request);
  },
};
