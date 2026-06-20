import { STATUS_LABELS } from "../lib/constants.js";

// Terminal/operator-console status tag. Sharp corners. Mono.
// Each status gets a distinct typographic treatment + glyph — not just colored dots.
const STYLES = {
  draft: "border border-neutral-400 text-neutral-500 dark:border-neutral-600 dark:text-neutral-400",
  self_review: "border border-amber-600/70 text-amber-700 dark:border-amber-400/70 dark:text-amber-300",
  qa_passed: "border border-blue-600 text-blue-700 dark:border-blue-400 dark:text-blue-300",
  user_approved: "border border-emerald-600 text-emerald-700 bg-emerald-500/10 dark:border-emerald-400 dark:text-emerald-300",
  sent: "bg-foreground text-background border border-foreground",
  opened: "border border-violet-600 text-violet-700 dark:border-violet-400 dark:text-violet-300",
  clicked: "border-l-2 border-r-2 border-y border-cyan-600 text-cyan-700 dark:border-cyan-400 dark:text-cyan-300",
  replied: "bg-emerald-600 text-white dark:bg-emerald-400 dark:text-black border border-emerald-700 dark:border-emerald-400",
  blocked: "border border-red-600 text-red-700 bg-red-500/10 dark:border-red-400 dark:text-red-300",
};

const GLYPHS = {
  draft: "◇",
  self_review: "◐",
  qa_passed: "◈",
  user_approved: "✓",
  sent: "▶",
  opened: "◉",
  clicked: "↗",
  replied: "↩",
  blocked: "✕",
};

export default function StatusPill({ status, className = "", testId }) {
  const cls = STYLES[status] || STYLES.draft;
  return (
    <span
      data-testid={testId || `status-pill-${status}`}
      className={`inline-flex items-center gap-1.5 px-1.5 py-[2px] text-[10px] font-mono uppercase tracking-[0.12em] font-semibold ${cls} ${className}`}
    >
      <span aria-hidden="true" className="text-[11px] leading-none">{GLYPHS[status] || "·"}</span>
      <span>{STATUS_LABELS[status] || status}</span>
    </span>
  );
}
