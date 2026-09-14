/** Server-side base URL of the FastAPI service. Browser calls go through Next route handlers later. */
export const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

export type ReadyResponse = {
  status: "ready" | "degraded";
  search: boolean;
  providers: Record<string, string>;
};

export async function fetchReady(): Promise<ReadyResponse | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/ready`, { cache: "no-store" });
    if (!res.ok && res.status !== 503) return null;
    return (await res.json()) as ReadyResponse;
  } catch {
    return null;
  }
}
