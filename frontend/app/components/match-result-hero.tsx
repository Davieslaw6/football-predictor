"use client";

import { useState } from "react";
import { MarketCall } from "../lib/types";
import { ConfidenceBadge } from "./goals-market-call";
import { RevealToggleButton } from "./reveal-toggle-button";

export function MatchResultHero({ homeTeam, awayTeam, call }: { homeTeam: string; awayTeam: string; call: MarketCall }) {
  const [revealed, setRevealed] = useState(false);
  const otherOptions = call.all_options.filter((o) => o.label !== call.call);

  return (
    <section
      className="rounded-2xl border p-6 shadow-sm sm:p-8"
      style={{ background: "var(--bg-elevated)", borderColor: "var(--line)" }}
    >
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-display text-base font-semibold tracking-tight sm:text-lg" style={{ color: "var(--ink-soft)" }}>
          {homeTeam} <span className="mx-1">vs</span> {awayTeam}
        </h2>
        <ConfidenceBadge level={call.confidence} />
      </div>

      <div className="font-display text-3xl font-extrabold leading-tight tracking-tight sm:text-4xl">
        {call.call}
      </div>
      <div className="font-mono mt-2 text-4xl font-bold sm:text-5xl" style={{ color: "var(--turf)" }}>
        {(call.call_probability * 100).toFixed(1)}%
      </div>

      <div className="mt-5">
        <RevealToggleButton revealed={revealed} onClick={() => setRevealed((r) => !r)} />
      </div>

      {revealed && (
        <div className="mt-4 space-y-2 border-t pt-4" style={{ borderColor: "var(--line)" }}>
          {otherOptions.map((o) => (
            <div key={o.label} className="flex items-center justify-between text-sm">
              <span style={{ color: "var(--ink-soft)" }}>{o.label}</span>
              <span className="font-mono font-medium">{(o.probability * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
