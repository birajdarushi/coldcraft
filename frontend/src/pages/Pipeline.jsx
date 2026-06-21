import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Briefcase, ArrowRight, Eye, RefreshCw, AlertCircle, FileText, CheckCircle2 } from "lucide-react";
import AppShell from "../components/AppShell.jsx";
import { Button, Panel, Overline, Tag, Loading, ErrorBlock, Banner } from "../components/ui.jsx";
import { api } from "../lib/api.js";

const COLUMNS = [
  { id: "scraped", label: "Scraped Leads", color: "border-muted-foreground/30 text-muted-foreground" },
  { id: "cold_emailed", label: "Cold Emailed", color: "border-amber-500/30 text-amber-500" },
  { id: "applied", label: "Applied", color: "border-blue-500/30 text-blue-500" },
  { id: "in_process", label: "Interviewing", color: "border-purple-500/30 text-purple-400" },
  { id: "offer", label: "Offers", color: "border-emerald-500/30 text-emerald-400 font-bold" },
  { id: "rejected", label: "Rejected", color: "border-red-500/20 text-red-500/80" },
];

export default function Pipeline() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionMessage, setActionMessage] = useState(null);

  useEffect(() => {
    fetchJobs();
  }, []);

  async function fetchJobs() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listJobs({ limit: 200 });
      // Ensure list is array
      setJobs(Array.isArray(res) ? res : res.jobs || []);
    } catch (err) {
      setError(err.detail || "Failed to load jobs list.");
    } finally {
      setLoading(false);
    }
  }

  // Native HTML5 Drag and Drop handlers
  function handleDragStart(e, jobId) {
    e.dataTransfer.setData("text/plain", jobId);
    e.dataTransfer.effectAllowed = "move";
  }

  async function handleDrop(e, targetStatus) {
    e.preventDefault();
    const jobId = e.dataTransfer.getData("text/plain");
    if (!jobId) return;

    // Optimistic Update
    const originalJobs = [...jobs];
    setJobs((prev) =>
      prev.map((job) => (job.id === jobId ? { ...job, status: targetStatus } : job))
    );

    try {
      await api.updateJobStatus(jobId, targetStatus);
      setActionMessage({ tone: "success", text: `Updated status to ${targetStatus.toUpperCase()}` });
      setTimeout(() => setActionMessage(null), 3000);
    } catch (err) {
      // Revert if API failed
      setJobs(originalJobs);
      setError(err.detail || "Failed to update job status on backend.");
    }
  }

  function handleDragOver(e) {
    e.preventDefault();
  }

  return (
    <AppShell title="Outreach Pipeline" subtitle="// WORKFLOW KANBAN · DRAG-AND-DROP JOB CARD MATRIX">
      <div className="h-[calc(100vh-64px)] flex flex-col p-4 space-y-3">
        {/* Banner area */}
        {actionMessage && (
          <Banner tone={actionMessage.tone} testId="pipeline-success">
            {actionMessage.text}
          </Banner>
        )}
        {error && <ErrorBlock message={error} onRetry={fetchJobs} />}

        {/* Board view */}
        <div className="flex-1 min-h-0 overflow-x-auto flex gap-4 pb-4 select-none">
          {loading ? (
            <div className="w-full flex items-center justify-center">
              <Loading label="CONSTRUCTING BOARD MATRIX..." />
            </div>
          ) : (
            COLUMNS.map((col) => {
              const colJobs = jobs.filter((j) => j.status === col.id);

              return (
                <div
                  key={col.id}
                  onDragOver={handleDragOver}
                  onDrop={(e) => handleDrop(e, col.id)}
                  className="w-72 shrink-0 flex flex-col border border-border bg-surface rounded-sm"
                >
                  {/* Header */}
                  <header className={`h-11 border-b border-border flex items-center justify-between px-3 ${col.color} bg-background/50`}>
                    <div className="flex items-center gap-2">
                      <span className="pulse-square w-1.5 h-1.5 bg-current" />
                      <span className="font-mono text-[11px] uppercase tracking-[0.15em] font-bold">
                        {col.label}
                      </span>
                    </div>
                    <span className="font-mono text-[10px] bg-muted border border-border px-1.5 py-0.5 rounded-sm tabular-nums">
                      {colJobs.length}
                    </span>
                  </header>

                  {/* Cards Area */}
                  <div className="flex-1 overflow-y-auto p-2.5 space-y-2 bg-surface/40">
                    {colJobs.length === 0 ? (
                      <div className="h-20 border border-dashed border-border/60 flex items-center justify-center font-mono text-[9px] text-muted-foreground/50 tracking-wider">
                        DRAG HERE
                      </div>
                    ) : (
                      colJobs.map((job) => (
                        <div
                          key={job.id}
                          draggable
                          onDragStart={(e) => handleDragStart(e, job.id)}
                          className="border border-border bg-background p-2.5 cursor-grab active:cursor-grabbing hover:border-foreground/40 transition-colors shadow-sm rounded-sm"
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-mono text-[9px] text-muted-foreground uppercase tracking-wider truncate max-w-[120px]">
                              {job.company}
                            </span>
                            {job.salary_range && (
                              <span className="font-mono text-[9px] text-emerald-500/80">
                                {job.salary_range}
                              </span>
                            )}
                          </div>

                          <h4 className="font-sans font-bold text-[12px] text-foreground line-clamp-1">
                            {job.title}
                          </h4>

                          {job.location && (
                            <div className="font-mono text-[9px] text-muted-foreground/70 mt-1">
                              {job.location}
                            </div>
                          )}

                          <div className="flex items-center justify-between mt-3 pt-2 border-t border-border/30">
                            <span className="font-mono text-[8px] text-muted-foreground">
                              {job.id.slice(0, 8)}
                            </span>
                            <div className="flex gap-1">
                              <Link to={`/jobs/${job.id}`}>
                                <button
                                  type="button"
                                  title="View job details"
                                  className="p-1 border border-border hover:bg-muted text-muted-foreground hover:text-foreground"
                                >
                                  <Eye className="w-2.5 h-2.5" />
                                </button>
                              </Link>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </AppShell>
  );
}
