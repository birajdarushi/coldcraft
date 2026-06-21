import { useEffect, useState } from "react";
import { ExternalLink, KeyRound, LogOut, Trash2 } from "lucide-react";
import AppShell from "../components/AppShell.jsx";
import { Button, Panel, Field, Input, Toggle, Banner, Loading, Tag, Overline } from "../components/ui.jsx";
import { api } from "../lib/api.js";
import { useAuth } from "../lib/auth.jsx";

const TABS = [
  { key: "account", label: "ACCOUNT", code: "00" },
  { key: "apikeys", label: "API KEYS", code: "01" },
  { key: "config", label: "SMTP CONFIG", code: "09" },
  { key: "profile", label: "PROFILE", code: "08" },
  { key: "policies", label: "POLICIES", code: "10" },
  { key: "features", label: "FEATURES", code: "11" },
  { key: "integrations", label: "INTEGRATIONS", code: "12" },
];

function AccountTab() {
  const { email, isGuest, logout } = useAuth();
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function deleteAccount() {
    setBusy(true);
    setError("");
    try {
      await api.deleteAccount();
      logout(); // clears token + returns to login
    } catch (e) {
      setError(e?.detail || "Could not delete account.");
      setBusy(false);
    }
  }

  if (isGuest) {
    return (
      <Panel title="Session">
        <Banner tone="warn">
          You're browsing as a guest. Sign in with email to manage an account.
        </Banner>
        <div className="mt-4">
          <Button variant="secondary" onClick={logout} data-testid="account-exit-guest">
            <LogOut className="w-3.5 h-3.5" /> Exit guest
          </Button>
        </div>
      </Panel>
    );
  }

  return (
    <div className="space-y-5">
      <Panel title="Session" code="GET /api/v1/auth/me · email-OTP login">
        <div className="flex items-center justify-between gap-4">
          <div>
            <Overline>Signed in as</Overline>
            <div className="font-mono text-[14px] mt-1" data-testid="account-email">{email || "—"}</div>
          </div>
          <Button variant="secondary" onClick={logout} data-testid="account-signout">
            <LogOut className="w-3.5 h-3.5" /> Sign out
          </Button>
        </div>
      </Panel>

      <Panel title="Danger zone" code="DELETE /api/v1/auth/account" className="border-red-500/60">
        <p className="font-mono text-[11px] leading-relaxed text-muted-foreground mb-4">
          Deleting your account removes all login codes tied to{" "}
          <span className="text-foreground">{email}</span> and signs you out. This cannot be undone.
        </p>
        {error && <div className="mb-3"><Banner tone="error">{error}</Banner></div>}
        <Field label="Type DELETE to confirm" className="max-w-xs">
          <Input
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="DELETE"
            data-testid="account-delete-confirm"
          />
        </Field>
        <div className="mt-3">
          <Button
            variant="danger"
            onClick={deleteAccount}
            disabled={busy || confirm !== "DELETE"}
            data-testid="account-delete"
          >
            <Trash2 className="w-3.5 h-3.5" /> {busy ? "Deleting…" : "Delete account"}
          </Button>
        </div>
      </Panel>
    </div>
  );
}

