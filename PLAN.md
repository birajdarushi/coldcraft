# GTM Engine — Master Plan

**Principles:** API-first · Configurable · Constitution-bound · Evidence-gated delivery

Read `AGENTS.md` for session workflow. This document is the architectural north star.

---

## What we are building

A personal job-seeker GTM engine: discover jobs, decide approach (warm vs cold), draft/send/track outreach via the user's SMTP, learn over time.

**Coldcraft** (this repo) is the Mailer bounded context. The full engine adds Scraper, Intel, Network, and Orchestration — all as **API modules**, not UI-first scripts.

---

## Core principles

### 1. API-first

| Rule | Meaning |
|------|---------|
| **API before UI** | Every capability ships as a REST endpoint before any React screen |
| **OpenAPI is the contract** | `/docs` and generated schemas are the integration surface |
| **UI is a thin client** | Frontend only calls APIs; no business logic in the browser |
| **Agents are services** | Scraper, Intel, Mailer, Network are invoked via HTTP (or shared use-cases called by HTTP handlers) |
| **Workers are API consumers** | Background jobs call the same use-cases the API calls — no duplicate logic |
| **No script-only flows** | `seed_db.py` and `dev_up.py` are dev/bootstrap only; production behavior is API-driven |

### 2. Configurable

| Layer | Storage | Changed via | Examples |
|-------|---------|-------------|----------|
| **Secrets** | `.env` / env vars | Deploy-time only | `ANTHROPIC_API_KEY`, `GTM_SMTP_ENCRYPTION_KEY`, `DATABASE_URL` |
| **User config** | `user_config` table | `GET/PUT /api/v1/config` | SMTP host/port/user, from_email, from_name, tracking_domain |
| **Sender profile** | `sender_profile` table | `GET/PUT /api/v1/profile` | Name, skills, proof_points, resume JSON, tone |
| **Policy overrides** | `policy_config` table | `GET/PUT /api/v1/policies` | Daily send limit, follow-up days, min match score, send window |
| **Integration config** | `integration_config` table | `GET/PUT /api/v1/integrations` | Apify key, scraper sources, IMAP settings |
| **Feature flags** | `feature_flags` table | `GET/PUT /api/v1/features` | tracking_enabled, auto_followups, intel_cache_days |
| **Constitution floors** | Code (`policies.py`) | Never below via API | Subject ≤50 chars, word count 100–180, min personalization ≥2 |

**Configurable does not mean weaken the constitution.** API policy overrides are clamped to `[HARD LIMIT]` minimums/maximums defined in `MAILER_CONSTITUTION.md`.

### 3. Layered monolith (for now)

Single FastAPI app, versioned routes, bounded contexts as packages:

```
coldcraft/          # mailer (exists)
gtm_api/            # route modules (to extract from app.py)
  routers/
    config.py
    campaigns.py
    tracking.py
    jobs.py         # phase 2
    intel.py        # phase 2
    workflows.py    # phase 2
    network.py      # phase 4
```

Defer microservices until multi-user or scale demands it.

---

## API surface map

Base path: `/api/v1`

### Phase 0 — Done ✅

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| POST | `/drafts` | Create draft campaign |
| POST | `/campaigns/{id}/approve` | User approval |
| POST | `/campaigns/{id}/send` | Send via SMTP |
| POST | `/campaigns/{id}/followups` | Schedule follow-ups |
| POST | `/campaigns/{id}/reply` | Record reply |

### Phase 1 — API platform (current)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/config` | Read user SMTP + tracking config |
| PUT | `/api/v1/config` | Update config (password encrypted server-side) |
| GET | `/api/v1/profile` | Read sender profile |
| PUT | `/api/v1/profile` | Update sender profile / resume |
| GET | `/api/v1/policies` | Read policy overrides + constitution floors |
| PUT | `/api/v1/policies` | Update policies (clamped to hard limits) |
| GET | `/api/v1/features` | Read feature flags |
| PUT | `/api/v1/features` | Toggle tracking, auto-followups, etc. |
| GET | `/api/v1/campaigns` | List/filter/paginate campaigns |
| GET | `/api/v1/campaigns/{id}` | Campaign detail + QA + follow-up schedule |
| GET | `/api/v1/campaigns/{id}/events` | Open/click/send/reply timeline |
| GET | `/track/open/{id}` | Tracking pixel (public, no auth v1) |
| GET | `/track/click/{id}` | Click redirect (public) |
| GET | `/api/v1/stats` | Dashboard aggregates (sent today, open rate) |

### Phase 2 — Intelligence

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/jobs/scrape` | Trigger scrape job (source configurable) |
| GET | `/api/v1/jobs` | List jobs with filters |
| GET | `/api/v1/jobs/{id}` | Job detail + match_score |
| POST | `/api/v1/intel/reports` | Generate company readiness report |
| GET | `/api/v1/intel/reports/{company}` | Cached report |
| POST | `/api/v1/workflows/target-company` | intel → jobs → draft suggestion |

### Phase 3 — Async

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/workers/followups/run` | Process due follow-ups (cron/worker calls this) |
| POST | `/api/v1/webhooks/gmail` | Inbound reply webhook |
| GET | `/api/v1/tasks` | Background task status |

