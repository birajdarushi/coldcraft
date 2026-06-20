import { useEffect, useRef, useState } from "react";
import { FileText, Plus, Trash2, Play, Save, Download, AlertTriangle, Sparkles, Wand2 } from "lucide-react";
import AppShell from "../components/AppShell.jsx";
import { Button, Panel, Field, Input, Textarea, Loading, Banner, Tag, relTime } from "../components/ui.jsx";
import { api } from "../lib/api.js";
import { useRateLimit } from "../lib/useRateLimit.js";

const STARTER = `\\documentclass[11pt]{article}
\\usepackage[margin=1in]{geometry}
\\usepackage{enumitem}
\\usepackage{hyperref}
\\setlength{\\parindent}{0pt}
\\pagestyle{empty}

\\begin{document}

{\\LARGE \\textbf{Rushiraj Birajdar}} \\\\
\\vspace{2pt}
Backend Engineer \\textbullet{} rushiraj@example.com \\textbullet{} github.com/rushiraj

\\hrulefill

\\textbf{EXPERIENCE} \\\\
\\textbf{Backend Engineer}, UMEED \\hfill 2023--Present \\\\
\\begin{itemize}[leftmargin=*, nosep]
  \\item Built a metering pipeline processing 4B events/month in Go + Kafka.
  \\item Cut manual invoice fixes 96\\% with a reconciliation job.
\\end{itemize}

\\vspace{6pt}
\\textbf{SKILLS} \\\\
Go, Python, Distributed Systems, Billing/Metering, PostgreSQL

\\end{document}
`;

