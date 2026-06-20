# Coldcraft / GTM Engine — Screen-by-Screen Functional Spec

**Purpose of this document:** describe *what each screen does* — its data, states, actions, validation, business rules, and the exact APIs behind it — so the UI can be (re)designed from a complete functional contract. **No visual/layout/design decisions are prescribed here.** Treat every screen below as a set of requirements, not a wireframe.

**Product in one line:** a personal, constitution-governed cold-outreach engine for job seekers. It discovers jobs, researches the target company, drafts hyper-personalized emails, runs them through self-review + an independent QA gate, requires explicit human approval, sends via the user's own SMTP inside a safe send window, tracks opens/clicks, and schedules follow-ups.

**Hard rule that shapes every screen:** the UI is a *thin client*. All business logic, validation, and limits live in the API. The browser never decides whether something is allowed — it calls an endpoint and renders the result or the error. Every number, list, and status shown must come from `/api/v1`; nothing is hardcoded or computed client-side beyond trivial formatting.

**Base URL:** all app endpoints are under `/api/v1` except public tracking routes (`/track/*`) and `/health`. In dev the Vite server proxies `/api`, `/track`, `/health` to the backend on `:8000`.

---

## Backend availability legend

Each screen is tagged with how much of its backend exists today, so you know what is real vs. aspirational:

- **LIVE** — API implemented and verified; screen can be fully wired now.
- **PARTIAL** — API exists but returns stubs for some fields (noted inline).
- **PLANNED** — API not built yet (Phase 3/4); screen is a forward spec.

---

## The pipeline every email passes through (mental model for the whole app)

Several screens are just windows onto stages of one pipeline. Understand the pipeline once; the screens then make sense.

```
Job / target           Company intel + sender profile
   │                          │
   ▼                          ▼
PREFLIGHT GATE  ── research threshold · do-not-contact list · ATS conflict
   │               · daily send limit · per-company 30-day limit
   │               · no-outreach policy · duplicate send
   ▼
HOOK GENERATION ── 3 candidate opening hooks, each scored on
   │               specificity / surprise / relevance; best is selected
   ▼
DRAFT + SELF-REVIEW ── word count 100–180 · subject ≤50 chars
   │                    · ≥2 company-specific personalization signals
   │                    · first sentence must not start with "I"
   │                    · ≤1 exclamation mark · no banned/spam phrases
   ▼
QA GATE ── independent validation, up to 2 auto-revision retries,
   │        then escalates (blocks) if still failing
   ▼
USER APPROVAL ── nothing sends without an explicit human approve action
   │
   ▼
SEND ── timezone-aware, only inside 6:00am–10:00pm recipient local time,
   │     via the user's SMTP; optional tracking pixel injected
   ▼
TRACK + FOLLOW-UP ── opens/clicks recorded; follow-ups scheduled at
                     Day 5 and Day 12 unless a reply arrives first
```

