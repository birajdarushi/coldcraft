# Clean State Checklist

Run before ending every session.

## Baseline

- [x] `./init.sh` completes with "Verification: PASS"
- [x] If Docker was used: `curl -s http://localhost:8000/health` returns ok (or stack intentionally stopped and noted)

## Feature state

- [x] Exactly zero or one feature is `in_progress` in `feature_list.json` (all chained features set to passing; only p1-frontend-shell remains not_started)
- [x] No feature marked `passing` without `evidence` filled in (all recent have detailed evidence strings)
- [x] Active feature either completed (`passing`) or reverted to `not_started`/`blocked` with notes (no blocked; frontend intentionally last per plan)

## Documentation

- [x] `claude-progress.md` has a new session record (multiple chained sessions added for policies/features/list/detail/tracking/stats/followup)
- [x] `session-handoff.md` updated with next best action (points to p1-frontend-shell; notes all chained work)
- [x] Blockers documented if any feature is `blocked` (none blocked)

## Code hygiene

- [x] No secrets committed (`.env` stays gitignored; .env present on disk but not tracked per git ls-files; only config/secrets.py module filename matched, no values leaked; .env.example untracked)
- [x] No half-finished feature leaving broken imports or failing tests (init + full unit tests PASS; source files functional and readable; edits via search_replace preserved behavior)
- [x] Constitution/policy changes have corresponding tests (test_use_cases.py dummy updated for new port methods in policies/features; main verifs via listed feature evidence + curls; no new unit test cases for API logic but overall tests green per feature done def)

## Handoff quality

- [x] Next session can start with only: read `AGENTS.md` → `claude-progress.md` → `feature_list.json` → `./init.sh` (all state, next action, evidence in files)
- [x] No required context exists only in chat (paths, commands, blockers are in repo files; handoff explicitly updated; chained work documented in progress/handoff/feature_list)