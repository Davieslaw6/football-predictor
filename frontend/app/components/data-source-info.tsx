"use client";

import { useEffect, useState } from "react";
import { DataSourceStatus, fetchDataSourceStatus } from "../lib/api";

export function DataSourceInfo() {
  const [status, setStatus] = useState<DataSourceStatus | null>(null);

  useEffect(() => {
    fetchDataSourceStatus().then(setStatus).catch(() => setStatus(null));
  }, []);

  if (!status) {
    return (
      <div className="mt-8 rounded-2xl border px-5 py-4 text-xs" style={{ borderColor: "var(--line)", background: "var(--bg-elevated)", color: "var(--ink-soft)" }}>
        <span className="football-spinner mr-2" aria-hidden="true">⚽</span>
        Checking prediction data source…
      </div>
    );
  }

  return (
    <section
      className="source-badge mt-8 rounded-2xl px-5 py-4"
      aria-label="Prediction data source"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="football-spinner text-base" aria-hidden="true">⚽</span>
          <span className="font-display text-sm font-bold uppercase tracking-widest">Prediction data source</span>
        </div>
        <span
          className="rounded-full px-3 py-1 font-mono text-[10px] font-semibold uppercase tracking-wider"
          style={{ background: "color-mix(in srgb, var(--turf) 16%, transparent)", color: "var(--turf)" }}
        >
          {status.prediction_source === "local" ? "LOCAL DATA" : "API DATA"}
        </span>
      </div>

      <p className="mt-2 text-xs leading-relaxed" style={{ color: "var(--ink-soft)" }}>
        {status.note}
      </p>

      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 font-mono text-[10px]" style={{ color: "var(--ink-soft)" }}>
        <span>
          Dataset: <strong style={{ color: "var(--ink)" }}>{status.dataset_available ? "available" : "not found"}</strong>
        </span>
        {status.dataset_last_updated && (
          <span>
            Last dataset update: <strong style={{ color: "var(--ink)" }}>{new Date(status.dataset_last_updated).toLocaleString()}</strong>
          </span>
        )}
        <span>
          API keys configured: <strong style={{ color: "var(--ink)" }}>
            {status.api_providers_configured.length ? status.api_providers_configured.join(", ") : "none"}
          </strong>
        </span>
      </div>
    </section>
  );
}
