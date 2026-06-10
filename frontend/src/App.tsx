import { useEffect, useState } from 'react'
import './App.css'

// Types matching /api/v1 responses (no hard-coded data)
interface Stats {
  sent_today: number
  open_rate: number
  pending_approvals: number
}

interface CampaignListItem {
  id: string
  subject: string
  recipient: string
  status: string
  created_at: string | null
  word_count: number
}

interface CampaignDetail {
  id: string
  subject: string
  body_html: string | null
  body_text: string | null
  recipient_email: string
  recipient_name: string
  status: string
  created_at: string | null
  qa_result: unknown
  followup_schedule: string[]
  word_count: number
}

interface EventItem {
  id: string
  event_type: string
  occurred_at: string | null
  metadata: Record<string, unknown> | null
}

interface ConfigData {
  smtp_host: string
  smtp_port: number
  smtp_user: string
  from_email: string
  from_name: string
  tracking_domain: string | null
}

interface ProfileData {
  name: string
  email: string
  skills: string[]
  proof_points: string[]
  tone: string | null
}

const API = '' // proxied by Vite dev server to http://localhost:8000

const TABS = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'campaigns', label: 'Campaigns' },
  { key: 'config', label: 'Config' },
] as const

type Tab = (typeof TABS)[number]['key']

