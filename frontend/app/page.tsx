"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCwIcon } from "lucide-react";
import { DomainTabs } from "@/components/DomainTabs";
import { StoryCard } from "@/components/StoryCard";
import { api } from "@/lib/api";
import type { Story } from "@/lib/types";

export default function QueuePage() {
  const [stories, setStories] = useState<Story[]>([]);
  const [domain, setDomain] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setStories(await api.queue(domain || undefined));
    } finally {
      setLoading(false);
    }
  }, [domain]);

  useEffect(() => { load(); }, [load]);

  const remove = (id: string) =>
    setStories((prev) => prev.filter((s) => s.id !== id));

  const handleRead = async (id: string) => {
    await api.markRead(id);
    remove(id);
  };
  const handleSkip = async (id: string) => {
    await api.markSkip(id);
    remove(id);
  };
  const handleSave = async (id: string) => {
    await api.markSave(id);
    remove(id);
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await api.refresh();
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-zinc-100">Queue</h1>
          <p className="text-sm text-zinc-500 mt-0.5">Top unread from the last 30 days</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg bg-zinc-800 text-zinc-300 hover:bg-zinc-700 disabled:opacity-50 transition-colors"
        >
          <RefreshCwIcon size={13} className={refreshing ? "animate-spin" : ""} />
          {refreshing ? "Running…" : "Refresh"}
        </button>
      </div>

      <DomainTabs active={domain} onChange={setDomain} />

      {loading ? (
        <div className="flex flex-col gap-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-40 rounded-xl bg-zinc-900 animate-pulse" />
          ))}
        </div>
      ) : stories.length === 0 ? (
        <p className="text-zinc-500 text-sm py-12 text-center">
          Queue is empty — run a refresh or wait for the scheduler.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {stories.map((s) => (
            <StoryCard
              key={s.id}
              story={s}
              onRead={handleRead}
              onSkip={handleSkip}
              onSave={handleSave}
            />
          ))}
        </div>
      )}
    </div>
  );
}
