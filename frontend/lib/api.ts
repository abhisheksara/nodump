import type { Source, Story } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  queue: (domain?: string) => {
    const qs = domain ? `?domain=${domain}` : "";
    return request<Story[]>(`/queue/${qs}`);
  },
  markRead: (id: string) =>
    request(`/stories/${id}/read`, { method: "POST" }),
  markSkip: (id: string) =>
    request(`/stories/${id}/skip`, { method: "POST" }),
  markSave: (id: string) =>
    request(`/stories/${id}/save`, { method: "POST" }),
  saved: () => request<Story[]>("/stories/saved"),
  history: (q?: string) => {
    const qs = q ? `?q=${encodeURIComponent(q)}` : "";
    return request<Story[]>(`/stories/history${qs}`);
  },
  sources: () => request<Source[]>("/sources/"),
  toggleSource: (id: number, active: boolean) =>
    request<Source>(`/sources/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active }),
    }),
  refresh: () => request("/refresh", { method: "POST" }),
};
