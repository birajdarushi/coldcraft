import { useState } from "react";
import { Link } from "react-router-dom";
import { Play, Check } from "lucide-react";
import AppShell from "../components/AppShell.jsx";
import StatusPill from "../components/StatusPill.jsx";
import { Button, Panel, Field, Input, Textarea, Banner, Overline, Tag } from "../components/ui.jsx";
import { api } from "../lib/api.js";
import { usePolicies } from "../lib/usePolicies.js";
import { useRateLimit } from "../lib/useRateLimit.js";

const STAGES = [
  { key: "research", label: "Research check", note: "intel threshold · sender profile", errs: ["research", "sender profile", "senderprofile"] },
  { key: "preflight", label: "Preflight gate", note: "DNC · ATS · daily/company limits · duplicate", errs: ["donotcontact", "do-not-contact", "ats", "dailylimit", "daily limit", "companylimit", "company limit", "nooutreach", "duplicate"] },
  { key: "hook", label: "Hook generation", note: "3 candidates · specificity/surprise/relevance", errs: ["hook"] },
  { key: "self_review", label: "Draft + self-review", note: "100–180 words · ≤ subject limit · ≥2 signals", errs: ["selfreview", "self-review", "self review", "banned", "word"] },
  { key: "qa", label: "QA gate", note: "independent validation · auto-revisions", errs: ["qa", "escalation"] },
];

function StageRow({ stage, state }) {
  const map = {
    idle: { glyph: "○", cls: "text-muted-foreground/50" },
    running: { glyph: "◐", cls: "text-amber-500 pulse-square" },
    done: { glyph: "●", cls: "text-emerald-500" },
    failed: { glyph: "✕", cls: "text-red-500" },
  };
  const s = map[state] || map.idle;
  return (
    <div className="flex items-center gap-3 py-2 border-b border-border last:border-0">
      <span className={`w-5 text-center text-sm ${s.cls}`}>{s.glyph}</span>
      <div className="flex-1 min-w-0">
        <div className="font-mono text-[12px] uppercase tracking-wider">{stage.label}</div>
        <div className="font-mono text-[9px] text-muted-foreground/70">{stage.note}</div>
      </div>
      <span className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">{state}</span>
    </div>
  );
}

function stageForError(detail) {
  const d = (detail || "").toLowerCase();
  for (const s of STAGES) {
    if (s.errs.some((e) => d.includes(e))) return s.key;
  }
  return null;
}

