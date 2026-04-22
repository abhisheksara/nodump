"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type {
  AdminStats,
  NudgeLogEntry,
  RunEntry,
  RunFile,
  SchedulerJob,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type TriggerKey = "all" | "arxiv" | "hackernews" | "nudge";
type TriggerStatus = "idle" | "loading" | "done" | "error";

interface TriggerState {
  status: TriggerStatus;
  message: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const SUB_DOMAIN_LABELS: Record<string, string> = {
  llms: "LLMs",
  agents: "Agents",
  applied_ml: "Applied ML",
  infra_inference: "Infra/Inference",
  other: "Other",
  none: "Unclassified",
};

const RELEVANCE_COLORS: Record<string, string> = {
  high: "text-emerald-400",
  medium: "text-amber-400",
  ignore: "text-zinc-500",
  none: "text-zinc-600",
};

const ACTION_COLORS: Record<string, string> = {
  stored: "text-emerald-400",
  dropped_ignore: "text-zinc-500",
  skipped_duplicate: "text-zinc-600",
  triage_failed: "text-red-400",
  enrich_failed: "text-red-400",
  store_failed: "text-red-400",
};

function fmt(n: number) {
  return n.toLocaleString();
}

function fmtDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function fmtSize(bytes: number) {
  if (bytes < 1024) return `${bytes}B`;
  return `${(bytes / 1024).toFixed(1)}KB`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: number | string;
  accent?: string;
}) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-zinc-800 bg-zinc-900 px-5 py-4">
      <span className="text-xs font-medium uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <span className={`text-2xl font-semibold tabular-nums ${accent ?? "text-zinc-100"}`}>
        {typeof value === "number" ? fmt(value) : value}
      </span>
    </div>
  );
}

