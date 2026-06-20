import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Download, Search, Trash2, X } from "lucide-react";
import AppShell from "../components/AppShell.jsx";
import { Button, Panel, Field, Input, Loading, ErrorBlock, EmptyBlock, Banner, relTime } from "../components/ui.jsx";
import { api } from "../lib/api.js";
import { usePolicies } from "../lib/usePolicies.js";

const PAGE_SIZE = 25;

function ScoreBar({ score, minMatch }) {
  if (score == null) return <span className="font-mono text-[10px] text-muted-foreground/60">unscored</span>;
  const eligible = minMatch == null ? true : score >= minMatch;
  return (
    <div className="flex items-center gap-2 justify-end">
      <div className="w-16 h-2 bg-muted">
        <div className={eligible ? "h-full bg-foreground" : "h-full bg-muted-foreground/40"} style={{ width: `${score}%` }} />
      </div>
      <span className={`font-mono text-[11px] tabular-nums w-6 text-right ${eligible ? "" : "text-muted-foreground/60"}`}>{score}</span>
    </div>
  );
}

function Check({ checked, onChange }) {
  return (
    <input
      type="checkbox"
      checked={checked}
      onChange={onChange}
      onClick={(e) => e.stopPropagation()}
      style={{ accentColor: "hsl(var(--foreground))" }}
      className="w-3.5 h-3.5 cursor-pointer align-middle"
    />
  );
}

