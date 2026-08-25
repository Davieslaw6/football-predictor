"use client";

interface AvailabilityInputProps {
  homeTeam: string;
  awayTeam: string;
  homePenalty: number;
  awayPenalty: number;
  onHomePenaltyChange: (v: number) => void;
  onAwayPenaltyChange: (v: number) => void;
  homePlayers: string;
  awayPlayers: string;
  onHomePlayersChange: (v: string) => void;
  onAwayPlayersChange: (v: string) => void;
}

export function AvailabilityInput({
  homeTeam, awayTeam, homePenalty, awayPenalty,
  onHomePenaltyChange, onAwayPenaltyChange,
  homePlayers, awayPlayers, onHomePlayersChange, onAwayPlayersChange,
}: AvailabilityInputProps) {
  return (
    <details className="interactive-card group rounded-xl border" style={{ borderColor: "var(--line)" }}>
      <summary
        className="font-display cursor-pointer list-none px-4 py-3 text-xs font-semibold uppercase tracking-widest"
        style={{ color: "var(--ink-soft)" }}
      >
        <span className="inline-block transition-transform group-open:rotate-90">▸</span>{" "}
        Injuries &amp; Availability (optional)
      </summary>
      <div className="grid grid-cols-1 gap-4 border-t px-4 py-4 sm:grid-cols-2" style={{ borderColor: "var(--line)" }}>
        <TeamAvailability
          team={homeTeam || "Home team"}
          penalty={homePenalty}
          onPenaltyChange={onHomePenaltyChange}
          players={homePlayers}
          onPlayersChange={onHomePlayersChange}
        />
        <TeamAvailability
          team={awayTeam || "Away team"}
          penalty={awayPenalty}
          onPenaltyChange={onAwayPenaltyChange}
          players={awayPlayers}
          onPlayersChange={onAwayPlayersChange}
        />
      </div>
    </details>
  );
}

function TeamAvailability({
  team, penalty, onPenaltyChange, players, onPlayersChange,
}: {
  team: string;
  penalty: number;
  onPenaltyChange: (v: number) => void;
  players: string;
  onPlayersChange: (v: string) => void;
}) {
  return (
    <div>
      <div className="mb-2 text-sm font-medium">{team}</div>
      <label className="mb-1 block text-xs" style={{ color: "var(--ink-soft)" }}>
        Squad strength missing ({(penalty * 100).toFixed(0)}%)
      </label>
      <input
        type="range"
        min={0}
        max={50}
        value={penalty * 100}
        onChange={(e) => onPenaltyChange(Number(e.target.value) / 100)}
        className="w-full accent-current"
        style={{ color: "var(--turf)" }}
      />
      <input
        type="text"
        placeholder="Injured/suspended players, comma-separated"
        value={players}
        onChange={(e) => onPlayersChange(e.target.value)}
        className="mt-2 w-full rounded-lg border px-3 py-2 text-xs outline-none"
        style={{ background: "var(--bg)", borderColor: "var(--line)", color: "var(--ink)" }}
      />
    </div>
  );
}
