"use client";

import { AnalysisResult } from "../lib/types";
import { MatchResultHero } from "./match-result-hero";
import { GoalsMarketCall } from "./goals-market-call";
import { EstimatedStatsCard } from "./estimated-stats-card";

export function ResultsPanel({ result }: { result: AnalysisResult }) {
  const { match_result_call, key_factors, team_snapshots, head_to_head, goals_markets, estimated_stats, availability_note, home_team, away_team } = result;

  return (
    <div className="w-full space-y-6">
      {/* The single decisive prediction — everything else is detail */}
      <MatchResultHero homeTeam={home_team} awayTeam={away_team} call={match_result_call} />

      {/* Goals markets — same one-call, reveal-more pattern */}
      <section
        className="rounded-2xl border p-6"
        style={{ background: "var(--bg-elevated)", borderColor: "var(--line)" }}
      >
        <h3 className="font-display mb-4 text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--ink-soft)" }}>
          Goals Markets
        </h3>
        <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <GoalsMarketCall title="Total Goals" market={goals_markets.total_goals_market} />
          <GoalsMarketCall title="Both Teams to Score" market={goals_markets.btts_market} />
        </div>
        <div className="mb-4 flex gap-6 font-mono text-sm" style={{ color: "var(--ink-soft)" }}>
          <span>Expected goals — {home_team}: <strong style={{ color: "var(--ink)" }}>{goals_markets.expected_home_goals}</strong></span>
          <span>{away_team}: <strong style={{ color: "var(--ink)" }}>{goals_markets.expected_away_goals}</strong></span>
        </div>
        <div className="flex flex-wrap gap-2">
          {goals_markets.most_likely_scorelines.map((s) => (
            <span
              key={s.score}
              className="font-mono rounded-lg border px-3 py-1.5 text-sm"
              style={{ borderColor: "var(--line)" }}
            >
              {s.score} <span style={{ color: "var(--ink-soft)" }}>· {(s.probability * 100).toFixed(1)}%</span>
            </span>
          ))}
        </div>
        <p className="mt-4 text-xs leading-relaxed" style={{ color: "var(--ink-soft)" }}>
          {goals_markets.model_note}
        </p>
      </section>

      {/* Corners & shots estimate */}
      <EstimatedStatsCard homeTeam={home_team} awayTeam={away_team} stats={estimated_stats} />

      {/* Key factors */}
      <section>
        <h3 className="font-display mb-3 text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--ink-soft)" }}>
          Key Factors
        </h3>
        <ul
          className="space-y-2 rounded-2xl border p-5"
          style={{ background: "var(--bg-elevated)", borderColor: "var(--line)" }}
        >
          {key_factors.map((f, i) => (
            <li key={i} className="flex gap-3 text-sm leading-relaxed">
              <span style={{ color: "var(--turf)" }}>▸</span>
              <span>{f}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* Team snapshots + H2H */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="rounded-2xl border p-5" style={{ background: "var(--bg-elevated)", borderColor: "var(--line)" }}>
          <h4 className="font-display mb-3 text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--ink-soft)" }}>
            Team Ratings
          </h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span>{home_team} Elo</span><span className="font-mono font-semibold">{team_snapshots.home.elo}</span></div>
            <div className="flex justify-between"><span>{away_team} Elo</span><span className="font-mono font-semibold">{team_snapshots.away.elo}</span></div>
            <div className="flex justify-between"><span>{home_team} form (pts/game)</span><span className="font-mono font-semibold">{team_snapshots.home.form_pts_per_game}</span></div>
            <div className="flex justify-between"><span>{away_team} form (pts/game)</span><span className="font-mono font-semibold">{team_snapshots.away.form_pts_per_game}</span></div>
          </div>
        </div>
        <div className="rounded-2xl border p-5" style={{ background: "var(--bg-elevated)", borderColor: "var(--line)" }}>
          <h4 className="font-display mb-3 text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--ink-soft)" }}>
            Head-to-Head
          </h4>
          {head_to_head.matches_considered > 0 ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span>Matches considered</span><span className="font-mono font-semibold">{head_to_head.matches_considered}</span></div>
              <div className="flex justify-between"><span>{home_team} wins</span><span className="font-mono font-semibold">{head_to_head.home_team_wins}</span></div>
              <div className="flex justify-between"><span>{away_team} wins</span><span className="font-mono font-semibold">{head_to_head.away_team_wins}</span></div>
            </div>
          ) : (
            <p className="text-sm" style={{ color: "var(--ink-soft)" }}>No prior meetings in the dataset.</p>
          )}
        </div>
      </section>

      {/* Availability note */}
      <p className="rounded-xl border-l-4 px-4 py-3 text-sm leading-relaxed" style={{ borderColor: "var(--amber)", background: "color-mix(in srgb, var(--amber) 8%, transparent)" }}>
        {availability_note}
      </p>
    </div>
  );
}
