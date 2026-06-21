// Primitive UI building blocks for the operator console.
// Sharp corners, mono type, high contrast — per the Coldcraft design system.

// Dev-only annotations (endpoint hints, screen codes) are hidden in production.
const IS_DEV = import.meta.env.DEV;

export function Button({ variant = "secondary", className = "", children, ...props }) {
  const base =
    "inline-flex items-center justify-center gap-2 px-4 py-2 font-mono text-[11px] uppercase font-bold tracking-[0.12em] transition-opacity disabled:opacity-40 disabled:cursor-not-allowed";
  const variants = {
    primary: "bg-foreground text-background hover:opacity-80",
    secondary: "bg-transparent border border-border text-foreground hover:bg-muted",
    danger: "bg-transparent border border-red-500 text-red-600 dark:text-red-400 hover:bg-red-500/10",
    ghost: "bg-transparent text-muted-foreground hover:text-foreground hover:bg-muted",
  };
  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}

// Bordered surface panel. Optional title row with overline + actions.
export function Panel({ title, code, right, className = "", bodyClass = "", children }) {
  return (
    <section className={`border border-border bg-surface ${className}`}>
      {(title || right) && (
        <header className="flex items-center justify-between gap-3 px-4 h-10 border-b border-border">
          <div className="flex items-baseline gap-2 min-w-0">
            {title && <Overline>{title}</Overline>}
            {IS_DEV && code && <span className="font-mono text-[9px] text-muted-foreground/60 truncate">{code}</span>}
          </div>
          {right}
        </header>
      )}
      <div className={`p-4 ${bodyClass}`}>{children}</div>
    </section>
  );
}

export function Overline({ children, className = "" }) {
  return (
    <span className={`font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground ${className}`}>
      {children}
    </span>
  );
}

export function Field({ label, hint, children, className = "" }) {
  return (
    <label className={`block ${className}`}>
      <div className="flex items-baseline justify-between mb-1.5">
        <Overline>{label}</Overline>
        {hint && <span className="font-mono text-[9px] text-muted-foreground/70">{hint}</span>}
      </div>
      {children}
    </label>
  );
}

export function Input({ className = "", ...props }) {
  return (
    <input
      className={`w-full bg-background border border-border px-3 py-2 font-mono text-[13px] text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-foreground transition-colors ${className}`}
      {...props}
    />
  );
}

export function Textarea({ className = "", ...props }) {
  return (
    <textarea
      className={`w-full bg-background border border-border px-3 py-2 font-mono text-[13px] leading-relaxed text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-foreground transition-colors ${className}`}
      {...props}
    />
  );
}

export function Select({ className = "", children, ...props }) {
  return (
    <select
      className={`bg-background border border-border px-3 py-2 font-mono text-[12px] uppercase tracking-wider text-foreground focus:outline-none focus:border-foreground ${className}`}
      {...props}
    >
      {children}
    </select>
  );
}

export function Toggle({ checked, onChange, testId }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      data-testid={testId}
      onClick={() => onChange(!checked)}
      className={`w-12 h-6 border flex items-center px-0.5 transition-colors ${
        checked ? "bg-foreground border-foreground justify-end" : "bg-background border-border justify-start"
      }`}
    >
      <span className={`block w-4 h-4 ${checked ? "bg-background" : "bg-muted-foreground"}`} />
    </button>
  );
}

// State blocks --------------------------------------------------------------

export function Loading({ label = "AWAITING DATA…" }) {
  return (
    <div className="flex items-center gap-3.5 py-8 px-1">
      <div className="brand-loader-base">
        <div className="brand-loader-walker" />
      </div>
      <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">{label}</span>
    </div>
  );
}

export function ErrorBlock({ message = "ERR_FETCH_FAILED", onRetry, testId }) {
  return (
    <div data-testid={testId} className="border border-red-500 bg-red-500/5 p-4">
      <div className="flex items-center justify-between gap-3">
        <span className="font-mono text-[11px] uppercase tracking-[0.15em] text-red-600 dark:text-red-400">
          ERR: {message}
        </span>
        {onRetry && (
          <Button variant="danger" onClick={onRetry} className="!py-1">Retry</Button>
        )}
      </div>
    </div>
  );
}

export function EmptyBlock({ message = "0 RESULTS", action }) {
  return (
    <div className="border border-dashed border-border p-8 text-center">
      <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">{message}</div>
      {action && <div className="mt-3 flex justify-center">{action}</div>}
    </div>
  );
}

export function Banner({ tone = "info", children, testId }) {
  const tones = {
    info: "border-border bg-muted text-foreground",
    success: "border-emerald-500 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
    error: "border-red-500 bg-red-500/10 text-red-600 dark:text-red-400",
    warn: "border-amber-500 bg-amber-500/10 text-amber-700 dark:text-amber-300",
  };
  return (
    <div data-testid={testId} className={`border px-3 py-2 font-mono text-[11px] tracking-wide ${tones[tone]}`}>
      {children}
    </div>
  );
}

export function Tag({ children, className = "" }) {
  return (
    <span className={`inline-block border border-border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground ${className}`}>
      {children}
    </span>
  );
}

export function PlannedBadge() {
  return (
    <span className="inline-flex items-center gap-1.5 border border-amber-500 text-amber-600 dark:text-amber-400 px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-[0.15em]">
      ◷ PLANNED
    </span>
  );
}

export function LiveBadge({ kind = "LIVE" }) {
  const map = {
    LIVE: "border-emerald-500 text-emerald-600 dark:text-emerald-400",
    PARTIAL: "border-blue-500 text-blue-600 dark:text-blue-400",
  };
  return (
    <span className={`inline-flex items-center gap-1.5 border px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-[0.15em] ${map[kind]}`}>
      {kind}
    </span>
  );
}

// Relative time helper
export function relTime(iso) {
  if (!iso) return "—";
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return "—";
  const diff = Date.now() - then;
  const m = Math.round(diff / 60000);
  if (m < 1) return "now";
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.round(h / 24);
  return `${d}d ago`;
}
