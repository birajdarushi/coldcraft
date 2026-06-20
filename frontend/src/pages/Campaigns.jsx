import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { RefreshCw, PenLine, Search, ChevronDown } from "lucide-react";
import AppShell from "../components/AppShell.jsx";
import StatusPill from "../components/StatusPill.jsx";
import { Button, Loading, ErrorBlock, EmptyBlock, relTime } from "../components/ui.jsx";
import { api } from "../lib/api.js";
import { STATUS_ORDER, STATUS_LABELS } from "../lib/constants.js";

const PAGE_SIZE = 25;

export default function Campaigns() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const status = params.get("status") || "";
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [statusOpen, setStatusOpen] = useState(false);

  async function load() {
    setState({ loading: true, error: null, data: null });
    try {
      const res = await api.listCampaigns({ status, limit: PAGE_SIZE, offset });
      setState({ loading: false, error: null, data: Array.isArray(res) ? res : [] });
    } catch (e) {
      setState({ loading: false, error: e?.detail || "UNABLE TO FETCH CAMPAIGNS", data: null });
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [status, offset]);

  function setStatus(s) {
    setOffset(0);
    setStatusOpen(false);
    if (s) setParams({ status: s });
    else setParams({});
  }

  const pageItems = state.data || [];
  const rows = pageItems.filter((c) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (c.subject || "").toLowerCase().includes(q) || (c.recipient || "").toLowerCase().includes(q);
  });
  const from = pageItems.length === 0 ? 0 : offset + 1;
  const to = offset + pageItems.length;
  const hasMore = pageItems.length >= PAGE_SIZE;

  const right = (
    <>
      <Button variant="ghost" onClick={load} data-testid="refresh-campaigns"><RefreshCw className="w-3.5 h-3.5" /> Refresh</Button>
      <Link to="/compose"><Button variant="primary"><PenLine className="w-3.5 h-3.5" /> Compose new</Button></Link>
    </>
  );

  return (
    <AppShell title="Campaigns" subtitle="// GET /API/V1/CAMPAIGNS · SERVER-SIDE FILTER + PAGINATE" right={right}>
      <div className="p-5 space-y-4">
        {/* controls */}
        <div className="flex flex-wrap items-center gap-3 border-b border-border pb-3">
          <div className="flex items-center gap-2 flex-1 min-w-[240px] border-b border-border focus-within:border-foreground">
            <Search className="w-3.5 h-3.5 text-muted-foreground" />
            <input
              data-testid="campaign-search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search subject or recipient…"
              className="flex-1 bg-transparent py-2 font-mono text-[13px] focus:outline-none placeholder:text-muted-foreground/50"
            />
          </div>

          <div className="relative">
            <button
              data-testid="status-filter"
              onClick={() => setStatusOpen((o) => !o)}
              className="flex items-center gap-2 border border-border px-3 py-2 font-mono text-[11px] uppercase tracking-wider hover:bg-muted"
            >
              <span className="text-muted-foreground">STATUS:</span>
              <span className="font-bold">{status ? STATUS_LABELS[status] : "ALL"}</span>
              <ChevronDown className="w-3 h-3" />
            </button>
            {statusOpen && (
              <div className="absolute z-20 right-0 mt-1 w-48 border border-border bg-surface shadow-lg">
                {["", ...STATUS_ORDER].map((s) => (
                  <button
                    key={s || "all"}
                    onClick={() => setStatus(s)}
                    className={`block w-full text-left px-3 py-2 font-mono text-[11px] uppercase tracking-wider hover:bg-muted ${
                      status === s ? "bg-muted font-bold" : "text-muted-foreground"
                    }`}
                  >
                    {s ? STATUS_LABELS[s] : "ALL"}
                  </button>
                ))}
              </div>
            )}
          </div>

          <span className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest ml-auto">
            SHOWING {from}–{to}
          </span>
        </div>

        {/* table */}
        {state.loading ? (
          <Loading label="FETCHING CAMPAIGNS…" />
        ) : state.error ? (
          <ErrorBlock message={state.error} onRetry={load} testId="campaigns-error" />
        ) : rows.length === 0 ? (
          <EmptyBlock
            message="0 RESULTS. INITIATE CAMPAIGN VIA COMPOSE."
            action={<Link to="/compose"><Button variant="primary"><PenLine className="w-3.5 h-3.5" /> Compose new</Button></Link>}
          />
        ) : (
          <div className="border border-border">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-muted/40">
                  {["#", "SUBJECT", "RECIPIENT", "STATUS", "CREATED", "WORDS"].map((h, i) => (
                    <th key={h} className={`font-mono text-[9px] tracking-[0.2em] text-muted-foreground uppercase font-semibold px-3 py-2 ${i >= 4 ? "text-right" : "text-left"} ${i === 0 ? "w-10" : ""}`}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((c, i) => (
                  <tr
                    key={c.id}
                    data-testid={`campaign-row-${c.id}`}
                    onClick={() => navigate(`/campaigns/${c.id}`)}
                    className="border-b border-border last:border-0 hover:bg-muted/50 cursor-pointer"
                  >
                    <td className="px-3 py-2.5 font-mono text-[11px] text-muted-foreground/60 tabular-nums">{String(offset + i + 1).padStart(2, "0")}</td>
                    <td className="px-3 py-2.5 font-mono text-[13px] truncate max-w-0 w-1/2">
                      {c.subject || <span className="text-muted-foreground/60 italic">(no subject)</span>}
                    </td>
                    <td className="px-3 py-2.5 font-mono text-[11px] text-muted-foreground">{c.recipient}</td>
                    <td className="px-3 py-2.5"><StatusPill status={c.status} /></td>
                    <td className="px-3 py-2.5 font-mono text-[11px] text-muted-foreground text-right tabular-nums">{relTime(c.created_at)}</td>
                    <td className="px-3 py-2.5 font-mono text-[11px] text-right tabular-nums">{c.word_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* pagination */}
        <div className="flex items-center justify-between border-t border-border pt-3">
          <span className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest">
            PAGE {Math.floor(offset / PAGE_SIZE) + 1} · LIMIT={PAGE_SIZE}&amp;OFFSET={offset}
          </span>
          <div className="flex gap-2">
            <Button variant="secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>Prev</Button>
            <Button variant="secondary" disabled={!hasMore} onClick={() => setOffset(offset + PAGE_SIZE)}>Next</Button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
