"""
Mailer Agent — GTM Engine
Orchestrates the full draft → QA → preview → send → track pipeline.
Every method maps directly to a step in MAILER_CONSTITUTION.md.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field

from .drafter import Drafter
from .smtp_client import SMTPClient
from .tracker import Tracker
from .validators import MailerValidator
from ..qa.agent import QAAgent
from ...db.models import Campaign, EmailEvent, UserConfig, Job
from ...db.session import get_session

logger = logging.getLogger(__name__)


@dataclass
class CampaignRequest:
    job_id: str
    recipient_email: str
    recipient_name: str
    company_intel: dict           # payload from Intel Agent
    sender_profile: dict          # from USER_CONFIG + resume
    triggered_by: str = "user"   # user | schedule


@dataclass
class DraftResult:
    campaign_id: str
    subject: str
    body_html: str
    body_text: str
    word_count: int
    personalization_signals: list[str]
    hook_candidates: list[dict]
    selected_hook: dict
    qa_result: Optional[dict] = None
    status: str = "draft"         # draft | qa_passed | qa_failed | user_approved | sent | failed


class MailerAgent:
    """
    Constitution-compliant mailer agent.
    Enforces every HARD LIMIT from MAILER_CONSTITUTION.md at the code level.
    """

    DAILY_SEND_LIMIT = 20
    HOURLY_SEND_LIMIT = 5
    MAX_FOLLOWUPS = 2             # initial + 2 = 3 total touches
    MAX_COMPANY_EMAILS_30D = 3
    FOLLOWUP_DAYS = [5, 12]
    MIN_WORD_COUNT = 100
    MAX_WORD_COUNT = 180
    MAX_SUBJECT_CHARS = 50
    MIN_PERSONALIZATION_SIGNALS = 2
    MIN_MATCH_SCORE = 40          # below this, warn before drafting
    QA_MAX_RETRIES = 2

    def __init__(self, config: UserConfig):
        self.config = config
        self.drafter = Drafter()
        self.smtp = SMTPClient(config)
        self.tracker = Tracker(config)
        self.validator = MailerValidator()
        self.qa = QAAgent()

    # ─────────────────────────────────────────────────────────────
    # ENTRY POINT — called by PM Agent
    # ─────────────────────────────────────────────────────────────

    def run(self, request: CampaignRequest) -> DraftResult:
        """
        Full pipeline: research_check → hook_gen → draft →
        self_review → qa_gate → user_preview → (send on approval).
        Returns DraftResult at user_preview stage.
        Actual send is triggered separately via send(campaign_id).
        """
        logger.info(f"Mailer Agent starting for job_id={request.job_id}")

        # Step 1: Research check
        self._research_check(request)

        # Step 2: Pre-flight hard limits
        self._preflight_checks(request)

        # Step 3: Hook generation (×3, best selected)
        hooks = self.drafter.generate_hooks(
            company_intel=request.company_intel,
            sender_profile=request.sender_profile,
            count=3
        )
        selected_hook = self._score_and_select_hook(hooks)

        # Step 4: Draft
        draft = self.drafter.draft(
            hook=selected_hook,
            company_intel=request.company_intel,
            sender_profile=request.sender_profile,
            recipient_name=request.recipient_name,
        )

        # Step 5: Self-review
        self._self_review(draft)

        # Step 6: QA gate (max 2 retries)
        qa_result = self._qa_gate(draft, request)
        draft.qa_result = qa_result

        # Step 7: Persist draft campaign (status = qa_passed)
        campaign_id = self._persist_draft(draft, request)
        draft.campaign_id = campaign_id

        return draft

    # ─────────────────────────────────────────────────────────────
    # STEP 1 — Research check
    # ─────────────────────────────────────────────────────────────

    def _research_check(self, request: CampaignRequest) -> None:
        """
        Constitution §2.2: halt if minimum research threshold not met.
        """
        required_intel_fields = [
            "product_description",
            "recent_signal",          # { type, description, date }
            "recipient_role",
            "recipient_public_work",  # at least one URL or text
        ]
        missing = [f for f in required_intel_fields if not request.company_intel.get(f)]
        if missing:
            raise ResearchInsufficientError(
                f"RESEARCH_INSUFFICIENT: missing fields: {missing}. "
                "Intel Agent must populate these before Mailer Agent can proceed."
            )

        required_sender_fields = ["name", "email", "skills", "proof_points"]
        missing_sender = [f for f in required_sender_fields if not request.sender_profile.get(f)]
        if missing_sender:
            raise SenderProfileIncompleteError(
                f"Sender profile missing: {missing_sender}"
            )

    # ─────────────────────────────────────────────────────────────
    # STEP 2 — Pre-flight hard limits
    # ─────────────────────────────────────────────────────────────

    def _preflight_checks(self, request: CampaignRequest) -> None:
        """
        Enforces all HARD LIMITs that prevent sending before drafting begins.
        Fail fast — don't spend tokens drafting if send is blocked anyway.
        """
        with get_session() as db:
            # Do-not-contact check
            if self._is_do_not_contact(request.recipient_email, db):
                raise DoNotContactError(
                    f"{request.recipient_email} is on the do-not-contact list. "
                    "This cannot be overridden."
                )

            # Same person in ATS pipeline check
            if self._in_ats_pipeline(request.recipient_email, request.job_id, db):
                raise ATSConflictError(
                    "This recipient is already in the ATS pipeline for this job. "
                    "Constitution §7.3: cannot cold email someone in an active formal application."
                )

            # Daily limit check
            today_count = self._sent_today_count(db)
            if today_count >= self.DAILY_SEND_LIMIT:
                raise DailyLimitError(
                    f"Daily send limit ({self.DAILY_SEND_LIMIT}) reached. "
                    f"Emails will be deferred to next available slot."
                )

            # Per-company 30-day limit
            company = request.company_intel.get("company_name", "")
            company_count = self._sent_to_company_30d(company, db)
            if company_count >= self.MAX_COMPANY_EMAILS_30D:
                raise CompanyLimitError(
                    f"Already sent {company_count} emails to {company} in the last 30 days. "
                    f"Max is {self.MAX_COMPANY_EMAILS_30D}."
                )

            # No-cold-outreach policy check
            if request.company_intel.get("no_cold_outreach_policy"):
                policy_text = request.company_intel.get("no_cold_outreach_policy_text", "")
                raise NoOutreachPolicyError(
                    f"{company} has a documented no-cold-outreach policy: '{policy_text}'. "
                    "User must provide explicit logged confirmation to proceed."
                )

            # Match score warning (not a hard block, but must surface)
            match_score = self._get_match_score(request.job_id, db)
            if match_score is not None and match_score < self.MIN_MATCH_SCORE:
                logger.warning(
                    f"LOW_MATCH_SCORE: {match_score}/100 for job {request.job_id}. "
                    "Draft will use growth-trajectory framing, not fit-claiming framing."
                )
                request.company_intel["low_match_mode"] = True
                request.company_intel["match_score"] = match_score

            # Idempotency: already sent to this recipient for this campaign?
            if self._already_sent(request.recipient_email, request.job_id, db):
                raise DuplicateSendError(
                    f"Email already sent to {request.recipient_email} for job {request.job_id}. "
                    "Constitution §7.9: idempotent sends only."
                )

    # ─────────────────────────────────────────────────────────────
    # STEP 3 — Hook scoring
    # ─────────────────────────────────────────────────────────────

    def _score_and_select_hook(self, hooks: list[dict]) -> dict:
        """
        Score each hook on 3 dimensions (1-5 each): specificity,
        surprise factor, relevance. Return highest-scoring hook.
        """
        def score(hook: dict) -> int:
            return (
                hook.get("specificity", 0) +
                hook.get("surprise_factor", 0) +
                hook.get("relevance", 0)
            )

        scored = sorted(hooks, key=score, reverse=True)
        best = scored[0]
        logger.info(
            f"Hook selected (score {score(best)}/15): {best.get('text', '')[:80]}..."
        )
        return best

    # ─────────────────────────────────────────────────────────────
    # STEP 5 — Self-review
    # ─────────────────────────────────────────────────────────────

    def _self_review(self, draft: DraftResult) -> None:
        """
        Constitution §4.1 Step 4: self-review checklist.
        Raises SelfReviewError with all failing checks (not just first).
        """
        failures = []

        words = draft.body_text.split()
        if len(words) < self.MIN_WORD_COUNT:
            failures.append(f"Word count {len(words)} is below minimum {self.MIN_WORD_COUNT}")
        if len(words) > self.MAX_WORD_COUNT:
            failures.append(f"Word count {len(words)} exceeds maximum {self.MAX_WORD_COUNT}")

        if len(draft.subject) > self.MAX_SUBJECT_CHARS:
            failures.append(f"Subject '{draft.subject}' is {len(draft.subject)} chars (max {self.MAX_SUBJECT_CHARS})")

        first_sentence = draft.body_text.strip().split(".")[0].strip()
        if first_sentence.startswith("I ") or first_sentence.startswith("I'"):
            failures.append("First sentence starts with 'I' — constitution §3.1 prohibits this")

        if len(draft.personalization_signals) < self.MIN_PERSONALIZATION_SIGNALS:
            failures.append(
                f"Only {len(draft.personalization_signals)} personalization signals "
                f"(minimum {self.MIN_PERSONALIZATION_SIGNALS})"
            )

        ask_count = draft.body_text.count("?")
        if ask_count > 3:
            failures.append(f"Too many question marks ({ask_count}) — suggests more than one ask")

        banned_phrases = [
            "passionate about", "exciting opportunity", "I would be incredibly",
            "I've long admired", "incredible work", "I think I might",
            "I am open to any", "look forward to hearing from you"
        ]
        for phrase in banned_phrases:
            if phrase.lower() in draft.body_text.lower():
                failures.append(f"Prohibited phrase found: '{phrase}'")

        exclamation_count = draft.body_text.count("!")
        if exclamation_count > 1:
            failures.append(f"Too many exclamation marks ({exclamation_count}) — max 1")

        if failures:
            # Self-correct one pass before raising
            draft = self.drafter.revise(draft, failures)
            # Re-check after revision
            remaining = self.validator.check_self_review(draft)
            if remaining:
                raise SelfReviewError(
                    f"Self-review failed after revision attempt. Remaining issues: {remaining}"
                )

    # ─────────────────────────────────────────────────────────────
    # STEP 6 — QA gate
    # ─────────────────────────────────────────────────────────────

    def _qa_gate(self, draft: DraftResult, request: CampaignRequest) -> dict:
        """
        Constitution §4.1 Step 5: QA gate, max 2 retries.
        On 3rd failure, escalate to PM Agent — do not silently drop.
        """
        payload = {
            "job_id": request.job_id,
            "company_name": request.company_intel.get("company_name"),
            "recipient_email": request.recipient_email,
            "subject": draft.subject,
            "body_html": draft.body_html,
            "body_text": draft.body_text,
            "word_count": len(draft.body_text.split()),
            "personalization_signals": draft.personalization_signals,
        }

        for attempt in range(self.QA_MAX_RETRIES + 1):
            result = self.qa.validate_email(payload)

            if result["status"] == "PASS":
                logger.info(f"QA gate passed on attempt {attempt + 1}")
                return result

            logger.warning(f"QA gate FAIL (attempt {attempt + 1}): {result['violations']}")

            if attempt < self.QA_MAX_RETRIES:
                # Remediate and retry
                draft = self.drafter.revise(draft, result["violations"])
                payload["body_text"] = draft.body_text
                payload["body_html"] = draft.body_html
                payload["subject"] = draft.subject
                payload["word_count"] = len(draft.body_text.split())
                payload["personalization_signals"] = draft.personalization_signals
            else:
                # Escalate to PM Agent
                raise QAEscalationError(
                    f"QA gate failed {self.QA_MAX_RETRIES + 1} times. "
                    f"Final violations: {result['violations']}. "
                    "Escalating to PM Agent."
                )

    # ─────────────────────────────────────────────────────────────
    # SEND — called after user approves preview
    # ─────────────────────────────────────────────────────────────

    def send(self, campaign_id: str) -> dict:
        """
        Constitution §4.1 Step 7: send after user APPROVE.
        Loads SMTP credentials fresh from USER_CONFIG — never from cache.
        """
        with get_session() as db:
            campaign = db.query(Campaign).filter_by(id=campaign_id).first()
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")

            if campaign.status != "user_approved":
                raise SendBlockedError(
                    f"Campaign {campaign_id} status is '{campaign.status}'. "
                    "Must be 'user_approved' before sending."
                )

            # Idempotency check — final gate before wire
            if self._already_sent(campaign.recipient_email, campaign.job_id, db):
                raise DuplicateSendError(
                    f"Idempotency violation: email already sent for campaign {campaign_id}"
                )

            # Timing check
            self._check_send_timing(campaign.recipient_email, campaign)

            # Send
            config = db.query(UserConfig).first()
            smtp = SMTPClient(config)  # fresh credentials load
            message_id = smtp.send(
                to_email=campaign.recipient_email,
                to_name=campaign.recipient_name,
                subject=campaign.subject,
                body_html=self.tracker.inject_pixel(campaign.body_html, campaign_id),
                body_text=campaign.body_text,
            )

            # Log send event
            event = EmailEvent(
                id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="sent",
                occurred_at=datetime.now(timezone.utc),
                metadata={"message_id": message_id},
            )
            db.add(event)
            campaign.status = "sent"
            campaign.sent_at = datetime.now(timezone.utc)
            campaign.message_id = message_id
            db.commit()

            logger.info(f"Email sent: campaign={campaign_id} message_id={message_id}")
            return {"status": "sent", "campaign_id": campaign_id, "message_id": message_id}

    # ─────────────────────────────────────────────────────────────
    # FOLLOW-UP SCHEDULER
    # ─────────────────────────────────────────────────────────────

    def schedule_followups(self, campaign_id: str) -> list[dict]:
        """
        Constitution §5.1: schedule Day 5 and Day 12 follow-ups.
        Returns scheduled task list for the worker queue.
        """
        with get_session() as db:
            campaign = db.query(Campaign).filter_by(id=campaign_id).first()
            if not campaign or campaign.status != "sent":
                return []

            tasks = []
            for day_offset in self.FOLLOWUP_DAYS:
                tasks.append({
                    "type": "followup",
                    "campaign_id": campaign_id,
                    "day_offset": day_offset,
                    "scheduled_for": self._compute_send_time(
                        campaign.recipient_email, day_offset
                    ),
                })

            logger.info(
                f"Scheduled {len(tasks)} follow-ups for campaign {campaign_id}"
            )
            return tasks

    def handle_reply(self, campaign_id: str, reply_type: str, reply_text: str) -> dict:
        """
        Constitution §5.3: on any reply, halt follow-ups immediately.
        Never auto-respond. Surface to user.
        """
        with get_session() as db:
            campaign = db.query(Campaign).filter_by(id=campaign_id).first()
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")

            # Cancel all pending follow-ups
            self._cancel_pending_followups(campaign_id, db)

            # Handle removal requests — HARD LIMIT
            if reply_type == "removal_request":
                self._add_to_do_not_contact(campaign.recipient_email, db)
                logger.warning(
                    f"DO_NOT_CONTACT: {campaign.recipient_email} added to blocklist "
                    f"after removal request on campaign {campaign_id}"
                )

            campaign.status = "replied"
            event = EmailEvent(
                id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type=f"reply_{reply_type}",
                occurred_at=datetime.now(timezone.utc),
                metadata={"reply_text": reply_text[:500]},
            )
            db.add(event)
            db.commit()

            return {
                "campaign_id": campaign_id,
                "reply_type": reply_type,
                "followups_cancelled": True,
                "action_required": self._reply_action(reply_type),
            }

    # ─────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────

    def _is_do_not_contact(self, email: str, db) -> bool:
        from ...db.models import DoNotContact
        return db.query(DoNotContact).filter_by(email=email).first() is not None

    def _in_ats_pipeline(self, email: str, job_id: str, db) -> bool:
        from ...db.models import ATSApplication
        return db.query(ATSApplication).filter_by(
            recipient_email=email, job_id=job_id
        ).first() is not None

    def _already_sent(self, email: str, job_id: str, db) -> bool:
        return db.query(Campaign).filter_by(
            recipient_email=email,
            job_id=job_id,
            status="sent"
        ).first() is not None

    def _sent_today_count(self, db) -> int:
        today = datetime.now(timezone.utc).date()
        return db.query(Campaign).filter(
            Campaign.status == "sent",
            Campaign.sent_at >= datetime.combine(today, datetime.min.time())
        ).count()

    def _sent_to_company_30d(self, company: str, db) -> int:
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        return db.query(Campaign).filter(
            Campaign.company_name == company,
            Campaign.status == "sent",
            Campaign.sent_at >= cutoff
        ).count()

    def _get_match_score(self, job_id: str, db) -> Optional[int]:
        job = db.query(Job).filter_by(id=job_id).first()
        return job.match_score if job else None

    def _check_send_timing(self, recipient_email: str, campaign) -> None:
        """Constitution §6.4: never send 10pm–6am recipient local time."""
        from ...utils.timezone import infer_recipient_timezone
        tz = infer_recipient_timezone(recipient_email, campaign.company_intel or {})
        hour = datetime.now(tz).hour
        if hour >= 22 or hour < 6:
            raise SendTimingError(
                f"Send blocked: recipient local time is {hour}:00. "
                "Constitution §6.4: do not send between 10pm and 6am."
            )

    def _compute_send_time(self, recipient_email: str, day_offset: int):
        from datetime import timedelta
        from ...utils.timezone import infer_recipient_timezone
        send_date = datetime.now(timezone.utc).date() + timedelta(days=day_offset)
        # Target 9am recipient local time
        tz = infer_recipient_timezone(recipient_email, {})
        return datetime.combine(send_date, datetime.min.time().replace(hour=9), tzinfo=tz)

    def _cancel_pending_followups(self, campaign_id: str, db) -> None:
        from ...db.models import ScheduledTask
        db.query(ScheduledTask).filter_by(
            campaign_id=campaign_id,
            status="pending"
        ).update({"status": "cancelled"})

    def _add_to_do_not_contact(self, email: str, db) -> None:
        from ...db.models import DoNotContact
        if not self._is_do_not_contact(email, db):
            db.add(DoNotContact(
                email=email,
                added_at=datetime.now(timezone.utc),
                reason="replied_removal_request"
            ))

    def _persist_draft(self, draft: DraftResult, request: CampaignRequest) -> str:
        campaign_id = str(uuid.uuid4())
        with get_session() as db:
            campaign = Campaign(
                id=campaign_id,
                job_id=request.job_id,
                company_name=request.company_intel.get("company_name"),
                recipient_email=request.recipient_email,
                recipient_name=request.recipient_name,
                subject=draft.subject,
                body_html=draft.body_html,
                body_text=draft.body_text,
                status="qa_passed",
                created_at=datetime.now(timezone.utc),
            )
            db.add(campaign)
            db.commit()
        return campaign_id

    def _reply_action(self, reply_type: str) -> str:
        return {
            "positive": "Recipient wants to talk. Draft a reply or send calendar link.",
            "rejection": "Marked rejected. No further action needed.",
            "ooo": "OOO detected. Follow-ups paused until OOO period ends.",
            "referral": "Referred to another contact. New campaign draft prepared — review before sending.",
            "removal_request": "Added to do-not-contact list. No further outreach permitted.",
        }.get(reply_type, "Review reply and decide next step.")


# ─────────────────────────────────────────────────────────────────
# Exception hierarchy — one exception per failure mode
# ─────────────────────────────────────────────────────────────────

class MailerAgentError(Exception): pass
class ResearchInsufficientError(MailerAgentError): pass
class SenderProfileIncompleteError(MailerAgentError): pass
class DoNotContactError(MailerAgentError): pass
class ATSConflictError(MailerAgentError): pass
class DailyLimitError(MailerAgentError): pass
class CompanyLimitError(MailerAgentError): pass
class NoOutreachPolicyError(MailerAgentError): pass
class DuplicateSendError(MailerAgentError): pass
class SelfReviewError(MailerAgentError): pass
class QAEscalationError(MailerAgentError): pass
class SendBlockedError(MailerAgentError): pass
class SendTimingError(MailerAgentError): pass
