export const fmtMs = (ms: number | undefined | null) =>
  ms == null ? "—" : ms >= 1000 ? `${(ms / 1000).toFixed(2)}s` : `${Math.round(ms)}ms`;
export const fmtUsd = (usd: number | undefined | null, digits = 4) =>
  usd == null ? "—" : `$${usd.toFixed(digits)}`;
export const fmtPct = (x: number | null | undefined, digits = 1) =>
  x == null ? "—" : `${(x * 100).toFixed(digits)}%`;
export const fmtNum = (x: number | null | undefined, digits = 3) =>
  x == null ? "—" : x.toFixed(digits);
export const fmtDate = (iso: string) => {
  try {
    return new Date(iso).toISOString().slice(0, 10);
  } catch {
    return iso;
  }
};
export const stageLabel: Record<string, string> = {
  embed_query: "Embed",
  vector_search: "Vector",
  bm25_search: "BM25",
  fusion: "Fusion",
  rerank: "Rerank",
  select_top_k: "Top-k",
  parent_expansion: "Context",
  merge_subqueries: "Merge",
};
