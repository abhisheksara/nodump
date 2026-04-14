const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface FeedItem {
  id: string;
  title: string;
  summary: string;
  why_it_matters: string;
  source: string;
  url: string;
  author: string;
  published_at: string;
  relevance_score: number;
  user_feedback: "up" | "down" | null;
}

export interface ChatResponse {
  response: string;
}

export async function getFeed(params?: {
  user_id?: string;
  source?: string;
  days?: number;
}): Promise<FeedItem[]> {
  const qs = new URLSearchParams();
  if (params?.user_id) qs.set("user_id", params.user_id);
  if (params?.source) qs.set("source", params.source);
  if (params?.days) qs.set("days", String(params.days));
  const res = await fetch(`${BASE}/feed/?${qs}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch feed");
  return res.json();
}

export async function submitFeedback(
  item_id: string,
  feedback: "up" | "down",
  user_id = "default"
): Promise<void> {
  await fetch(`${BASE}/feedback/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id, item_id, feedback }),
  });
}

export async function removeFeedback(item_id: string, user_id = "default"): Promise<void> {
  await fetch(`${BASE}/feedback/?user_id=${user_id}&item_id=${item_id}`, {
    method: "DELETE",
  });
}

export async function chat(message: string, days = 7): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, days }),
  });
  if (!res.ok) throw new Error("Chat request failed");
  return res.json();
}

export async function triggerRefresh(): Promise<{ stored: number }> {
  const res = await fetch(`${BASE}/feed/refresh`, { method: "POST" });
  if (!res.ok) throw new Error("Refresh failed");
  return res.json();
}
