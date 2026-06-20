import logging
import uuid
from datetime import datetime, timezone, timedelta

from .ports import (
    DraftGeneratorPort,
    ValidatorPort,
    QAGatewayPort,
    CampaignRepositoryPort,
    EventRepositoryPort,
    TrackerPort,
    MailerTransportPort,
    TimezonePort,
    JobScraperPort,
    IntelResearchPort,
)
from ..domain.models import CampaignRequest, DraftResult, NormalizedJob
from ..domain.errors import (
    ResearchInsufficientError,
    SenderProfileIncompleteError,
    DoNotContactError,
    ATSConflictError,
    DailyLimitError,
    CompanyLimitError,
    NoOutreachPolicyError,
    DuplicateSendError,
    SelfReviewError,
    QAEscalationError,
    SendBlockedError,
    SendTimingError,
)
from ..domain import policies

logger = logging.getLogger(__name__)


def _effective_policies(overrides: dict | None) -> dict:
    """Merge DB overrides with constitution defaults."""
    base = {
        "daily_send_limit": policies.DAILY_SEND_LIMIT,
        "max_company_emails_30d": policies.MAX_COMPANY_EMAILS_30D,
        "subject_max_chars": policies.MAX_SUBJECT_CHARS,
        "min_words": policies.MIN_WORDS,
        "max_words": policies.MAX_WORDS,
        "min_personalization": policies.MIN_PERSONALIZATION,
        "max_exclamations": policies.MAX_EXCLAMATIONS,
        "min_match_score": policies.MIN_MATCH_SCORE,
        "qa_max_retries": policies.QA_MAX_RETRIES,
        "followup_days": policies.FOLLOWUP_DAYS,
    }
    if overrides:
        for k, v in overrides.items():
            if v is not None:
                base[k] = v
    for key in ("daily_send_limit", "max_company_emails_30d", "subject_max_chars"):
        if key in base and base[key] is not None:
            base[key] = policies.clamp_policy_value(key, base[key])
    return base