function ProviderRow({ p, onSave }) {
  const [val, setVal] = useState("");
  const [saving, setSaving] = useState(false);

  async function save() {
    if (!val.trim()) return;
    setSaving(true);
    try { await onSave(p.provider, val.trim()); setVal(""); }
    finally { setSaving(false); }
  }

  const statusCls = p.configured
    ? "border-emerald-500 text-emerald-600 dark:text-emerald-400"
    : "border-amber-500 text-amber-600 dark:text-amber-400";

  return (
    <div className="border border-border bg-surface p-4">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <div className="flex items-center gap-2">
            <KeyRound className="w-3.5 h-3.5" />
            <span className="font-mono text-[13px] uppercase tracking-wider font-bold">{p.label}</span>
            <span className={`inline-block border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest ${statusCls}`}>
              {p.configured ? `CONFIGURED · ${p.source}` : "NOT SET"}
            </span>
          </div>
          <div className="font-mono text-[10px] text-muted-foreground mt-1.5 max-w-md">{p.feature}</div>
        </div>
        <a href={p.docs} target="_blank" rel="noreferrer"
          className="flex items-center gap-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground hover:text-foreground">
          Get key <ExternalLink className="w-3 h-3" />
        </a>
      </div>
      <div className="flex items-end gap-2">
        <Field label={`${p.provider} api key`} hint={p.source === "env" ? "set via env — UI override optional" : "write-only · encrypted at rest"} className="flex-1">
          <Input type="password" value={val} onChange={(e) => setVal(e.target.value)}
            placeholder={p.configured ? "•••••••••• (enter to replace)" : "paste key"}
            data-testid={`provider-input-${p.provider}`} />
        </Field>
        <Button variant="primary" onClick={save} disabled={saving || !val.trim()} data-testid={`provider-save-${p.provider}`}>
          {saving ? "Saving…" : "Save"}
        </Button>
      </div>
    </div>
  );
}

function ApiKeysTab() {
  const [providers, setProviders] = useState(null);
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);

  async function load() {
    setProviders(null); setError(null);
    try { const r = await api.getProviders(); setProviders(r.providers || []); }
    catch (e) { setError(e?.detail || "FAILED TO LOAD PROVIDERS"); }
  }
  useEffect(() => { load(); }, []);

  async function save(provider, api_key) {
    setMsg(null);
    try {
      const r = await api.setProvider({ provider, api_key });
      setProviders(r.providers || []);
      setMsg({ tone: "success", text: `${provider.toUpperCase()} KEY SAVED · ENCRYPTED · NEVER RETURNED` });
    } catch (e) { setMsg({ tone: "error", text: e?.detail || "SAVE FAILED" }); }
  }

  return (
    <Panel title="API keys" code="GET/PUT /api/v1/providers · keys power features below">
      <p className="font-mono text-[11px] leading-relaxed text-muted-foreground mb-4">
        Keys are encrypted at rest and never returned by the API. An env var (e.g. <span className="text-foreground">GEMINI_API_KEY</span>) takes
        precedence over a key saved here. Changes take effect on the next request.
      </p>
      {msg && <div className="mb-3"><Banner tone={msg.tone} testId="apikeys-msg">{msg.text}</Banner></div>}
      {error ? <Banner tone="error">{error}</Banner> : !providers ? <Loading /> : (
        <div className="space-y-3">
          {providers.map((p) => <ProviderRow key={p.provider} p={p} onSave={save} />)}
        </div>
      )}
      <div className="mt-4">
        <Overline>Note</Overline>
        <p className="font-mono text-[10px] text-muted-foreground mt-1">
          Gemini powers Compose (drafting) and Intel. Without a key those calls return a clear error.
        </p>
      </div>
    </Panel>
  );
}

function SaveBar({ saving, msg, onReload }) {
  return (
    <div className="flex items-center gap-3 pt-2">
      <Button type="submit" variant="primary" disabled={saving}>{saving ? "Saving…" : "Save"}</Button>
      <Button type="button" variant="secondary" onClick={onReload} disabled={saving}>Reload</Button>
      {msg && <Banner tone={msg.tone}>{msg.text}</Banner>}
    </div>
  );
}