export default function Resumes() {
  const [list, setList] = useState(null);
  const [sel, setSel] = useState(null); // selected resume {id,name,latex_source,...}
  const [source, setSource] = useState("");
  const [name, setName] = useState("");
  const [dirty, setDirty] = useState(false);

  const [pdfUrl, setPdfUrl] = useState(null);
  const [compiling, setCompiling] = useState(false);
  const [saving, setSaving] = useState(false);
  const [fixing, setFixing] = useState(false);
  const [err, setErr] = useState(null);      // {message, log}
  const [msg, setMsg] = useState(null);
  const blobRef = useRef(null);

  // Generate-from-JD
  const [jd, setJd] = useState("");
  const [jdName, setJdName] = useState("");
  const [generating, setGenerating] = useState(false);
  const [genMsg, setGenMsg] = useState(null);
  const rl = useRateLimit(); // shared 60s countdown for Gemini rate limits

  async function loadList() {
    setList(null);
    try { setList(await api.listResumes()); } catch { setList([]); }
  }
  useEffect(() => { loadList(); }, []);

  function open(r) {
    setSel(r); setSource(r.latex_source || ""); setName(r.name || "Untitled");
    setDirty(false); setErr(null); setMsg(null);
    clearPdf();
  }

  function clearPdf() {
    if (blobRef.current) { URL.revokeObjectURL(blobRef.current); blobRef.current = null; }
    setPdfUrl(null);
  }
  useEffect(() => () => clearPdf(), []);

  async function newResume() {
    const r = await api.createResume({ name: "Untitled resume", latex_source: STARTER, kind: "resume" });
    await loadList();
    open(r);
  }

  async function save() {
    if (!sel) return;
    setSaving(true); setMsg(null);
    try {
      const r = await api.updateResume(sel.id, { name, latex_source: source });
      setSel(r); setDirty(false);
      setMsg({ tone: "success", text: "SAVED" });
      loadList();
    } catch (e) { setMsg({ tone: "error", text: e?.detail || "SAVE FAILED" }); }
    finally { setSaving(false); }
  }

  async function compile() {
    setCompiling(true); setErr(null); setMsg(null);
    try {
      const blob = await api.compileLatex(source);
      clearPdf();
      const url = URL.createObjectURL(blob);
      blobRef.current = url;
      setPdfUrl(url);
    } catch (e) {
      setErr({ message: e?.detail || "COMPILE FAILED", log: e?.log || "" });
    } finally { setCompiling(false); }
  }

  // auto-compile a given source (used after generate / fix)
  async function compileSource(src) {
    setCompiling(true); setErr(null);
    try {
      const blob = await api.compileLatex(src);
      clearPdf();
      const url = URL.createObjectURL(blob);
      blobRef.current = url; setPdfUrl(url);
    } catch (e) {
      setErr({ message: e?.detail || "COMPILE FAILED", log: e?.log || "" });
    } finally { setCompiling(false); }
  }

  async function generate() {
    if (!jd.trim()) return;
    setGenerating(true); setGenMsg(null);
    try {
      const r = await api.generateResume({ job_description: jd, name: jdName || "AI resume" });
      await loadList();
      open(r.resume);
      setJd(""); setJdName("");
      setGenMsg({ tone: r.compiled ? "success" : "warn", text: r.compiled ? "GENERATED ✓ — compiled" : `GENERATED — needs fixing: ${(r.error || "").slice(0, 80)}` });
      compileSource(r.resume.latex_source);
    } catch (e) {
      if (rl.isRateLimit(e)) rl.start(60);
      setGenMsg({ tone: "error", text: e?.detail || "GENERATE FAILED" });
    } finally { setGenerating(false); }
  }

  async function fixWithAI() {
    if (!source.trim()) return;
    setFixing(true); setErr(null); setMsg(null);
    try {
      const r = await api.fixLatex(source);
      if (r.changed) { setSource(r.latex_source); setDirty(true); }
      setMsg({ tone: r.compiled ? "success" : "error", text: r.changed ? (r.compiled ? "FIXED ✓" : "FIX ATTEMPTED — still failing") : "ALREADY COMPILES" });
      await compileSource(r.latex_source);
    } catch (e) {
      if (rl.isRateLimit(e)) rl.start(60);
      setErr({ message: e?.detail || "FIX FAILED", log: "" });
    } finally { setFixing(false); }
  }

  function download() {
    if (!pdfUrl) return;
    const a = document.createElement("a");
    a.href = pdfUrl;
    a.download = `${(name || "resume").replace(/\s+/g, "_")}.pdf`;
    a.click();
  }

  async function del(r, e) {
    e.stopPropagation();
    if (!window.confirm(`Delete "${r.name}"?`)) return;
    await api.deleteResume(r.id);
    if (sel?.id === r.id) { setSel(null); setSource(""); clearPdf(); }
    loadList();
  }

  const right = (
    <Button variant="primary" onClick={newResume} data-testid="new-resume"><Plus className="w-3.5 h-3.5" /> New resume</Button>
  );

  return (
    <AppShell title="Resumes" subtitle="// LATEX DOCS · COMPILE → PDF · GET/PUT /API/V1/RESUMES" right={right}>
      <div className="p-5 grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-5 h-full">
        {/* list + generator */}
        <div className="space-y-3">
          {/* Generate from job description */}
          <div className="border border-border bg-surface p-3 space-y-2">
            <div className="flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-accent" />
              <span className="font-mono text-[10px] tracking-[0.2em] uppercase font-bold">Generate from JD</span>
            </div>
            <p className="font-mono text-[9px] text-muted-foreground leading-relaxed">
              Gemini tailors a resume to the job, reusing facts &amp; style from your stored resumes.
            </p>
            <Input value={jdName} onChange={(e) => setJdName(e.target.value)} placeholder="Name (optional)" />
            <Textarea rows={5} value={jd} onChange={(e) => setJd(e.target.value)} placeholder="Paste the job description…" data-testid="jd-input" />
            <Button variant="primary" onClick={generate} disabled={generating || rl.active || !jd.trim()} data-testid="generate-resume" className="w-full">
              <Sparkles className="w-3.5 h-3.5" /> {generating ? "Generating…" : rl.active ? `⏳ Rate limited · retry in ${rl.remaining}s` : "Generate resume"}
            </Button>
            {!rl.active && genMsg && <Banner tone={genMsg.tone} testId="gen-msg">{genMsg.text}</Banner>}
          </div>

          <div className="font-mono text-[10px] tracking-[0.2em] text-muted-foreground uppercase mb-1">Stored ({list?.length ?? "…"})</div>
          {list == null ? <Loading /> : list.length === 0 ? (
            <div className="border border-dashed border-border p-4 font-mono text-[11px] text-muted-foreground">
              No resumes yet. Create one.
            </div>
          ) : list.map((r) => (
            <div key={r.id} onClick={() => open(r)} data-testid={`resume-${r.id}`}
              className={`border border-border p-3 cursor-pointer hover:bg-muted/50 ${sel?.id === r.id ? "bg-muted" : "bg-surface"}`}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <FileText className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
                  <span className="font-mono text-[12px] truncate">{r.name}</span>
                </div>
                <button onClick={(e) => del(r, e)} className="text-muted-foreground hover:text-red-500 shrink-0"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
              <div className="mt-1.5 flex items-center gap-2">
                <Tag>{r.kind}</Tag>
                <span className="font-mono text-[9px] text-muted-foreground">{relTime(r.updated_at)}</span>
              </div>
            </div>
          ))}
        </div>

        {/* editor + preview */}
        {!sel ? (
          <div className="border border-dashed border-border flex items-center justify-center min-h-[400px]">
            <div className="text-center">
              <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Select a resume or create one</div>
              <div className="mt-3"><Button variant="primary" onClick={newResume}><Plus className="w-3.5 h-3.5" /> New resume</Button></div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 min-h-0">
            {/* editor */}
            <div className="flex flex-col border border-border bg-surface min-h-[520px]">
              <div className="flex items-center gap-2 px-3 h-11 border-b border-border">
                <input value={name} onChange={(e) => { setName(e.target.value); setDirty(true); }}
                  className="flex-1 bg-transparent font-mono text-[13px] focus:outline-none" />
                {dirty && <span className="font-mono text-[9px] text-amber-500">● UNSAVED</span>}
              </div>
              <textarea
                value={source}
                onChange={(e) => { setSource(e.target.value); setDirty(true); }}
                spellCheck={false}
                data-testid="latex-editor"
                className="flex-1 w-full bg-background p-3 font-mono text-[12px] leading-relaxed resize-none focus:outline-none"
              />
              <div className="flex items-center gap-2 px-3 h-12 border-t border-border">
                <Button variant="primary" onClick={compile} disabled={compiling} data-testid="compile-btn">
                  <Play className="w-3.5 h-3.5" /> {compiling ? "Compiling…" : "Compile"}
                </Button>
                <Button variant="secondary" onClick={fixWithAI} disabled={fixing || rl.active} data-testid="fix-ai-btn">
                  <Wand2 className="w-3.5 h-3.5" /> {fixing ? "Fixing…" : rl.active ? `Retry ${rl.remaining}s` : "Fix with AI"}
                </Button>
                <Button variant="secondary" onClick={save} disabled={saving}>
                  <Save className="w-3.5 h-3.5" /> {saving ? "Saving…" : "Save"}
                </Button>
                <Button variant="secondary" onClick={download} disabled={!pdfUrl}>
                  <Download className="w-3.5 h-3.5" /> Download
                </Button>
                {msg && <span className={`font-mono text-[10px] uppercase tracking-wider ${msg.tone === "success" ? "text-emerald-500" : "text-red-500"}`}>{msg.text}</span>}
              </div>
            </div>

            {/* preview */}
            <div className="flex flex-col border border-border bg-surface min-h-[520px]">
              <div className="px-3 h-11 border-b border-border flex items-center">
                <span className="font-mono text-[10px] tracking-[0.2em] text-muted-foreground uppercase">PDF preview</span>
              </div>
              <div className="flex-1 min-h-0 bg-muted/30">
                {err ? (
                  <div className="p-3 space-y-2 overflow-auto h-full">
                    <Banner tone="error"><AlertTriangle className="inline w-3 h-3 mr-1 -mt-0.5" />{err.message}</Banner>
                    <Button variant="primary" onClick={fixWithAI} disabled={fixing || rl.active} data-testid="fix-ai-err">
                      <Wand2 className="w-3.5 h-3.5" /> {fixing ? "Fixing…" : rl.active ? `Retry in ${rl.remaining}s` : "Fix with AI"}
                    </Button>
                    {err.log && <pre className="font-mono text-[10px] leading-relaxed whitespace-pre-wrap bg-background border border-border p-2 text-red-600 dark:text-red-400">{err.log}</pre>}
                  </div>
                ) : pdfUrl ? (
                  <iframe title="pdf-preview" src={pdfUrl} className="w-full h-full" />
                ) : (
                  <div className="h-full flex items-center justify-center font-mono text-[11px] text-muted-foreground uppercase tracking-wider">
                    {compiling ? "Compiling…" : "Compile to preview"}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
