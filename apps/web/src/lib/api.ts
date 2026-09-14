"use client";

import type {
  AnswerResponse,
  AskRequest,
  CatalogueStats,
  DocumentDetail,
  DocumentSummary,
  Principal,
  ReadyResponse,
  ReportSummary,
  RequestRecord,
  SearchResponse,
  SystemSummary,
} from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const TOKEN_KEY = "cloudops.token";

export class ApiError extends Error {
  constructor(
    public status: number,
    public title: string,
    public detail: string,
    public requestId?: string,
  ) {
    super(`${status} ${title}: ${detail}`);
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}
export function setToken(t: string | null) {
  try {
    if (t) localStorage.setItem(TOKEN_KEY, t);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable */
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    let title = res.statusText;
    let detail = "";
    let requestId: string | undefined;
    try {
      const p = await res.json();
      title = p.title ?? title;
      detail = p.detail ?? JSON.stringify(p);
      requestId = p.request_id;
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(res.status, title, detail, requestId);
  }
  return (await res.json()) as T;
}

export const api = {
  login: (username: string, password: string) =>
    request<{ access_token: string; expires_in: number; roles: string[] }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  me: () => request<Principal>("/auth/me"),
  ready: () => request<ReadyResponse>("/ready"),
  ask: (body: AskRequest) =>
    request<AnswerResponse>("/ask", { method: "POST", body: JSON.stringify(body) }),
  search: (query: string, k = 10, extra: Partial<AskRequest> = {}) =>
    request<SearchResponse>("/search", {
      method: "POST",
      body: JSON.stringify({ query, k, ...extra }),
    }),
  documents: (params: Record<string, string | number | undefined> = {}) => {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") q.set(k, String(v));
    const qs = q.toString();
    return request<DocumentSummary[]>(`/documents${qs ? `?${qs}` : ""}`);
  },
  document: (id: string) => request<DocumentDetail>(`/documents/${encodeURIComponent(id)}`),
  documentStats: () => request<CatalogueStats>("/documents/stats"),
  reports: () => request<ReportSummary[]>("/evaluation/reports"),
  systemSummary: () => request<SystemSummary>("/system/summary"),
  systemRequests: (n = 50) => request<RequestRecord[]>(`/system/requests?n=${n}`),
};

/** Server-sent events from POST /ask/stream. */
export type StreamEvent =
  | { event: "retrieval"; trail: AnswerResponse["trail"]; sources: AnswerResponse["sources"]; conflicts: AnswerResponse["conflicts"]; query_plan: AnswerResponse["query_plan"] }
  | { event: "delta"; text: string }
  | { event: "done"; response: AnswerResponse };

export async function* askStream(body: AskRequest, signal?: AbortSignal): AsyncGenerator<StreamEvent> {
  const headers = new Headers({ "Content-Type": "application/json", Accept: "text/event-stream" });
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API_BASE_URL}/ask/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    let detail = res.statusText;
    try {
      const p = await res.json();
      detail = p.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, "stream failed", detail);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const frame = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const data = frame
        .split("\n")
        .filter((l) => l.startsWith("data: "))
        .map((l) => l.slice(6))
        .join("\n");
      if (data) yield JSON.parse(data) as StreamEvent;
    }
  }
}
