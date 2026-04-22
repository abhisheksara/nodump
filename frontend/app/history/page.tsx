"use client";

import { useEffect, useState } from "react";
import { SearchIcon } from "lucide-react";
import { StoryCard } from "@/components/StoryCard";
import { api } from "@/lib/api";
import type { Story } from "@/lib/types";

export default function HistoryPage() {
  const [stories, setStories] = useState<Story[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const t = setTimeout(() => {
      api.history(q || undefined).then(setStories).finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-zinc-100">History</h1>
        <p className="text-sm text-zinc-500 mt-0.5">Read and skipped stories</p>
      </div>

      <div className="relative">
        <SearchIcon size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by title…"
          className="w-full pl-9 pr-3 py-2 text-sm rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-600"
        />
      </div>

      {loading ? (
        <div className="flex flex-col gap-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-24 rounded-xl bg-zinc-900 animate-pulse" />
          ))}
        </div>
      ) : stories.length === 0 ? (
        <p className="text-zinc-500 text-sm py-12 text-center">
          {q ? "No matches found." : "No history yet."}
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {stories.map((s) => (
            <StoryCard key={s.id} story={s} />
          ))}
        </div>
      )}
    </div>
  );
}
