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

- Implemented Network Manager CRUD and Search endpoints (`POST/GET/PUT/DELETE /api/v1/network/contacts`, `GET /api/v1/network/search?company=X`).
- Implemented Memory Bank CRUD and GitHub repositories summarization (`GET/PUT /api/v1/memory`, `POST /api/v1/memory/github-summary` which uses GITHUB_TOKEN and summarizes via Gemini with robust fallback stubs).
- Implemented Learning Roadmaps Generation and Node toggle status (`POST /api/v1/roadmaps` which generates a roadmap via Gemini with a structured node-graph fallback, `GET /api/v1/roadmaps/{id}`, and `PUT /api/v1/roadmaps/{id}/nodes/{node_id}`).
- Implemented job status updates and column stats (`PUT /api/v1/jobs/{id}/status`, `GET /api/v1/jobs/stats`).
- Extended the database repository layer (`SQLAlchemyCampaignRepository` and `CampaignRepositoryPort`) to fully support these models, serialization helpers, and encryption logic.
- Created `tests/unit/test_network_memory_roadmaps.py` to completely verify all the new endpoints.
- Re-ran the full unit test suite (56 tests) and confirmed that all tests pass.

## Still broken or unverified

- None. All features are fully functional, verified by unit tests, and compile without issues.


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

**p2-intel-report is now `passing`** (2026-06-10):
- POST /api/v1/intel/reports generates 7-section readiness report (sample provider for 37signals).
- GET /api/v1/intel/reports/{company} returns cached report (14-day TTL).
- Verified live + 18 unit tests green.

**Gmail OAuth & Inbox Hub is now `passing`** (2026-06-21):
- Implemented `GmailClient` in `coldcraft/infrastructure/gmail_client.py` for OAuth token exchange/refresh and Composition/Compose API RFC 2822 formatting.
- Implemented `/api/v1/inbox` endpoints in `coldcraft/api/routers/inbox.py` for OAuth connection callback, thread listing with fallback mocks, smart thread classification, and reply draft generation.
- Added SQLite/Postgres credential repository save/load/decrypt functions (encrypted with GTM_SMTP_ENCRYPTION_KEY).
- Comprehensive unit tests created in `tests/unit/test_inbox.py` covering all edge cases.
**Network Manager is now `passing`** (2026-06-21):
- CRUD operations for contacts (`/api/v1/network/contacts`) using repository pattern.
- Fuzzy/ILike search for contacts by company (`/api/v1/network/search?company=X`).

**Memory Bank is now `passing`** (2026-06-21):
- CRUD operations for memory entries (`/api/v1/memory`).
- Git summary integration (`/api/v1/memory/github-summary`) that fetches from GitHub and LLM-summarizes repositories via Gemini.

**Learning Roadmaps is now `passing`** (2026-06-21):
- Learning roadmap graph generation via Gemini with optional syllabus context.
- Single node status update and completion toggle (`/api/v1/roadmaps/{id}/nodes/{node_id}`).
- Full unit and integration tests written in `tests/unit/test_network_memory_roadmaps.py` cover all endpoints.

**Wired Inline Send Reply & Multi-Gmail** (2026-06-21):
- Added `email` column to `GmailCredential` model and schema migration to support multiple Gmail connections.
- Implemented `get_user_profile` in `GmailClient` and wired connection callback to store connecting user's email address.
- Aggregated inbox thread listing across all connected Gmail accounts, tagging threads with `connected_email`.
- Implemented `POST /api/v1/inbox/threads/{id}/send` backend endpoint with automatic credentials lookup matching the thread's email.
- Wired the "Send Inline Reply" button in `Inbox.jsx` with full async api call and error/success state banners.
- Unit and integration tests cover sending, callback email storage, and multi-gmail thread listing.

**Gmail Layout Redesign & Unsubscriber** (2026-06-21):
- Implemented List-Unsubscribe parsing, Scan Candidates (`is:unread older_than:30d -is:starred` filtered by system labels), individual unsubscription, and bulk unsubscription logic in `GmailClient`.
- Implemented routes `POST /unsubscribe/scan`, `POST /unsubscribe/bulk`, and `POST /threads/{id}/unsubscribe` in `inbox.py`.
- Registered `scanUnsubscribeTargets`, `bulkUnsubscribe`, and `unsubscribeThread` in frontend `api.js`.
- Redesigned `Inbox.jsx` UI layout:
  - Navigation sidebar: Inbox, Starred, Sent, Drafts, and Clean Up.
  - Full-width Gmail-style thread list with checkboxes, star quick toggle, tags, and quick hover "Unsubscribe" actions.
  - Full-width details view with a "Back to Inbox" toolbar, sandboxed HTML frame, and reply hub.
  - "Clean Up" panel view for scanning candidates and triggering bulk unsubscriptions.
- Created 4 unit tests covering parsing, scanning, individual/bulk endpoints in `test_inbox.py` (64/64 tests pass).

**Next (Phase 2):** p2-pm-workflow per priority in feature_list.json. Only set one feature to `in_progress` at a time.

All Phase 1, Phase 2 (config, scraper, intel, inbox send, unsubscriber), and Phase 4 CRUD work is API-driven and verified.

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