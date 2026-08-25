"use client";

import { useEffect, useState } from "react";

interface PremiumStatsOption {
  key: string;
  label: string;
  configured: boolean;
}

interface PremiumStatsStatus {
  enabled_provider: string | null;
  options: PremiumStatsOption[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function fetchStatus(): Promise<PremiumStatsStatus> {
  const res = await fetch(`${API_BASE}/api/premium-stats`);
  if (!res.ok) throw new Error("Failed to fetch premium stats status");
  return res.json();
}

async function setProvider(provider: string | null): Promise<void> {
  const res = await fetch(`${API_BASE}/api/premium-stats/selection`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Failed to update premium stats provider");
  }
}

export function PremiumStatsPanel() {
  const [status, setStatus] = useState<PremiumStatsStatus | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchStatus().then(setStatus).catch(() => setLoadError(true));
  }, []);

  async function handleSelect(provider: string | null) {
    if (!status) return;
    setSaving(true);
    const previous = status.enabled_provider;
    setStatus({ ...status, enabled_provider: provider }); // optimistic
    try {
      await setProvider(provider);
    } catch {
      setStatus({ ...status, enabled_provider: previous }); // revert
    } finally {
      setSaving(false);
    }
  }

  return (
    <details className="interactive-card group rounded-xl border" style={{ borderColor: "var(--line)" }}>
      <summary
        className="font-display cursor-pointer list-none px-4 py-3 text-xs font-semibold uppercase tracking-widest"
        style={{ color: "var(--ink-soft)" }}
      >
        <span className="inline-block transition-transform group-open:rotate-90">▸</span>{" "}
        Corners &amp; Shots Data Source
      </summary>
      <div className="border-t px-4 py-4" style={{ borderColor: "var(--line)" }}>
        {loadError || !status ? (
          <p className="text-sm" style={{ color: "var(--ink-soft)" }}>
            {loadError ? "Could not load settings — is the backend running?" : "Loading…"}
          </p>
        ) : (
          <>
            <p className="mb-3 text-xs leading-relaxed" style={{ color: "var(--ink-soft)" }}>
              By default, corners and shots are a rough estimate derived from goal-scoring
              patterns — clearly labeled as such, not a validated prediction. If your
              Sportmonks or API-Football plan includes match statistics, enable it here for
              real data instead.
            </p>
            <div className="space-y-2">
              <ProviderOption
                label="Estimate (default, always available)"
                selected={status.enabled_provider === null}
                disabled={saving}
                onClick={() => handleSelect(null)}
              />
              {status.options.map((opt) => (
                <ProviderOption
                  key={opt.key}
                  label={opt.label}
                  badge={opt.configured ? undefined : "no api key"}
                  selected={status.enabled_provider === opt.key}
                  disabled={saving}
                  onClick={() => handleSelect(opt.key)}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </details>
  );
}

function ProviderOption({
  label, badge, selected, disabled, onClick,
}: { label: string; badge?: string; selected: boolean; disabled: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="flex w-full items-center justify-between rounded-full border px-4 py-2 text-left text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-60"
      style={{
        borderColor: selected ? "var(--turf)" : "var(--line)",
        background: selected ? "color-mix(in srgb, var(--turf) 12%, transparent)" : "transparent",
      }}
    >
      <span className="flex items-center gap-2">
        <span
          className="flex h-4 w-4 items-center justify-center rounded-full border"
          style={{ borderColor: selected ? "var(--turf)" : "var(--line)" }}
        >
          {selected && <span className="h-2 w-2 rounded-full" style={{ background: "var(--turf)" }} />}
        </span>
        {label}
      </span>
      {badge && (
        <span
          className="font-mono rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wide"
          style={{ background: "color-mix(in srgb, var(--ink-soft) 15%, transparent)", color: "var(--ink-soft)" }}
        >
          {badge}
        </span>
      )}
    </button>
  );
}