function ConfigTab() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function load() {
    setForm(null); setMsg(null);
    const c = await api.getConfig();
    setForm(c
      ? { delivery_mode: "smtp", ...c, smtp_pass: "" }
      : { smtp_host: "", smtp_port: 587, smtp_user: "", from_email: "", from_name: "", tracking_domain: "", smtp_pass: "", delivery_mode: "smtp" });
  }
  useEffect(() => { load(); }, []);

  async function save(e) {
    e.preventDefault(); setSaving(true); setMsg(null);
    try {
      const body = { ...form }; if (!body.smtp_pass) delete body.smtp_pass;
      await api.saveConfig(body);
      setMsg({ tone: "success", text: "SAVED · PASSWORD NEVER RETURNED BY GET" });
      setForm((f) => ({ ...f, smtp_pass: "" }));
    } catch (e) { setMsg({ tone: "error", text: e?.detail || "SAVE FAILED" }); }
    finally { setSaving(false); }
  }

  if (!form) return <Loading />;
  const mode = form.delivery_mode || "smtp";
  const live = mode === "smtp";
  const setMode = (m) => setForm((f) => ({ ...f, delivery_mode: m }));

  return (
    <Panel title="SMTP & tracking" code="GET/PUT /api/v1/config · password write-only">
      {/* Delivery-mode switch */}
      <div className="border border-border bg-background p-4 mb-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <Overline>Delivery mode</Overline>
            <p className="font-mono text-[10px] text-muted-foreground mt-1 max-w-md">
              {live
                ? "LIVE — sends real email via the SMTP server below (auth + TLS)."
                : "TEST — captures mail locally in Mailpit (localhost:8025). No real delivery, no auth."}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className={`font-mono text-[11px] uppercase tracking-wider ${!live ? "font-bold text-foreground" : "text-muted-foreground"}`}>
              Mailpit · test
            </span>
            <label className="switch" title="Toggle delivery mode">
              <input
                type="checkbox"
                data-testid="delivery-mode-switch"
                checked={live}
                onChange={(e) => setMode(e.target.checked ? "smtp" : "mailpit")}
              />
              <span className="slider" />
            </label>
            <span className={`font-mono text-[11px] uppercase tracking-wider ${live ? "font-bold text-foreground" : "text-muted-foreground"}`}>
              SMTP · live
            </span>
          </div>
        </div>
        {!live && (
          <Banner tone="warn" testId="mailpit-note">
            Mailpit mode active — the SMTP credentials below are ignored. Sends land at{" "}
            <a className="underline" href={import.meta.env.VITE_MAILPIT_URL || "http://localhost:8025"} target="_blank" rel="noreferrer">the Mailpit inbox</a>.
          </Banner>
        )}
      </div>

      <form onSubmit={save} className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className={`md:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4 ${live ? "" : "opacity-50"}`}>
          <Field label="SMTP host"><Input value={form.smtp_host} onChange={set("smtp_host")} required={live} /></Field>
          <Field label="Port"><Input type="number" value={form.smtp_port} onChange={set("smtp_port")} required={live} /></Field>
          <Field label="SMTP user"><Input value={form.smtp_user} onChange={set("smtp_user")} required={live} /></Field>
          <Field label="Password" hint="blank keeps existing"><Input type="password" placeholder="(keep existing)" value={form.smtp_pass} onChange={set("smtp_pass")} /></Field>
        </div>
        <Field label="From email"><Input type="email" value={form.from_email} onChange={set("from_email")} required /></Field>
        <Field label="From name"><Input value={form.from_name} onChange={set("from_name")} required /></Field>
        <Field label="Tracking domain" hint="optional" className="md:col-span-2"><Input value={form.tracking_domain || ""} onChange={set("tracking_domain")} /></Field>
        <div className="md:col-span-2"><SaveBar saving={saving} msg={msg} onReload={load} /></div>
      </form>
    </Panel>
  );
}

