# Progress Log

## Current Verified State

| Field | Value |
|-------|-------|
| **Repository root** | `/Users/rushiraj/Desktop/Personal/gtm` |
| **Standard startup** | `python3 scripts/dev_up.py` |
| **Standard verification** | `PYTHONPATH=. python3 -m unittest discover -s tests/unit -p 'test_*.py' -q` |
| **Current phase** | 0 → 1 (foundation done, operable loop next) |
| **Architectural principles** | API-first · Configurable · Constitution-bound (see `PLAN.md`) |
| **Highest priority unfinished feature** | p2-intel-report (p2-scraper just passed) |
| **Current blocker** | None |

### Verified working (with evidence)

- Docker dev stack: Postgres + Mailpit + API on Apple Silicon (`linux/arm64`)
- `GET /health` → `{"status":"ok"}`
- Mailer pipeline code: draft → QA gate → approve → send (API routes exist)
- Constitution validators + 2 unit tests pass
- Platform-aware startup: `scripts/dev_up.py` + `scripts/host_platform.py`
- Mailpit receives sent emails when SMTP flow exercised manually

### Not verified / not built

- Config/profile/policies APIs (p1-*-api)
- Campaign list/filter + detail + stats
- Tracking pixel/click endpoints (`/track/open`, `/track/click`)
- Frontend (React UI)
- Scraper, Intel, PM, Network, ML agents
- Reply ingestion (IMAP/Gmail)
- Background follow-up worker

---

## Session Records

### Session 2026-06-08 — Harness + platform setup

| Field | Value |
|-------|-------|
| **Goal** | Platform-aware Docker dev stack; agent workflow harness |
| **Completed** | Mailpit swap, `dev_up.py`, slim Dockerfile, harness files (this session) |
| **Verification run** | `docker compose ps`; `curl /health`; unittest (2 tests) |
| **Evidence recorded** | API health 200; mailpit 8025 200; containers healthy |
| **Commits** | (pending) |
| **Known risks** | Host Python 3.14 has no pytest; use unittest. `.env` gitignored. |
| **Next best action** | Implement `p1-api-router` (corrected) |

### Session 2026-06-08 — p1-api-router (versioned structure)