export default function Jobs() {
  const navigate = useNavigate();
  const { floors } = usePolicies();
  const minMatch = floors?.min_match_score ?? null;

  const [url, setUrl] = useState("");
  const [source, setSource] = useState("careers_page");
  const [scraping, setScraping] = useState(false);
  const [scrapeMsg, setScrapeMsg] = useState(null);
  const [companyFilter, setCompanyFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [state, setState] = useState({ loading: true, error: null, items: [] });

  const [selected, setSelected] = useState(() => new Set());
  const [deleting, setDeleting] = useState(false);
  const [actionMsg, setActionMsg] = useState(null);

  async function load() {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const items = await api.listJobs({ company: companyFilter, limit: PAGE_SIZE, offset });
      setState({ loading: false, error: null, items: items || [] });
    } catch (e) {
      setState({ loading: false, error: e?.detail || "FETCH FAILED", items: [] });
    }
  }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [companyFilter, offset]);
  // Clear selection whenever the visible page/filter changes
  useEffect(() => { setSelected(new Set()); }, [companyFilter, offset]);

  async function scrape() {
    setScrapeMsg(null);
    setScraping(true);
    try {
      const r = await api.scrapeJobs({ url, source });
      setScrapeMsg({ tone: "success", text: `SCRAPED ${r.scraped} · SKIPPED ${r.skipped} (deduped by url)` });
      setOffset(0);
      load();
    } catch (e) {
      setScrapeMsg({ tone: "error", text: e?.detail || "SCRAPE FAILED" });
    } finally {
      setScraping(false);
    }
  }

  const items = state.items;
  const from = items.length === 0 ? 0 : offset + 1;
  const to = offset + items.length;

  const allSelected = items.length > 0 && items.every((j) => selected.has(j.id));
  const someSelected = selected.size > 0;

  function toggle(id) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }
  function toggleAll() {
    setSelected((prev) => {
      if (items.every((j) => prev.has(j.id))) return new Set(); // unselect all on page
      return new Set(items.map((j) => j.id));
    });
  }

  async function deleteSelected() {
    if (selected.size === 0) return;
    if (!window.confirm(`Delete ${selected.size} job(s)? This cannot be undone.`)) return;
    setDeleting(true);
    setActionMsg(null);
    try {
      const ids = [...selected];
      const r = await api.deleteJobs(ids);
      setActionMsg({ tone: "success", text: `DELETED ${r.deleted} JOB(S)` });
      setSelected(new Set());
      await load();
    } catch (e) {
      setActionMsg({ tone: "error", text: e?.detail || "DELETE FAILED" });
    } finally {
      setDeleting(false);
    }
  }

  return (
    <AppShell title="Jobs" subtitle="// POST /API/V1/JOBS/SCRAPE · GET /API/V1/JOBS">
      <div className="p-5 space-y-5 max-w-6xl">
        {/* scrape trigger */}
        <Panel title="Trigger scrape" code="greenhouse / lever / careers page">
          <div className="flex flex-wrap items-end gap-3">
            <Field label="Careers URL" className="flex-1 min-w-[280px]">
              <Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://boards.greenhouse.io/acme" />
            </Field>
            <Field label="Source">
              <Input value={source} onChange={(e) => setSource(e.target.value)} className="w-40" />
            </Field>
            <Button variant="primary" onClick={scrape} disabled={scraping || !url} data-testid="scrape-btn">
              <Download className="w-3.5 h-3.5" /> {scraping ? "Scraping…" : "Scrape"}
            </Button>
          </div>
          {scrapeMsg && <div className="mt-3"><Banner tone={scrapeMsg.tone}>{scrapeMsg.text}</Banner></div>}
        </Panel>

        {/* list */}
        <div>
          {/* Bulk action bar — animates in at the top when rows are selected */}
          <div
            className={`overflow-hidden transition-all duration-300 ease-out ${someSelected ? "max-h-20 opacity-100 mb-3" : "max-h-0 opacity-0 mb-0"}`}
            data-testid="bulk-action-bar"
          >
            <div className="flex items-center justify-between gap-3 border border-foreground bg-foreground text-background px-4 py-2.5">
              <span className="font-mono text-[11px] uppercase tracking-[0.15em] font-bold">
                {selected.size} selected
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSelected(new Set())}
                  data-testid="bulk-clear"
                  className="flex items-center gap-1.5 px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider border border-background/40 hover:bg-background/10"
                >
                  <X className="w-3.5 h-3.5" /> Clear
                </button>
                <button
                  onClick={deleteSelected}
                  disabled={deleting}
                  data-testid="bulk-delete"
                  className="flex items-center gap-1.5 px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider font-bold bg-red-600 text-white hover:bg-red-500 disabled:opacity-50"
                >
                  <Trash2 className="w-3.5 h-3.5" /> {deleting ? "Deleting…" : "Delete selected"}
                </button>
              </div>
            </div>
          </div>

          {actionMsg && <div className="mb-3"><Banner tone={actionMsg.tone} testId="jobs-action-msg">{actionMsg.text}</Banner></div>}

          <div className="flex items-center gap-3 border-b border-border pb-3 mb-3">
            <div className="flex items-center gap-2 flex-1 max-w-xs border-b border-border focus-within:border-foreground">
              <Search className="w-3.5 h-3.5 text-muted-foreground" />
              <input value={companyFilter} onChange={(e) => { setOffset(0); setCompanyFilter(e.target.value); }}
                placeholder="Filter by company…"
                className="flex-1 bg-transparent py-2 font-mono text-[13px] focus:outline-none placeholder:text-muted-foreground/50" />
            </div>
            <span className="ml-auto font-mono text-[10px] text-muted-foreground uppercase tracking-widest">
              SHOWING {from}–{to}{minMatch != null ? ` · MIN_MATCH ${minMatch}` : ""}
            </span>
          </div>

          {state.loading ? <Loading label="FETCHING JOBS…" /> : state.error ? (
            <ErrorBlock message={state.error} onRetry={load} />
          ) : items.length === 0 ? (
            <EmptyBlock message="0 JOBS. RUN A SCRAPE ABOVE." />
          ) : (
            <div className="border border-border">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border bg-muted/40">
                    <th className="w-10 px-3 py-2 text-left">
                      <Check checked={allSelected} onChange={toggleAll} />
                    </th>
                    {["TITLE", "COMPANY", "LOCATION", "SOURCE", "MATCH", "SCRAPED"].map((h, i) => (
                      <th key={h} className={`font-mono text-[9px] tracking-[0.2em] text-muted-foreground uppercase font-semibold px-3 py-2 ${i >= 4 ? "text-right" : "text-left"}`}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {items.map((j) => {
                    const eligible = j.match_score == null || minMatch == null ? true : j.match_score >= minMatch;
                    const isSel = selected.has(j.id);
                    return (
                      <tr key={j.id} data-testid={`job-row-${j.id}`}
                        className={`border-b border-border last:border-0 hover:bg-muted/50 ${isSel ? "bg-muted/60" : ""} ${eligible ? "" : "opacity-50"}`}>
                        <td className="px-3 py-2.5" onClick={(e) => e.stopPropagation()}>
                          <Check checked={isSel} onChange={() => toggle(j.id)} />
                        </td>
                        <td onClick={() => navigate(`/jobs/${j.id}`)} className="px-3 py-2.5 font-mono text-[13px] truncate max-w-0 w-2/5 cursor-pointer">{j.title}</td>
                        <td onClick={() => navigate(`/jobs/${j.id}`)} className="px-3 py-2.5 font-mono text-[11px] text-muted-foreground cursor-pointer">{j.company || "—"}</td>
                        <td onClick={() => navigate(`/jobs/${j.id}`)} className="px-3 py-2.5 font-mono text-[11px] text-muted-foreground cursor-pointer">{j.location || "—"}</td>
                        <td className="px-3 py-2.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{j.source}</td>
                        <td className="px-3 py-2.5"><ScoreBar score={j.match_score} minMatch={minMatch} /></td>
                        <td className="px-3 py-2.5 font-mono text-[11px] text-muted-foreground text-right tabular-nums">{relTime(j.scraped_at)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          <div className="flex items-center justify-between mt-3">
            <div className="font-mono text-[10px] text-muted-foreground/60">
              {minMatch != null ? `// ROWS BELOW ${minMatch} ARE DE-EMPHASIZED — NOT OUTREACH-ELIGIBLE.` : ""}
            </div>
            <div className="flex gap-2">
              <Button variant="secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>Prev</Button>
              <Button variant="secondary" disabled={items.length < PAGE_SIZE} onClick={() => setOffset(offset + PAGE_SIZE)}>Next</Button>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
