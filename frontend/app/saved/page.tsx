"use client";

import { useEffect, useState } from "react";
import { StoryCard } from "@/components/StoryCard";
import { api } from "@/lib/api";
import type { Story } from "@/lib/types";

export default function SavedPage() {
  const [stories, setStories] = useState<Story[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.saved().then(setStories).finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-zinc-100">Saved</h1>
        <p className="text-sm text-zinc-500 mt-0.5">Stories you bookmarked</p>
      </div>

      {loading ? (
        <div className="flex flex-col gap-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-40 rounded-xl bg-zinc-900 animate-pulse" />
          ))}
        </div>
      ) : stories.length === 0 ? (
        <p className="text-zinc-500 text-sm py-12 text-center">Nothing saved yet.</p>
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
