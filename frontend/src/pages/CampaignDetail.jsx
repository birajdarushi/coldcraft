import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, RefreshCw, Check, Send as SendIcon, Clock, Reply } from "lucide-react";
import AppShell from "../components/AppShell.jsx";
import StatusPill from "../components/StatusPill.jsx";
import { Button, Panel, Overline, Loading, ErrorBlock, Banner, Tag, relTime } from "../components/ui.jsx";
import { api } from "../lib/api.js";

const EVENT_GLYPH = { sent: "▶", opened: "◉", clicked: "↗", replied: "↩" };

export default function CampaignDetail() {
  const { id } = useParams();
  const [detail, setDetail] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("html");
  const [action, setAction] = useState(null); // {tone, text}

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [d, ev] = await Promise.all([api.getCampaign(id), api.getCampaignEvents(id)]);
      setDetail(d);
      setEvents(ev);
    } catch (e) {
      setError(e?.detail || "CAMPAIGN NOT FOUND");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  async function approve() {
    setAction(null);
    try {
      const r = await api.approveCampaign(id);
      setAction({ tone: "success", text: `APPROVED → ${r.status}` });
      load();
    } catch (e) { setAction({ tone: "error", text: e?.detail || "APPROVE FAILED" }); }
  }
  async function send() {
    setAction(null);
    try {
      const r = await api.sendCampaign(id);
      setAction({ tone: "success", text: `SENT ✓ (${r.campaign_id || id})` });
      load();
    } catch (e) { setAction({ tone: "error", text: e?.detail || "SEND BLOCKED" }); }
  }
  async function followups() {
    setAction(null);
    try {
      const r = await api.scheduleFollowups(id);
      setAction({ tone: "success", text: `FOLLOW-UPS SCHEDULED · ${(r?.followups || []).length} task(s)` });
      load();
    } catch (e) { setAction({ tone: "error", text: e?.detail || "FOLLOW-UP SCHEDULING FAILED" }); }
  }
  async function recordReply() {
    setAction(null);
    const text = window.prompt("Reply text:");
    if (text == null) return;
    const type = window.prompt("Reply type (positive / neutral / negative):", "positive") || "neutral";
    try {
      await api.recordReply(id, { reply_type: type, reply_text: text });
      setAction({ tone: "success", text: `REPLY RECORDED (${type})` });
      load();
    } catch (e) { setAction({ tone: "error", text: e?.detail || "RECORD REPLY FAILED" }); }
  }

  const right = (
    <>
      <Link to="/campaigns"><Button variant="ghost"><ArrowLeft className="w-3.5 h-3.5" /> All campaigns</Button></Link>
      <Button variant="ghost" onClick={load}><RefreshCw className="w-3.5 h-3.5" /> Reload</Button>
    </>
  );

  return (
    <AppShell title="Campaign" subtitle={`// GET /API/V1/CAMPAIGNS/${(id || "").slice(0, 8)}…`} right={right}>
      <div className="p-5 space-y-4 max-w-5xl">
        {loading ? <Loading label="LOADING CAMPAIGN…" /> : error ? (
          <ErrorBlock message={error} onRetry={load} />
        ) : (
          <>
            {action && <Banner tone={action.tone} testId="action-banner">{action.text}</Banner>}

            {/* header */}
            <Panel>
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="font-sans text-xl font-bold tracking-tight">
                    {detail.subject || <span className="text-muted-foreground/60 italic">(no subject)</span>}
                  </div>
                  <div className="font-mono text-[12px] text-muted-foreground mt-1">
                    {detail.recipient_name} &lt;{detail.recipient_email}&gt;
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    <StatusPill status={detail.status} />
                    <span className="font-mono text-[10px] text-muted-foreground/60">{detail.id.slice(0, 8)}…</span>
                    <span className="font-mono text-[10px] text-muted-foreground/60">· {relTime(detail.created_at)}</span>
                  </div>
                </div>
                <div className="flex flex-col gap-2 shrink-0">
                  {["qa_passed", "draft"].includes(detail.status) && (
                    <Button variant="primary" onClick={approve} data-testid="approve-btn"><Check className="w-3.5 h-3.5" /> Approve</Button>
                  )}
                  {detail.status === "user_approved" && (
                    <Button variant="primary" onClick={send} data-testid="send-btn"><SendIcon className="w-3.5 h-3.5" /> Send now</Button>
                  )}
                  <Button variant="secondary" onClick={followups} data-testid="followups-btn"><Clock className="w-3.5 h-3.5" /> Follow-ups</Button>
                  <Button variant="secondary" onClick={recordReply} data-testid="reply-btn"><Reply className="w-3.5 h-3.5" /> Record reply</Button>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 pt-4 border-t border-border">
                <div>
                  <Overline>Word count</Overline>
                  <div className="font-mono text-lg tabular-nums mt-1">{detail.word_count}</div>
                </div>
                <div>
                  <Overline>Follow-up schedule</Overline>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {detail.followup_schedule.length ? detail.followup_schedule.map((d, i) => (
                      <Tag key={i}>D{[5, 12][i]} · {d}</Tag>
                    )) : <span className="font-mono text-[11px] text-muted-foreground">none</span>}
                  </div>
                </div>
                <div>
                  <Overline>QA result</Overline>
                  <div className="font-mono text-[11px] text-muted-foreground/70 mt-1 italic">not available (stub)</div>
                </div>
                <div>
                  <Overline>Created</Overline>
                  <div className="font-mono text-[11px] mt-1">{detail.created_at ? new Date(detail.created_at).toLocaleString() : "—"}</div>
                </div>
              </div>
            </Panel>

            {/* personalization signals */}
            {detail.personalization_signals?.length > 0 && (
              <Panel title="Personalization signals" right={<span className="font-mono text-[10px] text-muted-foreground">≥ 2 REQUIRED</span>}>
                <ul className="space-y-1">
                  {detail.personalization_signals.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 font-mono text-[12px]">
                      <span className="text-accent">▸</span><span>{s}</span>
                    </li>
                  ))}
                </ul>
              </Panel>
            )}

            {/* body preview */}
            <Panel
              title="Preview"
              code="live render · untrusted html sandboxed"
              right={
                <div className="flex gap-1">
                  {["html", "text"].map((t) => (
                    <button key={t} onClick={() => setTab(t)}
                      className={`px-2 py-1 font-mono text-[10px] uppercase tracking-wider border ${tab === t ? "border-foreground bg-muted" : "border-border text-muted-foreground"}`}>
                      {t}
                    </button>
                  ))}
                </div>
              }
            >
              {tab === "html" ? (
                detail.body_html ? (
                  <iframe title="email-preview" sandbox="allow-same-origin" srcDoc={detail.body_html}
                    className="w-full h-[360px] border border-border bg-white" />
                ) : <div className="font-mono text-[11px] text-muted-foreground p-4 border border-border">NO HTML BODY (status: {detail.status})</div>
              ) : (
                <pre className="font-mono text-[12px] leading-relaxed whitespace-pre-wrap bg-background border border-border p-3 max-h-[360px] overflow-auto">
                  {detail.body_text || "(empty)"}
                </pre>
              )}
            </Panel>

            {/* events */}
            <Panel title="Events" code="GET /…/events">
              {events.length === 0 ? (
                <div className="font-mono text-[11px] text-muted-foreground">NO EVENTS RECORDED YET.</div>
              ) : (
                <ul className="divide-y divide-border">
                  {events.map((ev) => (
                    <li key={ev.id} className="flex items-center gap-3 py-2 font-mono text-[11px]">
                      <span className="w-5 text-center">{EVENT_GLYPH[ev.event_type] || "·"}</span>
                      <span className="w-44 shrink-0 text-muted-foreground tabular-nums">{new Date(ev.occurred_at).toLocaleString()}</span>
                      <span className="font-bold uppercase tracking-wider w-20">{ev.event_type}</span>
                      {ev.metadata && Object.keys(ev.metadata).length > 0 && (
                        <span className="text-muted-foreground/70 truncate">{JSON.stringify(ev.metadata)}</span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          </>
        )}
      </div>
    </AppShell>
  );
}
