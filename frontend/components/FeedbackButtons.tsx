"use client";

import { useState } from "react";
import { removeFeedback, submitFeedback } from "@/lib/api";

interface Props {
  itemId: string;
  initial: "up" | "down" | null;
  userId?: string;
}

export default function FeedbackButtons({ itemId, initial, userId = "default" }: Props) {
  const [feedback, setFeedback] = useState<"up" | "down" | null>(initial);
  const [loading, setLoading] = useState(false);

  async function handle(value: "up" | "down") {
    if (loading) return;
    setLoading(true);
    try {
      if (feedback === value) {
        // Toggle off
        await removeFeedback(itemId, userId);
        setFeedback(null);
      } else {
        await submitFeedback(itemId, value, userId);
        setFeedback(value);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => handle("up")}
        disabled={loading}
        title="Relevant"
        className={[
          "flex items-center gap-1 px-2 py-1 rounded text-xs border transition-colors",
          feedback === "up"
            ? "border-green-500 text-green-400 bg-green-500/10"
            : "border-zinc-700 text-zinc-500 hover:border-green-600 hover:text-green-400",
        ].join(" ")}
      >
        <span>+1</span>
        <span>Relevant</span>
      </button>
      <button
        onClick={() => handle("down")}
        disabled={loading}
        title="Not relevant"
        className={[
          "flex items-center gap-1 px-2 py-1 rounded text-xs border transition-colors",
          feedback === "down"
            ? "border-red-500 text-red-400 bg-red-500/10"
            : "border-zinc-700 text-zinc-500 hover:border-red-600 hover:text-red-400",
        ].join(" ")}
      >
        <span>-1</span>
        <span>Not relevant</span>
      </button>
    </div>
  );
}
