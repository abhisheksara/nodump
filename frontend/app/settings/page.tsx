"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Source } from "@/lib/types";

export default function SettingsPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState<number | null>(null);

  useEffect(() => {
    api.sources().then(setSources).finally(() => setLoading(false));
  }, []);

  const toggle = async (src: Source) => {
    setToggling(src.id);
    try {
      const updated = await api.toggleSource(src.id, !src.active);
      setSources((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
    } finally {
      setToggling(null);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-zinc-100">Settings</h1>
        <p className="text-sm text-zinc-500 mt-0.5">Manage ingestion sources</p>
      </div>

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wide">Sources</h2>
        {loading ? (
          <div className="h-24 rounded-xl bg-zinc-900 animate-pulse" />
        ) : (
          sources.map((src) => (
            <div
              key={src.id}
              className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900 px-5 py-4"
            >
              <div>
                <p className="text-sm font-medium text-zinc-200 capitalize">{src.name}</p>
                <p className="text-xs text-zinc-500">
                  Every {src.fetch_interval_mins >= 60
                    ? `${src.fetch_interval_mins / 60}h`
                    : `${src.fetch_interval_mins}m`}
                  {src.last_fetched_at
                    ? ` · last fetched ${new Date(src.last_fetched_at).toLocaleString()}`
                    : " · never fetched"}
                </p>
              </div>
              <button
                onClick={() => toggle(src)}
                disabled={toggling === src.id}
                className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none disabled:opacity-50 ${
                  src.active ? "bg-emerald-500" : "bg-zinc-700"
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                    src.active ? "translate-x-5" : "translate-x-0"
                  }`}
                />
              </button>
            </div>
          ))
        )}
      </section>
    </div>
  );
}