function ProfileTab() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const setArr = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) }));

  async function load() {
    setForm(null); setMsg(null);
    const p = await api.getProfile();
    setForm(p || { name: "", email: "", skills: [], proof_points: [], tone: "" });
  }
  useEffect(() => { load(); }, []);

  async function save(e) {
    e.preventDefault(); setSaving(true); setMsg(null);
    try { await api.saveProfile(form); setMsg({ tone: "success", text: "PROFILE SAVED" }); }
    catch (e) { setMsg({ tone: "error", text: e?.detail || "SAVE FAILED" }); }
    finally { setSaving(false); }
  }

  if (!form) return <Loading />;
  return (
    <Panel title="Sender profile" code="GET/PUT /api/v1/profile · fallback for compose">
      <form onSubmit={save} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="Name"><Input value={form.name} onChange={set("name")} required /></Field>
          <Field label="Email"><Input type="email" value={form.email} onChange={set("email")} required /></Field>
        </div>
        <Field label="Skills" hint="comma separated"><Input value={(form.skills || []).join(", ")} onChange={setArr("skills")} /></Field>
        <Field label="Proof points" hint="comma separated"><Input value={(form.proof_points || []).join(", ")} onChange={setArr("proof_points")} /></Field>
        <Field label="Tone"><Input value={form.tone || ""} onChange={set("tone")} placeholder="direct, technical, no fluff" /></Field>
        <SaveBar saving={saving} msg={msg} onReload={load} />
      </form>
    </Panel>
  );
}

function PoliciesTab() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);
  const num = (k) => (e) => setForm((f) => ({ ...f, [k]: Number(e.target.value) }));

  async function load() { setForm(null); setMsg(null); setForm(await api.getPolicies()); }
  useEffect(() => { load(); }, []);

  async function save(e) {
    e.preventDefault(); setSaving(true); setMsg(null);
    try {
      await api.savePolicies({
        daily_send_limit: form.daily_send_limit,
        max_company_emails_30d: form.max_company_emails_30d,
        subject_max_chars: form.subject_max_chars,
        followup_days: form.followup_days,
      });
      setMsg({ tone: "success", text: "POLICIES SAVED (CLAMPED TO FLOORS)" });
    } catch (e) { setMsg({ tone: "error", text: e?.detail || "SAVE FAILED" }); }
    finally { setSaving(false); }
  }

  if (!form) return <Loading />;
  const floors = form.constitution_floors || {};
  const rows = [
    ["daily_send_limit", "Daily send limit", floors.daily_send_limit],
    ["max_company_emails_30d", "Per-company / 30d", floors.max_company_emails_30d],
    ["subject_max_chars", "Subject max chars", floors.subject_max_chars],
  ];
  return (
    <Panel title="Policy overrides" code="GET/PUT /api/v1/policies · tighten only, never loosen">
      <form onSubmit={save} className="space-y-4">
        {rows.map(([k, label, ceil]) => {
          const over = form[k] > ceil;
          return (
            <div key={k} className="flex items-end gap-4">
              <Field label={label} hint={`ceiling ${ceil}`} className="w-48">
                <Input type="number" value={form[k] ?? ""} onChange={num(k)}
                  className={over ? "border-red-500 text-red-500" : ""} />
              </Field>
              <div className="flex-1 pb-2">
                <div className="font-mono text-[10px] text-muted-foreground">
                  CONSTITUTION FLOOR: <span className="font-bold">{ceil}</span> · overrides may only go ≤ this.
                  {over && <span className="text-red-500"> EXCEEDS — will 422.</span>}
                </div>
              </div>
            </div>
          );
        })}
        <Field label="Follow-up days" hint="comma separated" className="w-48">
          <Input value={(form.followup_days || []).join(", ")}
            onChange={(e) => setForm((f) => ({ ...f, followup_days: e.target.value.split(",").map((s) => Number(s.trim())).filter((n) => !Number.isNaN(n)) }))} />
        </Field>
        <SaveBar saving={saving} msg={msg} onReload={load} />
      </form>
    </Panel>
  );
}

