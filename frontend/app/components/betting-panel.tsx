"use client";

import { useState } from "react";
import { AnalysisResult } from "../lib/types";

interface BettingPanelProps {
  result: AnalysisResult;
}

export function BettingPanel({ result }: BettingPanelProps) {
  const [homeOdds, setHomeOdds] = useState("");
  const [drawOdds, setDrawOdds] = useState("");
  const [awayOdds, setAwayOdds] = useState("");

  const rows = [
    { label: `${result.home_team} Win`, prob: result.final_probabilities.home_win, odds: homeOdds, setOdds: setHomeOdds },
    { label: "Draw", prob: result.final_probabilities.draw, odds: drawOdds, setOdds: setDrawOdds },
    { label: `${result.away_team} Win`, prob: result.final_probabilities.away_win, odds: awayOdds, setOdds: setAwayOdds },
  ];

  return (
    <section
      className="rounded-2xl border p-6"
      style={{ background: "var(--bg-elevated)", borderColor: "var(--line)" }}
    >
      <h3 className="font-display mb-1 text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--ink-soft)" }}>
        Value Bet Comparison
      </h3>
      <p className="mb-4 text-sm" style={{ color: "var(--ink-soft)" }}>
        Enter bookmaker decimal odds to compare against the model&apos;s probabilities. This is not connected to a live odds feed — enter odds manually to see if the model finds value.
      </p>

      <div className="space-y-3">
        {rows.map((row) => {
          const oddsNum = parseFloat(row.odds);
          const impliedProb = oddsNum > 0 ? 1 / oddsNum : null;
          const edge = impliedProb !== null ? row.prob - impliedProb : null;
          const hasValue = edge !== null && edge > 0.03;

          return (
            <div key={row.label} className="grid grid-cols-[1fr_auto_auto] items-center gap-3 sm:grid-cols-[1fr_100px_140px]">
              <span className="text-sm font-medium">{row.label}</span>
              <input
                type="number"
                step="0.01"
                min="1"
                placeholder="Odds"
                value={row.odds}
                onChange={(e) => row.setOdds(e.target.value)}
                className="w-full rounded-lg border px-3 py-2 text-sm font-mono outline-none"
                style={{ background: "var(--bg)", borderColor: "var(--line)", color: "var(--ink)" }}
              />
              <span
                className="font-mono text-xs text-right"
                style={{ color: hasValue ? "var(--turf)" : "var(--ink-soft)" }}
              >
                {edge !== null
                  ? hasValue
                    ? `+${(edge * 100).toFixed(1)}% edge`
                    : `${(edge * 100).toFixed(1)}% edge`
                  : "—"}
              </span>
            </div>
          );
        })}
      </div>

      <div
        className="mt-5 rounded-xl border-l-4 px-4 py-3 text-xs leading-relaxed"
        style={{ borderColor: "var(--away)", background: "color-mix(in srgb, var(--away) 8%, transparent)", color: "var(--ink-soft)" }}
      >
        <strong style={{ color: "var(--ink)" }}>Responsible gambling notice:</strong> These probabilities are model estimates
        with real uncertainty (see model accuracy on the methodology page) — they are not guarantees. Betting
        involves financial risk. Never stake more than you can afford to lose, and treat any &ldquo;value&rdquo;
        figure here as one input among many, not advice. If gambling stops being fun or you feel unable to
        stop, support is available — in the UK, GamCare (0808 8020 133) and the National Gambling Helpline;
        in the US, the National Problem Gambling Helpline (1-800-522-4700).
      </div>
    </section>
  );
}