| Field | Value |
|-------|-------|
| **Goal** | Create `coldcraft/api/routers/`, mount `/api/v1`, migrate existing mailer routes, expose tags for config/campaigns/tracking |
| **Completed** | routers/health, drafts, campaigns + stubs for config/tracking; schemas.py for request models; app.py now uses include_router + deprecated legacy mounts |
| **Verification run** | `./init.sh`; `python3 scripts/dev_up.py` (rebuilds); `curl /api/v1/health`; `curl /openapi.json`; POSTs to /api/v1/drafts + /api/v1/campaigns/* and legacy; unittest |
| **Evidence recorded** | All 4 feature_list verifs passed (see feature_list.json). Tags present, v1 paths active, legacy deprecated but functional, health dual, unit tests green. 500s on some /drafts are pre-existing intel shape issues in drafter (not router). |
| **Commits** | (pending) |
| **Known risks** | None new. The p0 /drafts call site was passing dict; now correctly adapts to CampaignRequest in the router. |
| **Next best action** | `p1-config-api` — GET/PUT /api/v1/config (encrypt on write, never return pass) |

### Session 2026-06-10 — p1-config-api (SMTP config via API)

| Field | Value |
|-------|-------|
| **Goal** | Implement GET/PUT /api/v1/config; encrypt pass server-side; mailer send path loads live DB config |
| **Completed** | Extended CampaignRepositoryPort + SQLAlchemy impl (save_user_config upsert); added ConfigUpdate + ConfigResponse + serialize in schemas; replaced stub with get_config_router (encrypt on PUT via secrets, redacted GET, handles first create + updates); wired in app.py + routers/__init__ (factory pattern); seed updated to shared encrypt helper; dummy repo updated for test compat; distinctive config PUT exercised end-to-end |
| **Verification run** | `./init.sh`; full unittest (green); `python3 scripts/dev_up.py` (rebuilds on source change); docker compose up --build api; curls for GET (404 then 200 redacted), PUT (persists, returns redacted); psql direct row inspect; inserted test campaign + forced approved state; SendUseCase path reached with loaded config; plain delivery using DB-loaded config values hit Mailpit with exact From we configured via API; openapi paths+tags+schemas checked; re-ran unittests |
| **Evidence recorded** | See feature_list.json (p1-config-api now passing). All 4 verifs + extra (DB roundtrip, decrypt in container, Mailpit receipt with configured identity, no password leakage, OpenAPI contract). Key management via .env (dev_up generated) + GTM_SMTP_ENCRYPTION_KEY in containers. |
| **Commits** | (pending) |
| **Known risks** | smtp_client always does starttls() — works for real SMTP 587 but dev mailpit 1025 needs plain (used workaround for verif delivery). Pre-existing LLM key empty causes draft 500s (bypassed with direct campaign insert for send-path test). |
| **Next best action** | p1-profile-api (or p1-policies-api). Update handoff + clean-state at session end. |

### Session 2026-06-10 — p1-profile-api (Sender profile + draft fallback)

| Field | Value |
|-------|-------|
| **Goal** | Implement GET/PUT /api/v1/profile; integrate so /drafts can omit sender_profile and use stored one |
| **Completed** | New SenderProfile model (singleton + JSON fields); extended CampaignRepositoryPort + repo impl (get returns dict for .get() compat, save upsert); ProfileUpdate/Response + serialize in schemas; new get_profile_router factory (no encryption, simple like config); mounted under /api/v1; updated get_drafts_router signature + fallback logic when sender_profile omitted/empty; wiring in app.py; test dummy updated; full rebuild + verifs |
| **Verification run** | Rebuilt via docker compose up --build api; PUT/GET /api/v1/profile; POST /drafts without sender_profile key (confirmed via logs it passed profile check and reached drafter/LLM, no SenderProfileIncompleteError); unit tests; openapi inspect |
| **Evidence recorded** | See feature_list.json (p1-profile-api now passing). All 3 verifs + integration (fallback worked). Same architecture pattern as config. |
| **Commits** | (pending) |
| **Known risks** | Drafts still surface 500 without ANTHROPIC_API_KEY (pre-existing; profile fallback verified before LLM step). |
| **Next best action** | p1-policies-api (constitution-clamped overrides). |

### Session 2026-06-10 — p1-policies-api (Clamped policy overrides + mailer integration)

| Field | Value |
|-------|-------|
| **Goal** | GET/PUT /api/v1/policies with clamping (422 for violations), return floors, make mailer use DB overrides for daily etc. |
| **Completed** | Added PolicyConfig model; extended port + repo get/save; PolicyUpdate/Response + serialize + effective merge helper; new get_policies_router with validation using floors/ceilings from domain/policies; mounted; updated CreateDraftUseCase (preflight, self-review, qa, match, followup) + Schedule to load _effective_policies from repo; test dummy; multiple rebuilds + verifs |
| **Verification run** | Rebuilds; GET policies (current+ floors); PUT 25 success + GET; PUT 100 ->422; PUT subject=40 ->422; set daily=0 then /drafts -> exact DailyLimitError 422 using the DB value (0); unit tests green; openapi |
| **Evidence recorded** | See feature_list.json (now passing). All verifs + mailer respect (limit from DB enforced in preflight). |
| **Commits** | (pending) |
| **Known risks** | validators.py still uses direct module policies (self-review in use case now uses overrides; daily limit verif covered). |
| **Next best action** | p1-features-api (feature flags like tracking_enabled). |

### Session 2026-06-10 — p1-frontend-shell (Minimal React UI shell)
| Field | Value |
|-------|-------|
| **Goal** | Thin React + Vite + TS shell: Dashboard (stats only), Campaigns list + detail/preview, Config + Profile screens — 100% data from /api/v1, no hardcodes. |
| **Completed** | Vite React TS scaffold in `frontend/`; Tailwind v3; Vite proxy for /api + /track; backend CORS middleware; full shell in App.tsx (tab nav, live fetches, forms, iframe preview, approve/send actions, loading/error states); types matching schemas; build clean. |
| **Verification run** | Backend stack already up (health 200). `npm run dev` (background) served 200 + full React HTML at :5173. `npm run build` (tsc + vite) clean twice. Dashboard exercised live GET /api/v1/stats only. Config: PUT (redacted pass handling) + GET roundtrip with distinctive values. Profile: PUT arrays + GET. Campaigns list + detail from real /campaigns endpoints (multiple rows, events, followup_schedule). Full unit tests green. Grep: no hardcoded data. Curls for PUT/GET matched UI code paths exactly. |
| **Evidence recorded** | See feature_list.json (p1-frontend-shell now passing). All 4 verifs + extra (proxy, CORS, actions, live DB data, build, unittests). Phase 1 complete. |
| **Commits** | (pending) |
| **Known risks** | None. Dev server + docker stack independent (user runs `npm run dev` in frontend/ alongside `python3 scripts/dev_up.py`). Drafts still 500 without ANTHROPIC key (pre-existing, unrelated to shell). |
| **Next best action** | Phase 2 work (p2-integration-config or p2-scraper). Update handoff + clean-state. |

### Session 2026-06-10 — p2-integration-config (Integration secrets + sources via API)

| Field | Value |
|-------|-------|
| **Goal** | Implement GET/PUT /api/v1/integrations; encrypt secrets server-side (apify_token etc); redacted GET; prerequisite for scraper. |
| **Completed** | New IntegrationConfig model (apify_token_enc + scraper_sources JSON); extended port + repo (get/save with upsert, return dict with _enc); IntegrationUpdate/Response + serialize_integrations (redacts to "***"); new get_integrations_router (encrypts on PUT via shared secret helper); mounted under /api/v1 (tag integrations); dummy + wiring + secrets.py extended with encrypt_secret; full rebuilds. |
| **Verification run** | `./init.sh`; unit tests (green); `python3 scripts/dev_up.py`; `docker compose ... up --build api`; distinctive PUT with real secret token + sources; multiple GETs; grep for secret string in responses; partial update test; OpenAPI path inspect; re-ran unittests. |
| **Evidence recorded** | See feature_list.json (p2-integration-config now passing). Both verifs + extras (redaction confirmed by absence of distinctive secret in body, persistence across partial PUTs, table auto-created, unit tests, stack rebuilt). Followed p1 config/features pattern exactly. |
| **Commits** | (pending) |
| **Known risks** | None new. Encryption key is dev bootstrap (same as SMTP); real Phase 2 scraper will decrypt when it reads the config. No decrypt helper added yet (not required for this feature's verifs). |
| **Next best action** | Mark this passing (done), update handoff. Start p2-scraper or p2-intel-report per priority in feature_list. Run clean-state-checklist. |

### Session 2026-06-10 — p2-scraper (Job scraper API)

| Field | Value |
|-------|-------|
| **Goal** | POST /api/v1/jobs/scrape triggers scrape; GET /api/v1/jobs lists normalized jobs; duplicates skipped |
| **Completed** | Extended Job model (title, company, url unique, location, description, source, scraped_at) + lightweight migration in init_db; CareersPageScraper (Greenhouse/Lever/JSON-LD/generic); ScrapeJobsUseCase + JobScraperPort; repo save_job dedup by url; jobs router mounted; schemas; unit tests |
| **Verification run** | `./init.sh` (7 tests green); docker compose rebuild api; POST scrape GitLab Greenhouse board (142 jobs); GET /jobs normalized rows; second scrape skipped=142; OpenAPI paths confirmed |
| **Evidence recorded** | See feature_list.json (p2-scraper now passing). All 3 verifs + unit tests + OpenAPI. |
| **Commits** | (pending) |
| **Known risks** | Greenhouse HTML entities in description field (cosmetic). Apify/linkedin source not wired yet. |
| **Next best action** | p2-intel-report. Update handoff + clean-state at session end. |