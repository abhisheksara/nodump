"use client";

import { useState } from "react";
import useSWR from "swr";
import { getFeed, triggerRefresh, type FeedItem } from "@/lib/api";
import FeedItemComponent from "./FeedItem";

const SOURCES = [
  { value: "", label: "All" },
  { value: "arxiv", label: "arXiv" },
  { value: "blog", label: "Blogs" },
];

const DAYS = [
  { value: 1, label: "Today" },
  { value: 3, label: "3 days" },
  { value: 7, label: "Week" },
];

export default function FeedList() {
  const [source, setSource] = useState("");
  const [days, setDays] = useState(3);
  const [refreshing, setRefreshing] = useState(false);

  const { data, error, isLoading, mutate } = useSWR<FeedItem[]>(
    ["feed", source, days],
    () => getFeed({ source: source || undefined, days }),
    { refreshInterval: 0 }
  );

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await triggerRefresh();
      await mutate();
    } finally {
      setRefreshing(false);
    }
  }

  const items = data ?? [];

  return (
    <div>
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="flex gap-1">
          {SOURCES.map((s) => (
            <button
              key={s.value}
              onClick={() => setSource(s.value)}
              className={[
                "px-3 py-1 rounded text-xs border transition-colors",
                source === s.value
                  ? "border-indigo-500 text-indigo-300 bg-indigo-500/10"
                  : "border-zinc-700 text-zinc-500 hover:border-zinc-500",
              ].join(" ")}
            >
              {s.label}
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          {DAYS.map((d) => (
            <button
              key={d.value}
              onClick={() => setDays(d.value)}
              className={[
                "px-3 py-1 rounded text-xs border transition-colors",
                days === d.value
                  ? "border-indigo-500 text-indigo-300 bg-indigo-500/10"
                  : "border-zinc-700 text-zinc-500 hover:border-zinc-500",
              ].join(" ")}
            >
              {d.label}
            </button>
          ))}
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="ml-auto px-3 py-1 rounded text-xs border border-zinc-700 text-zinc-500 hover:border-zinc-500 hover:text-zinc-300 transition-colors disabled:opacity-40"
        >
          {refreshing ? "Fetching..." : "Refresh feed"}
        </button>
      </div>

      {/* States */}
      {isLoading && (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="border border-zinc-800 rounded-lg p-5 animate-pulse">
              <div className="h-3 bg-zinc-800 rounded w-1/4 mb-3" />
              <div className="h-5 bg-zinc-800 rounded w-3/4 mb-3" />
              <div className="h-3 bg-zinc-800 rounded w-full mb-2" />
              <div className="h-3 bg-zinc-800 rounded w-5/6" />
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="border border-red-800 rounded-lg p-5 text-red-400 text-sm">
          Failed to load feed. Make sure the backend is running at{" "}
          <code className="text-red-300">localhost:8000</code>.
        </div>
      )}

      {!isLoading && !error && items.length === 0 && (
        <div className="border border-zinc-800 rounded-lg p-8 text-center text-zinc-500 text-sm">
          <p className="mb-2">No items yet.</p>
          <p>
            Click <strong className="text-zinc-400">Refresh feed</strong> to fetch the latest AI
            content, or wait for the scheduled ingestion to run.
          </p>
        </div>
      )}

      {!isLoading && !error && items.length > 0 && (
        <div className="space-y-4">
          {items.map((item, i) => (
            <FeedItemComponent key={item.id} item={item} rank={i + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