class CreateDraftUseCase:
    def __init__(
        self,
        drafter: DraftGeneratorPort,
        validator: ValidatorPort,
        qa_gateway: QAGatewayPort,
        campaigns: CampaignRepositoryPort,
    ):
        self.drafter = drafter
        self.validator = validator
        self.qa_gateway = qa_gateway
        self.campaigns = campaigns
        self._policy_overrides: dict | None = None
        self._policies: dict | None = None

    def _load_policy_overrides(self) -> None:
        if self._policy_overrides is None:
            self._policy_overrides = self.campaigns.get_policies() or {}
            self._policies = _effective_policies(self._policy_overrides)

    def _get_policy(self, key: str, default=None):
        if self._policies is None:
            self._load_policy_overrides()
        return self._policies.get(key, default) if self._policies else default

    def execute(self, request: CampaignRequest) -> DraftResult:
        self._load_policy_overrides()
        self._research_check(request)
        self._preflight_checks(request)

        # Single Gemini call: the model brainstorms its own hook and writes the
        # email (was 2 calls: generate_hooks + draft). QA gate below is rule-based.
        draft = self.drafter.draft_oneshot(
            company_intel=request.company_intel,
            sender_profile=request.sender_profile,
            recipient_name=request.recipient_name,
        )

        self._self_review(draft)

        qa_result = self._qa_gate(draft, request)
        draft.qa_result = qa_result

        campaign_id = self.campaigns.create_draft_campaign(draft, request)
        draft.campaign_id = campaign_id
        return draft

    def _research_check(self, request: CampaignRequest) -> None:
        required_intel_fields = [
            "product_description",
            "recent_signal",
            "recipient_role",
            "recipient_public_work",
        ]
        missing = [f for f in required_intel_fields if not request.company_intel.get(f)]
        if missing:
            raise ResearchInsufficientError(
                f"RESEARCH_INSUFFICIENT: missing fields: {missing}. Intel Agent must populate these before Mailer Agent can proceed."
            )

        required_sender_fields = ["name", "email", "skills", "proof_points"]
        missing_sender = [f for f in required_sender_fields if not request.sender_profile.get(f)]
        if missing_sender:
            raise SenderProfileIncompleteError(f"Sender profile missing: {missing_sender}")

    def _preflight_checks(self, request: CampaignRequest) -> None:
        if self.campaigns.is_do_not_contact(request.recipient_email):
            raise DoNotContactError(
                f"{request.recipient_email} is on the do-not-contact list. This cannot be overridden."
            )

        if self.campaigns.in_ats_pipeline(request.recipient_email, request.job_id):
            raise ATSConflictError(
                "This recipient is already in the ATS pipeline for this job. Constitution §7.3: cannot cold email someone in an active formal application."
            )

        today_count = self.campaigns.sent_today_count()
        daily_limit = self._get_policy("daily_send_limit", policies.DAILY_SEND_LIMIT)
        if today_count >= daily_limit:
            raise DailyLimitError(
                f"Daily send limit ({daily_limit}) reached. Emails will be deferred to next available slot."
            )

        company = request.company_intel.get("company_name", "")
        company_count = self.campaigns.sent_to_company_30d(company)
        max_company = self._get_policy("max_company_emails_30d", policies.MAX_COMPANY_EMAILS_30D)
        if company_count >= max_company:
            raise CompanyLimitError(
                f"Already sent {company_count} emails to {company} in the last 30 days. Max is {max_company}."
            )

        if request.company_intel.get("no_cold_outreach_policy"):
            policy_text = request.company_intel.get("no_cold_outreach_policy_text", "")
            raise NoOutreachPolicyError(
                f"{company} has a documented no-cold-outreach policy: '{policy_text}'. User must provide explicit logged confirmation to proceed."
            )

        match_score = self.campaigns.get_match_score(request.job_id)
        min_match = self._get_policy("min_match_score", policies.MIN_MATCH_SCORE)
        if match_score is not None and match_score < min_match:
            logger.warning(
                f"LOW_MATCH_SCORE: {match_score}/100 for job {request.job_id}. Draft will use growth-trajectory framing, not fit-claiming framing."
            )
            request.company_intel["low_match_mode"] = True
            request.company_intel["match_score"] = match_score

        if self.campaigns.already_sent(request.recipient_email, request.job_id):
            raise DuplicateSendError(
                f"Email already sent to {request.recipient_email} for job {request.job_id}. Constitution §7.9: idempotent sends only."
            )

    def _score_and_select_hook(self, hooks: list[dict]) -> dict:
        def score(hook: dict) -> int:
            return hook.get("specificity", 0) + hook.get("surprise_factor", 0) + hook.get("relevance", 0)

        scored = sorted(hooks, key=score, reverse=True)
        best = scored[0]
        logger.info(f"Hook selected (score {score(best)}/15): {best.get('text', '')[:80]}...")
        return best

    def _self_review(self, draft: DraftResult) -> None:
        failures = []
        words = draft.body_text.split()
        min_w = self._get_policy("min_words", policies.MIN_WORDS)
        max_w = self._get_policy("max_words", policies.MAX_WORDS)
        if len(words) < min_w:
            failures.append(f"Word count {len(words)} is below minimum {min_w}")
        if len(words) > max_w:
            failures.append(f"Word count {len(words)} exceeds maximum {max_w}")

        subj_max = self._get_policy("subject_max_chars", policies.MAX_SUBJECT_CHARS)
        if len(draft.subject) > subj_max:
            failures.append(f"Subject '{draft.subject}' is {len(draft.subject)} chars (max {subj_max})")

        first_sentence = draft.body_text.strip().split(".")[0].strip()
        if first_sentence.startswith("I ") or first_sentence.startswith("I'"):
            failures.append("First sentence starts with 'I' — constitution §3.1 prohibits this")

        min_pers = self._get_policy("min_personalization", policies.MIN_PERSONALIZATION)
        if len(draft.personalization_signals) < min_pers:
            failures.append(
                f"Only {len(draft.personalization_signals)} personalization signals (minimum {min_pers})"
            )

        ask_count = draft.body_text.count("?")
        if ask_count > 3:
            failures.append(f"Too many question marks ({ask_count}) — suggests more than one ask")

        for phrase in policies.BANNED_PHRASES[:8]:
            if phrase.lower() in draft.body_text.lower():
                failures.append(f"Prohibited phrase found: '{phrase}'")

        exclamation_count = draft.body_text.count("!")
        max_excl = self._get_policy("max_exclamations", policies.MAX_EXCLAMATIONS)
        if exclamation_count > max_excl:
            failures.append(f"Too many exclamation marks ({exclamation_count}) — max {max_excl}")

        if failures:
            updated = self.drafter.revise(draft, failures)
            remaining = self.validator.check_self_review(updated)
            if remaining:
                raise SelfReviewError(
                    f"Self-review failed after revision attempt. Remaining issues: {remaining}"
                )

    def _qa_gate(self, draft: DraftResult, request: CampaignRequest) -> dict:
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

        qa_retries = self._get_policy("qa_max_retries", policies.QA_MAX_RETRIES)
        for attempt in range(qa_retries + 1):
            result = self.qa_gateway.validate_email(payload)
            if result["status"] == "PASS":
                logger.info(f"QA gate passed on attempt {attempt + 1}")
                return result

            logger.warning(f"QA gate FAIL (attempt {attempt + 1}): {result['violations']}")
            if attempt < qa_retries:
                draft = self.drafter.revise(draft, result["violations"])
                payload.update(
                    {
                        "body_text": draft.body_text,
                        "body_html": draft.body_html,
                        "subject": draft.subject,
                        "word_count": len(draft.body_text.split()),
                        "personalization_signals": draft.personalization_signals,
                    }
                )
            else:
                raise QAEscalationError(
                    f"QA gate failed {qa_retries + 1} times. Final violations: {result['violations']}. Escalating to PM Agent."
                )


