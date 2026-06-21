import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { RefreshCw, PenLine } from "lucide-react";
import AppShell from "../components/AppShell.jsx";
import ConstitutionPanel from "../components/ConstitutionPanel.jsx";
import StatusPill from "../components/StatusPill.jsx";
import { Button, Panel, Overline, Loading, ErrorBlock } from "../components/ui.jsx";
import { api } from "../lib/api.js";
import { useFetch } from "../lib/useFetch.js";
import { usePolicies } from "../lib/usePolicies.js";
import { STATUS_ORDER } from "../lib/constants.js";

function Metric({ label, value, sub, loading, error }) {
  return (
    <div className="border border-border bg-surface p-4 flex flex-col justify-between min-h-[150px]" data-testid={`metric-${label}`}>
      <Overline>{label}</Overline>
      <div className="mt-2">
        {error ? (
          <div className="font-mono text-sm text-red-600 dark:text-red-400 uppercase tracking-wider">ERR_FETCH</div>
        ) : loading ? (
          <div className="font-mono text-sm text-muted-foreground uppercase tracking-wider">AWAITING…</div>
        ) : (
          <div className="font-mono text-6xl font-light tracking-tighter tabular-nums leading-none">{value}</div>
        )}
      </div>
      <div className="font-mono text-[10px] text-muted-foreground/70 mt-3">{sub}</div>
    </div>
  );
}

export default function Dashboard() {
  const { data: stats, loading, error, reload } = useFetch(() => api.getStats(), []);
  const { policies } = usePolicies();
  const [campaigns, setCampaigns] = useState(null);

  async function loadCampaigns() {
    try { setCampaigns(await api.listCampaigns({ limit: 1000 })); }
    catch { setCampaigns([]); }
  }
  useEffect(() => { loadCampaigns(); }, []);

  function refresh() { reload(); loadCampaigns(); }

  const right = (
    <>
      <Link to="/campaigns?status=qa_passed"><Button variant="secondary">Review approvals</Button></Link>
      <Link to="/compose"><Button variant="primary"><PenLine className="w-3.5 h-3.5" /> Compose new</Button></Link>
      <Button variant="ghost" onClick={refresh} data-testid="refresh-stats"><RefreshCw className="w-3.5 h-3.5" /> Refresh</Button>
    </>
  );

  // Daily envelope derived from real stats + effective policy
  const effLimit = policies
    ? (policies.daily_send_limit ?? policies.constitution_floors?.daily_send_limit)
    : null;
  const sentToday = stats?.sent_today ?? 0;
  const remaining = effLimit != null ? Math.max(0, effLimit - sentToday) : null;

  // Status breakdown derived from the real campaigns list
  const counts = {};
  (campaigns || []).forEach((c) => { counts[c.status] = (counts[c.status] || 0) + 1; });
  const present = STATUS_ORDER.filter((s) => counts[s]);

  return (
    <AppShell title="Dashboard" subtitle="// OPERATIONS OVERVIEW · GET /API/V1/STATS" right={right}>
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_300px] gap-px bg-border">
        {/* main column */}
        <div className="bg-background p-5 space-y-5">
          {error && <ErrorBlock message="UNABLE TO FETCH STATS" onRetry={refresh} testId="stats-error" />}

          {/* hero metrics — straight from /api/v1/stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Metric label="Sent today" loading={loading} error={error}
              value={stats?.sent_today}
              sub={effLimit != null ? `${remaining} remaining · cap ${effLimit}/day` : (import.meta.env.DEV ? "GET /stats" : "")} />
            <Metric label="Open rate" loading={loading} error={error}
              value={stats ? `${(stats.open_rate * 100).toFixed(1)}%` : ""}
              sub="(opened + replied) / sent" />
            <Metric label="Pending approvals" loading={loading} error={error}
              value={stats?.pending_approvals}
              sub="qa_passed + user_approved" />
          </div>

          {/* daily envelope — derived from /stats + /policies */}
          <Panel title="Daily envelope" code="sent_today vs effective daily limit">
            {loading || effLimit == null ? <Loading /> : (
              <>
                <div className="flex items-baseline gap-2 mb-3">
                  <span className="font-mono text-2xl font-light tabular-nums">{sentToday} / {effLimit}</span>
                  <span className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest">sent · {remaining} remaining</span>
                </div>
                <div className="flex gap-0.5 h-6">
                  {Array.from({ length: effLimit }).map((_, i) => (
                    <div key={i} className={`flex-1 ${i < sentToday ? "bg-foreground" : "bg-muted"}`} />
                  ))}
                </div>
                <div className="font-mono text-[10px] text-muted-foreground mt-2">
                  When the envelope fills, the preflight daily-limit gate blocks new drafts.
                </div>
              </>
            )}
          </Panel>

          {/* status breakdown — derived from the real campaigns list */}
          <Panel title="Campaign status breakdown" code="GET /campaigns (aggregated client-side)">
            {campaigns == null ? <Loading /> : present.length === 0 ? (
              <div className="font-mono text-[11px] text-muted-foreground">NO CAMPAIGNS YET.</div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                {present.map((s) => (
                  <Link key={s} to={`/campaigns?status=${s}`}
                    className="border border-border bg-background p-3 hover:bg-muted transition-colors">
                    <div className="font-mono text-3xl font-light tabular-nums leading-none">{counts[s]}</div>
                    <div className="mt-2"><StatusPill status={s} /></div>
                  </Link>
                ))}
              </div>
            )}
          </Panel>

          {import.meta.env.DEV && (
            <div className="font-mono text-[10px] text-muted-foreground/60">
              // ALL VALUES FROM /api/v1. ZEROS ARE VALID DATA. NO FABRICATED METRICS.
            </div>
          )}
        </div>

        {/* right rail */}
        <div className="bg-background p-5">
          <ConstitutionPanel />
        </div>
      </div>
    </AppShell>
  );
}