### Phase 4 — Network + ML

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/network/import` | Import LinkedIn CSV |
| GET | `/api/v1/network/paths` | Warm paths to target company |
| GET | `/api/v1/ml/predictions` | Reply probability for candidate |

---

## Configuration model (detail)

```json
{
  "config": {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "you@domain.com",
    "from_email": "you@domain.com",
    "from_name": "Your Name",
    "tracking_domain": "track.yourdomain.com"
  },
  "profile": {
    "name": "Rushiraj",
    "email": "you@domain.com",
    "skills": ["Python", "FastAPI"],
    "proof_points": ["UMEED", "Forseti"],
    "tone": "direct, technical, no fluff"
  },
  "policies": {
    "daily_send_limit": 20,
    "hourly_send_limit": 5,
    "max_company_emails_30d": 3,
    "followup_days": [5, 12],
    "min_match_score": 40,
    "send_window_start_hour": 6,
    "send_window_end_hour": 22
  },
  "features": {
    "tracking_enabled": true,
    "auto_followups": false,
    "intel_cache_days": 14
  },
  "integrations": {
    "apify_token": "***",
    "scraper_sources": ["linkedin", "careers_page"],
    "imap_enabled": false
  }
}
```

Policies load order: **constitution floors → `policy_config` DB → request-time validation**.

---

## Phase plan

### Phase 0 — Runnable mailer ✅

- [x] Docker dev stack (platform-aware)
- [x] Mailer draft/approve/send API
- [x] Unit test baseline
- [x] Agent harness (`AGENTS.md`, `feature_list.json`, etc.)

**Gate:** `./init.sh` passes; `curl /health` ok; draft→send visible in Mailpit.

---

### Phase 1 — API platform + operable mailer loop

**Theme:** Everything configurable and queryable via API. UI comes last.

| Order | Feature ID | Deliverable |
|-------|------------|-------------|
| 1 | `p1-api-router` | Versioned `/api/v1` router structure; migrate existing routes |
| 2 | `p1-config-api` | `GET/PUT /config` — SMTP + tracking |
| 3 | `p1-profile-api` | `GET/PUT /profile` — sender profile |
| 4 | `p1-policies-api` | `GET/PUT /policies` — clamped overrides |
| 5 | `p1-features-api` | `GET/PUT /features` — feature flags |
| 6 | `p1-campaign-list-api` | `GET /campaigns` with filters |
| 7 | `p1-campaign-detail-api` | `GET /campaigns/{id}` + events |
| 8 | `p1-tracking-api` | `/track/open`, `/track/click` |
| 9 | `p1-stats-api` | `GET /stats` dashboard aggregates |
| 10 | `p1-followup-visibility` | Follow-up schedule in campaign detail |
| 11 | `p1-frontend-shell` | React UI consuming APIs only |

**Phase 1 gate:** Complete mailer loop using **only curl/Postman** — no manual DB edits, no `.env` changes except secrets bootstrap.

---

### Phase 2 — Intelligence upstream

| Order | Feature ID | Deliverable |
|-------|------------|-------------|
| 1 | `p2-integration-config` | Scraper credentials via `/integrations` |
| 2 | `p2-scraper` | `POST /jobs/scrape` → normalized jobs in DB |
| 3 | `p2-jobs-api` | `GET /jobs` list/detail |
| 4 | `p2-intel-report` | `POST /intel/reports` — 7-section report |
| 5 | `p2-pm-workflow` | `POST /workflows/target-company` |

**Gate:** `POST /workflows/target-company` with `37signals` → intel report → job list → draft suggestion.

---

### Phase 3 — Async + reliability

- Background worker calls `POST /workers/followups/run`
- Reply ingestion via webhook or IMAP (configurable in `/integrations`)
- Integration test suite in CI
- Audit log API

**Gate:** Day 5 follow-up sends without manual intervention; reply cancels sequence.

---

### Phase 4 — Network + learning

- `POST /network/import` (LinkedIn CSV)
- `GET /network/paths?company=X`
- Feature store + XGBoost after 30+ labeled sends
- PM routes warm path before cold when score warrants

**Gate:** Target company returns ranked warm paths with advisory P(reply).

---

## Data model additions (Phase 1 config)

```sql
-- New tables for configurable layer
sender_profile     (id, jsonb profile, updated_at)
policy_config      (id, jsonb policies, updated_at)
feature_flags      (id, jsonb flags, updated_at)
integration_config (id, jsonb integrations, updated_at)  -- phase 2
```

Existing `user_config` stays for SMTP credentials.

---

## What we explicitly defer

- RabbitMQ (Celery + Redis first)
- Neo4j (NetworkX first)
- Multi-tenant auth
- UI before API for any feature
- ML before 30+ labeled outreach events

---

## Next session

**Start with:** `p1-api-router` then `p1-config-api`

See `feature_list.json` for verification steps and `session-handoff.md` for pickup state.