class SendCampaignUseCase:
    def __init__(
        self,
        campaigns: CampaignRepositoryPort,
        events: EventRepositoryPort,
        tracker: TrackerPort,
        timezone_port: TimezonePort,
        transport_factory,
    ):
        self.campaigns = campaigns
        self.events = events
        self.tracker = tracker
        self.timezone_port = timezone_port
        self.transport_factory = transport_factory

    def execute(self, campaign_id: str) -> dict:
        campaign = self.campaigns.get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        if campaign.status != "user_approved":
            raise SendBlockedError(
                f"Campaign {campaign_id} status is '{campaign.status}'. Must be 'user_approved' before sending."
            )

        if self.campaigns.already_sent(campaign.recipient_email, campaign.job_id):
            raise DuplicateSendError(
                f"Idempotency violation: email already sent for campaign {campaign_id}"
            )

        tz = self.timezone_port.infer_recipient_timezone(
            campaign.recipient_email, getattr(campaign, "company_intel", {}) or {}
        )
        hour = datetime.now(tz).hour
        if hour >= 22 or hour < 6:
            raise SendTimingError(
                f"Send blocked: recipient local time is {hour}:00. Constitution §6.4: do not send between 10pm and 6am."
            )

        config = self.campaigns.get_user_config()
        transport: MailerTransportPort = self.transport_factory(config)

        features = self.campaigns.get_features() or {}
        if features.get("tracking_enabled", True):
            body_html = self.tracker.inject_pixel(campaign.body_html, campaign_id)
        else:
            body_html = campaign.body_html  # no pixel injection when disabled

        message_id = transport.send(
            to_email=campaign.recipient_email,
            to_name=campaign.recipient_name,
            subject=campaign.subject,
            body_html=body_html,
            body_text=campaign.body_text,
        )

        self.events.record_sent(campaign_id, message_id)
        self.campaigns.mark_campaign_sent(campaign_id, message_id)

        logger.info(f"Email sent: campaign={campaign_id} message_id={message_id}")
        return {"status": "sent", "campaign_id": campaign_id, "message_id": message_id}