function BreakdownRow({
  label,
  value,
  max,
  colorClass,
}: {
  label: string;
  value: number;
  max: number;
  colorClass?: string;
}) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="w-32 shrink-0 text-xs text-zinc-400 truncate">{label}</span>
      <div className="relative flex-1 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
        <div
          className={`absolute inset-y-0 left-0 rounded-full transition-all duration-500 ${colorClass ?? "bg-zinc-500"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-8 text-right text-xs tabular-nums text-zinc-400">{fmt(value)}</span>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-xs font-medium uppercase tracking-widest text-zinc-500">{title}</h2>
      {children}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Trigger button
// ---------------------------------------------------------------------------

function TriggerButton({
  label,
  state,
  onClick,
}: {
  label: string;
  state: TriggerState;
  onClick: () => void;
}) {
  const isLoading = state.status === "loading";
  const isDone = state.status === "done";
  const isError = state.status === "error";

  return (
    <button
      onClick={onClick}
      disabled={isLoading}
      className={`flex flex-col gap-1 rounded-xl border px-5 py-4 text-left transition-colors disabled:opacity-60 ${
        isError
          ? "border-red-800 bg-red-950/30"
          : isDone
          ? "border-emerald-800 bg-emerald-950/30"
          : "border-zinc-800 bg-zinc-900 hover:border-zinc-700 hover:bg-zinc-800/60"
      }`}
    >
      <div className="flex items-center gap-2">
        {isLoading && (
          <span className="inline-block h-3 w-3 rounded-full border-2 border-zinc-600 border-t-zinc-300 animate-spin" />
        )}
        {isDone && <span className="text-emerald-400">✓</span>}
        {isError && <span className="text-red-400">✗</span>}
        <span className="text-sm font-medium text-zinc-200">{label}</span>
      </div>
      {state.message && (
        <span
          className={`text-xs ${isError ? "text-red-400" : "text-zinc-400"}`}
        >
          {state.message}
        </span>
      )}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Run log row (expandable)
// ---------------------------------------------------------------------------

function RunRow({ file }: { file: RunFile }) {
  const [open, setOpen] = useState(false);
  const [entries, setEntries] = useState<RunEntry[] | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (entries !== null) return;
    setLoading(true);
    try {
      const data = await api.adminRunDetail(file.filename);
      setEntries(data);
    } finally {
      setLoading(false);
    }
  }, [file.filename, entries]);

  const toggle = () => {
    if (!open) load();
    setOpen((v) => !v);
  };

  const stats =
    entries &&
    entries.reduce(
      (acc, e) => {
        const a = e.action ?? "unknown";
        acc[a] = (acc[a] ?? 0) + 1;
        return acc;
      },
      {} as Record<string, number>,
    );

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 overflow-hidden">
      <button
        onClick={toggle}
        className="flex w-full items-center justify-between px-5 py-3 text-left hover:bg-zinc-800/40 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs text-zinc-300">{file.timestamp}</span>
          <span className="text-xs text-zinc-600">{fmtSize(file.size_bytes)}</span>
        </div>
        <span className="text-xs text-zinc-600">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="border-t border-zinc-800 px-5 py-4 flex flex-col gap-4">
          {loading && (
            <div className="h-8 rounded-lg bg-zinc-800 animate-pulse" />
          )}
          {stats && (
            <div className="flex flex-wrap gap-3">
              {Object.entries(stats).map(([action, count]) => (
                <span
                  key={action}
                  className={`inline-flex items-center gap-1 text-xs ${ACTION_COLORS[action] ?? "text-zinc-400"}`}
                >
                  <span className="font-mono">{count}</span>
                  <span>{action.replace(/_/g, " ")}</span>
                </span>
              ))}
            </div>
          )}
          {entries && entries.length > 0 && (
            <div className="flex flex-col gap-1 max-h-64 overflow-y-auto">
              {entries.map((e, i) => (
                <div
                  key={i}
                  className="grid grid-cols-[6rem_1fr_5rem] gap-2 text-xs items-start py-1 border-b border-zinc-800/50 last:border-0"
                >
                  <span className={`${ACTION_COLORS[e.action ?? ""] ?? "text-zinc-400"} shrink-0`}>
                    {e.action?.replace(/_/g, " ")}
                  </span>
                  <span className="text-zinc-400 truncate">{e.title ?? "—"}</span>
                  <span className="text-zinc-600 text-right shrink-0">
                    {e.relevance_label ?? e.triage_label ?? "—"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [scheduler, setScheduler] = useState<SchedulerJob[]>([]);
  const [runs, setRuns] = useState<RunFile[]>([]);
  const [nudgeLogs, setNudgeLogs] = useState<NudgeLogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const [triggers, setTriggers] = useState<Record<TriggerKey, TriggerState>>({
    all: { status: "idle", message: "" },
    arxiv: { status: "idle", message: "" },
    hackernews: { status: "idle", message: "" },
    nudge: { status: "idle", message: "" },
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, sched, r, nl] = await Promise.all([
        api.adminStats(),
        api.adminScheduler(),
        api.adminRuns(),
        api.adminNudgeLogs(),
      ]);
      setStats(s);
      setScheduler(sched);
      setRuns(r);
      setNudgeLogs(nl);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const trigger = async (key: TriggerKey) => {
    setTriggers((prev) => ({
      ...prev,
      [key]: { status: "loading", message: "Starting…" },
    }));
    try {
      if (key === "all") await api.adminTriggerAll();
      else if (key === "nudge") await api.adminTriggerNudge();
      else await api.adminTriggerSource(key);
      setTriggers((prev) => ({
        ...prev,
        [key]: { status: "done", message: "Running in background" },
      }));
    } catch (e) {
      setTriggers((prev) => ({
        ...prev,
        [key]: { status: "error", message: "Failed to start" },
      }));
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <div className="h-8 w-32 rounded-lg bg-zinc-800 animate-pulse" />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-20 rounded-xl bg-zinc-900 animate-pulse" />
          ))}
        </div>
        <div className="h-40 rounded-xl bg-zinc-900 animate-pulse" />
      </div>
    );
  }

  const relMax = Math.max(...Object.values(stats?.by_relevance ?? {}), 1);
  const domMax = Math.max(...Object.values(stats?.by_sub_domain ?? {}), 1);
  const srcMax = Math.max(...Object.values(stats?.by_source ?? {}), 1);

  return (
    <div className="flex flex-col gap-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-zinc-100">Admin</h1>
          <p className="text-sm text-zinc-500 mt-0.5">Pipeline control &amp; system status</p>
        </div>
        <button
          onClick={load}
          className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors px-3 py-1.5 rounded-lg border border-zinc-800 hover:border-zinc-700"
        >
          Refresh
        </button>
      </div>

      {/* Stats */}
      <Section title="Overview">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard label="Total Stories" value={stats?.total_stories ?? 0} />
          <StatCard
            label="Unread High"
            value={stats?.unread_high ?? 0}
            accent="text-emerald-400"
          />
          <StatCard label="Added (24h)" value={stats?.stories_last_24h ?? 0} />
          <StatCard label="Added (7d)" value={stats?.stories_last_7d ?? 0} />
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard label="Read" value={stats?.user_states?.read ?? 0} />
          <StatCard label="Saved" value={stats?.user_states?.saved ?? 0} />
          <StatCard label="Skipped" value={stats?.user_states?.skipped ?? 0} />
          <StatCard
            label="Nudges Sent"
            value={nudgeLogs.length}
          />
        </div>
      </Section>

      {/* Breakdowns */}
      <Section title="Breakdown">
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 px-5 py-4 flex flex-col gap-3">
            <span className="text-xs font-medium uppercase tracking-widest text-zinc-500">
              Relevance
            </span>
            <div className="flex flex-col gap-2">
              {Object.entries(stats?.by_relevance ?? {})
                .sort((a, b) => b[1] - a[1])
                .map(([label, count]) => (
                  <BreakdownRow
                    key={label}
                    label={label}
                    value={count}
                    max={relMax}
                    colorClass={
                      label === "high"
                        ? "bg-emerald-500"
                        : label === "medium"
                        ? "bg-amber-500"
                        : "bg-zinc-600"
                    }
                  />
                ))}
              {!stats?.by_relevance ||
                (Object.keys(stats.by_relevance).length === 0 && (
                  <span className="text-xs text-zinc-600">No data</span>
                ))}
            </div>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-900 px-5 py-4 flex flex-col gap-3">
            <span className="text-xs font-medium uppercase tracking-widest text-zinc-500">
              Sub-domain
            </span>
            <div className="flex flex-col gap-2">
              {Object.entries(stats?.by_sub_domain ?? {})
                .sort((a, b) => b[1] - a[1])
                .map(([d, count]) => (
                  <BreakdownRow
                    key={d}
                    label={SUB_DOMAIN_LABELS[d] ?? d}
                    value={count}
                    max={domMax}
                    colorClass="bg-sky-600"
                  />
                ))}
              {!stats?.by_sub_domain ||
                (Object.keys(stats.by_sub_domain).length === 0 && (
                  <span className="text-xs text-zinc-600">No data</span>
                ))}
            </div>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-900 px-5 py-4 flex flex-col gap-3">
            <span className="text-xs font-medium uppercase tracking-widest text-zinc-500">
              Source
            </span>
            <div className="flex flex-col gap-2">
              {Object.entries(stats?.by_source ?? {})
                .sort((a, b) => b[1] - a[1])
                .map(([src, count]) => (
                  <BreakdownRow
                    key={src}
                    label={src}
                    value={count}
                    max={srcMax}
                    colorClass="bg-violet-600"
                  />
                ))}
              {!stats?.by_source ||
                (Object.keys(stats.by_source).length === 0 && (
                  <span className="text-xs text-zinc-600">No data</span>
                ))}
            </div>
          </div>
        </div>
      </Section>

      {/* Scheduler */}
      <Section title="Scheduler">
        {scheduler.length === 0 ? (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 px-5 py-4">
            <span className="text-sm text-zinc-500">Scheduler not running</span>
          </div>
        ) : (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 overflow-hidden">
            {scheduler.map((job, i) => (
              <div
                key={job.id}
                className={`flex items-center justify-between px-5 py-3 ${
                  i < scheduler.length - 1 ? "border-b border-zinc-800" : ""
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  <span className="text-sm font-medium text-zinc-200 font-mono">{job.id}</span>
                </div>
                <div className="text-right">
                  <div className="text-xs text-zinc-400">
                    Next: {fmtDate(job.next_run_time)}
                  </div>
                  <div className="text-xs text-zinc-600 truncate max-w-48">{job.trigger}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* Triggers */}
      <Section title="Pipeline Controls">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <TriggerButton
            label="Run All Sources"
            state={triggers.all}
            onClick={() => trigger("all")}
          />
          <TriggerButton
            label="Run arXiv"
            state={triggers.arxiv}
            onClick={() => trigger("arxiv")}
          />
          <TriggerButton
            label="Run HackerNews"
            state={triggers.hackernews}
            onClick={() => trigger("hackernews")}
          />
          <TriggerButton
            label="Send Nudge"
            state={triggers.nudge}
            onClick={() => trigger("nudge")}
          />
        </div>
        <p className="text-xs text-zinc-600">
          Triggers run in the background — check run logs below for results.
        </p>
      </Section>

      {/* Run logs */}
      <Section title={`Recent Runs (${runs.length})`}>
        {runs.length === 0 ? (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 px-5 py-4">
            <span className="text-sm text-zinc-500">No runs yet</span>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {runs.map((f) => (
              <RunRow key={f.filename} file={f} />
            ))}
          </div>
        )}
      </Section>

      {/* Nudge history */}
      <Section title="Nudge History">
        {nudgeLogs.length === 0 ? (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 px-5 py-4">
            <span className="text-sm text-zinc-500">No nudges sent yet</span>
          </div>
        ) : (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 overflow-hidden">
            {nudgeLogs.map((log, i) => (
              <div
                key={log.id}
                className={`flex items-center justify-between px-5 py-3 ${
                  i < nudgeLogs.length - 1 ? "border-b border-zinc-800" : ""
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-sm text-zinc-300">{fmtDate(log.sent_at)}</span>
                </div>
                <span className="text-xs text-zinc-400">
                  {log.stories_count} stor{log.stories_count === 1 ? "y" : "ies"} sent
                </span>
              </div>
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}