export default function Apply() {
  const { floors } = usePolicies();
  const subjMax = floors?.subject_max_chars ?? null;

  const [form, setForm] = useState({
    job_id: "",
    recipient_name: "",
    recipient_email: "",
    subject: "",
    company_intel: "",
    triggered_by: "user",
  });
  const [stages, setStages] = useState({});
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const rl = useRateLimit();

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const subjLen = form.subject.length;
  const subjOver = subjMax != null && subjLen > subjMax;

  async function run(e) {
    e.preventDefault();
    setResult(null);
    setError(null);
    setRunning(true);

    const order = STAGES.map((s) => s.key);
    // optimistic: light the stages while the request is in flight
    setStages(Object.fromEntries(order.map((k, i) => [k, i === 0 ? "running" : "idle"])));

    // build the request: company_intel must be an object for the API
    let intel = {};
    try {
      intel = form.company_intel.trim().startsWith("{")
        ? JSON.parse(form.company_intel)
        : { summary: form.company_intel };
    } catch {
      intel = { summary: form.company_intel };
    }

    const payload = {
      job_id: form.job_id,
      recipient_email: form.recipient_email,
      recipient_name: form.recipient_name,
      company_intel: intel,
      triggered_by: form.triggered_by || "user",
    };

    try {
      const r = await api.createDraft(payload);
      setStages(Object.fromEntries(order.map((k) => [k, "done"])));
      setResult(r);
    } catch (err) {
      if (rl.isRateLimit(err)) rl.start(60);
      const failedKey = stageForError(err?.detail) || "qa";
      const idx = order.indexOf(failedKey);
      const next = {};
      order.forEach((k, i) => {
        next[k] = i < idx ? "done" : i === idx ? "failed" : "idle";
      });
      setStages(next);
      setError({ stage: failedKey, detail: err?.detail || "draft refused" });
    } finally {
      setRunning(false);
    }
  }

  function reset() {
    setStages({});
    setResult(null);
    setError(null);
  }

  return (
    <AppShell title="Apply" subtitle="// POST /API/V1/DRAFTS · CONSTITUTION-GOVERNED PIPELINE">
      <div className="p-5 grid grid-cols-1 lg:grid-cols-2 gap-5 max-w-6xl">
        {/* form */}
        <form onSubmit={run} className="space-y-4">
          <Panel title="Target" code="job + recipient">
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Field label="Job ID" hint="required"><Input value={form.job_id} onChange={set("job_id")} placeholder="job id from /jobs" required /></Field>
                <Field label="Subject" hint={subjMax ? `${subjLen}/${subjMax}` : `${subjLen}`}>
                  <Input value={form.subject} onChange={set("subject")}
                    className={subjOver ? "border-red-500 text-red-600 dark:text-red-400" : ""} />
                </Field>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Recipient name" hint="required"><Input value={form.recipient_name} onChange={set("recipient_name")} required /></Field>
                <Field label="Recipient email" hint="required"><Input type="email" value={form.recipient_email} onChange={set("recipient_email")} required /></Field>
              </div>
              {subjOver && <div className="font-mono text-[10px] text-red-500">SUBJECT EXCEEDS HARD LIMIT — self-review will reject.</div>}
            </div>
          </Panel>

          <Panel title="Company intel" code="must meet research threshold">
            <Textarea rows={6} value={form.company_intel} onChange={set("company_intel")}
              placeholder='Researched, company-specific facts (plain text, or JSON object). Thin intel → ResearchInsufficientError (422).' />
            <div className="mt-2 font-mono text-[10px] text-muted-foreground">
              Sender profile is omitted → server falls back to the saved <Link to="/settings" className="underline">Sender Profile</Link>.
              Drafting requires a server-side ANTHROPIC_API_KEY.
            </div>
          </Panel>

          <div className="flex gap-2">
            <Button type="submit" variant="primary" disabled={running || rl.active} data-testid="run-pipeline">
              <Play className="w-3.5 h-3.5" /> {running ? "Running pipeline…" : rl.active ? `Retry in ${rl.remaining}s` : "Run pipeline"}
            </Button>
            <Button type="button" variant="secondary" onClick={reset} disabled={running}>Reset</Button>
            {rl.active && (
              <span className="font-mono text-[11px] text-amber-600 dark:text-amber-400 self-center">⏳ rate limited · retry in {rl.remaining}s</span>
            )}
          </div>
        </form>

        {/* pipeline + result */}
        <div className="space-y-4">
          <Panel title="Pipeline" code="stage progress (gate inferred from API result)">
            {STAGES.map((s) => <StageRow key={s.key} stage={s} state={stages[s.key] || "idle"} />)}
          </Panel>

          {error && (
            <Panel title="Refused" right={<StatusPill status="blocked" />}>
              <Banner tone="error" testId="compose-error">{error.detail}</Banner>
              <p className="font-mono text-[11px] text-muted-foreground mt-3">
                Blocked at the <span className="font-bold uppercase">{error.stage}</span> gate. Fix the offending input and re-run — every rejection names the rule it failed.
              </p>
            </Panel>
          )}

          {result && (
            <Panel title="Draft produced" right={<StatusPill status={result.status} />}>
              <div className="space-y-3">
                <div>
                  <Overline>Subject</Overline>
                  <div className="font-mono text-[13px] mt-1">{result.subject}</div>
                </div>
                <div className="flex gap-4 flex-wrap">
                  <div><Overline>Words</Overline><div className="font-mono text-lg tabular-nums">{result.word_count}</div></div>
                  {result.personalization_signals?.length > 0 && (
                    <div>
                      <Overline>Personalization</Overline>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {result.personalization_signals.map((s, i) => <Tag key={i}>{s}</Tag>)}
                      </div>
                    </div>
                  )}
                </div>
                {result.body_text && (
                  <pre className="font-mono text-[11px] leading-relaxed whitespace-pre-wrap bg-background border border-border p-3 max-h-48 overflow-auto">{result.body_text}</pre>
                )}
                {result.qa_result && <Banner tone="success">QA · {JSON.stringify(result.qa_result)}</Banner>}
                {result.campaign_id && (
                  <Link to={`/campaigns/${result.campaign_id}`}>
                    <Button variant="primary"><Check className="w-3.5 h-3.5" /> Review & approve</Button>
                  </Link>
                )}
              </div>
            </Panel>
          )}
        </div>
      </div>
    </AppShell>
  );
}
