"use client";

import { cn } from "@/lib/utils";

export const DOMAINS = [
  { key: "", label: "All" },
  { key: "llms", label: "LLMs" },
  { key: "agents", label: "Agents" },
  { key: "applied_ml", label: "Applied ML" },
  { key: "infra_inference", label: "Infra / Inference" },
] as const;

interface Props {
  active: string;
  onChange: (domain: string) => void;
}

export function DomainTabs({ active, onChange }: Props) {
  return (
    <div className="flex gap-1 flex-wrap">
      {DOMAINS.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          className={cn(
            "px-3 py-1.5 text-sm rounded-lg font-medium transition-colors",
            active === key
              ? "bg-zinc-100 text-zinc-900"
              : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800",
          )}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
