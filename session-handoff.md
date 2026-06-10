# Session Handoff

> Update this file at the end of every session.

## Architectural direction

- **API-first:** Every feature ships as `/api/v1` endpoint before UI
- **Configurable:** SMTP, profile, policies, flags via `GET/PUT` — not `.env` or code edits
- **Plan:** See `PLAN.md` for full API map and phase gates

## Currently verified

- Dev stack: `python3 scripts/dev_up.py`
- `./init.sh` → PASS (always)
- Full Phase 1: all p1-* APIs + p1-frontend-shell `passing`
- 12+ features passing (Phase 0 + router + config/profile/policies/features + list/detail/tracking/stats/followup + shell)
- UI is thin client: Dashboard (/stats only), Campaigns list+detail+preview+actions, Config+Profile forms — all live /api/v1 fetches, Vite proxy + backend CORS
- `npm run dev` serves at :5173; full `npm run build` clean; backend unittests green
- Unit tests green; all verifs executed with evidence in feature_list.json

## Changes this session

- Completed `p1-frontend-shell` (final Phase 1 deliverable):
  - Scaffolding: Vite + React 19 + TS in `frontend/`, Tailwind v3 via PostCSS, clean package
  - Proxy: Vite dev server proxies `/api`, `/track`, `/health` → localhost:8000 (clean dev experience)
  - Backend: Added CORSMiddleware (localhost:5173 etc.) in coldcraft/api/app.py:create_app
  - Shell implementation (single App.tsx for minimal surface):
    - Tab nav: Dashboard / Campaigns / Config
    - Dashboard: exclusively fetches + renders GET /api/v1/stats (cards for sent_today, open_rate, pending_approvals)
    - Campaigns: live list (with ?status filter), selectable detail with body preview (iframe srcDoc for HTML + text fallback), followup_schedule badges, events timeline (lazy load), Approve/Send actions wired to real POSTs + auto refresh
    - Config: full GET/PUT forms for /api/v1/config (password field special: optional on update, never echoed) + /api/v1/profile (skills/proof_points as comma-editable arrays)
    - All state from fetch; loading, error, success banners; no mock data
  - Verification: `npm run dev` (serves 200 + HMR), clean `npm run build`, live PUT/GET curls matching form payloads, real campaign data rendered, unit tests still green, grep clean
- Updated feature_list (status=passing + detailed evidence), claude-progress (new session record + top summary), this handoff
- Rebuilds + dev server launch + multiple curl verifs against running stack

Phase 1 (API platform + operable loop via thin UI) is now complete. All data/config flows through /api/v1 only.

## Still broken or unverified

- Phase 1 complete (all listed p1-* features passing including frontend shell)
- smtp_client always forces starttls() (fine for prod 587; dev mailpit 1025 used plain workaround in prior verifs)
- Drafts still surface 500 without ANTHROPIC_API_KEY (pre-existing LLM step; unrelated to config/profile/UI)
- No React in docker-compose (UI is separate `cd frontend && npm run dev`; intentional for Phase 1 shell)
- p2+ (scraper, intel, workers, network) remain not_started per plan gates

## Next best action

**Phase 1 complete.** p1-frontend-shell is now `passing`.

**p2-integration-config is now `passing`** (2026-06-10):
- GET/PUT /api/v1/integrations implemented.
- Secrets (apify_token) encrypted on write using the bootstrap GTM_SMTP_ENCRYPTION_KEY, **never** returned on GET (redacted to "***").
- scraper_sources list roundtrips correctly.
- Partial updates preserve existing secrets.
- New IntegrationConfig table + full wiring followed the established config/profile/features pattern.
- Verified live on rebuilt stack + unit tests green.

**p2-scraper is now `passing`** (2026-06-10):
- POST /api/v1/jobs/scrape with career page URL (Greenhouse/Lever/JSON-LD supported).
- GET /api/v1/jobs returns normalized jobs (title, company, url, location, description, source, scraped_at).
- Duplicate URLs skipped on re-scrape (unique url constraint + save_job dedup).
- Verified live: GitLab Greenhouse board → 142 jobs first pass, 0 scraped / 142 skipped on second pass.
- Unit tests: 7/7 green including test_scraper.py.

**Next (Phase 2):** p2-intel-report per priority in feature_list.json. Only set one feature to `in_progress` at a time.

All Phase 1 work (API surface + thin UI shell) is API-driven and verified. UI is deliberately separate process for now.

**Do not** start p2 items without updating feature_list (set one to in_progress) and following the one-feature rule.

Before ending any session: run through clean-state-checklist.md .

## Commands

```bash
./init.sh
python3 scripts/dev_up.py          # starts db + mailpit + api + frontend (Vite) together
# All published on localhost:
#   UI:       http://localhost:5173
#   API docs: http://localhost:8000/docs
#   Mailpit:  http://localhost:8025

curl -s http://localhost:8000/api/v1/health
curl -s http://localhost:8000/api/v1/stats

# You can still run the UI standalone (outside Docker):
cd frontend && npm run dev
```