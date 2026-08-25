"use client";

import { useEffect, useState } from "react";
import { ProviderStatus, fetchProviders, setProviderEnabled } from "../lib/api";

function StatusDot({ available, configured }: { available: boolean; configured: boolean }) {
  const color = available ? "var(--turf)" : configured ? "var(--amber)" : "var(--ink-soft)";
  return <span className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />;
}

export function ProviderTogglePanel() {
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [loadError, setLoadError] = useState(false);
  const [toggling, setToggling] = useState<string | null>(null);

  useEffect(() => {
    fetchProviders().then(setProviders).catch(() => setLoadError(true));
  }, []);

  async function handleToggle(key: string, currentlyEnabled: boolean) {
    setToggling(key);
    // optimistic update
    setProviders((prev) => prev.map((p) => (p.key === key ? { ...p, enabled: !currentlyEnabled, available: !currentlyEnabled && p.configured } : p)));
    try {
      await setProviderEnabled(key, !currentlyEnabled);
    } catch {
      // revert on failure
      setProviders((prev) => prev.map((p) => (p.key === key ? { ...p, enabled: currentlyEnabled } : p)));
    } finally {
      setToggling(null);
    }
  }

  return (
    <details className="interactive-card group rounded-xl border" style={{ borderColor: "var(--line)" }}>
      <summary
        className="font-display cursor-pointer list-none px-4 py-3 text-xs font-semibold uppercase tracking-widest"
        style={{ color: "var(--ink-soft)" }}
      >
        <span className="inline-block transition-transform group-open:rotate-90">▸</span>{" "}
        Live Data Providers
      </summary>
      <div className="border-t px-4 py-4" style={{ borderColor: "var(--line)" }}>
        {loadError ? (
          <p className="text-sm" style={{ color: "var(--ink-soft)" }}>
            Could not load provider settings — is the backend running?
          </p>
        ) : (
          <>
            <p className="mb-3 text-xs leading-relaxed" style={{ color: "var(--ink-soft)" }}>
              Toggle each provider independently. Both Sportmonks and API-Football
              are paid services — each needs its own API key set as an environment
              variable before it does anything, whether toggled on or off. See the
              README for setup.
            </p>
            <div className="space-y-3">
              {providers.map((p) => (
                <div key={p.key} className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <StatusDot available={p.available} configured={p.configured} />
                    <span className="text-sm font-medium">{p.label}</span>
                    <span
                      className="font-mono rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wide"
                      style={{
                        background: p.available
                          ? "color-mix(in srgb, var(--turf) 18%, transparent)"
                          : p.configured
                          ? "color-mix(in srgb, var(--amber) 18%, transparent)"
                          : "color-mix(in srgb, var(--ink-soft) 15%, transparent)",
                        color: p.available ? "var(--turf)" : p.configured ? "var(--amber)" : "var(--ink-soft)",
                      }}
                    >
                      {p.available ? "active" : p.configured ? "no key match" : "no api key"}
                    </span>
                  </div>
                  <button
                    onClick={() => handleToggle(p.key, p.enabled)}
                    disabled={toggling === p.key}
                    role="switch"
                    aria-checked={p.enabled}
                    aria-label={`Toggle ${p.label}`}
                    className="relative h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-50"
                    style={{ background: p.enabled ? "var(--turf)" : "var(--line)" }}
                  >
                    <span
                      className="absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform"
                      style={{ transform: p.enabled ? "translateX(22px)" : "translateX(2px)" }}
                    />
                  </button>
                </div>
              ))}
            </div>
            <p className="mt-4 text-xs leading-relaxed" style={{ color: "var(--ink-soft)" }}>
              Set <code className="font-mono">SPORTMONKS_API_KEY</code> and/or{" "}
              <code className="font-mono">API_FOOTBALL_API_KEY</code> as environment
              variables before starting the backend. A provider showing &ldquo;no api
              key&rdquo; is disabled from live results regardless of the toggle above
              until a key is set.
            </p>
          </>
        )}
      </div>
    </details>
  );
}