function FeaturesTab() {
  const [form, setForm] = useState(null);
  const [msg, setMsg] = useState(null);

  async function load() { setForm(null); setForm(await api.getFeatures()); }
  useEffect(() => { load(); }, []);

  async function toggle(k, v) {
    setForm((f) => ({ ...f, [k]: v }));
    try { await api.saveFeatures({ [k]: v }); setMsg({ tone: "success", text: `${k.toUpperCase()} = ${v}` }); }
    catch (e) { setMsg({ tone: "error", text: e?.detail || "SAVE FAILED" }); }
  }

  if (!form) return <Loading />;
  const flags = [
    ["tracking_enabled", "Tracking", "Injects the open/click pixel on send. When off, /track hits are ignored."],
    ["auto_followups", "Auto follow-ups", "Lets the Phase-3 worker process due follow-ups automatically."],
  ];
  return (
    <Panel title="Feature flags" code="GET/PUT /api/v1/features · effects on next send">
      <div className="space-y-px bg-border border border-border">
        {flags.map(([k, label, desc]) => (
          <div key={k} className="flex items-center justify-between gap-4 bg-surface p-4">
            <div>
              <div className="font-mono text-[13px] uppercase tracking-wider">{label}</div>
              <div className="font-mono text-[10px] text-muted-foreground mt-1 max-w-md">{desc}</div>
            </div>
            <Toggle checked={!!form[k]} onChange={(v) => toggle(k, v)} testId={`toggle-${k}`} />
          </div>
        ))}
      </div>
      {msg && <div className="mt-3"><Banner tone={msg.tone}>{msg.text}</Banner></div>}
    </Panel>
  );
}

function IntegrationsTab() {
  const [form, setForm] = useState(null);
  const [token, setToken] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  async function load() { setForm(null); setMsg(null); setToken(""); setForm(await api.getIntegrations()); }
  useEffect(() => { load(); }, []);

  async function save(e) {
    e.preventDefault(); setSaving(true); setMsg(null);
    try {
      const body = { scraper_sources: form.scraper_sources };
      if (token) body.apify_token = token;
      const r = await api.saveIntegrations(body);
      setForm(r); setToken("");
      setMsg({ tone: "success", text: "SAVED · SECRET REDACTED ON GET" });
    } catch (e) { setMsg({ tone: "error", text: e?.detail || "SAVE FAILED" }); }
    finally { setSaving(false); }
  }

  if (!form) return <Loading />;
  return (
    <Panel title="Integrations" code="GET/PUT /api/v1/integrations · secrets write-only">
      <form onSubmit={save} className="space-y-4">
        <Field label="Apify token" hint={form.apify_token ? "stored: ***  ·  blank keeps existing" : "none stored"}>
          <Input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder={form.apify_token ? "(keep existing ***)" : "paste token"} />
        </Field>
        <Field label="Scraper sources" hint="comma separated">
          <Input value={(form.scraper_sources || []).join(", ")}
            onChange={(e) => setForm((f) => ({ ...f, scraper_sources: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) }))} />
        </Field>
        <div className="flex flex-wrap gap-1">
          {(form.scraper_sources || []).map((s) => <Tag key={s}>{s}</Tag>)}
        </div>
        <SaveBar saving={saving} msg={msg} onReload={load} />
      </form>
    </Panel>
  );
}

export default function Settings() {
  const [tab, setTab] = useState("account");
  return (
    <AppShell title="Settings" subtitle="// CONFIGURABLE LAYER · GET/PUT /API/V1/*">
      <div className="p-5 max-w-4xl">
        <div className="flex flex-wrap gap-px bg-border border border-border mb-5">
          {TABS.map((t) => (
            <button key={t.key} onClick={() => setTab(t.key)} data-testid={`settings-tab-${t.key}`}
              className={`flex items-center gap-2 px-4 py-2.5 font-mono text-[11px] uppercase tracking-wider ${tab === t.key ? "bg-foreground text-background" : "bg-surface text-muted-foreground hover:bg-muted"}`}>
              {import.meta.env.DEV && <span className="opacity-50 text-[9px]">{t.code}</span>}{t.label}
            </button>
          ))}
        </div>

        {tab === "account" && <AccountTab />}
        {tab === "apikeys" && <ApiKeysTab />}
        {tab === "config" && <ConfigTab />}
        {tab === "profile" && <ProfileTab />}
        {tab === "policies" && <PoliciesTab />}
        {tab === "features" && <FeaturesTab />}
        {tab === "integrations" && <IntegrationsTab />}
      </div>
    </AppShell>
  );
}
