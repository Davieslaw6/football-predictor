"use client";

import { useEffect, useState } from "react";
import { ThemeToggle } from "./theme-toggle";
import { DataSourceInfo } from "./components/data-source-info";
import { TeamSelect } from "./components/team-select";
import { AvailabilityInput } from "./components/availability-input";
import { LeagueUpdatePanel } from "./components/league-update-panel";
import { ProviderTogglePanel } from "./components/provider-toggle-panel";
import { PremiumStatsPanel } from "./components/premium-stats-panel";
import { ResultsPanel } from "./components/results-panel";
import { BettingPanel } from "./components/betting-panel";
import { fetchTeams, analyzeMatch } from "./lib/api";
import { AnalysisResult } from "./lib/types";

export default function Home() {
  const [teams, setTeams] = useState<string[]>([]);
  const [homeTeam, setHomeTeam] = useState("");
  const [awayTeam, setAwayTeam] = useState("");
  const [homePenalty, setHomePenalty] = useState(0);
  const [awayPenalty, setAwayPenalty] = useState(0);
  const [homePlayers, setHomePlayers] = useState("");
  const [awayPlayers, setAwayPlayers] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [teamsError, setTeamsError] = useState(false);

  useEffect(() => {
    fetchTeams()
      .then(setTeams)
      .catch(() => setTeamsError(true));
  }, []);

  const canAnalyze = homeTeam && awayTeam && homeTeam !== awayTeam && !loading;

  async function handleAnalyze() {
    if (!canAnalyze) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await analyzeMatch({
        home_team: homeTeam,
        away_team: awayTeam,
        home_injury_penalty: homePenalty,
        away_injury_penalty: awayPenalty,
        home_out_players: homePlayers.split(",").map((s) => s.trim()).filter(Boolean),
        away_out_players: awayPlayers.split(",").map((s) => s.trim()).filter(Boolean),
      });
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell mx-auto min-h-screen max-w-4xl px-5 pb-24 pt-8 sm:px-8">
      <div className="ambient-orb one" aria-hidden="true" />
      <div className="ambient-orb two" aria-hidden="true" />
      <header className="relative z-10 mb-10 flex items-center justify-between">
        <div className="font-display text-xl font-extrabold tracking-tight">
          FULL<span style={{ color: "var(--turf)" }}>TIME</span>
          <span className="ml-2 align-middle font-mono text-[9px] font-medium uppercase tracking-[.22em]" style={{ color: "var(--ink-soft)" }}>
            football intelligence
          </span>
        </div>
        <ThemeToggle />
      </header>

      <section className="pitch-lines mb-10 rounded-2xl border p-8 sm:p-12" style={{ borderColor: "var(--line)" }}>
        <span className="relative z-10 inline-flex items-center gap-2 font-mono text-[10px] font-semibold uppercase tracking-[.22em]" style={{ color: "var(--turf)" }}>
          <span className="h-1.5 w-1.5 animate-pulse rounded-full" style={{ background: "var(--turf)" }} />
          Match intelligence engine
        </span>
        <h1 className="relative z-10 mt-3 font-display text-5xl font-extrabold leading-[0.9] tracking-tight sm:text-7xl">
          Two teams.
          <br />
          <span style={{ color: "var(--turf)" }}>One prediction,</span>
          <br />
          built from evidence.
        </h1>
        <p className="relative z-10 mt-5 max-w-xl text-sm leading-relaxed sm:text-base" style={{ color: "var(--ink-soft)" }}>
          Elo ratings, recent form, head-to-head history, and goal expectancy —
          trained on{" "}
          <span className="font-mono font-semibold" style={{ color: "var(--ink)" }}>27,000+</span>{" "}
          real matches across 14 competitions and validated on data the model never trained on.
        </p>
        <div className="football-float" aria-hidden="true">⚽</div>
      </section>

      <section
        className="interactive-card mb-8 rounded-2xl border p-6 shadow-sm sm:p-8"
        style={{ background: "var(--bg-elevated)", borderColor: "var(--line)" }}
      >
        {teamsError ? (
          <p className="rounded-lg border-l-4 px-4 py-3 text-sm" style={{ borderColor: "var(--away)", color: "var(--ink-soft)" }}>
            Could not reach the prediction API. Make sure the backend is running
            (<code className="font-mono">uvicorn app.main:app --port 8000</code>) and reachable at the configured API URL.
          </p>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_auto_1fr] sm:items-end">
              <TeamSelect label="Home team" teams={teams} value={homeTeam} onChange={setHomeTeam} accentVar="--turf" />
              <div className="font-display hidden pb-3.5 text-center text-sm font-bold sm:block" style={{ color: "var(--ink-soft)" }}>
                VS
              </div>
              <TeamSelect label="Away team" teams={teams} value={awayTeam} onChange={setAwayTeam} accentVar="--away" />
            </div>

            <div className="mt-5">
              <AvailabilityInput
                homeTeam={homeTeam}
                awayTeam={awayTeam}
                homePenalty={homePenalty}
                awayPenalty={awayPenalty}
                onHomePenaltyChange={setHomePenalty}
                onAwayPenaltyChange={setAwayPenalty}
                homePlayers={homePlayers}
                awayPlayers={awayPlayers}
                onHomePlayersChange={setHomePlayers}
                onAwayPlayersChange={setAwayPlayers}
              />
            </div>

            <div className="mt-3">
              <LeagueUpdatePanel />
            </div>

            <div className="mt-3">
              <ProviderTogglePanel />
            </div>

            <div className="mt-3">
              <PremiumStatsPanel />
            </div>

            {homeTeam && awayTeam && homeTeam === awayTeam && (
              <p className="mt-4 text-sm" style={{ color: "var(--away)" }}>
                Home and away team must be different.
              </p>
            )}

            <button
              onClick={handleAnalyze}
              disabled={!canAnalyze}
              className={`analyze-button font-display mt-6 w-full rounded-xl py-4 text-lg font-bold uppercase tracking-wide disabled:cursor-not-allowed disabled:opacity-40 ${loading ? "is-loading" : ""}`}
              style={{ background: "var(--turf)", color: "var(--bg)" }}
              aria-busy={loading}
            >
              <span className="flex items-center justify-center gap-3">
                {loading && <span className="football-spinner" aria-hidden="true">⚽</span>}
                <span>{loading ? "Analyzing match…" : "Analyze Match"}</span>
              </span>
              {loading && <span className="loading-track" aria-hidden="true" />}
            </button>

            {error && (
              <p className="mt-4 rounded-lg border-l-4 px-4 py-3 text-sm" style={{ borderColor: "var(--away)", color: "var(--ink-soft)" }}>
                {error}
              </p>
            )}
          </>
        )}
      </section>

      {result && (
        <div className="space-y-6">
          <ResultsPanel result={result} />
          <BettingPanel result={result} />
        </div>
      )}

      <DataSourceInfo />

      <footer className="mt-8 text-center text-xs" style={{ color: "var(--ink-soft)" }}>
        Predictions are statistical estimates, not certainties. Trained on 14 competitions across Europe — coverage varies by league and updates as data is refreshed.
      </footer>
    </main>
  );
}