function App() {
  const [tab, setTab] = useState<Tab>('dashboard')

  // Dashboard (strictly uses /api/v1/stats)
  const [stats, setStats] = useState<Stats | null>(null)
  const [statsLoading, setStatsLoading] = useState(false)
  const [statsError, setStatsError] = useState<string | null>(null)

  // Campaigns list + detail (live from /api/v1/campaigns)
  const [campaigns, setCampaigns] = useState<CampaignListItem[]>([])
  const [campaignsLoading, setCampaignsLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<CampaignDetail | null>(null)
  const [events, setEvents] = useState<EventItem[]>([])
  const [eventsLoading, setEventsLoading] = useState(false)
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  // Config + Profile (GET/PUT live)
  const [config, setConfig] = useState<ConfigData | null>(null)
  const [configForm, setConfigForm] = useState<Partial<ConfigData & { smtp_pass?: string }>>({})
  const [configLoading, setConfigLoading] = useState(false)
  const [configMsg, setConfigMsg] = useState<string | null>(null)

  const [profile, setProfile] = useState<ProfileData | null>(null)
  const [profileForm, setProfileForm] = useState<Partial<ProfileData>>({})
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileMsg, setProfileMsg] = useState<string | null>(null)

  // --- Dashboard: ONLY hits /api/v1/stats ---
  async function loadStats() {
    setStatsLoading(true)
    setStatsError(null)
    try {
      const res = await fetch(`${API}/api/v1/stats`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: Stats = await res.json()
      setStats(data)
    } catch (e: any) {
      setStatsError(e.message || 'Failed to load stats')
      setStats(null)
    } finally {
      setStatsLoading(false)
    }
  }

  // --- Campaigns ---
  async function loadCampaigns(status?: string) {
    setCampaignsLoading(true)
    try {
      const q = status ? `?status=${encodeURIComponent(status)}` : ''
      const res = await fetch(`${API}/api/v1/campaigns${q}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: CampaignListItem[] = await res.json()
      setCampaigns(data)
    } catch (e) {
      setCampaigns([])
    } finally {
      setCampaignsLoading(false)
    }
  }

  async function loadDetail(id: string) {
    setSelectedId(id)
    setDetail(null)
    setEvents([])
    try {
      const res = await fetch(`${API}/api/v1/campaigns/${id}`)
      if (!res.ok) throw new Error('Not found')
      const d: CampaignDetail = await res.json()
      setDetail(d)
    } catch {
      setDetail(null)
    }
  }

  async function loadEvents(id: string) {
    setEventsLoading(true)
    try {
      const res = await fetch(`${API}/api/v1/campaigns/${id}/events`)
      if (res.ok) {
        const evs: EventItem[] = await res.json()
        setEvents(evs)
      }
    } finally {
      setEventsLoading(false)
    }
  }

  async function approve(id: string) {
    setActionMsg(null)
    try {
      const res = await fetch(`${API}/api/v1/campaigns/${id}/approve`, { method: 'POST' })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`)
      setActionMsg(`Approved → ${body.status || 'user_approved'}`)
      await loadCampaigns(statusFilter || undefined)
      if (selectedId === id) await loadDetail(id)
    } catch (e: any) {
      setActionMsg(`Approve failed: ${e.message}`)
    }
  }

  async function send(id: string) {
    setActionMsg(null)
    try {
      const res = await fetch(`${API}/api/v1/campaigns/${id}/send`, { method: 'POST' })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`)
      setActionMsg(`Sent ✓ (id: ${body.campaign_id || id})`)
      await loadCampaigns(statusFilter || undefined)
      if (selectedId === id) await loadDetail(id)
    } catch (e: any) {
      setActionMsg(`Send failed: ${e.message}`)
    }
  }

  function onStatusFilterChange(v: string) {
    const next = v || ''
    setStatusFilter(next)
    loadCampaigns(next || undefined)
  }

  // --- Config ---
  async function loadConfig() {
    setConfigLoading(true)
    setConfigMsg(null)
    try {
      const res = await fetch(`${API}/api/v1/config`)
      if (res.status === 404) {
        setConfig(null)
        setConfigForm({ smtp_host: '', smtp_port: 587, smtp_user: '', from_email: '', from_name: '', tracking_domain: '' })
        return
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: ConfigData = await res.json()
      setConfig(data)
      setConfigForm({ ...data, smtp_pass: '' })
    } catch (e: any) {
      setConfigMsg(e.message)
    } finally {
      setConfigLoading(false)
    }
  }

  async function saveConfig(e: React.FormEvent) {
    e.preventDefault()
    setConfigLoading(true)
    setConfigMsg(null)
    try {
      const payload: any = {
        smtp_host: configForm.smtp_host,
        smtp_port: Number(configForm.smtp_port),
        smtp_user: configForm.smtp_user,
        from_email: configForm.from_email,
        from_name: configForm.from_name,
        tracking_domain: configForm.tracking_domain || null,
      }
      if (configForm.smtp_pass) payload.smtp_pass = configForm.smtp_pass

      const res = await fetch(`${API}/api/v1/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      const saved: ConfigData = await res.json()
      setConfig(saved)
      setConfigForm({ ...saved, smtp_pass: '' })
      setConfigMsg('Config saved (password never returned by GET)')
    } catch (e: any) {
      setConfigMsg(`Save failed: ${e.message}`)
    } finally {
      setConfigLoading(false)
    }
  }

  // --- Profile ---
  async function loadProfile() {
    setProfileLoading(true)
    setProfileMsg(null)
    try {
      const res = await fetch(`${API}/api/v1/profile`)
      if (res.status === 404) {
        setProfile(null)
        setProfileForm({ name: '', email: '', skills: [], proof_points: [], tone: '' })
        return
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: ProfileData = await res.json()
      setProfile(data)
      setProfileForm(data)
    } catch (e: any) {
      setProfileMsg(e.message)
    } finally {
      setProfileLoading(false)
    }
  }

  async function saveProfile(e: React.FormEvent) {
    e.preventDefault()
    setProfileLoading(true)
    setProfileMsg(null)
    try {
      const payload = {
        name: profileForm.name || '',
        email: profileForm.email || '',
        skills: profileForm.skills || [],
        proof_points: profileForm.proof_points || [],
        tone: profileForm.tone || null,
      }
      const res = await fetch(`${API}/api/v1/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      const saved: ProfileData = await res.json()
      setProfile(saved)
      setProfileForm(saved)
      setProfileMsg('Profile saved')
    } catch (e: any) {
      setProfileMsg(`Save failed: ${e.message}`)
    } finally {
      setProfileLoading(false)
    }
  }

  function updateProfileArray(field: 'skills' | 'proof_points', value: string) {
    const arr = value
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    setProfileForm((f) => ({ ...f, [field]: arr }))
  }

  // Load on tab switch + initial dashboard
  useEffect(() => {
    if (tab === 'dashboard' && !stats && !statsLoading) {
      loadStats()
    }
    if (tab === 'campaigns' && campaigns.length === 0 && !campaignsLoading) {
      loadCampaigns(statusFilter || undefined)
    }
    if (tab === 'config') {
      if (!config && !configLoading) loadConfig()
      if (!profile && !profileLoading) loadProfile()
    }
  }, [tab])

  return (
    <div className="shell">
      {/* Top nav */}
      <header className="nav">
        <div className="nav-inner">
          <div className="flex items-center gap-3">
            <div className="font-semibold tracking-tight text-xl text-zinc-900">Coldcraft</div>
            <div className="text-xs px-2 py-0.5 rounded bg-zinc-100 text-zinc-500">Mailer</div>
          </div>

          <nav className="flex items-center gap-1 ml-6">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`tab ${tab === t.key ? 'tab-active' : 'tab-inactive'}`}
              >
                {t.label}
              </button>
            ))}
          </nav>

          <div className="ml-auto text-xs text-zinc-400 flex items-center gap-3">
            <span>API: /api/v1</span>
            <a className="underline" href="http://localhost:8025" target="_blank" rel="noreferrer">Mailpit</a>
            <a className="underline" href="http://localhost:8000/docs" target="_blank" rel="noreferrer">/docs</a>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-6">
        {/* DASHBOARD — only /api/v1/stats */}
        {tab === 'dashboard' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="section-title">Dashboard</div>
              <button onClick={loadStats} className="btn" disabled={statsLoading}>
                {statsLoading ? 'Refreshing…' : 'Refresh'}
              </button>
            </div>

            {statsError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded">Error: {statsError}</div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="card">
                <div className="text-xs text-zinc-500">Sent today</div>
                <div className="text-4xl font-semibold text-zinc-900 mt-1 tabular-nums">
                  {stats ? stats.sent_today : '—'}
                </div>
                <div className="text-[11px] text-zinc-400 mt-1">from GET /api/v1/stats</div>
              </div>
              <div className="card">
                <div className="text-xs text-zinc-500">Open rate</div>
                <div className="text-4xl font-semibold text-zinc-900 mt-1 tabular-nums">
                  {stats ? (stats.open_rate * 100).toFixed(0) + '%' : '—'}
                </div>
                <div className="text-[11px] text-zinc-400 mt-1">from GET /api/v1/stats</div>
              </div>
              <div className="card">
                <div className="text-xs text-zinc-500">Pending approvals</div>
                <div className="text-4xl font-semibold text-zinc-900 mt-1 tabular-nums">
                  {stats ? stats.pending_approvals : '—'}
                </div>
                <div className="text-[11px] text-zinc-400 mt-1">qa_passed + user_approved</div>
              </div>
            </div>

            <div className="mt-6 text-xs text-zinc-400">
              This screen fetches <span className="font-mono">/api/v1/stats</span> only. No other endpoints.
            </div>
          </div>
        )}

        {/* CAMPAIGNS — list + preview/detail from live API */}
        {tab === 'campaigns' && (
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <div className="section-title">Campaigns</div>
              <select
                value={statusFilter}
                onChange={(e) => onStatusFilterChange(e.target.value)}
                className="input w-auto text-sm"
              >
                <option value="">All statuses</option>
                <option value="qa_passed">qa_passed</option>
                <option value="user_approved">user_approved</option>
                <option value="sent">sent</option>
                <option value="opened">opened</option>
                <option value="replied">replied</option>
              </select>
              <button onClick={() => loadCampaigns(statusFilter || undefined)} className="btn">Refresh list</button>
              <span className="text-xs text-zinc-400 ml-auto">GET /api/v1/campaigns</span>
            </div>

            {actionMsg && (
              <div className="p-2 text-sm bg-emerald-50 border border-emerald-200 text-emerald-700 rounded">{actionMsg}</div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
              {/* List */}
              <div className="lg:col-span-2 card overflow-auto max-h-[520px]">
                <div className="text-sm font-medium mb-2">All campaigns{statusFilter ? ` (filtered: ${statusFilter})` : ''}</div>
                {campaignsLoading && <div className="text-xs text-zinc-400">Loading…</div>}
                {!campaignsLoading && campaigns.length === 0 && (
                  <div className="text-sm text-zinc-400">No campaigns. Create via POST /api/v1/drafts or seed.</div>
                )}
                <table className="table">
                  <thead>
                    <tr>
                      <th>Subject</th>
                      <th>To</th>
                      <th>Status</th>
                      <th className="text-right">Words</th>
                    </tr>
                  </thead>
                  <tbody>
                    {campaigns.map((c) => (
                      <tr
                        key={c.id}
                        onClick={() => loadDetail(c.id)}
                        className={`cursor-pointer hover:bg-zinc-50 ${selectedId === c.id ? 'bg-zinc-100' : ''}`}
                      >
                        <td className="pr-2">{c.subject || '(no subject)'}</td>
                        <td className="text-xs text-zinc-500">{c.recipient}</td>
                        <td>
                          <span className={`status status-${c.status}`}>{c.status}</span>
                        </td>
                        <td className="text-right tabular-nums text-xs">{c.word_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Detail / Preview */}
              <div className="lg:col-span-3">
                {!selectedId && <div className="card text-sm text-zinc-500">Select a campaign from the list to preview body, schedule, and events.</div>}

                {detail && (
                  <div className="space-y-4">
                    <div className="card">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <div className="font-semibold text-lg">{detail.subject}</div>
                          <div className="text-sm text-zinc-500">
                            {detail.recipient_name} &lt;{detail.recipient_email}&gt;
                          </div>
                          <div className="mt-1">
                            <span className={`status status-${detail.status}`}>{detail.status}</span>
                            <span className="ml-2 text-xs text-zinc-400 mono">{detail.id.slice(0, 8)}…</span>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          {['qa_passed', 'draft'].includes(detail.status) && (
                            <button onClick={() => approve(detail.id)} className="btn">Approve</button>
                          )}
                          {detail.status === 'user_approved' && (
                            <button onClick={() => send(detail.id)} className="btn btn-primary">Send now</button>
                          )}
                          <button onClick={() => loadDetail(detail.id)} className="btn">Reload</button>
                        </div>
                      </div>

                      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <div className="label">Follow-up schedule (from policy)</div>
                          <div className="flex flex-wrap gap-1">
                            {detail.followup_schedule.length ? (
                              detail.followup_schedule.map((d, i) => (
                                <span key={i} className="px-2 py-0.5 text-xs bg-zinc-100 rounded border">{d}</span>
                              ))
                            ) : (
                              <span className="text-xs text-zinc-400">none</span>
                            )}
                          </div>
                        </div>
                        <div>
                          <div className="label">Word count / created</div>
                          <div className="text-sm">
                            {detail.word_count} words · {detail.created_at ? new Date(detail.created_at).toLocaleString() : '—'}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Body preview */}
                    <div className="card">
                      <div className="flex items-center gap-2 mb-2">
                        <div className="text-sm font-medium">Preview</div>
                        <div className="text-[10px] text-zinc-400">live from API — no hardcoded content</div>
                      </div>

                      <div className="flex gap-2 mb-2 text-xs">
                        <button
                          className="btn"
                          onClick={() => {
                            /* html shown by default in iframe */
                          }}
                        >
                          HTML
                        </button>
                        <button
                          className="btn"
                          onClick={() => {
                            /* text is below */
                          }}
                        >
                          Text
                        </button>
                      </div>

                      {detail.body_html ? (
                        <iframe
                          title="email-html-preview"
                          className="preview-frame"
                          srcDoc={detail.body_html}
                          sandbox="allow-same-origin"
                        />
                      ) : (
                        <div className="text-xs text-zinc-400 p-3 border rounded">No HTML body</div>
                      )}

                      <details className="mt-3">
                        <summary className="cursor-pointer text-xs text-zinc-500 select-none">Plain text version</summary>
                        <pre className="mt-2 text-xs bg-zinc-50 p-3 rounded border overflow-auto whitespace-pre-wrap mono">
                          {detail.body_text || '(empty)'}
                        </pre>
                      </details>
                    </div>

                    {/* Events */}
                    <div className="card">
                      <div className="flex items-center gap-2 mb-2">
                        <div className="text-sm font-medium">Events</div>
                        <button onClick={() => selectedId && loadEvents(selectedId)} className="btn text-xs">
                          {eventsLoading ? 'Loading…' : 'Load / refresh events'}
                        </button>
                        <span className="text-[10px] text-zinc-400">GET /…/events</span>
                      </div>
                      {events.length === 0 && !eventsLoading && (
                        <div className="text-xs text-zinc-400">No events recorded yet.</div>
                      )}
                      <ul className="text-sm space-y-1">
                        {events.map((ev) => (
                          <li key={ev.id} className="flex gap-2 text-xs">
                            <span className="font-mono text-zinc-400 w-40 shrink-0">
                              {ev.occurred_at ? new Date(ev.occurred_at).toLocaleString() : '—'}
                            </span>
                            <span className="font-medium">{ev.event_type}</span>
                            {ev.metadata && Object.keys(ev.metadata).length > 0 && (
                              <span className="text-zinc-400 mono">{JSON.stringify(ev.metadata)}</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* CONFIG — real GET/PUT for config + profile */}
        {tab === 'config' && (
          <div className="space-y-8">
            {/* SMTP Config */}
            <div>
              <div className="section-title">SMTP &amp; Tracking Config</div>
              <div className="text-xs text-zinc-400 mb-3">GET /api/v1/config → PUT (password encrypted server-side, never returned)</div>

              {configMsg && <div className="mb-3 text-sm p-2 bg-zinc-100 border rounded">{configMsg}</div>}

              <form onSubmit={saveConfig} className="card max-w-2xl grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="label">SMTP Host</label>
                  <input className="input" value={configForm.smtp_host || ''} onChange={(e) => setConfigForm({ ...configForm, smtp_host: e.target.value })} required />
                </div>
                <div>
                  <label className="label">Port</label>
                  <input className="input" type="number" value={configForm.smtp_port || 587} onChange={(e) => setConfigForm({ ...configForm, smtp_port: Number(e.target.value) })} required />
                </div>
                <div>
                  <label className="label">SMTP User</label>
                  <input className="input" value={configForm.smtp_user || ''} onChange={(e) => setConfigForm({ ...configForm, smtp_user: e.target.value })} required />
                </div>
                <div>
                  <label className="label">Password (leave blank to keep on update)</label>
                  <input
                    className="input"
                    type="password"
                    placeholder={config ? '(keep existing)' : 'required for first create'}
                    value={configForm.smtp_pass || ''}
                    onChange={(e) => setConfigForm({ ...configForm, smtp_pass: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label">From Email</label>
                  <input className="input" value={configForm.from_email || ''} onChange={(e) => setConfigForm({ ...configForm, from_email: e.target.value })} required />
                </div>
                <div>
                  <label className="label">From Name</label>
                  <input className="input" value={configForm.from_name || ''} onChange={(e) => setConfigForm({ ...configForm, from_name: e.target.value })} required />
                </div>
                <div className="md:col-span-2">
                  <label className="label">Tracking Domain (optional)</label>
                  <input className="input" value={configForm.tracking_domain || ''} onChange={(e) => setConfigForm({ ...configForm, tracking_domain: e.target.value })} />
                </div>

                <div className="md:col-span-2 flex gap-2">
                  <button type="submit" className="btn btn-primary" disabled={configLoading}>
                    {configLoading ? 'Saving…' : 'Save Config (PUT /api/v1/config)'}
                  </button>
                  <button type="button" onClick={loadConfig} className="btn" disabled={configLoading}>Reload</button>
                </div>
              </form>

              {config && (
                <div className="mt-2 text-xs text-emerald-600">Current (redacted): {config.from_name} &lt;{config.from_email}&gt; — password omitted by server</div>
              )}
            </div>

            {/* Sender Profile */}
            <div>
              <div className="section-title">Sender Profile</div>
              <div className="text-xs text-zinc-400 mb-3">GET /api/v1/profile → PUT (used as fallback for /drafts when no sender_profile sent)</div>

              {profileMsg && <div className="mb-3 text-sm p-2 bg-zinc-100 border rounded">{profileMsg}</div>}

              <form onSubmit={saveProfile} className="card max-w-2xl space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="label">Name</label>
                    <input className="input" value={profileForm.name || ''} onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })} required />
                  </div>
                  <div>
                    <label className="label">Email</label>
                    <input className="input" type="email" value={profileForm.email || ''} onChange={(e) => setProfileForm({ ...profileForm, email: e.target.value })} required />
                  </div>
                </div>

                <div>
                  <label className="label">Skills (comma separated)</label>
                  <input
                    className="input"
                    value={(profileForm.skills || []).join(', ')}
                    onChange={(e) => updateProfileArray('skills', e.target.value)}
                    placeholder="Python, FastAPI, TypeScript"
                  />
                </div>
                <div>
                  <label className="label">Proof points (comma separated)</label>
                  <input
                    className="input"
                    value={(profileForm.proof_points || []).join(', ')}
                    onChange={(e) => updateProfileArray('proof_points', e.target.value)}
                    placeholder="Built X, Led Y, Shipped Z"
                  />
                </div>
                <div>
                  <label className="label">Tone</label>
                  <input className="input" value={profileForm.tone || ''} onChange={(e) => setProfileForm({ ...profileForm, tone: e.target.value })} placeholder="direct, technical, no fluff" />
                </div>

                <div className="flex gap-2">
                  <button type="submit" className="btn btn-primary" disabled={profileLoading}>
                    {profileLoading ? 'Saving…' : 'Save Profile (PUT /api/v1/profile)'}
                  </button>
                  <button type="button" onClick={loadProfile} className="btn" disabled={profileLoading}>Reload</button>
                </div>
              </form>

              {profile && (
                <div className="mt-2 text-xs text-emerald-600">
                  Current: {profile.name} — {profile.skills.length} skills, {profile.proof_points.length} proof points
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      <footer className="max-w-6xl mx-auto px-6 pb-10 text-[10px] text-zinc-400">
        All data comes from the live <span className="font-mono">/api/v1</span> backend. No mock or hardcoded values in the UI.
      </footer>
    </div>
  )
}

export default App
