import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { 
  Mail, 
  Sparkles, 
  Send, 
  Check, 
  AlertCircle, 
  ShieldAlert, 
  Loader2, 
  ArrowLeft, 
  Star, 
  FileText, 
  Trash2, 
  Archive, 
  Info,
  ExternalLink,
  RefreshCw,
  BellOff
} from "lucide-react";
import AppShell from "../components/AppShell.jsx";
import { Button, Panel, Textarea, Overline, Banner, Tag, relTime, Loading, ErrorBlock } from "../components/ui.jsx";
import { api } from "../lib/api.js";
import { useInbox } from "../lib/InboxContext.jsx";

const TAGS = [
  { value: "all", label: "All Threads" },
  { value: "applied", label: "Applied" },
  { value: "rejected", label: "Rejected" },
  { value: "interview", label: "Interview" },
  { value: "follow-up", label: "Follow-up" },
];

export default function Inbox() {
  const [searchParams, setSearchParams] = useSearchParams();

  // ── Context-backed state (survives navigation) ──────────────────────────
  const {
    threads,
    setThreads,
    loading,
    error,
    setError,
    nextPageToken,
    prevPageTokens,
    pageIndex,
    fetchThreads,
    goNextPage,
    goPrevPage,
    removeThread,
    refresh,
  } = useInbox();

  // ── Per-session UI state (reset on each visit is fine) ─────────────────
  const [activeFolder, setActiveFolder] = useState("inbox");
  const [activeThreadId, setActiveThreadId] = useState(null);
  const [selectedTag, setSelectedTag] = useState("all");
  const [selectedThreadIds, setSelectedThreadIds] = useState(new Set());
  const [connecting, setConnecting] = useState(false);
  const [connMessage, setConnMessage] = useState(null);
  const [aiDraft, setAiDraft] = useState(null);
  const [generatingDraft, setGeneratingDraft] = useState(false);
  const [replyBody, setReplyBody] = useState("");
  const [sendingReply, setSendingReply] = useState(false);
  const [replySuccess, setReplySuccess] = useState(false);
  const [candidates, setCandidates] = useState([]);
  const [loadingCandidates, setLoadingCandidates] = useState(false);
  const [selectedCandidateIds, setSelectedCandidateIds] = useState(new Set());
  const [unsubscribeMessage, setUnsubscribeMessage] = useState(null);
  const [processingUnsubscribe, setProcessingUnsubscribe] = useState(false);

  const redirectUri = window.location.origin + "/inbox";

  // On mount: handle OAuth callback OR trigger initial fetch (skipped if fresh)
  useEffect(() => {
    const code = searchParams.get("code");
    if (code) {
      handleOAuthCallback(code);
    } else {
      // Context fetch: skips network if data is <60s old
      fetchThreads();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleOAuthCallback(code) {
    try {
      const res = await api.callbackInbox(code, redirectUri);
      setConnMessage({ tone: "success", text: res.message || "Connected successfully!" });
      setSearchParams({});
      // Force full refresh after connecting a new account
      refresh();
    } catch (err) {
      setError(err.detail || "Google authentication callback failed.");
    }
  }

  async function handleArchive(threadId) {
    setError(null);
    try {
      await api.archiveThread(threadId);
      removeThread(threadId);
      if (activeThreadId === threadId) setActiveThreadId(null);
    } catch (err) {
      setError(err.detail || "Archive action failed.");
    }
  }

  async function handleTrash(threadId) {
    setError(null);
    try {
      await api.trashThread(threadId);
      removeThread(threadId);
      if (activeThreadId === threadId) setActiveThreadId(null);
    } catch (err) {
      setError(err.detail || "Trash action failed.");
    }
  }

  async function handleConnect() {
    setConnecting(true);
    try {
      const { redirect_url } = await api.connectInbox(redirectUri);
      if (redirect_url) {
        window.location.href = redirect_url;
      }
    } catch (err) {
      setError(err.detail || "Failed to launch Google auth connection.");
      setConnecting(false);
    }
  }

  async function handleGenerateAIDraft(threadId) {
    setGeneratingDraft(true);
    setAiDraft(null);
    try {
      const res = await api.createInboxReply(threadId);
      setAiDraft(res);
      setReplyBody(res.body || "");
    } catch (err) {
      setError(err.detail || "AI failed to generate a reply draft.");
    } finally {
      setGeneratingDraft(false);
    }
  }

  // Scan candidates
  async function scanUnsubscribeCandidates() {
    setLoadingCandidates(true);
    setUnsubscribeMessage(null);
    try {
      const list = await api.scanUnsubscribeTargets();
      setCandidates(Array.isArray(list) ? list : []);
      setSelectedCandidateIds(new Set());
    } catch (err) {
      setUnsubscribeMessage({ tone: "error", text: err.detail || "Failed to scan unsubscribe candidates." });
    } finally {
      setLoadingCandidates(false);
    }
  }

  // Individual thread unsubscribe
  async function handleUnsubscribe(threadId) {
    setProcessingUnsubscribe(true);
    setUnsubscribeMessage(null);
    try {
      const res = await api.unsubscribeThread(threadId);
      setUnsubscribeMessage({
        tone: "success",
        text: `Successfully unsubscribed via: ${res.methods?.join(", ") || "archive/mute"}.`
      });
      setCandidates(prev => prev.filter(c => c.id !== threadId));
      removeThread(threadId);
      if (activeThreadId === threadId) setActiveThreadId(null);
    } catch (err) {
      setUnsubscribeMessage({ tone: "error", text: err.detail || "Unsubscribe action failed." });
    } finally {
      setProcessingUnsubscribe(false);
    }
  }

  async function handleBulkUnsubscribe() {
    if (selectedCandidateIds.size === 0) return;
    setProcessingUnsubscribe(true);
    setUnsubscribeMessage(null);
    const idsToUnsub = Array.from(selectedCandidateIds);
    try {
      const res = await api.bulkUnsubscribe(idsToUnsub);
      const successfulCount = res.results?.filter(r => r.status === "success").length || 0;
      setUnsubscribeMessage({
        tone: "success",
        text: `Bulk unsubscribe processed. Successfully cleaned up ${successfulCount} senders.`
      });
      const removedSet = new Set(selectedCandidateIds);
      setCandidates(prev => prev.filter(c => !removedSet.has(c.id)));
      removedSet.forEach(id => removeThread(id));
      setSelectedCandidateIds(new Set());
    } catch (err) {
      setUnsubscribeMessage({ tone: "error", text: err.detail || "Bulk unsubscribe action failed." });
    } finally {
      setProcessingUnsubscribe(false);
    }
  }

  // Star thread quick toggle (mocked/heuristic)
  function toggleStarThread(e, threadId) {
    e.stopPropagation();
    // In our system, starred maps to shifting between starred status or interview heuristic
    setThreads(prev => prev.map(t => {
      if (t.id === threadId) {
        return { ...t, status: t.status === "interview" ? "follow-up" : "interview" };
      }
      return t;
    }));
  }

  // Thread checkboxes toggle
  function toggleThreadSelection(e, threadId) {
    e.stopPropagation();
    setSelectedThreadIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(threadId)) {
        newSet.delete(threadId);
      } else {
        newSet.add(threadId);
      }
      return newSet;
    });
  }

  // Candidate checkbox toggle
  function toggleCandidateSelection(threadId) {
    setSelectedCandidateIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(threadId)) {
        newSet.delete(threadId);
      } else {
        newSet.add(threadId);
      }
      return newSet;
    });
  }

  const activeThread = threads.find((t) => t.id === activeThreadId);

  // Folder filtering logic mapping Gmail folders to status categories
  const folderFilteredThreads = threads.filter((t) => {
    if (activeFolder === "inbox") {
      // Inbox contains general threads (we exclude sent ones for pure inbox feel)
      return t.status !== "sent";
    }
    if (activeFolder === "starred") {
      // Starred maps to interview heuristic threads
      return t.status === "interview";
    }
    if (activeFolder === "sent") {
      return t.status === "sent";
    }
    if (activeFolder === "drafts") {
      // Show threads that are follow-up as drafts candidate
      return t.status === "follow-up";
    }
    return true;
  });

  // Tag filter logic (within folders)
  const finalThreads = folderFilteredThreads.filter((t) => {
    if (selectedTag === "all") return true;
    return t.status === selectedTag;
  });

  return (
    <AppShell title="Inbox Hub" subtitle="// GMAIL SYNC & OUTREACH REPLY CO-PILOT">
      <div className="h-full flex flex-col md:flex-row divide-x divide-border overflow-hidden">
        
        {/* Left Navigation Sidebar (Gmail style folders) */}
        <div className="w-full md:w-60 shrink-0 flex flex-col h-[calc(100vh-64px)] bg-surface border-r border-border">
          {/* OAuth connection panel */}
          <div className="p-3 border-b border-border space-y-2">
            <div className="flex items-center justify-between">
              <Overline className="text-[10px]">Gmail Integration</Overline>
              <Tag className="border-emerald-500/30 text-emerald-400 text-[8px] px-1 py-0">OAuth</Tag>
            </div>
            <Button
              variant="secondary"
              className="w-full justify-center !py-1.5 text-[11px]"
              onClick={handleConnect}
              disabled={connecting}
            >
              {connecting ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Connecting...
                </>
              ) : (
                <>
                  <Mail className="w-3.5 h-3.5" />
                  Connect Account
                </>
              )}
            </Button>
          </div>

          {/* Folder List */}
          <div className="flex-1 p-2 space-y-0.5 overflow-y-auto">
            <button
              onClick={() => { setActiveFolder("inbox"); setActiveThreadId(null); }}
              className={`w-full flex items-center justify-between px-3 py-2 text-[12px] font-mono uppercase tracking-wider rounded-sm transition-colors ${
                activeFolder === "inbox" 
                  ? "bg-foreground text-background font-bold" 
                  : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              }`}
            >
              <div className="flex items-center gap-2">
                <Mail className="w-3.5 h-3.5" />
                <span>Inbox</span>
              </div>
              <span className="text-[10px]">
                {threads.filter(t => t.status !== "sent").length}
              </span>
            </button>

            <button
              onClick={() => { setActiveFolder("starred"); setActiveThreadId(null); }}
              className={`w-full flex items-center justify-between px-3 py-2 text-[12px] font-mono uppercase tracking-wider rounded-sm transition-colors ${
                activeFolder === "starred" 
                  ? "bg-foreground text-background font-bold" 
                  : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              }`}
            >
              <div className="flex items-center gap-2">
                <Star className="w-3.5 h-3.5" />
                <span>Starred</span>
              </div>
              <span className="text-[10px]">
                {threads.filter(t => t.status === "interview").length}
              </span>
            </button>

            <button
              onClick={() => { setActiveFolder("sent"); setActiveThreadId(null); }}
              className={`w-full flex items-center justify-between px-3 py-2 text-[12px] font-mono uppercase tracking-wider rounded-sm transition-colors ${
                activeFolder === "sent" 
                  ? "bg-foreground text-background font-bold" 
                  : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              }`}
            >
              <div className="flex items-center gap-2">
                <Send className="w-3.5 h-3.5" />
                <span>Sent</span>
              </div>
              <span className="text-[10px]">
                {threads.filter(t => t.status === "sent").length}
              </span>
            </button>

            <button
              onClick={() => { setActiveFolder("drafts"); setActiveThreadId(null); }}
              className={`w-full flex items-center justify-between px-3 py-2 text-[12px] font-mono uppercase tracking-wider rounded-sm transition-colors ${
                activeFolder === "drafts" 
                  ? "bg-foreground text-background font-bold" 
                  : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              }`}
            >
              <div className="flex items-center gap-2">
                <FileText className="w-3.5 h-3.5" />
                <span>Drafts</span>
              </div>
              <span className="text-[10px]">
                {threads.filter(t => t.status === "follow-up").length}
              </span>
            </button>

            <div className="my-2 border-t border-border/50"></div>

            <button
              onClick={() => { setActiveFolder("cleanup"); setActiveThreadId(null); }}
              className={`w-full flex items-center justify-between px-3 py-2.5 text-[12px] font-mono uppercase tracking-wider rounded-sm border transition-colors ${
                activeFolder === "cleanup" 
                  ? "bg-foreground text-background border-foreground font-bold" 
                  : "bg-surface text-amber-500 border-amber-500/20 hover:bg-amber-500/10"
              }`}
            >
              <div className="flex items-center gap-2">
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clean Up</span>
              </div>
              <span className="px-1.5 py-0.5 text-[8px] font-bold bg-amber-500 text-background rounded-full font-sans uppercase">
                New
              </span>
            </button>
          </div>
        </div>

        {/* Main Content Area (Gmail full-width list or details) */}
        <div className="flex-1 flex flex-col h-[calc(100vh-64px)] overflow-hidden bg-background">
          
          {/* Global connection/error messages */}
          {connMessage && (
            <div className="p-3 bg-surface border-b border-border">
              <Banner tone={connMessage.tone}>{connMessage.text}</Banner>
            </div>
          )}
          {error && (
            <div className="p-3 bg-surface border-b border-border">
              <ErrorBlock message={error} onRetry={fetchThreads} />
            </div>
          )}

          {/* VIEW: Clean Up Dashboard (Folder selected) */}
          {activeFolder === "cleanup" ? (
            <div className="flex-1 flex flex-col overflow-y-auto p-4 space-y-4">
              <Panel 
                title="Clutter Clean Up Co-Pilot" 
                code="unsubscriber-v1"
                right={
                  <Button
                    variant="primary"
                    className="gap-2 !py-1 text-[11px]"
                    onClick={scanUnsubscribeCandidates}
                    disabled={loadingCandidates}
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${loadingCandidates ? "animate-spin" : ""}`} />
                    Scan 30d+ Clutter
                  </Button>
                }
              >
                <div className="space-y-3">
                  <div className="flex items-start gap-2.5 p-3 bg-muted/60 border border-border/80 text-muted-foreground">
                    <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                    <p className="font-mono text-[11px] leading-relaxed">
                      Our automatic unsubscriber scans your mailbox for unread emails that are <strong className="text-foreground">older than 30 days</strong>, and which <strong className="text-foreground">do not have stars or custom user labels</strong>. Clicking "Unsubscribe" executes unsubscriptions by parsing RFC headers and automates Gmail archiving/muting.
                    </p>
                  </div>

                  {unsubscribeMessage && (
                    <Banner tone={unsubscribeMessage.tone}>{unsubscribeMessage.text}</Banner>
                  )}

                  {loadingCandidates ? (
                    <div className="p-8"><Loading label="SCANNING CLUTTER CANDIDATES..." /></div>
                  ) : candidates.length === 0 ? (
                    <div className="border border-dashed border-border p-12 text-center text-muted-foreground font-mono text-[12px]">
                      NO CANDIDATES FOUND. CLICK "SCAN 30D+ CLUTTER" TO INITIATE A MAILBOX SEARCH.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {/* Bulk actions bar */}
                      <div className="flex items-center justify-between p-2.5 bg-muted border border-border">
                        <div className="flex items-center gap-2">
                          <input 
                            type="checkbox" 
                            className="rounded-sm border-border bg-background"
                            checked={selectedCandidateIds.size === candidates.length}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedCandidateIds(new Set(candidates.map(c => c.id)));
                              } else {
                                setSelectedCandidateIds(new Set());
                              }
                            }}
                          />
                          <span className="font-mono text-[11px] text-foreground">
                            {selectedCandidateIds.size} Senders Selected
                          </span>
                        </div>
                        <Button
                          variant="secondary"
                          className="!py-1 !px-3 text-[11px] border-amber-500/30 text-amber-400 hover:bg-amber-500/10"
                          disabled={selectedCandidateIds.size === 0 || processingUnsubscribe}
                          onClick={handleBulkUnsubscribe}
                        >
                          {processingUnsubscribe ? "Cleaning..." : "Bulk Unsubscribe & Archive"}
                        </Button>
                      </div>

                      {/* Candidates List */}
                      <div className="border border-border bg-surface divide-y divide-border/60">
                        {candidates.map((c) => (
                          <div 
                            key={c.id}
                            className="p-3 flex items-start gap-3 hover:bg-muted/30 transition-colors"
                          >
                            <input 
                              type="checkbox"
                              className="mt-1 rounded-sm border-border bg-background"
                              checked={selectedCandidateIds.has(c.id)}
                              onChange={() => toggleCandidateSelection(c.id)}
                            />
                            
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between">
                                <span className="font-mono text-[12px] font-bold text-foreground truncate">
                                  {c.from_name || c.from_email}
                                </span>
                                <span className="font-mono text-[10px] text-muted-foreground">
                                  {relTime(c.timestamp)}
                                </span>
                              </div>
                              <div className="font-sans text-[12px] text-foreground font-semibold line-clamp-1 mt-0.5">
                                {c.subject}
                              </div>
                              <div className="font-sans text-[11px] text-muted-foreground line-clamp-1 mt-0.5">
                                {c.snippet}
                              </div>
                              <div className="flex items-center gap-2 mt-2">
                                <span className="text-[10px] font-mono text-muted-foreground truncate">
                                  Sender: {c.from_email}
                                </span>
                                {c.unsubscribe_mailto && (
                                  <Tag className="text-[9px] border-blue-500/30 text-blue-400">mailto</Tag>
                                )}
                                {c.unsubscribe_url && (
                                  <Tag className="text-[9px] border-purple-500/30 text-purple-400">web-link</Tag>
                                )}
                                {!c.list_unsubscribe && (
                                  <Tag className="text-[9px] border-amber-500/30 text-amber-500">archive/mute only</Tag>
                                )}
                              </div>
                            </div>

                            <div className="flex items-center gap-2 shrink-0">
                              {c.unsubscribe_url && (
                                <a 
                                  href={c.unsubscribe_url} 
                                  target="_blank" 
                                  rel="noopener noreferrer"
                                  className="p-1 hover:bg-muted rounded text-muted-foreground hover:text-foreground"
                                  title="Visit unsubscribe link"
                                >
                                  <ExternalLink className="w-3.5 h-3.5" />
                                </a>
                              )}
                              <Button
                                variant="secondary"
                                className="!py-1 !px-2.5 text-[10px]"
                                onClick={() => handleUnsubscribe(c.id)}
                                disabled={processingUnsubscribe}
                              >
                                Unsubscribe
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </Panel>
            </div>
          ) : activeThread ? (
            /* VIEW: Thread Details View (Opened Email) */
            <div className="flex-1 flex flex-col min-h-0 overflow-y-auto p-4 space-y-4">
              
              {/* Back to Inbox Toolbar */}
              <div className="flex items-center justify-between p-2 bg-surface border border-border">
                <Button
                  variant="secondary"
                  className="!py-1 gap-1 text-[11px]"
                  onClick={() => { setActiveThreadId(null); setAiDraft(null); setReplyBody(""); setReplySuccess(false); }}
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  Back to {activeFolder}
                </Button>

                <div className="flex items-center gap-2">
                  <Button
                    variant="secondary"
                    className="!py-1 gap-1 text-[11px] hover:bg-muted/50"
                    onClick={() => handleArchive(activeThread.id)}
                  >
                    <Archive className="w-3.5 h-3.5" />
                    Archive
                  </Button>
                  <Button
                    variant="secondary"
                    className="!py-1 gap-1 text-[11px] hover:bg-red-500/10 text-red-400"
                    onClick={() => handleTrash(activeThread.id)}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    Trash
                  </Button>
                  <Button
                    variant="secondary"
                    className="!py-1 gap-1 text-[11px] border-amber-500/30 text-amber-400 hover:bg-amber-500/10"
                    onClick={() => handleUnsubscribe(activeThread.id)}
                    disabled={processingUnsubscribe}
                  >
                    <BellOff className="w-3.5 h-3.5" />
                    Unsubscribe
                  </Button>
                </div>
              </div>

              {unsubscribeMessage && (
                <Banner tone={unsubscribeMessage.tone}>{unsubscribeMessage.text}</Banner>
              )}

              {/* Thread detail panel */}
              <Panel
                title="Thread Details"
                code={activeThread.id}
                right={
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] text-muted-foreground">
                      FROM: {activeThread.from_email}
                    </span>
                    <Tag
                      className={
                        activeThread.status === "interview"
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : activeThread.status === "rejected"
                          ? "bg-red-500/10 text-red-400 border-red-500/20"
                          : "bg-muted text-foreground"
                      }
                    >
                      {activeThread.status}
                    </Tag>
                  </div>
                }
              >
                <div className="space-y-3">
                  <div>
                    <h2 className="font-sans font-bold text-[16px] text-foreground">
                      {activeThread.subject}
                    </h2>
                  </div>
                  <div className="border border-border bg-surface p-1 rounded-sm">
                    {activeThread.body && (activeThread.body.includes("<html") || activeThread.body.includes("<div") || activeThread.body.includes("<p") || activeThread.body.includes("<br") || activeThread.body.includes("<table")) ? (
                      <iframe
                        title="email-body"
                        sandbox="allow-same-origin"
                        srcDoc={`
                          <!DOCTYPE html>
                          <html>
                            <head>
                              <style>
                                body {
                                  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                                  font-size: 13px;
                                  line-height: 1.5;
                                  color: #111111;
                                  background-color: #ffffff;
                                  margin: 12px;
                                  word-wrap: break-word;
                                }
                              </style>
                            </head>
                            <body>
                              ${activeThread.body}
                            </body>
                          </html>
                        `}
                        className="w-full h-80 border-0 bg-white"
                      />
                    ) : (
                      <pre className="font-mono text-[12px] leading-relaxed whitespace-pre-wrap text-foreground select-text p-3">
                        {activeThread.body}
                      </pre>
                    )}
                  </div>
                </div>
              </Panel>

              {/* Reply Hub */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* AI Draft Assist */}
                <Panel
                  title="AI Reply Assistant"
                  code="copilot-draft"
                  right={
                    <Button
                      variant="primary"
                      className="!py-1 gap-1 text-[11px]"
                      onClick={() => handleGenerateAIDraft(activeThread.id)}
                      disabled={generatingDraft}
                    >
                      {generatingDraft ? (
                        <>
                          <Loader2 className="w-3 h-3 animate-spin" />
                          Analyzing...
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-3 h-3" />
                          Draft Smart Reply
                        </>
                      )}
                    </Button>
                  }
                >
                  <div className="space-y-2">
                    <p className="font-mono text-[10px] text-muted-foreground">
                      AI scans the thread category, extracts deadlines/schedule links, and generates outreach replies per the Mailer Constitution policies.
                    </p>
                    {aiDraft ? (
                      <div className="border border-border/80 bg-surface/50 p-3 space-y-2">
                        <div className="flex items-center justify-between">
                          <Overline className="text-[10px]">Draft Target Email</Overline>
                          <Tag>{aiDraft.to_email}</Tag>
                        </div>
                        <div className="font-mono text-[11px] font-bold text-foreground">
                          {aiDraft.subject}
                        </div>
                        <pre className="font-mono text-[11px] leading-relaxed text-muted-foreground whitespace-pre-wrap max-h-36 overflow-y-auto border-t border-border/40 pt-2">
                          {aiDraft.body}
                        </pre>
                        {aiDraft.draft_id && (
                          <Banner tone="success">
                            Draft synced: ID: {aiDraft.draft_id.slice(0, 15)}...
                          </Banner>
                        )}
                      </div>
                    ) : (
                      <div className="border border-dashed border-border p-6 text-center text-muted-foreground font-mono text-[11px]">
                        NO DRAFT GENERATED. CLICK ABOVE TO USE CO-PILOT.
                      </div>
                    )}
                  </div>
                </Panel>

                {/* Composer */}
                <Panel title="Reply Inline Composer" code="smtp / gmail draft">
                  <div className="space-y-3">
                    <Textarea
                      rows={6}
                      value={replyBody}
                      onChange={(e) => setReplyBody(e.target.value)}
                      placeholder="Type your outbound message reply here. Supports syncing back to Gmail drafts."
                    />

                    {replySuccess && (
                      <Banner tone="success">
                        Reply finalized! Syncing / reply dispatch succeeded.
                      </Banner>
                    )}

                    <div className="flex justify-end gap-2">
                      <Button
                        variant="secondary"
                        onClick={() => {
                          setReplyBody(aiDraft ? aiDraft.body : "");
                        }}
                        disabled={!aiDraft}
                      >
                        Reset to AI
                      </Button>
                      <Button
                        variant="primary"
                        onClick={async () => {
                          setSendingReply(true);
                          setReplySuccess(false);
                          setError(null);
                          try {
                            await api.sendInboxReply(activeThread.id, {
                              subject: aiDraft?.subject || `Re: ${activeThread.subject}`,
                              body: replyBody,
                              to_email: activeThread.from_email
                            });
                            setReplySuccess(true);
                          } catch (err) {
                            setError(err.detail || "Failed to send inline reply.");
                          } finally {
                            setSendingReply(false);
                          }
                        }}
                        disabled={!replyBody.trim() || sendingReply}
                      >
                        {sendingReply ? "Dispatching..." : "Send Inline Reply"}
                      </Button>
                    </div>
                  </div>
                </Panel>
              </div>
            </div>
          ) : (
            /* VIEW: Folder Thread List (Gmail style full-width rows) */
            <div className="flex-1 flex flex-col overflow-hidden">
              
              {/* Toolbar */}
              <div className="p-3 border-b border-border bg-surface flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <h3 className="font-mono font-bold text-[13px] uppercase tracking-wider text-foreground">
                    {activeFolder} Folder
                  </h3>
                <button 
                    onClick={() => fetchThreads()}
                    className="p-1 hover:bg-muted rounded text-muted-foreground hover:text-foreground transition-colors"
                    title="Refresh threads"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                  </button>

                  {/* Pagination Controls */}
                  <div className="flex items-center gap-1 border-l border-border pl-3">
                    <Button
                      variant="secondary"
                      className="!py-0.5 !px-2 text-[10px] gap-0.5"
                      disabled={prevPageTokens.length === 0}
                      onClick={goPrevPage}
                    >
                      &lt; Newer
                    </Button>
                    <span className="font-mono text-[9px] text-muted-foreground px-1 select-none">
                      pg {pageIndex}
                    </span>
                    <Button
                      variant="secondary"
                      className="!py-0.5 !px-2 text-[10px] gap-0.5"
                      disabled={!nextPageToken}
                      onClick={goNextPage}
                    >
                      Older &gt;
                    </Button>
                  </div>
                </div>

                {/* Tag filters within folder */}
                <div className="flex items-center gap-1.5 overflow-x-auto">
                  <span className="font-mono text-[9px] text-muted-foreground mr-1">FILTER:</span>
                  {TAGS.map((t) => (
                    <button
                      key={t.value}
                      onClick={() => setSelectedTag(t.value)}
                      className={`px-2 py-0.5 text-[9px] font-mono uppercase border tracking-wider transition-colors ${
                        selectedTag === t.value
                          ? "bg-foreground text-background border-foreground font-bold"
                          : "bg-surface text-muted-foreground border-border hover:text-foreground"
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Thread items full-width list */}
              <div className="flex-1 overflow-y-auto divide-y divide-border bg-surface">
                {loading ? (
                  <div className="p-8"><Loading label="SYNCHRONIZING MAILBOX..." /></div>
                ) : finalThreads.length === 0 ? (
                  <div className="p-16 text-center text-muted-foreground font-mono text-[12px]">
                    0 THREADS FOUND FOR "{selectedTag.toUpperCase()}" IN {activeFolder.toUpperCase()} FOLDER.
                  </div>
                ) : (
                  finalThreads.map((t) => (
                    <div
                      key={t.id}
                      onClick={() => {
                        setActiveThreadId(t.id);
                        setAiDraft(null);
                        setReplyBody("");
                        setReplySuccess(false);
                      }}
                      className="group flex items-center justify-between p-3.5 cursor-pointer hover:bg-muted/40 transition-colors border-l-2 border-transparent hover:border-foreground relative"
                    >
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        {/* Selector checkbox */}
                        <input 
                          type="checkbox"
                          className="rounded-sm border-border bg-background hidden md:inline-block"
                          checked={selectedThreadIds.has(t.id)}
                          onClick={(e) => e.stopPropagation()}
                          onChange={(e) => toggleThreadSelection(e, t.id)}
                        />

                        {/* Star quick toggle */}
                        <button
                          onClick={(e) => toggleStarThread(e, t.id)}
                          className={`p-0.5 rounded transition-colors ${
                            t.status === "interview" 
                              ? "text-amber-400" 
                              : "text-muted-foreground hover:text-foreground"
                          }`}
                        >
                          <Star className="w-3.5 h-3.5 fill-current" />
                        </button>

                        {/* Sender */}
                        <span className="font-mono text-[12px] font-bold text-foreground truncate w-40 shrink-0">
                          {t.from_name || t.from_email}
                        </span>

                        {/* Subject + Snippet */}
                        <div className="flex items-baseline gap-2 min-w-0 flex-1">
                          <span className="font-sans text-[13px] font-semibold text-foreground truncate">
                            {t.subject}
                          </span>
                          <span className="text-muted-foreground text-[12px] font-sans truncate hidden sm:inline">
                            &mdash; {t.snippet}
                          </span>
                        </div>
                      </div>

                      {/* Right area: Tag + Date + Hover Actions */}
                      <div className="flex items-center gap-3 shrink-0 ml-2">
                        {/* Status tag */}
                        <Tag
                          className={
                            t.status === "interview"
                              ? "border-emerald-500/20 text-emerald-400 bg-emerald-500/5 text-[9px]"
                              : t.status === "rejected"
                              ? "border-red-500/20 text-red-400 bg-red-500/5 text-[9px]"
                              : t.status === "applied"
                              ? "border-blue-500/20 text-blue-400 bg-blue-500/5 text-[9px]"
                              : "border-amber-500/20 text-amber-400 bg-amber-500/5 text-[9px]"
                          }
                        >
                          {t.status}
                        </Tag>

                        {/* Date */}
                        <span className="font-mono text-[10px] text-muted-foreground w-16 text-right">
                          {relTime(t.timestamp)}
                        </span>

                        {/* Quick hover actions (Gmail style) */}
                        <div className="absolute right-3 bg-gradient-to-l from-surface via-surface pl-6 pr-1 hidden group-hover:flex items-center gap-1.5">
                          <Button
                            variant="secondary"
                            className="!p-1 !h-7 !w-7 justify-center border-border hover:bg-muted/50 text-foreground"
                            title="Archive Thread"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleArchive(t.id);
                            }}
                          >
                            <Archive className="w-3.5 h-3.5" />
                          </Button>
                          <Button
                            variant="secondary"
                            className="!p-1 !h-7 !w-7 justify-center border-red-500/20 hover:bg-red-500/10 text-red-400"
                            title="Move to Trash"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleTrash(t.id);
                            }}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                          <Button
                            variant="secondary"
                            className="!p-1 !h-7 !w-7 justify-center border-amber-500/20 hover:bg-amber-500/10 text-amber-500"
                            title="Unsubscribe Sender"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleUnsubscribe(t.id);
                            }}
                          >
                            <BellOff className="w-3.5 h-3.5" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
