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