**Status lifecycle of a campaign** (the `status` field you'll render everywhere):
`draft` → `self_review` → `qa_passed` (or blocked) → `user_approved` → `sent` → `opened` → `clicked` → `replied`. Blocked/failed terminal states surface as API errors (HTTP 422/409) carrying a specific reason.

---

## Constitution floors (immutable limits — display, never let the user exceed)

These are enforced in code (`domain/policies.py`) and **cannot be weakened by any API or screen**. The Policies screen may make them *stricter*, never looser. Surface them as read-only context wherever a user edits a related setting.

| Rule | Hard limit |
|------|-----------|
| Subject line length | ≤ 50 characters |
| Body word count | 100–180 words |
| Personalization signals | ≥ 2 company-specific references |
| First sentence | Must not start with "I" |
| Exclamation marks | ≤ 1 |
| Daily send cap | 20 emails/day |
| Hourly send cap | 5 emails/hour |
| Per-company cap | 3 emails per rolling 30 days |
| Send window | 06:00–22:00 recipient local time |
| Follow-ups | Up to 2, at Day 5 and Day 12 |
| QA revision retries | 2 before escalation |
| Minimum job match score | 40 |
| Banned phrases | "passionate about", "exciting opportunity", "look forward to hearing from you", "click here", "guaranteed", "100%", etc. (full list server-side) |
| Spam-trigger words | "urgent", "winner", "congratulations", "free", "risk free", "buy now", etc. |

---

# SCREENS

---

## 0. Global App Shell — LIVE

**Purpose:** persistent frame around every screen; navigation + environment awareness.

**Must contain:**
- Product identity ("Coldcraft" / Mailer context label).
- Primary navigation across the top-level destinations (see screen list below). Today only Dashboard / Campaigns / Config exist; the full app needs: Dashboard, Campaigns, Compose, Jobs, Intel, Settings (with sub-sections Config / Profile / Policies / Features / Integrations).
- Quick links to operational tools: Mailpit inbox (dev mail viewer, `VITE_MAILPIT_URL`, default `http://localhost:8025`) and the OpenAPI docs (`/docs`).
- An indicator of which API base it's talking to.

**States:** none beyond active-nav highlighting.

**Rules:** navigation is client-only routing; no data side effects. Every destination lazy-loads its own data on entry.

---

## 1. Dashboard — LIVE

**Purpose:** at-a-glance health of the outreach operation. The current implementation intentionally calls **only** `GET /api/v1/stats`.

**Data (all from `GET /api/v1/stats`):**
| Field | Meaning | Server computation |
|-------|---------|--------------------|
| `sent_today` | Emails sent today | count of campaigns sent today |
| `open_rate` | Fraction 0–1 (render as %) | `(opened + replied) / sent`, or 0 if no sends |
| `pending_approvals` | Items awaiting human action | count of `qa_passed` + `user_approved` |

**Actions:** Refresh (re-fetch stats).

**States:** loading (fetching), error (HTTP failure → show message, render `—` for values), empty (zeros are valid data, not empty).

**Rules:** no other endpoint may be called from this screen. Values are raw from the API; the only client transform is `open_rate * 100` for display.

**Worth adding (forward spec, needs new aggregates):** trend over time, reply rate, sends-remaining-today against the daily limit, count of blocked/escalated drafts. These require new fields on `/stats` — do not fabricate them client-side.

---

## 2. Campaigns — List — LIVE

**Purpose:** browse, filter, and select campaigns; entry point to detail/preview and to approve/send actions.

**Data (from `GET /api/v1/campaigns?status=&limit=&offset=`):** array of:
| Field | Notes |
|-------|-------|
| `id` | campaign UUID |
| `subject` | may be empty → render "(no subject)" |
| `recipient` | recipient email |
| `status` | drives status styling/grouping |
| `created_at` | ISO timestamp or null |
| `word_count` | computed from body text |

**Filters / controls:**
- Status filter (server-side via `?status=`): values seen in UI today — `qa_passed`, `user_approved`, `sent`, `opened`, `replied`; plus "All". The full status vocabulary is the lifecycle list above.
- Pagination: `limit` (1–1000, default 100) + `offset` (≥0). UI currently fetches a single page; a real list needs paging controls.
- Refresh.

**Actions:** select a row → loads detail (screen 3).

**States:** loading; empty ("No campaigns. Create via Compose / `POST /drafts`."); error (fall back to empty list).

**Rules:** filtering and pagination are server-side — never filter the full set in the browser. Selecting a row must not mutate anything.

---

## 3. Campaign Detail / Preview — PARTIAL

**Purpose:** inspect a single campaign fully and act on it (approve, send, schedule follow-ups, record reply).

**Data (from `GET /api/v1/campaigns/{id}`):**
| Field | Notes |
|-------|-------|
| `id`, `subject`, `status` | header identity |
| `recipient_name`, `recipient_email` | recipient |
| `body_html` | rendered preview (sandboxed iframe; treat as untrusted HTML) |
| `body_text` | plain-text alternative |
| `word_count` | from body text |
| `created_at` | ISO or null |
| `followup_schedule` | array of ISO dates, computed from policy `followup_days` anchored on send/created time (Day 5 / Day 12 by default) |
| `qa_result` | **STUB — currently always null.** Spec target: the QA verdict object (scores, violations, warnings, retry count). Do not invent; render "not available" until persisted. |

**Events timeline (from `GET /api/v1/campaigns/{id}/events`):** array of `{ id, event_type, occurred_at, metadata }`. Event types include `sent`, `opened`, `clicked`, `replied`. Load on demand / refreshable.

**Actions (state-gated — the API enforces, the UI should mirror):**
| Action | Endpoint | Allowed when | Result |
|--------|----------|--------------|--------|
| Approve | `POST /campaigns/{id}/approve` | status in `{qa_passed, draft}` | → `user_approved`; 409 if status disallows |
| Send now | `POST /campaigns/{id}/send` | status `user_approved` | sends via SMTP; 422 on send-block (timing/limits/duplicate) |
| Schedule follow-ups | `POST /campaigns/{id}/followups` | after send | persists scheduled tasks for Day 5/12 |
| Record reply | `POST /campaigns/{id}/reply` body `{reply_type, reply_text}` | any time a reply exists | sets reply state; should cancel pending follow-ups |
| Reload | re-GET detail/events | always | refresh |

**States:** nothing selected (prompt to pick from list); loading; detail-not-found (404); action-success banner (e.g. "Approved → user_approved"); action-error banner carrying the API `detail` string (this is where constitution/limit violations surface to the user — show the message verbatim).

**Rules:**
- Action buttons must be shown/enabled strictly by `status`; but always defer to the API's response — a 409/422 means re-sync and show the reason.
- `body_html` is model-generated and must be rendered sandboxed.
- Send failures are *expected* business outcomes (outside send window, daily/company limit hit, duplicate). Present them as informative, not as crashes.

**Forward spec:** show the personalization signals, the selected hook vs. the rejected hook candidates, and the QA scores once `qa_result` is persisted.

---

## 4. Compose / Create Draft — LIVE (backend), NO UI YET

**Purpose:** the core creation flow — turn a target (job + company intel + recipient) into a QA-passed draft via the full pipeline. This is the most important screen to design and currently has **no front-end**; only `POST /api/v1/drafts` exists.

**Inputs (request body for `POST /api/v1/drafts`):**
| Field | Required | Notes |
|-------|----------|-------|
| `job_id` | yes | the job this outreach targets |
| `recipient_email` | yes | who receives it |
| `recipient_name` | yes | personalization + greeting |
| `company_intel` | yes | dict of researched facts; **must meet a research threshold or the draft is refused** |
| `sender_profile` | no | dict (name, skills, proof_points, tone). If omitted/empty, server falls back to the saved Sender Profile (screen 8) |
| `triggered_by` | no | defaults to "user" |

**What happens on submit (the pipeline — surface progress/results per stage):**
1. **Research check** — refuses (`ResearchInsufficientError` → 422) if `company_intel` is too thin, or `SenderProfileIncompleteError` if profile is missing required fields.
2. **Preflight gate** — any of these block with a specific 422 and a message the UI must show: do-not-contact (`DoNotContactError`), ATS conflict (`ATSConflictError`), daily limit (`DailyLimitError`), per-company 30-day limit (`CompanyLimitError`), no-outreach policy (`NoOutreachPolicyError`), duplicate (`DuplicateSendError`).
3. **Hook generation** — 3 candidate hooks generated, each scored (specificity / surprise / relevance); the top-scoring one is selected.
4. **Draft + self-review** — enforces word count 100–180, subject ≤50 chars, ≥2 personalization signals, first sentence not starting with "I", ≤1 exclamation, no banned/spam phrases. Failure → `SelfReviewError`.
5. **QA gate** — independent validation; up to 2 auto-revisions; still failing → `QAEscalationError` (escalated/blocked).

**Response (`serialize_draft`):** `{ campaign_id, subject, body_text, body_html, word_count, personalization_signals[], status, qa_result }`. On success the new campaign appears in the list (screen 2) at status `qa_passed` (or `draft`), ready for approval.

**States to design for:** form entry/validation; in-flight (pipeline running — ideally show stage progress); refusal/blocked (render the exact error + which gate failed, so the user can fix intel or pick another recipient); success (show the produced draft inline with subject, body preview, word count, personalization signals, and a path to approve).

**Rules:**
- This screen is where the constitution is most visible to the user. Every rejection is a teaching moment — show *which* rule failed and the offending value where the API provides it.
- Requires `ANTHROPIC_API_KEY` to be configured server-side; without it, drafting fails. The UI should detect/communicate this rather than show an opaque 500.
- `company_intel` will usually be pre-filled from the Intel report (screen 7) when arriving via that flow.

---

## 5. Jobs — Scrape + List — LIVE

**Purpose:** populate and browse the pool of target jobs that outreach is built from.

### 5a. Trigger scrape
**Input (`POST /api/v1/jobs/scrape`):** `{ url, source? }`. `url` is a careers page (Greenhouse/Lever boards and JSON-LD/generic HTML are supported). `source` optional (e.g. `careers_page`, `linkedin`).

**Response (`ScrapeResponse`):** `{ scraped, skipped, jobs[] }`. `skipped` counts duplicates (deduped by job URL). Show both counts after a run.

**States:** idle; scraping (can be long-running / hundreds of jobs); success (e.g. "142 scraped, 0 new on re-run"); error (`ScraperError` → 422 with reason, e.g. unreachable/unparseable page).

### 5b. Jobs list
**Data (`GET /api/v1/jobs?company=&limit=&offset=`):** array of `JobResponse`:
| Field | Notes |
|-------|-------|
| `id`, `title`, `url`, `source` | core |
| `company`, `location`, `description` | may be null |
| `match_score` | 0–100; gate for outreach (min 40). May be null until scored |
| `scraped_at` | ISO or null |

**Controls:** filter by `company`; pagination (`limit` 1–1000, `offset`). 

**Actions (forward spec):** select a job → Job Detail; "Draft outreach for this job" → Compose (screen 4) pre-seeded with `job_id` and company.

**Rules:** dedup is server-side by URL; re-scraping is safe and idempotent. Jobs below `min_match_score` (40) should be visibly de-emphasized as not outreach-eligible.

---

## 6. Job Detail — PARTIAL (no dedicated endpoint yet)

**Purpose:** full view of one job + its match score, as the launch point to compose outreach.

**Data:** today there is no `GET /jobs/{id}` (PLAN lists it; not implemented). Source from the list item until added. Show: title, company, location, full description, source, URL (link out), `match_score`, `scraped_at`.

**Actions:** "Generate intel for this company" → screen 7; "Compose outreach" → screen 4 (blocked in UI if `match_score < 40`, but always defer to API).

**Forward spec:** dedicated detail endpoint with match-score breakdown (why it scored as it did).

---

## 7. Company Intel Report — LIVE

**Purpose:** generate and read a structured "readiness" dossier on a target company that feeds `company_intel` into Compose.

**Generate (`POST /api/v1/intel/reports`):** `{ company, force_refresh? }`. Cached reports are reused unless `force_refresh=true`; default cache TTL ~14 days.

**Read cached (`GET /api/v1/intel/reports/{company}`):** 404 if none.

**Data (`IntelReportResponse`):** `{ company, generated_at, cached (bool), sections{} }`. Seven sections, each `{ title, content, sources[], caveat? }`:
1. `company_fundamentals`
2. `engineering_culture`
3. `hiring_signals`
4. `recent_activity`
5. `recipient_intelligence` (who to contact — hiring manager / team lead)
6. `outreach_readiness` (is this company ready to be approached, and how)
7. `sources_and_limitations`

**States:** no report yet (offer Generate); generating; cached badge (show `cached` + `generated_at`, offer "Regenerate" = `force_refresh`); per-section caveat banner (dev uses a **sample provider** — sections carry an explicit "sample data" caveat that must be shown so the user doesn't trust placeholder facts as real).

**Rules:** always surface `sources[]` and `caveat` per section — provenance is a product requirement, not decoration. The report's facts are the raw material for `company_intel` in Compose; offer a direct "Use this for a draft" handoff.

---

## 8. Settings → Sender Profile — LIVE

**Purpose:** store the sender's identity once so drafts don't need it every time (fallback for Compose).

**Data (`GET /api/v1/profile`, 404 if unset):** `{ name, email, skills[], proof_points[], tone }`.

**Edit (`PUT /api/v1/profile`):** same shape; `skills` and `proof_points` are arrays (UI may accept comma-separated and split). `tone` is free text (e.g. "direct, technical, no fluff").

**States:** unset (404 → empty editable form, first save creates); loaded; saving; saved confirmation; validation (name + email required).

**Rules:** this profile is the fallback used by `POST /drafts` when `sender_profile` is omitted — make that relationship explicit in the UI. Weak/empty profiles cause `SenderProfileIncompleteError` at draft time.

---

## 9. Settings → SMTP & Tracking Config — LIVE

**Purpose:** configure the user's own outbound mail server + tracking domain, with no `.env` edits.

**Data (`GET /api/v1/config`, 404 if unset):** `{ smtp_host, smtp_port, smtp_user, from_email, from_name, tracking_domain }`. **The password is never returned** by GET — by design.

**Edit (`PUT /api/v1/config`):** all of the above plus `smtp_pass` (plain on input only). 
- On first create, `smtp_pass` is **required** (422 otherwise).
- On update, leaving `smtp_pass` blank **keeps the existing** password. The server encrypts it at rest (Fernet) and never echoes it.

**States:** unset (empty form, password required); loaded (password field empty with "(keep existing)" affordance); saving; saved ("password never returned by GET"); error (422 missing password on create; 500 if encryption key missing server-side).

**Rules:**
- Never display, log, or round-trip the password. The blank-means-keep behavior must be obvious so users don't accidentally wipe it.
- This config is what actual sends use; changes take effect on the next send. Consider a "send test email" affordance (forward spec — no endpoint yet) to validate credentials.
- Single-row singleton (one config per install).

---

## 10. Settings → Policies — LIVE

**Purpose:** let the user make outreach limits *stricter* than the constitution; show the immutable floors alongside.

**Data (`GET /api/v1/policies`):** `{ daily_send_limit, max_company_emails_30d, subject_max_chars, followup_days[], constitution_floors{} }`. Overrides are null when unset (meaning "use constitution default"). `constitution_floors` is the full immutable reference table — render it read-only next to each editable field.

**Edit (`PUT /api/v1/policies`):** any of `daily_send_limit`, `max_company_emails_30d`, `subject_max_chars`, `followup_days`. 
- Each editable value must be ≥ 1.
- Each is **clamped to / rejected above** its constitution ceiling: `daily_send_limit` ≤ 20, `max_company_emails_30d` ≤ 3, `subject_max_chars` ≤ 50. Exceeding → 422 with the exact ceiling message.

**States:** loaded (show current override or "default"); saving; saved; validation error (show the API's ceiling message verbatim).

**Rules:** the screen's entire job is to communicate "you may tighten, never loosen." Show the floor/ceiling beside every input and disable/flag values that would exceed it — but the API is the source of truth. Changing `daily_send_limit` immediately affects whether new drafts pass the preflight daily-limit check.

---

## 11. Settings → Feature Flags — LIVE

**Purpose:** toggle behavioral features.

**Data (`GET /api/v1/features`):** `{ tracking_enabled (default true), auto_followups (default true) }`.

**Edit (`PUT /api/v1/features`):** same booleans.

**Effects (make these visible):**
- `tracking_enabled=false` → no tracking pixel injected on send, and `/track/*` hits are ignored (no open/click events recorded). `true` restores both.
- `auto_followups` → governs whether follow-ups are processed automatically (consumed by the Phase 3 worker).

**States:** loaded; saving; saved.

**Rules:** flags change send/track behavior on the next send — state the consequence next to each toggle.

---

## 12. Settings → Integrations — LIVE

**Purpose:** configure scraper credentials and sources (Apify, scraper source list, future IMAP).

**Data (`GET /api/v1/integrations`):** `{ apify_token, scraper_sources[] }`. `apify_token` is **redacted**: returns `"***"` if a secret is stored, else `null` — the real token is never returned.

**Edit (`PUT /api/v1/integrations`):** `{ apify_token?, scraper_sources? }`. 
- Providing `apify_token` encrypts + stores it (same key as SMTP).
- Omitting `apify_token` **preserves** the existing one (partial update).
- `scraper_sources` is a list (e.g. `["linkedin", "careers_page", "greenhouse"]`).

**States:** unset (`***`/null, empty sources); loaded; saving; saved.

**Rules:** identical secret-handling discipline as SMTP config — never display or round-trip the real token; "blank keeps existing." `scraper_sources` configured here drive what the Jobs scraper (screen 5) can target.

---

## 13. Target-Company Workflow — PLANNED (Phase 2, not built)

**Purpose:** one action orchestrates the upstream funnel for a company: **intel → jobs → draft suggestion**.

**Intended (`POST /api/v1/workflows/target-company`):** input a company; returns a `workflow_id` and per-step results (intel report, matched jobs, a suggested draft). Mailer is blocked if intel is incomplete (same research threshold as Compose).

**Screen spec:** single company input → a stepped results view (intel summary → ranked jobs → proposed draft) with a handoff into Compose/Approve. Show each step's status and any gate that blocked progression.

---

## 14. Follow-up Worker Monitor — PLANNED (Phase 3)

**Purpose:** visibility into automated follow-up processing.

**Intended (`POST /api/v1/workers/followups/run`, `GET /api/v1/tasks`):** a worker processes due follow-ups (respecting `auto_followups`); tasks have status. Screen: list of scheduled/sent/cancelled follow-up tasks with due dates, plus a manual "run now" trigger. Replies cancel a sequence.

---

## 15. Reply Ingestion — PLANNED (Phase 3)

**Purpose:** record inbound replies (webhook or IMAP poll), which set campaign `status=replied` and cancel pending follow-ups.

**Intended (`POST /api/v1/webhooks/gmail`, plus reply handling already at `POST /campaigns/{id}/reply`):** screen shows reply status per campaign and confirms follow-up cancellation. Configuration of IMAP/webhook lives under Integrations (screen 12).

---

## 16. Network / Warm Paths — PLANNED (Phase 4)

**Purpose:** find warm introductions to a target company before going cold.

**Intended (`POST /api/v1/network/import` LinkedIn CSV, `GET /api/v1/network/paths?company=X`):** import contacts; screen returns top-3 ranked warm paths to a company, with an advisory reply-probability once enough labeled sends exist (ML, after 30+ outreach events). The PM logic routes a warm path ahead of a cold email when the score warrants.

---

# Cross-cutting requirements (apply to every screen)

1. **Errors are first-class content.** The API returns meaningful `detail` strings for every business rule (limits, constitution violations, send-window blocks, insufficient research, duplicates). Render them to the user verbatim — they are the product's voice, not generic failures. Map: 422 = business/validation rule, 409 = state conflict (e.g. approve wrong status), 404 = not found, 500 = server/config problem (e.g. missing encryption key or Anthropic key).
2. **Secrets never appear in the UI.** SMTP password and Apify token are write-only from the client's perspective; GET responses redact them. "Blank means keep existing" everywhere a secret is editable.
3. **Status drives affordances, API confirms them.** Show/enable actions by `status`, but treat the API response as authoritative and re-sync on conflict.
4. **No fabricated data.** Anything not provided by an endpoint (e.g. `qa_result` today) is shown as "not available," never invented or computed client-side.
5. **Provenance & caveats.** Intel sections carry sources and sample-data caveats — always display them.
6. **Constitution is omnipresent.** Wherever a limit is relevant (Compose, Policies, Campaign send), show the floor and explain that the system tightens but never loosens it.
7. **Operability without UI.** Per the API-first principle, every screen maps to endpoints that already work via curl/Postman; the UI must not introduce logic that isn't in the API.

---

# Screen inventory summary

| # | Screen | Backend | Primary endpoints |
|---|--------|---------|-------------------|
| 0 | App Shell | LIVE | — |
| 1 | Dashboard | LIVE | `GET /stats` |
| 2 | Campaigns list | LIVE | `GET /campaigns` |
| 3 | Campaign detail/preview | PARTIAL (`qa_result` stub) | `GET /campaigns/{id}`, `/events`, `POST approve/send/followups/reply` |
| 4 | Compose / create draft | LIVE (no UI) | `POST /drafts` |
| 5 | Jobs scrape + list | LIVE | `POST /jobs/scrape`, `GET /jobs` |
| 6 | Job detail | PARTIAL (no `/jobs/{id}`) | `GET /jobs` (filtered) |
| 7 | Company intel report | LIVE (sample provider) | `POST /intel/reports`, `GET /intel/reports/{company}` |
| 8 | Sender profile | LIVE | `GET/PUT /profile` |
| 9 | SMTP & tracking config | LIVE | `GET/PUT /config` |
| 10 | Policies | LIVE | `GET/PUT /policies` |
| 11 | Feature flags | LIVE | `GET/PUT /features` |
| 12 | Integrations | LIVE | `GET/PUT /integrations` |
| 13 | Target-company workflow | PLANNED | `POST /workflows/target-company` |
| 14 | Follow-up worker monitor | PLANNED | `POST /workers/followups/run`, `GET /tasks` |
| 15 | Reply ingestion | PLANNED | `POST /webhooks/gmail`, `POST /campaigns/{id}/reply` |
| 16 | Network / warm paths | PLANNED | `POST /network/import`, `GET /network/paths` |

Public, non-screen routes: `GET /track/open/{id}` (1×1 pixel, records open), `GET /track/click/{id}?url=` (302 redirect, records click), `GET /health`.
