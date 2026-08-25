"use client";

import { useEffect, useRef, useState } from "react";

interface TeamSelectProps {
  label: string;
  teams: string[];
  value: string;
  onChange: (team: string) => void;
  accentVar: string; // css var name for the focus/highlight color
}

export function TeamSelect({ label, teams, value, onChange, accentVar }: TeamSelectProps) {
  const [query, setQuery] = useState(value);
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => setQuery(value), [value]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filtered = teams
    .filter((t) => t.toLowerCase().includes(query.toLowerCase()))
    .slice(0, 8);

  function selectTeam(team: string) {
    onChange(team);
    setQuery(team);
    setOpen(false);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!open) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlight((h) => Math.min(h + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((h) => Math.max(h - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filtered[highlight]) selectTeam(filtered[highlight]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={containerRef} className="relative w-full">
      <label
        className="font-display mb-1.5 block text-xs font-semibold uppercase tracking-widest"
        style={{ color: "var(--ink-soft)" }}
      >
        {label}
      </label>
      <input
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-autocomplete="list"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          setHighlight(0);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder="Search team…"
        className="w-full rounded-lg border px-4 py-3 text-lg font-medium outline-none transition-colors"
        style={{
          background: "var(--bg-elevated)",
          borderColor: "var(--line)",
          color: "var(--ink)",
        }}
      />
      {open && filtered.length > 0 && (
        <ul
          className="absolute z-20 mt-1 max-h-64 w-full overflow-y-auto rounded-lg border shadow-lg"
          style={{ background: "var(--bg-elevated)", borderColor: "var(--line)" }}
        >
          {filtered.map((team, i) => (
            <li key={team}>
              <button
                type="button"
                onClick={() => selectTeam(team)}
                onMouseEnter={() => setHighlight(i)}
                className="block w-full px-4 py-2.5 text-left text-sm transition-colors"
                style={{
                  background: i === highlight ? `color-mix(in srgb, var(${accentVar}) 14%, transparent)` : "transparent",
                  color: "var(--ink)",
                }}
              >
                {team}
              </button>
            </li>
          ))}
        </ul>
      )}
      {open && query && filtered.length === 0 && (
        <div
          className="absolute z-20 mt-1 w-full rounded-lg border px-4 py-3 text-sm"
          style={{ background: "var(--bg-elevated)", borderColor: "var(--line)", color: "var(--ink-soft)" }}
        >
          No teams match &ldquo;{query}&rdquo;
        </div>
      )}
    </div>
  );
}
