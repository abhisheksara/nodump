import type { FeedItem as FeedItemType } from "@/lib/api";
import FeedbackButtons from "./FeedbackButtons";

const SOURCE_LABELS: Record<string, string> = {
  arxiv: "arXiv",
  blog: "Blog",
  twitter: "X",
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  return (
    <div className="flex items-center gap-2 text-xs text-zinc-500">
      <div className="w-16 h-1 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-indigo-500 rounded-full"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span>{pct}% relevant</span>
    </div>
  );
}

interface Props {
  item: FeedItemType;
  rank: number;
}

export default function FeedItem({ item, rank }: Props) {
  return (
    <article className="border border-zinc-800 rounded-lg p-5 hover:border-zinc-700 transition-colors">
      {/* Header row */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex items-center gap-2 text-xs text-zinc-500 shrink-0">
          <span className="text-zinc-600 font-bold">#{rank}</span>
          <span className="px-1.5 py-0.5 bg-zinc-800 rounded text-zinc-400">
            {SOURCE_LABELS[item.source] ?? item.source}
          </span>
          {item.author && <span className="text-zinc-600">{item.author}</span>}
          <span className="text-zinc-700">{formatDate(item.published_at)}</span>
        </div>
        <ScoreBar score={item.relevance_score} />
      </div>

      {/* Title */}
      <a
        href={item.url}
        target="_blank"
        rel="noopener noreferrer"
        className="block text-base font-semibold text-zinc-100 hover:text-indigo-300 transition-colors mb-3 leading-snug"
      >
        {item.title}
      </a>

      {/* Summary */}
      {item.summary && (
        <p className="text-sm text-zinc-400 leading-relaxed mb-3">{item.summary}</p>
      )}

      {/* Why it matters */}
      {item.why_it_matters && (
        <div className="border-l-2 border-indigo-500/50 pl-3 mb-4">
          <p className="text-xs text-zinc-500 uppercase tracking-wide mb-1">Why this matters</p>
          <p className="text-sm text-indigo-300 leading-relaxed">{item.why_it_matters}</p>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between">
        <FeedbackButtons itemId={item.id} initial={item.user_feedback} />
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
        >
          Read full &rarr;
        </a>
      </div>
    </article>
  );
}
