"use client";

export function RevealToggleButton({
  revealed, onClick, showLabel = "Show other outcomes", hideLabel = "Hide other outcomes", size = "md",
}: {
  revealed: boolean;
  onClick: () => void;
  showLabel?: string;
  hideLabel?: string;
  size?: "sm" | "md";
}) {
  const padding = size === "sm" ? "px-3 py-1.5 text-xs" : "px-4 py-2 text-xs";
  return (
    <button
      type="button"
      onClick={onClick}
      aria-expanded={revealed}
      className={`inline-flex items-center gap-1.5 rounded-full border font-semibold uppercase tracking-wide transition-colors ${padding}`}
      style={{ borderColor: "var(--line)", color: "var(--ink-soft)" }}
    >
      <span
        className="inline-block text-[10px] transition-transform duration-200"
        style={{ transform: revealed ? "rotate(180deg)" : "none" }}
      >
        ▾
      </span>
      {revealed ? hideLabel : showLabel}
    </button>
  );
}
