import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ExternalLink, FileSearch, PenLine } from "lucide-react";
import AppShell from "../components/AppShell.jsx";
import { Button, Panel, Overline, Loading, ErrorBlock, LiveBadge } from "../components/ui.jsx";
import { api } from "../lib/api.js";
import { usePolicies } from "../lib/usePolicies.js";

// The backend exposes GET /jobs (list) but no GET /jobs/{id}; derive detail
// from the list. Descriptions arrive HTML-escaped — decode + strip to text.
function decodeStrip(html) {
  if (!html) return "";
  const txt = document.createElement("textarea");
  txt.innerHTML = html;
  const decoded = txt.value;
  const div = document.createElement("div");
  div.innerHTML = decoded;
  return (div.textContent || div.innerText || "").replace(/\s+/g, " ").trim();
}

export default function JobDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { floors } = usePolicies();
  const minMatch = floors?.min_match_score ?? null;

  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      setLoading(true); setError(null);
      try {
        const list = await api.listJobs({ limit: 1000 });
        const found = (list || []).find((j) => j.id === id);
        if (!found) throw new Error("JOB NOT FOUND IN LIST");
        setJob(found);
      } catch (e) { setError(e?.detail || e?.message || "JOB NOT FOUND"); }
      finally { setLoading(false); }
    })();
  }, [id]);

  const eligible = job?.match_score == null || minMatch == null ? false : job.match_score >= minMatch;
  const right = <Link to="/jobs"><Button variant="ghost"><ArrowLeft className="w-3.5 h-3.5" /> All jobs</Button></Link>;

  return (
    <AppShell title="Job" subtitle="// DERIVED FROM GET /API/V1/JOBS (no /jobs/{id} endpoint)" right={right}>
      <div className="p-5 max-w-4xl space-y-4">
        {loading ? <Loading /> : error ? <ErrorBlock message={error} /> : (
          <>
            <div className="flex items-center gap-2">
              <LiveBadge kind="PARTIAL" />
              <span className="font-mono text-[10px] text-muted-foreground">detail derived from list item</span>
            </div>

            <Panel>
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="font-sans text-2xl font-bold tracking-tight">{job.title}</div>
                  <div className="font-mono text-[12px] text-muted-foreground mt-1">{job.company || "—"}{job.location ? ` · ${job.location}` : ""}</div>
                </div>
                {job.url && (
                  <a href={job.url} target="_blank" rel="noreferrer">
                    <Button variant="secondary"><ExternalLink className="w-3.5 h-3.5" /> Posting</Button>
                  </a>
                )}
              </div>

              <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-border">
                <div>
                  <Overline>Match score</Overline>
                  <div className={`font-mono text-3xl font-light tabular-nums mt-1 ${job.match_score == null || !eligible ? "text-muted-foreground/60" : ""}`}>
                    {job.match_score ?? "—"}
                  </div>
                  <div className={`font-mono text-[10px] mt-1 ${job.match_score == null ? "text-muted-foreground" : eligible ? "text-emerald-600 dark:text-emerald-400" : "text-red-500"}`}>
                    {job.match_score == null ? "UNSCORED" : eligible ? "OUTREACH-ELIGIBLE" : `BELOW MIN (${minMatch})`}
                  </div>
                </div>
                <div><Overline>Source</Overline><div className="font-mono text-[12px] uppercase mt-1">{job.source}</div></div>
                <div><Overline>Job ID</Overline><div className="font-mono text-[11px] mt-1 truncate">{job.id}</div></div>
              </div>
            </Panel>

            <Panel title="Description">
              <p className="font-mono text-[12.5px] leading-relaxed text-foreground/90">{decodeStrip(job.description) || "—"}</p>
            </Panel>

            <div className="flex gap-2">
              {job.company && (
                <Link to={`/intel?company=${encodeURIComponent(job.company)}`}>
                  <Button variant="secondary"><FileSearch className="w-3.5 h-3.5" /> Generate intel</Button>
                </Link>
              )}
              <Button variant="primary" disabled={!eligible}
                onClick={() => navigate(`/compose`)}
                title={eligible ? "" : "Below min match score / unscored"}>
                <PenLine className="w-3.5 h-3.5" /> Compose outreach
              </Button>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
