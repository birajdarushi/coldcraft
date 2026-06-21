import { useState, useEffect } from "react";
import { Brain, GitBranch, Plus, RefreshCw, Save, Trash2, ShieldAlert, Award, FileText, CheckCircle2 } from "lucide-react";
import AppShell from "../components/AppShell.jsx";
import { Button, Panel, Field, Input, Textarea, Overline, Tag, Banner, Loading, ErrorBlock, Select } from "../components/ui.jsx";
import { api } from "../lib/api.js";

const TYPES = [
  { value: "identity", label: "Identity & Profile" },
  { value: "resume_bullet", label: "Resume Accomplishment Bullets" },
  { value: "style_option", label: "Outreach Style & Tone Options" },
  { value: "github_summary", label: "GitHub Portfolio blurb" },
];

export default function Memory() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  // Form state
  const [form, setForm] = useState({
    type: "identity",
    key: "",
    value: "",
    source: "user_input",
  });

  useEffect(() => {
    fetchMemory();
  }, []);

  async function fetchMemory() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listMemory();
      setEntries(Array.isArray(res) ? res : []);
    } catch (err) {
      setError(err.detail || "Failed to load memory bank entries.");
    } finally {
      setLoading(false);
    }
  }

  const setVal = (key) => (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }));

  async function handleSave(e) {
    e.preventDefault();
    if (!form.key.trim() || !form.value.trim()) return;
    setError(null);
    try {
      const saved = await api.saveMemory(form);
      // If it exists, update it. If not, add it.
      setEntries((prev) => {
        const index = prev.findIndex((item) => item.key === saved.key && item.type === saved.type);
        if (index > -1) {
          const updated = [...prev];
          updated[index] = saved;
          return updated;
        }
        return [saved, ...prev];
      });
      setActionMessage({ tone: "success", text: "Saved entry to memory bank." });
      setForm((prev) => ({ ...prev, key: "", value: "" }));
      setTimeout(() => setActionMessage(null), 3000);
    } catch (err) {
      setError(err.detail || "Failed to save memory entry.");
    }
  }

  async function handleSyncGithub() {
    setSyncing(true);
    setError(null);
    try {
      const newEntry = await api.syncGithubSummary();
      setEntries((prev) => {
        const index = prev.findIndex((item) => item.key === newEntry.key && item.type === newEntry.type);
        if (index > -1) {
          const updated = [...prev];
          updated[index] = newEntry;
          return updated;
        }
        return [newEntry, ...prev];
      });
      setActionMessage({ tone: "success", text: "Successfully synced and generated GitHub projects summary blurb!" });
      setTimeout(() => setActionMessage(null), 4000);
    } catch (err) {
      setError(err.detail || "Failed to sync GitHub profile summaries.");
    } finally {
      setSyncing(false);
    }
  }

  function handleSelectEntry(entry) {
    setForm({
      type: entry.type,
      key: entry.key,
      value: entry.value,
      source: entry.source || "user_input",
    });
  }

  // Group entries by type for visualization
  const grouped = {
    identity: entries.filter((e) => e.type === "identity"),
    resume_bullet: entries.filter((e) => e.type === "resume_bullet"),
    style_option: entries.filter((e) => e.type === "style_option"),
    github_summary: entries.filter((e) => e.type === "github_summary"),
  };

  return (
    <AppShell title="Memory Bank" subtitle="// KNOWLEDGE BASE · SENDER IDENTITY, RESUME BULLETS & OUTREACH PREFERENCES">
      <div className="p-4 grid grid-cols-1 lg:grid-cols-3 gap-4 max-w-7xl">
        {/* Left Column: Sync widget & Creator Form */}
        <div className="space-y-4 lg:col-span-1">
          
          {/* SYNC GITHUB BLURB CARD */}
          <Panel title="Sync GitHub Portfolio" code="automatic memory sync">
            <div className="space-y-3">
              <p className="font-mono text-[10px] text-muted-foreground">
                Fetches your active public repositories, catalogs language mix & descriptions, and compiles a technical project blurb using LLM reasoning.
              </p>
              <Button
                variant="primary"
                className="w-full justify-center gap-1.5"
                onClick={handleSyncGithub}
                disabled={syncing}
              >
                {syncing ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    Compiling Summaries...
                  </>
                ) : (
                  <>
                    <GitBranch className="w-3.5 h-3.5" />
                    Sync with GitHub
                  </>
                )}
              </Button>
            </div>
          </Panel>

          {/* ADD / EDIT FORM */}
          <Panel title="Save Memory Bullet" code="save / edit card">
            <form onSubmit={handleSave} className="space-y-3">
              <Field label="Memory Category">
                <Select value={form.type} onChange={setVal("type")} className="w-full">
                  {TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </Select>
              </Field>

              <Field label="Key Reference" hint="e.g. outbound_style_casual">
                <Input
                  value={form.key}
                  onChange={setVal("key")}
                  placeholder="e.g. background_summary"
                  required
                />
              </Field>

              <Field label="Memory Value Content">
                <Textarea
                  rows={6}
                  value={form.value}
                  onChange={setVal("value")}
                  placeholder="Insert exact resume bullet, bio summaries, or special instructions. E.g. '5+ years experience building highly-scaled API infrastructures using Go.'"
                  required
                />
              </Field>

              <Field label="Source Tag">
                <Input
                  value={form.source}
                  onChange={setVal("source")}
                  placeholder="user_input, resume_pdf, github_sync"
                />
              </Field>

              {error && <Banner tone="error">{error}</Banner>}

              <Button type="submit" variant="primary" className="w-full">
                <Save className="w-3.5 h-3.5" />
                Commit to Memory
              </Button>
            </form>
          </Panel>
        </div>

        {/* Right Columns: Memory Cards grid */}
        <div className="lg:col-span-2 space-y-4">
          {actionMessage && <Banner tone={actionMessage.tone}>{actionMessage.text}</Banner>}

          <Panel
            title="Memory Bank Vault"
            code="committed outline facts"
            right={
              <span className="font-mono text-[10px] text-muted-foreground">
                ITEMS: {entries.length}
              </span>
            }
          >
            {loading ? (
              <Loading label="EXTRACTING MEMORY ARCHIVE..." />
            ) : entries.length === 0 ? (
              <div className="border border-dashed border-border p-16 text-center text-muted-foreground font-mono text-[12px]">
                MEMORY VAULT IS EMPTY. SYNC GITHUB OR SAVE ENTRY TO SEED INFORMATION.
              </div>
            ) : (
              <div className="space-y-6">
                {/* Loop through categories */}
                {Object.entries(grouped).map(([typeKey, list]) => {
                  const typeLabel = TYPES.find((t) => t.value === typeKey)?.label || typeKey;
                  if (list.length === 0) return null;

                  return (
                    <div key={typeKey} className="space-y-2.5">
                      <Overline className="text-foreground tracking-[0.25em]">{typeLabel}</Overline>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {list.map((entry) => (
                          <div
                            key={entry.id}
                            onClick={() => handleSelectEntry(entry)}
                            className="border border-border bg-background p-3.5 hover:border-foreground/40 cursor-pointer transition-colors relative flex flex-col justify-between rounded-sm"
                          >
                            <div>
                              <div className="flex items-center justify-between gap-1 mb-1">
                                <span className="font-mono text-[10px] font-bold text-foreground truncate max-w-[170px]">
                                  {entry.key}
                                </span>
                                <span className="font-mono text-[8px] bg-muted px-1.5 py-0.5 border border-border text-muted-foreground">
                                  {entry.source || "user"}
                                </span>
                              </div>
                              <p className="font-sans text-[11.5px] leading-relaxed text-muted-foreground mt-2 select-text">
                                {entry.value}
                              </p>
                            </div>
                            <div className="mt-3.5 pt-2 border-t border-border/20 flex justify-end">
                              <span className="font-mono text-[8px] text-muted-foreground/60">
                                ID: {entry.id.slice(0, 8)}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Panel>
        </div>
      </div>
    </AppShell>
  );
}
