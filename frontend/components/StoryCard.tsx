"use client";

import { BookmarkIcon, CheckIcon, SkipForwardIcon } from "lucide-react";
import type { Story } from "@/lib/types";
import { cn } from "@/lib/utils";

const LABEL_COLORS: Record<string, string> = {
  high: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  medium: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  low: "bg-zinc-700 text-zinc-400 border-zinc-600",
};

const DOMAIN_LABELS: Record<string, string> = {
  llms: "LLMs",
  agents: "Agents",
  applied_ml: "Applied ML",
  infra_inference: "Infra / Inference",
  other: "Other",
};

interface Props {
  story: Story;
  onRead?: (id: string) => void;
  onSkip?: (id: string) => void;
  onSave?: (id: string) => void;
}

export function StoryCard({ story, onRead, onSkip, onSave }: Props) {
  const labelColor = LABEL_COLORS[story.relevance_label ?? "low"];
  const domain = DOMAIN_LABELS[story.sub_domain ?? "other"] ?? "Other";

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 flex flex-col gap-3 hover:border-zinc-700 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <a
          href={story.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-base font-semibold text-zinc-100 hover:text-white leading-snug"
        >
          {story.title}
        </a>
        <span
          className={cn(
            "shrink-0 text-xs font-medium px-2 py-0.5 rounded-full border",
            labelColor,
          )}
        >
          {story.relevance_label ?? "?"}
        </span>
      </div>

      {story.summary && (
        <p className="text-sm text-zinc-400 leading-relaxed">{story.summary}</p>
      )}

      {story.why_matters && (
        <p className="text-xs text-zinc-500">
          <span className="font-medium text-zinc-400">Why it matters: </span>
          {story.why_matters}
        </p>
      )}

      {story.what_to_do && (
        <p className="text-xs text-zinc-500">
          <span className="font-medium text-zinc-400">→ </span>
          {story.what_to_do}
        </p>
      )}

      <div className="flex items-center justify-between pt-1">
        <span className="text-xs text-zinc-600">{domain}</span>

        <div className="flex gap-2">
          {onSkip && (
            <button
              onClick={() => onSkip(story.id)}
              className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
              title="Skip"
            >
              <SkipForwardIcon size={14} />
            </button>
          )}
          {onSave && (
            <button
              onClick={() => onSave(story.id)}
              className="p-1.5 rounded-lg text-zinc-500 hover:text-amber-300 hover:bg-zinc-800 transition-colors"
              title="Save"
            >
              <BookmarkIcon size={14} />
            </button>
          )}
          {onRead && (
            <button
              onClick={() => onRead(story.id)}
              className="p-1.5 rounded-lg text-zinc-500 hover:text-emerald-400 hover:bg-zinc-800 transition-colors"
              title="Mark read"
            >
              <CheckIcon size={14} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
