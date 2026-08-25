"use client";

import { useState } from "react";
import { MarketCall } from "../lib/types";
import { RevealToggleButton } from "./reveal-toggle-button";

export function ConfidenceBadge({ level }: { level: "High" | "Medium" | "Low" }) {
  const color = level === "High" ? "var(--turf)" : level === "Medium" ? "var(--amber)" : "var(--ink-soft)";
  return (
    <span
      className="font-display rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide"
      style={{ background: `color-mix(in srgb, ${color} 18%, transparent)`, color }}
    >
      {level}
    </span>
  );
}

export function GoalsMarketCall({ title, market }: { title: string; market: MarketCall }) {
  const [revealed, setRevealed] = useState(false);
  const otherOptions = market.all_options.filter((o) => o.label !== market.call);

  return (
    <div className="rounded-xl border p-4" style={{ borderColor: "var(--line)" }}>
      <div className="mb-2 flex items-center justify-between">
        <span className="font-display text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--ink-soft)" }}>
          {title}
        </span>
        <ConfidenceBadge level={market.confidence} />
      </div>

      <div className="mb-1 text-lg font-semibold">{market.call}</div>
      <div className="font-mono text-2xl font-bold" style={{ color: "var(--turf)" }}>
        {(market.call_probability * 100).toFixed(1)}%
      </div>

      <div className="mt-3">
        <RevealToggleButton
          revealed={revealed}
          onClick={() => setRevealed((r) => !r)}
          showLabel="Show other outcome"
          hideLabel="Hide other outcome"
          size="sm"
        />
      </div>

      {revealed && (
        <div className="mt-3 space-y-1.5 border-t pt-3" style={{ borderColor: "var(--line)" }}>
          {otherOptions.map((o) => (
            <div key={o.label} className="flex justify-between text-sm">
              <span style={{ color: "var(--ink-soft)" }}>{o.label}</span>
              <span className="font-mono">{(o.probability * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
