"use client";

import { useTheme } from "./theme-context";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <button
      onClick={toggleTheme}
      aria-label={`Switch to ${isDark ? "light" : "dark"} mode`}
      className="theme-toggle relative flex items-center gap-1 rounded-full border p-1 cursor-pointer"
      style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
    >
      <span
        className="flex h-8 w-8 items-center justify-center rounded-full text-sm transition-all duration-300"
        style={{
          background: !isDark ? "var(--turf)" : "transparent",
          color: !isDark ? "var(--bg-elevated)" : "var(--ink-soft)",
          transform: !isDark ? "rotate(0deg) scale(1.05)" : "rotate(-15deg) scale(.9)",
        }}
      >☀</span>
      <span
        className="flex h-8 w-8 items-center justify-center rounded-full text-sm transition-all duration-300"
        style={{
          background: isDark ? "var(--turf)" : "transparent",
          color: isDark ? "var(--bg-elevated)" : "var(--ink-soft)",
          transform: isDark ? "rotate(0deg) scale(1.05)" : "rotate(15deg) scale(.9)",
        }}
      >☾</span>
    </button>
  );
}