class ScheduleFollowupsUseCase:
    def __init__(self, campaigns: CampaignRepositoryPort, timezone_port: TimezonePort):
        self.campaigns = campaigns
        self.timezone_port = timezone_port
        self._policies = None

    def _get_followup_days(self):
        if self._policies is None:
            overrides = self.campaigns.get_policies() or {}
            self._policies = _effective_policies(overrides)
        return self._policies.get("followup_days", policies.FOLLOWUP_DAYS)

    def execute(self, campaign_id: str) -> list[dict]:
        campaign = self.campaigns.get_campaign(campaign_id)
        if not campaign or campaign.status != "sent":
            return []

        followup_days = self._get_followup_days()
        tasks = []
        for day_offset in followup_days:
            send_date = datetime.now(timezone.utc).date() + timedelta(days=day_offset)
            tz = self.timezone_port.infer_recipient_timezone(campaign.recipient_email, {})
            scheduled_for = datetime.combine(send_date, datetime.min.time().replace(hour=9), tzinfo=tz)
            tasks.append(
                {
                    "type": "followup",
                    "campaign_id": campaign_id,
                    "day_offset": day_offset,
                    "scheduled_for": scheduled_for,
                }
            )
        return tasks


class HandleReplyUseCase:
    def __init__(self, campaigns: CampaignRepositoryPort, events: EventRepositoryPort):
        self.campaigns = campaigns
        self.events = events

    def execute(self, campaign_id: str, reply_type: str, reply_text: str) -> dict:
        campaign = self.campaigns.get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        self.campaigns.cancel_pending_followups(campaign_id)

        if reply_type == "removal_request":
            self.campaigns.add_to_do_not_contact(campaign.recipient_email)

        self.events.record_reply(campaign_id, reply_type, reply_text)

        return {
            "campaign_id": campaign_id,
            "reply_type": reply_type,
            "followups_cancelled": True,
            "action_required": {
                "positive": "Recipient wants to talk. Draft a reply or send calendar link.",
                "rejection": "Marked rejected. No further action needed.",
                "ooo": "OOO detected. Follow-ups paused until OOO period ends.",
                "referral": "Referred to another contact. New campaign draft prepared — review before sending.",
                "removal_request": "Added to do-not-contact list. No further outreach permitted.",
            }.get(reply_type, "Review reply and decide next step."),
        }


class ScrapeJobsUseCase:
    def __init__(self, scraper: JobScraperPort, campaigns: CampaignRepositoryPort):
        self.scraper = scraper
        self.campaigns = campaigns

    def execute(self, url: str, source: str | None = None) -> dict:
        integrations = self.campaigns.get_integrations() or {}
        resolved_source = source or (
            (integrations.get("scraper_sources") or ["careers_page"])[0]
            if integrations.get("scraper_sources")
            else "careers_page"
        )
        scraped_jobs = self.scraper.scrape(url, source=resolved_source)
        saved: list[dict] = []
        skipped = 0
        for job in scraped_jobs:
            job_id, created = self.campaigns.save_job(job)
            row = self._serialize_job(job, job_id)
            if created:
                saved.append(row)
            else:
                skipped += 1
        return {
            "scraped": len(saved),
            "skipped": skipped,
            "jobs": saved,
        }

    @staticmethod
    def _serialize_job(job: NormalizedJob, job_id: str) -> dict:
        return {
            "id": job_id,
            "title": job.title,
            "company": job.company,
            "url": job.url,
            "location": job.location,
            "description": job.description,
            "source": job.source,
            "match_score": None,
        }


DEFAULT_INTEL_CACHE_DAYS = 14


class GenerateIntelReportUseCase:
    def __init__(self, research: IntelResearchPort, campaigns: CampaignRepositoryPort):
        self.research = research
        self.campaigns = campaigns

    def execute(self, company: str, *, force_refresh: bool = False, cache_days: int = DEFAULT_INTEL_CACHE_DAYS) -> dict:
        slug = company.strip().lower()
        if not slug:
            raise ValueError("company is required")

        if not force_refresh:
            cached = self.campaigns.get_intel_report(slug)
            if cached and self._is_fresh(cached["generated_at"], cache_days):
                return {**cached, "cached": True}

        sections = self.research.generate(slug)
        now = datetime.now(timezone.utc)
        self.campaigns.save_intel_report(slug, sections, now)
        return {
            "company": slug,
            "sections": sections,
            "generated_at": now.isoformat(),
            "cached": False,
        }

    def get_cached(self, company: str) -> dict | None:
        slug = company.strip().lower()
        report = self.campaigns.get_intel_report(slug)
        if not report:
            return None
        return {**report, "cached": True}

    @staticmethod
    def _is_fresh(generated_at: str, cache_days: int) -> bool:
        dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - dt
        return age.days < cache_days
