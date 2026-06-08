# Coldcraft

Constitution-governed AI cold outreach engine for job seekers. Coldcraft drafts, validates, and sends hyper-personalized emails designed to earn replies — not get ignored.

Most cold email tools optimize for volume. Coldcraft optimizes for precision: every message is researched, scored, self-reviewed, QA-gated, and rate-limited before it ever leaves your outbox.

## Why Coldcraft

- **Research-first** — refuses to draft when company intel is incomplete
- **Constitution-bound** — hard limits on tone, structure, send timing, and claims
- **Multi-stage validation** — self-review, rule checks, and an independent QA gate with auto-revision
- **Reputation-safe** — daily caps, per-company limits, do-not-contact enforcement, and ATS conflict detection
- **Human in the loop** — nothing sends without explicit user approval

## How it works

```
Company intel + sender profile
        │
        ▼
  Preflight checks ──► research threshold, DNC list, ATS conflicts, rate limits
        │
        ▼
  Hook generation ──► 3 candidates scored on specificity, surprise, relevance
        │
        ▼
  Draft + self-review ──► word count, banned phrases, personalization signals
        │
        ▼
  QA gate ──► independent validation with up to 2 revision retries
        │
        ▼
  User approval ──► draft stored, awaiting explicit send confirmation
        │
        ▼
  Send ──► timezone-aware delivery via SMTP, open/click tracking, follow-up scheduling
```

## Architecture

Coldcraft uses a layered design with clear boundaries:

| Layer | Responsibility |
|-------|----------------|
| **Domain** | Models, policies, and typed errors (`ResearchInsufficientError`, `DoNotContactError`, etc.) |
| **Application** | Use cases: `CreateDraft`, `SendCampaign`, `ScheduleFollowups`, `HandleReply` |
| **Infrastructure** | Claude API drafting, SQLAlchemy persistence, SMTP transport, timezone inference |
| **Interfaces** | `MailerAPI` — thin adapter over the `MailerAgent` facade |

The `MailerAgent` facade wires everything together and exposes a backward-compatible API for the broader GTM engine.

## The Constitution

All agent behavior is governed by [`MAILER_CONSTITUTION.md`](MAILER_CONSTITUTION.md) — a 470-line rulebook injected into every drafting invocation. Rules marked **[HARD LIMIT]** cannot be overridden at runtime.

Key constraints enforced in code:

| Rule | Limit |
|------|-------|
| Subject line | ≤ 50 characters |
| Body length | 100–180 words |
| Personalization signals | ≥ 2 company-specific references |
| First sentence | Must not start with "I" |
| Daily send cap | 20 emails |
| Per-company cap (30 days) | 3 emails |
| Send window | 6:00 AM – 10:00 PM recipient local time |
| Follow-ups | Up to 2, scheduled at days 5 and 12 |
| QA retries | 2 revision attempts before escalation |

Banned phrases like *"passionate about"*, *"exciting opportunity"*, and *"look forward to hearing from you"* are rejected automatically.

## Quick start

### Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/) (`ANTHROPIC_API_KEY`)
- SMTP credentials for your sending domain
- A running GTM database (SQLAlchemy-backed — see `infrastructure/persistence/`)

### Install

```bash
git clone https://github.com/birajdarushi/coldcraft.git
cd coldcraft
pip install anthropic cryptography sqlalchemy
```

### Environment variables

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export GTM_SMTP_ENCRYPTION_KEY="your-fernet-key"  # for encrypted SMTP passwords at rest
```

### Usage

```python
from coldcraft import MailerAgent, CampaignRequest

agent = MailerAgent(config)

request = CampaignRequest(
    job_id="job-abc123",
    recipient_email="jane@acme.com",
    recipient_name="Jane Chen",
    company_intel={
        "company_name": "Acme Corp",
        "product_description": "Event-sourced billing platform for B2B SaaS",
        "recent_signal": {
            "type": "blog_post",
            "description": "Engineering post on migrating to event-sourced reads",
            "date": "2026-03-15",
        },
        "recipient_role": "Engineering Manager",
        "recipient_public_work": "Authored the SMART360 billing migration post",
        "tech_stack": ["Python", "Kafka", "PostgreSQL"],
    },
    sender_profile={
        "name": "Alex Rivera",
        "email": "alex@example.com",
        "skills": ["Python", "Playwright", "QA Automation"],
        "proof_points": [
            {
                "name": "Forseti framework",
                "outcome": "83+ page objects, 60+ test modules",
                "tech": "Playwright + Python POM",
            }
        ],
    },
)

# Draft → validate → QA gate → persist
draft = agent.run(request)
print(draft.subject)
print(draft.body_text)

# Send after user approval (campaign status must be 'user_approved')
result = agent.send(draft.campaign_id)

# Schedule follow-ups and handle replies
followups = agent.schedule_followups(draft.campaign_id)
agent.handle_reply(draft.campaign_id, reply_type="positive", reply_text="Let's chat Thursday.")
```

## API surface

| Method | Description |
|--------|-------------|
| `agent.run(request)` | Create a draft: hooks → draft → self-review → QA gate |
| `agent.send(campaign_id)` | Send an approved campaign via SMTP |
| `agent.schedule_followups(campaign_id)` | Queue day-5 and day-12 follow-ups |
| `agent.handle_reply(campaign_id, type, text)` | Process replies, cancel follow-ups, update DNC list |

For HTTP-style integration, use `MailerAPI` from `coldcraft.interfaces`.

## Safety and compliance

Coldcraft treats a bad cold email as worse than no email at all:

- **Do-not-contact list** — permanent block; removal requests are a hard stop
- **ATS conflict detection** — won't cold-email someone you're already applying to formally
- **Duplicate send prevention** — idempotent sends enforced at the database level
- **Credential hygiene** — SMTP passwords encrypted at rest (Fernet), decrypted only at send time, never logged
- **No-cold-outreach policies** — surfaces company policies and requires explicit logged override

## Testing

```bash
python -m unittest discover -s tests/unit -v
```

Unit tests cover validator rules and use-case preflight logic (DNC blocking, research thresholds, etc.).

## Project structure

```
coldcraft/
├── agent.py                  # MailerAgent facade
├── drafter.py                # Claude-powered hook + draft generation
├── validators.py             # Format, content, and deliverability checks
├── smtp_client.py            # TLS SMTP transport with header hygiene
├── tracker.py                # Open/click tracking via pixel + link rewriting
├── MAILER_CONSTITUTION.md    # Authoritative behavior rulebook
├── application/
│   ├── use_cases.py          # CreateDraft, Send, Followups, HandleReply
│   └── ports.py              # Protocol interfaces for adapters
├── domain/
│   ├── models.py             # CampaignRequest, DraftResult
│   ├── policies.py           # Numeric limits and banned phrases
│   └── errors.py             # Typed domain exceptions
├── infrastructure/
│   ├── llm/                  # QA gateway adapter
│   ├── persistence/          # SQLAlchemy repositories
│   └── time/                 # Recipient timezone inference
├── interfaces/
│   └── mailer_api.py         # API-style entrypoint
├── prompts/
│   └── registry.py           # System prompts for drafter, hooks, revisions
└── tests/unit/
```

## Part of a larger GTM engine

Coldcraft is the **Mailer Agent** module in a personal job-seeker GTM stack. It expects upstream agents to supply company intelligence and a complete sender profile, and integrates with a shared database and QA agent for end-to-end campaign orchestration.

## License

See repository for license details.