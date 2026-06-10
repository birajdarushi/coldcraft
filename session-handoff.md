# Session Handoff

> Update this file at the end of every session.

## Architectural direction

- **API-first:** Every feature ships as `/api/v1` endpoint before UI
- **Configurable:** SMTP, profile, policies, flags via `GET/PUT` — not `.env` or code edits
- **Plan:** See `PLAN.md` for full API map and phase gates

## Currently verified

- Dev stack: `python3 scripts/dev_up.py`
- `./init.sh` → PASS (always)
- p1-api-router + p1-config-api + p1-profile-api complete
- 6× features `passing` (Phase 0 + router + config + profile)
- Sender profile now stored via API and automatically used by /drafts when omitted
- Unit tests green; profile verifs + fallback integration executed

## Changes this session

- Implemented `p1-policies-api` (following profile/config pattern + deep mailer integration):
  - Added PolicyConfig model (singleton for overrides like daily_send_limit, subject_max_chars, followup_days)
  - Extended port + repo get_policies/save_policies (partial updates)
  - Schemas + serialize_policies (includes constitution_floors); helper _effective_policies
  - New router policies.py with clamping logic (422 for >ceiling daily, <floor subject etc) using domain/policies floors+ceilings
  - Wired in app + __init__
  - Major: refactored CreateDraftUseCase (and ScheduleFollowups) to _load_policy_overrides and use _get_policy / effective for preflight (daily, company), self-review (words, subject, etc), qa retries, match score, followups
  - Updated dummy, tests green
- Full verifs: GET (current+floors), PUT 25 success, 100/40 ->422, set daily=0 then draft -> DailyLimitError using DB value 0 (proves respect)
- Updated feature_list, claude-progress (new session record), handoff
- Rebuilds + curls + logs inspection

- Also completed prior p1-profile-api in same flow (per user request to chain)

## Still broken or unverified

- p1-campaign-detail-api, stats, tracking endpoints still not_started (list now passing)
- p1-policies-api + features + list complete (chained)
- smtp_client always forces starttls() (fine for prod, dev mailpit 1025 needs plain SMTP)
- Drafts still 500 without ANTHROPIC_API_KEY (pre-existing; profile fallback verified before the LLM step)
- No UI

## Next best action

**Work on:** `p1-frontend-shell` (last for Phase 1, per rules only after all APIs).

All prior chained: list/detail/tracking/stats/followup done. Frontend shell is the final Phase 1 (React consuming /api/v1 only). Do not start UI scaffolding yet.

**Do not touch:** frontend, scraper etc. 

Before ending, run clean-state-checklist.md .

## Commands

```bash
./init.sh
python3 scripts/dev_up.py
curl -s http://localhost:8000/api/v1/health
curl -s http://localhost:8000/api/v1/config
curl -s -X PUT http://localhost:8000/api/v1/config -H 'content-type: application/json' -d '{...}'
curl -s http://localhost:8000/docs
curl -s http://localhost:8025
```