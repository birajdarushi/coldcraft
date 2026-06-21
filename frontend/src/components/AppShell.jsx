import { NavLink, useLocation } from "react-router-dom";
import { useTheme } from "../lib/theme.jsx";
import {
  LayoutDashboard, Mail, PenLine, Briefcase, Network,
  SlidersHorizontal, ExternalLink, Sun, Moon, Square,
  GitBranch, Brain
} from "lucide-react";

const NAV = [
  { to: "/", label: "DASHBOARD", code: "01", icon: LayoutDashboard, testId: "nav-dashboard" },
  { to: "/inbox", label: "INBOX", code: "02", icon: Mail, testId: "nav-inbox" },
  { to: "/pipeline", label: "PIPELINE", code: "03", icon: Briefcase, testId: "nav-pipeline" },
  { to: "/apply", label: "APPLY", code: "04", icon: PenLine, testId: "nav-apply" },
  { to: "/network", label: "NETWORK", code: "05", icon: Network, testId: "nav-network" },
  { to: "/roadmap", label: "ROADMAP", code: "06", icon: GitBranch, testId: "nav-roadmap" },
  { to: "/memory", label: "MEMORY", code: "07", icon: Brain, testId: "nav-memory" },
  { to: "/settings", label: "SETTINGS", code: "08", icon: SlidersHorizontal, testId: "nav-settings" },
];

const NAV_PLANNED = [];

const IS_DEV = import.meta.env.DEV;
const API_BASE = import.meta.env.VITE_API_URL || (IS_DEV ? "http://localhost:8000" : "");
const MAILPIT_URL = import.meta.env.VITE_MAILPIT_URL || (IS_DEV ? "http://localhost:8025" : "");

function BrandMark() {
  const size = 28;
  const inner = Math.round(size * 0.43);
  const corner = Math.max(4, Math.round(size * 0.29));
  const off = Math.max(2, Math.round(size * 0.07));
  const border = Math.max(1, Math.round(size * 0.07));

  return (
    <div 
      className="brand-mark-container"
      style={{
        "--logo-size": `${size}px`,
        "--logo-corner": `${corner}px`,
        "--logo-offset": `${off}px`,
        "--logo-border": `${border}px`,
        "--logo-inner": `${inner}px`,
      }}
    >
      <div className="brand-mark-logo" data-testid="brand-mark">
        <div className="brand-mark-inner" />
        <span className="brand-mark-accent" />
      </div>
      <div className="leading-none">
        <div className="font-sans font-extrabold tracking-tighter uppercase text-[18px]">Coldcraft</div>
        <div className="font-mono text-[9px] tracking-[0.25em] text-muted-foreground mt-0.5">GTM·ENGINE</div>
      </div>
    </div>
  );
}

function ApiIndicator() {
  return (
    <div
      data-testid="api-indicator"
      className="flex items-center justify-between gap-2 px-2.5 py-1.5 border border-border bg-background"
      title="Live API connected"
    >
      <div className="flex items-center gap-2">
        <span className="pulse-square w-2 h-2 bg-emerald-500" aria-hidden="true" />
        <span className="font-mono text-[10px] tracking-widest">/api/v1</span>
      </div>
      <span className="font-mono text-[9px] tracking-widest text-muted-foreground">LIVE</span>
    </div>
  );
}

function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      type="button"
      onClick={toggle}
      data-testid="theme-toggle"
      className="flex items-center gap-2 px-2.5 py-1.5 border border-border hover:bg-muted transition-colors w-full"
      aria-label="Toggle theme"
    >
      {theme === "dark" ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
      <span className="font-mono text-[10px] tracking-[0.2em] uppercase">
        MODE:&nbsp;<span className="font-bold">{theme}</span>
      </span>
    </button>
  );
}

function NavItem({ item, planned }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.to === "/"}
      data-testid={item.testId}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2 border-l-2 transition-colors ${
          isActive
            ? "border-foreground bg-muted text-foreground"
            : "border-transparent text-muted-foreground hover:text-foreground hover:bg-muted/60"
        }`
      }
    >
      {IS_DEV && <span className="font-mono text-[9px] w-5">{item.code}</span>}
      <Icon className="w-3.5 h-3.5" />
      <span className="font-mono text-[11px] tracking-[0.2em] uppercase font-medium">{item.label}</span>
      {planned && (
        <span className="ml-auto font-mono text-[8px] tracking-widest text-amber-500/80">SOON</span>
      )}
    </NavLink>
  );
}

function Sidebar() {
  const location = useLocation();
  return (
    <aside className="hidden md:flex md:flex-col w-64 shrink-0 border-r border-border bg-surface">
      <div className="h-16 px-4 flex items-center border-b border-border">
        <BrandMark />
      </div>

      <nav className="flex-1 overflow-y-auto py-3">
        <div className="font-mono text-[9px] tracking-[0.3em] text-muted-foreground/70 px-5 mb-2">NAVIGATION</div>
        <div className="flex flex-col gap-0.5 px-2">
          {NAV.map((item) => <NavItem key={item.label} item={item} />)}
        </div>

        <div className="font-mono text-[9px] tracking-[0.3em] text-muted-foreground/70 px-5 mt-5 mb-2">PLANNED · PHASE 3–4</div>
        <div className="flex flex-col gap-0.5 px-2">
          {NAV_PLANNED.map((item) => <NavItem key={item.label} item={item} planned />)}
        </div>
      </nav>

      <div className="border-t border-border p-3 space-y-2">
        <div className="font-mono text-[9px] tracking-[0.3em] text-muted-foreground/70 px-1 mb-1">UTILITIES</div>
        {MAILPIT_URL && (
          <a
            href={MAILPIT_URL}
            target="_blank"
            rel="noopener noreferrer"
            data-testid="util-mailpit"
            className="flex items-center justify-between gap-2 px-2.5 py-1.5 border border-border hover:bg-muted text-[10px] font-mono tracking-wider uppercase"
          >
            <span>Mailpit inbox</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        )}
        {API_BASE && (
          <a
            href={`${API_BASE}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            data-testid="util-api-docs"
            className="flex items-center justify-between gap-2 px-2.5 py-1.5 border border-border hover:bg-muted text-[10px] font-mono tracking-wider uppercase"
          >
            <span>API docs</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        )}
        <ApiIndicator />
        <ThemeToggle />
      </div>

      {IS_DEV && (
        <div className="px-4 py-3 border-t border-border">
          <div className="font-mono text-[9px] tracking-[0.25em] text-muted-foreground/60 leading-relaxed truncate">
            {location.pathname} · v0.1·mock
          </div>
        </div>
      )}
    </aside>
  );
}

function TopBar({ title, subtitle, right }) {
  return (
    <header className="h-16 shrink-0 border-b border-border bg-background flex items-center justify-between px-6 gap-4">
      <div className="flex items-baseline gap-4 min-w-0">
        <h1 className="font-sans uppercase tracking-tighter text-2xl font-extrabold leading-none truncate">
          {title}
        </h1>
        {IS_DEV && subtitle && (
          <span className="hidden lg:inline font-mono text-[10px] tracking-[0.2em] text-muted-foreground uppercase truncate">
            {subtitle}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">{right}</div>
    </header>
  );
}

export default function AppShell({ title, subtitle, right, children }) {
  return (
    <div className="h-screen overflow-hidden flex bg-background text-foreground">
      <Sidebar />
      <main className="flex-1 flex flex-col min-w-0 h-screen">
        <TopBar title={title} subtitle={subtitle} right={right} />
        <div className="flex-1 min-h-0 overflow-y-auto">{children}</div>
      </main>
    </div>
  );
}
