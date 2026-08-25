"use client";

import { EstimatedStats } from "../lib/types";

export function EstimatedStatsCard({
  homeTeam, awayTeam, stats,
}: { homeTeam: string; awayTeam: string; stats: EstimatedStats }) {
  return (
    <section
      className="rounded-2xl border p-6"
      style={{ background: "var(--bg-elevated)", borderColor: "var(--line)" }}
    >
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-display text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--ink-soft)" }}>
          Corners &amp; Shots
        </h3>
        <span
          className="font-display rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide"
          style={{
            background: stats.premium_data_available
              ? "color-mix(in srgb, var(--turf) 18%, transparent)"
              : "color-mix(in srgb, var(--ink-soft) 15%, transparent)",
            color: stats.premium_data_available ? "var(--turf)" : "var(--ink-soft)",
          }}
        >
          {stats.premium_data_available ? "Real data" : "Estimate"}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatBlock label={`${homeTeam} corners`} value={stats.home_corners_estimate} />
        <StatBlock label={`${awayTeam} corners`} value={stats.away_corners_estimate} />
        <StatBlock label={`${homeTeam} shots`} value={stats.home_shots_estimate} />
        <StatBlock label={`${awayTeam} shots`} value={stats.away_shots_estimate} />
      </div>

      <p className="mt-4 text-xs leading-relaxed" style={{ color: "var(--ink-soft)" }}>
        {stats.premium_data_available
          ? `Real match-statistics data from ${stats.premium_source}.`
          : stats.methodology_note}
      </p>
      {stats.premium_error && (
        <p className="mt-2 text-xs leading-relaxed" style={{ color: "var(--amber)" }}>
          Premium data unavailable: {stats.premium_error}. Showing the estimate instead.
        </p>
      )}
    </section>
  );
}

function StatBlock({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="text-xs" style={{ color: "var(--ink-soft)" }}>{label}</div>
      <div className="font-mono text-2xl font-bold">{value}</div>
    </div>
  );
}
