"use client";

import { useEffect, useRef, useState } from "react";
import { LeagueInfo, fetchLeagues, setLeagueSelection, triggerUpdate, fetchUpdateStatus, UpdateStatus } from "../lib/api";

export function LeagueUpdatePanel() {
  const [leagues, setLeagues] = useState<LeagueInfo[]>([]);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [updateStatus, setUpdateStatus] = useState<UpdateStatus | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetchLeagues().then(setLeagues).catch(() => setLoadError(true));
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  function toggleLeague(key: string) {
    setLeagues((prev) => prev.map((l) => (l.key === key ? { ...l, selected: !l.selected } : l)));
  }

  async function saveSelection() {
    setSaving(true);
    try {
      const selectedKeys = leagues.filter((l) => l.selected).map((l) => l.key);
      await setLeagueSelection(selectedKeys);
    } catch {
      // selection save failed silently retried on next save attempt
    } finally {
      setSaving(false);
    }
  }

  async function handleUpdateNow() {
    try {
      await triggerUpdate();
    } catch (e) {
      setUpdateStatus({
        status: "error",
        started_at: null,
        finished_at: null,
        log: "",
        error: e instanceof Error ? e.message : "Failed to start update",
      });
      return;
    }
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      const status = await fetchUpdateStatus().catch(() => null);
      if (status) {
        setUpdateStatus(status);
        if (status.status !== "running" && pollRef.current) {
          clearInterval(pollRef.current);
        }
      }
    }, 2000);
  }

  const isUpdating = updateStatus?.status === "running";
  const noneSelected = leagues.length > 0 && leagues.every((l) => !l.selected);

  return (
    <details className="interactive-card group rounded-xl border" style={{ borderColor: "var(--line)" }}>
      <summary
        className="font-display cursor-pointer list-none px-4 py-3 text-xs font-semibold uppercase tracking-widest"
        style={{ color: "var(--ink-soft)" }}
      >
        <span className="inline-block transition-transform group-open:rotate-90">▸</span>{" "}
        Leagues &amp; Data Updates
      </summary>
      <div className="border-t px-4 py-4" style={{ borderColor: "var(--line)" }}>
        {loadError ? (
          <p className="text-sm" style={{ color: "var(--ink-soft)" }}>
            Could not load league settings — is the backend running?
          </p>
        ) : (
          <>
            <p className="mb-3 text-xs leading-relaxed" style={{ color: "var(--ink-soft)" }}>
              Choose which competitions get refreshed when you update data. Predictions
              always use whichever leagues were included the last time the model was trained.
            </p>
            <div className="space-y-2">
              {leagues.map((league) => (
                <label key={league.key} className="flex cursor-pointer items-center gap-3 text-sm">
                  <input
                    type="checkbox"
                    checked={league.selected}
                    onChange={() => toggleLeague(league.key)}
                    className="h-4 w-4 accent-current"
                    style={{ color: "var(--turf)" }}
                  />
                  <span className="flex-1">{league.label}</span>
                  <span
                    className="font-mono rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wide"
                    style={{
                      background: league.competition_type === "continental"
                        ? "color-mix(in srgb, var(--amber) 18%, transparent)"
                        : "color-mix(in srgb, var(--turf) 18%, transparent)",
                      color: league.competition_type === "continental" ? "var(--amber)" : "var(--turf)",
                    }}
                  >
                    {league.competition_type}
                  </span>
                </label>
              ))}
            </div>

            {noneSelected && (
              <p className="mt-3 text-xs" style={{ color: "var(--away)" }}>
                At least one league must stay selected.
              </p>
            )}

            <div className="mt-4 flex flex-wrap gap-2">
              <button
                onClick={saveSelection}
                disabled={saving || noneSelected}
                className="rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-wide transition-colors disabled:cursor-not-allowed disabled:opacity-40"
                style={{ borderColor: "var(--line)", color: "var(--ink)" }}
              >
                {saving ? "Saving…" : "Save selection"}
              </button>
              <button
                onClick={handleUpdateNow}
                disabled={isUpdating}
                className="font-display rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-wide transition-colors disabled:cursor-not-allowed disabled:opacity-60"
                style={{ background: "var(--turf)", color: "var(--bg)" }}
              >
                {isUpdating ? "Updating…" : "Update Now"}
              </button>
            </div>

            {updateStatus && (
              <div
                className="mt-3 rounded-lg border-l-4 px-3 py-2 text-xs leading-relaxed"
                style={{
                  borderColor: updateStatus.status === "error" ? "var(--away)" : "var(--turf)",
                  background: `color-mix(in srgb, ${updateStatus.status === "error" ? "var(--away)" : "var(--turf)"} 8%, transparent)`,
                  color: "var(--ink-soft)",
                }}
              >
                {updateStatus.status === "running" && "Fetching latest match data and retraining the model — this can take up to a couple of minutes…"}
                {updateStatus.status === "success" && "Update complete. New matches and any newly-selected leagues are now reflected in predictions."}
                {updateStatus.status === "error" && `Update failed: ${updateStatus.error}`}
              </div>
            )}

            <p className="mt-4 text-xs leading-relaxed" style={{ color: "var(--ink-soft)" }}>
              For automatic daily updates (not just on-demand), schedule{" "}
              <code className="font-mono">backend/daily_update_standalone.py</code> with
              Windows Task Scheduler or cron — see the README for setup steps.
            </p>
          </>
        )}
      </div>
    </details>
  );
}
