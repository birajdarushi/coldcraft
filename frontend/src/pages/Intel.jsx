import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Play, RefreshCw, PenLine, AlertTriangle } from "lucide-react";
import AppShell from "../components/AppShell.jsx";
import { Button, Panel, Input, Banner, Overline, Tag, Loading } from "../components/ui.jsx";
import { api } from "../lib/api.js";
import { useRateLimit } from "../lib/useRateLimit.js";

const SECTION_ORDER = [
  "company_fundamentals",
  "engineering_culture",
  "hiring_signals",
  "recent_activity",
  "recipient_intelligence",
  "outreach_readiness",
  "sources_and_limitations",
];

function Section({ index, data }) {
  return (
    <Panel
      title={`${String(index + 1).padStart(2, "0")} · ${data.title}`}
      right={data.sources?.length ? <span className="font-mono text-[9px] text-muted-foreground">{data.sources.length} SRC</span> : null}
    >
      <p className="font-mono text-[12.5px] leading-relaxed text-foreground/90">{data.content}</p>
      {data.sources?.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-3">
          {data.sources.map((s, i) => <Tag key={i}>{s}</Tag>)}
        </div>
      )}
      {data.caveat && (
        <div className="mt-3 flex items-start gap-2 border border-amber-500/60 bg-amber-500/5 px-2 py-1.5">
          <AlertTriangle className="w-3 h-3 text-amber-500 shrink-0 mt-0.5" />
          <span className="font-mono text-[10px] leading-relaxed text-amber-700 dark:text-amber-300">{data.caveat}</span>
        </div>
      )}
    </Panel>
  );
}

export default function Intel() {
  const [params] = useSearchParams();
  const [company, setCompany] = useState(params.get("company") || "Stripe");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const rl = useRateLimit();

  async function generate(force = false) {
    setLoading(true); setError(null);
    try {
      const r = await api.generateIntel({ company, force_refresh: force });
      setReport(r);
    } catch (e) {
      if (rl.isRateLimit(e)) rl.start(60);
      setError(e?.detail || "GENERATION FAILED");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell title="Intel" subtitle="// POST /API/V1/INTEL/REPORTS · 7-SECTION READINESS DOSSIER">
      <div className="p-5 max-w-4xl space-y-4">
        <Panel title="Target company" code="generates company_intel for compose">
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <Input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="e.g. 37signals" />
            </div>
            <Button variant="primary" onClick={() => generate(false)} disabled={loading || rl.active || !company} data-testid="generate-intel">
              <Play className="w-3.5 h-3.5" /> {loading ? "Generating…" : rl.active ? `Retry in ${rl.remaining}s` : "Generate"}
            </Button>
            {report && (
              <Button variant="secondary" onClick={() => generate(true)} disabled={loading || rl.active}>
                <RefreshCw className="w-3.5 h-3.5" /> {rl.active ? `Retry in ${rl.remaining}s` : "Regenerate"}
              </Button>
            )}
          </div>
        </Panel>

        {error && <Banner tone="error">{error}</Banner>}
        {loading && <Loading label="COMPILING DOSSIER…" />}

        {report && !loading && (
          <>
            <div className="flex items-center justify-between border border-border bg-surface px-4 py-3">
              <div className="flex items-baseline gap-3">
                <span className="font-sans text-xl font-bold tracking-tight">{report.company}</span>
                <Tag className={report.cached ? "border-blue-500 text-blue-600 dark:text-blue-400" : "border-emerald-500 text-emerald-600 dark:text-emerald-400"}>
                  {report.cached ? "CACHED" : "FRESH"}
                </Tag>
                <span className="font-mono text-[10px] text-muted-foreground">gen {new Date(report.generated_at).toLocaleString()}</span>
              </div>
              <Link to="/compose">
                <Button variant="primary"><PenLine className="w-3.5 h-3.5" /> Use for a draft</Button>
              </Link>
            </div>

            <Banner tone="warn" testId="sample-caveat">
              <AlertTriangle className="inline w-3 h-3 mr-1 -mt-0.5" />
              DEV PROVIDER · SECTIONS CARRY SAMPLE-DATA CAVEATS. PROVENANCE SHOWN PER SECTION.
            </Banner>

            <div className="grid grid-cols-1 gap-4">
              {(() => {
                const keys = Object.keys(report.sections || {});
                const ordered = [
                  ...SECTION_ORDER.filter((k) => keys.includes(k)),
                  ...keys.filter((k) => !SECTION_ORDER.includes(k)),
                ];
                return ordered.map((key, i) => (
                  <Section key={key} index={i} data={report.sections[key]} />
                ));
              })()}
            </div>
          </>
        )}

        {!report && !loading && !error && (
          <div className="border border-dashed border-border p-8 text-center">
            <Overline>No report yet</Overline>
            <p className="font-mono text-[11px] text-muted-foreground mt-2">Enter a company and generate a readiness dossier.</p>
          </div>
        )}
      </div>
    </AppShell>
  );
}
