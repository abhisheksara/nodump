export type RelevanceLabel = "high" | "medium" | "low";
export type SubDomain = "llms" | "agents" | "applied_ml" | "infra_inference" | "other";
export type StoryState = "read" | "skipped" | "saved";

export interface Story {
  id: string;
  source_id: number;
  url: string;
  title: string;
  author: string | null;
  published_at: string | null;
  summary: string | null;
  why_matters: string | null;
  what_to_do: string | null;
  relevance_label: RelevanceLabel | null;
  relevance_score: number | null;
  domain: string | null;
  sub_domain: SubDomain | null;
  processed_at: string | null;
}

export interface Source {
  id: number;
  name: string;
  kind: string;
  active: boolean;
  fetch_interval_mins: number;
  last_fetched_at: string | null;
}

export interface AdminStats {
  total_stories: number;
  stories_last_24h: number;
  stories_last_7d: number;
  by_relevance: Record<string, number>;
  by_sub_domain: Record<string, number>;
  by_source: Record<string, number>;
  user_states: Record<string, number>;
  unread_high: number;
}

export interface SchedulerJob {
  id: string;
  next_run_time: string | null;
  trigger: string;
}

export interface RunFile {
  filename: string;
  timestamp: string;
  size_bytes: number;
}

export interface RunEntry {
  ts: string | null;
  action: string | null;
  title: string | null;
  url: string | null;
  triage_label: string | null;
  relevance_label: string | null;
  relevance_score: number | null;
  sub_domain: string | null;
  error: string | null;
}

export interface NudgeLogEntry {
  id: number;
  sent_at: string;
  stories_count: number;
  top_story_id: string | null;
}
