# GTM Engine — Agent Operating Rules

You are working on **Coldcraft**, the Mailer Agent inside a personal job-seeker GTM engine.
Read this file first. Do not guess project state from chat history alone.

## What we are building

A constitution-governed system that helps one job seeker:

1. Discover jobs (future: Scraper)
2. Decide readiness and approach (future: Intel, Network)
3. Draft, QA-gate, approve, and send cold email via the user's SMTP (Coldcraft — **in progress**)
4. Track opens/clicks/replies and learn over time (future: ML)

**North star:** Target a company → get intel → draft → approve → send → track — without manual glue.

## Architectural principles (non-negotiable)

1. **API-first** — Ship REST endpoints before UI. OpenAPI `/docs` is the contract. UI is a thin client. Workers call the same APIs/use-cases as HTTP handlers.
2. **Configurable** — SMTP, sender profile, policies, feature flags, and integrations are stored in DB and changed via `GET/PUT /api/v1/*` — not by editing code or `.env` (except bootstrap secrets).
3. **Constitution floors** — Policy overrides via API are clamped to `[HARD LIMIT]` minimums in `MAILER_CONSTITUTION.md`. Configurable ≠ weaker spam/reputation rules.

Full plan: `PLAN.md` · Feature backlog: `feature_list.json`

## Session startup (required, in order)

1. Read `claude-progress.md` — current verified state and blockers
2. Read `feature_list.json` — find the single `in_progress` feature (or the lowest-priority `not_started` if none)
3. Read `session-handoff.md` if it exists and has a recent entry
4. Run `./init.sh` — creates `.venv`, installs deps, verifies baseline. **Stop if verification fails.**
5. Confirm Docker stack if the feature needs it: `curl -s http://localhost:8000/health`
6. Read only the code/docs needed for the selected feature — do not repo-wide refactor

## Working rules

- **One feature at a time.** Only one entry in `feature_list.json` may be `in_progress`.
- **Constitution-bound.** Mailer rules live in `MAILER_CONSTITUTION.md` and `coldcraft/domain/policies.py`. `[HARD LIMIT]` rules must be enforced in code + tests, not prompts alone.
- **Evidence before passing.** A feature is `passing` only after verification steps run and evidence is recorded in `feature_list.json`.
- **API before UI.** Do not build React screens until the backing `/api/v1` endpoints exist and are verified.
- **Config before hardcoding.** New behavior knobs go in DB + config API, not new env vars (except secrets).
- **Scope discipline.** Do not build Scraper, Intel, Network, RabbitMQ, or ML unless that feature is explicitly selected.
- **Match existing architecture.** Use `domain` → `application` → `infrastructure` layers. Extend ports, don't bypass them.
- **No false progress.** Do not mark UI, tracking, or integration features as done without running the verification steps.

## Key paths

| What | Where |
|------|-------|
| Mailer agent | `coldcraft/agent.py`, `coldcraft/application/use_cases.py` |
| Constitution | `MAILER_CONSTITUTION.md` |
| Master plan | `PLAN.md` |
| API | `coldcraft/api/app.py` → migrate to `/api/v1` routers |
| DB models | `coldcraft/db/models.py` |
| Tests | `tests/unit/` |
| Dev startup | `python3 scripts/dev_up.py` |
| Docker compose | `docker-compose.yml` + `docker-compose.platform.yml` (generated) |

## Standard commands

```bash
# Install + verify (or use ./init.sh)
./init.sh
source .venv/bin/activate   # optional; init.sh uses .venv automatically
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests/unit -p 'test_*.py' -q

# Start dev stack (Postgres + Mailpit + API)
python3 scripts/dev_up.py

# Health check
curl -s http://localhost:8000/health

# Mailpit UI (sent emails)
open http://localhost:8025
```

## Definition of done (feature-level)

A feature is **done** only when ALL of these are true:

1. Implementation matches `user_visible_behavior` in `feature_list.json`
2. Verification steps in `feature_list.json` were executed (not just read)
3. Evidence recorded in `feature_list.json` `evidence` field
4. Unit tests added or updated for constitution/policy changes
5. `PYTHONPATH=. python3 -m unittest discover -s tests/unit -p 'test_*.py' -q` passes
6. `claude-progress.md` session record updated
7. `session-handoff.md` updated
8. Feature status set to `passing`; no other feature left in `in_progress`

## Definition of done (session-level)

Before ending a session, run `clean-state-checklist.md`.

## Phase map (do not skip ahead without passing prior phase gates)

| Phase | Goal | Gate |
|-------|------|------|
| **0** | Runnable mailer backend | draft → approve → send → Mailpit |
| **1** | Operable loop | UI + tracking API + campaign list |
| **2** | Intelligence upstream | Scraper + Intel + PM workflow |
| **3** | Async + replies | Worker + reply ingestion + CI |
| **4** | Network + ML | Warm paths + learning loop |

Current phase: **0 → 1 transition**. See `feature_list.json` for ordered work.

## What not to do

- Do not add RabbitMQ/Neo4j/React scaffolding unless the active feature requires it
- Do not weaken `[HARD LIMIT]` rules to make tests pass
- Do not mark features `passing` without evidence
- Do not edit `.env` secrets into committed files
- Do not create markdown docs the user did not ask for (except harness files)

## Deeper context (read when needed)

- `README.md` — product overview and mailer pipeline
- `MAILER_CONSTITUTION.md` — full mailer rules
- `.env.example` — required environment variables