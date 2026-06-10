import uuid
from datetime import datetime, timezone, timedelta

from ...db.session import get_session
from ...db.models import Campaign, EmailEvent, UserConfig, Job, SenderProfile, PolicyConfig, FeatureConfig, ScheduledTask


class SQLAlchemyCampaignRepository:
    def is_do_not_contact(self, email: str) -> bool:
        from ...db.models import DoNotContact
        with get_session() as db:
            return db.query(DoNotContact).filter_by(email=email).first() is not None

    def in_ats_pipeline(self, email: str, job_id: str) -> bool:
        from ...db.models import ATSApplication
        with get_session() as db:
            return db.query(ATSApplication).filter_by(recipient_email=email, job_id=job_id).first() is not None

    def sent_today_count(self) -> int:
        with get_session() as db:
            today = datetime.now(timezone.utc).date()
            return db.query(Campaign).filter(
                Campaign.status == "sent",
                Campaign.sent_at >= datetime.combine(today, datetime.min.time()),
            ).count()

    def sent_to_company_30d(self, company: str) -> int:
        with get_session() as db:
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            return db.query(Campaign).filter(
                Campaign.company_name == company,
                Campaign.status == "sent",
                Campaign.sent_at >= cutoff,
            ).count()

    def get_match_score(self, job_id: str):
        with get_session() as db:
            job = db.query(Job).filter_by(id=job_id).first()
            return job.match_score if job else None

    def already_sent(self, email: str, job_id: str) -> bool:
        with get_session() as db:
            return db.query(Campaign).filter_by(
                recipient_email=email,
                job_id=job_id,
                status="sent",
            ).first() is not None

    def create_draft_campaign(self, draft, request) -> str:
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

    def get_campaign(self, campaign_id: str):
        with get_session() as db:
            campaign = db.query(Campaign).filter_by(id=campaign_id).first()
            if campaign:
                db.expunge(campaign)
            return campaign

    def list_campaigns(self, status: str | None = None, limit: int = 100, offset: int = 0) -> list:
        with get_session() as db:
            q = db.query(Campaign)
            if status:
                q = q.filter(Campaign.status == status)
            q = q.order_by(Campaign.created_at.desc()).offset(offset).limit(limit)
            rows = q.all()
            result = []
            for c in rows:
                db.expunge(c)
                result.append({
                    "id": c.id,
                    "subject": c.subject,
                    "recipient": c.recipient_email,
                    "status": c.status,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "word_count": len(c.body_text.split()) if c.body_text else 0,
                })
            return result

    def list_events(self, campaign_id: str) -> list:
        with get_session() as db:
            events = db.query(EmailEvent).filter_by(campaign_id=campaign_id).order_by(EmailEvent.occurred_at.asc()).all()
            result = []
            for e in events:
                db.expunge(e)
                result.append({
                    "id": e.id,
                    "event_type": e.event_type,
                    "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
                    "metadata": e.event_metadata,
                })
            return result

    def record_event(self, campaign_id: str, event_type: str, metadata: dict | None = None) -> None:
        with get_session() as db:
            event = EmailEvent(
                id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type=event_type,
                occurred_at=datetime.now(timezone.utc),
                event_metadata=metadata or {},
            )
            db.add(event)
            db.commit()

    def mark_campaign_opened(self, campaign_id: str) -> None:
        with get_session() as db:
            campaign = db.query(Campaign).filter_by(id=campaign_id).first()
            if campaign and campaign.status not in ("sent", "opened", "replied"):
                campaign.status = "opened"
                db.commit()

    def count_by_status(self, status: str) -> int:
        with get_session() as db:
            return db.query(Campaign).filter(Campaign.status == status).count()

    def create_scheduled_task(self, campaign_id: str, task_type: str, scheduled_for: str) -> None:
        with get_session() as db:
            # scheduled_for as iso or datetime str; for simplicity store as pending
            from datetime import datetime, timezone
            dt = datetime.fromisoformat(scheduled_for.replace("Z", "+00:00")) if isinstance(scheduled_for, str) else scheduled_for
            task = ScheduledTask(
                campaign_id=campaign_id,
                task_type=task_type,
                scheduled_for=dt,
                status="pending",
            )
            db.add(task)
            db.commit()

    def get_user_config(self):
        with get_session() as db:
            config = db.query(UserConfig).first()
            if config:
                db.expunge(config)
            return config

    def save_user_config(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_pass_enc: str,
        from_email: str,
        from_name: str,
        tracking_domain: str | None = None,
    ) -> None:
        with get_session() as db:
            existing = db.query(UserConfig).first()
            if existing:
                existing.smtp_host = smtp_host
                existing.smtp_port = smtp_port
                existing.smtp_user = smtp_user
                existing.smtp_pass_enc = smtp_pass_enc
                existing.from_email = from_email
                existing.from_name = from_name
                existing.tracking_domain = tracking_domain
            else:
                db.add(
                    UserConfig(
                        smtp_host=smtp_host,
                        smtp_port=smtp_port,
                        smtp_user=smtp_user,
                        smtp_pass_enc=smtp_pass_enc,
                        from_email=from_email,
                        from_name=from_name,
                        tracking_domain=tracking_domain,
                    )
                )
            db.commit()

    def get_sender_profile(self):
        with get_session() as db:
            profile = db.query(SenderProfile).first()
            if profile:
                db.expunge(profile)
                return {
                    "name": profile.name,
                    "email": profile.email,
                    "skills": profile.skills or [],
                    "proof_points": profile.proof_points or [],
                    "tone": profile.tone,
                }
            return None

    def save_sender_profile(
        self,
        name: str,
        email: str,
        skills: list,
        proof_points: list,
        tone: str | None = None,
    ) -> None:
        with get_session() as db:
            existing = db.query(SenderProfile).first()
            if existing:
                existing.name = name
                existing.email = email
                existing.skills = skills
                existing.proof_points = proof_points
                existing.tone = tone
            else:
                db.add(
                    SenderProfile(
                        name=name,
                        email=email,
                        skills=skills,
                        proof_points=proof_points,
                        tone=tone,
                    )
                )
            db.commit()

    def get_policies(self):
        with get_session() as db:
            cfg = db.query(PolicyConfig).first()
            if cfg:
                db.expunge(cfg)
                return {
                    "daily_send_limit": cfg.daily_send_limit,
                    "max_company_emails_30d": cfg.max_company_emails_30d,
                    "subject_max_chars": cfg.subject_max_chars,
                    "followup_days": cfg.followup_days,
                }
            return None

    def save_policies(
        self,
        daily_send_limit: int | None = None,
        max_company_emails_30d: int | None = None,
        subject_max_chars: int | None = None,
        followup_days: list | None = None,
    ) -> None:
        with get_session() as db:
            existing = db.query(PolicyConfig).first()
            if existing:
                if daily_send_limit is not None:
                    existing.daily_send_limit = daily_send_limit
                if max_company_emails_30d is not None:
                    existing.max_company_emails_30d = max_company_emails_30d
                if subject_max_chars is not None:
                    existing.subject_max_chars = subject_max_chars
                if followup_days is not None:
                    existing.followup_days = followup_days
            else:
                db.add(
                    PolicyConfig(
                        daily_send_limit=daily_send_limit,
                        max_company_emails_30d=max_company_emails_30d,
                        subject_max_chars=subject_max_chars,
                        followup_days=followup_days,
                    )
                )
            db.commit()

    def get_features(self):
        with get_session() as db:
            cfg = db.query(FeatureConfig).first()
            if cfg:
                db.expunge(cfg)
                return {
                    "tracking_enabled": cfg.tracking_enabled,
                    "auto_followups": cfg.auto_followups,
                }
            # defaults
            return {"tracking_enabled": True, "auto_followups": True}

    def save_features(
        self,
        tracking_enabled: bool | None = None,
        auto_followups: bool | None = None,
    ) -> None:
        with get_session() as db:
            existing = db.query(FeatureConfig).first()
            if existing:
                if tracking_enabled is not None:
                    existing.tracking_enabled = tracking_enabled
                if auto_followups is not None:
                    existing.auto_followups = auto_followups
            else:
                db.add(
                    FeatureConfig(
                        tracking_enabled=tracking_enabled if tracking_enabled is not None else True,
                        auto_followups=auto_followups if auto_followups is not None else True,
                    )
                )
            db.commit()

    def mark_user_approved(self, campaign_id: str) -> bool:
        with get_session() as db:
            campaign = db.query(Campaign).filter_by(id=campaign_id).first()
            if not campaign:
                return False
            campaign.status = "user_approved"
            db.commit()
            return True

    def mark_campaign_sent(self, campaign_id: str, message_id: str) -> None:
        with get_session() as db:
            campaign = db.query(Campaign).filter_by(id=campaign_id).first()
            if not campaign:
                return
            campaign.status = "sent"
            campaign.sent_at = datetime.now(timezone.utc)
            campaign.message_id = message_id
            db.commit()

    def cancel_pending_followups(self, campaign_id: str) -> None:
        from ...db.models import ScheduledTask
        with get_session() as db:
            db.query(ScheduledTask).filter_by(campaign_id=campaign_id, status="pending").update({"status": "cancelled"})
            db.commit()

    def add_to_do_not_contact(self, email: str) -> None:
        from ...db.models import DoNotContact
        with get_session() as db:
            exists = db.query(DoNotContact).filter_by(email=email).first()
            if not exists:
                db.add(
                    DoNotContact(
                        email=email,
                        added_at=datetime.now(timezone.utc),
                        reason="replied_removal_request",
                    )
                )
                db.commit()


class SQLAlchemyEventRepository:
    def record_sent(self, campaign_id: str, message_id: str) -> None:
        with get_session() as db:
            event = EmailEvent(
                id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="sent",
                occurred_at=datetime.now(timezone.utc),
                event_metadata={"message_id": message_id},
            )
            db.add(event)
            db.commit()

    def record_reply(self, campaign_id: str, reply_type: str, reply_text: str) -> None:
        with get_session() as db:
            campaign = db.query(Campaign).filter_by(id=campaign_id).first()
            if campaign:
                campaign.status = "replied"
            event = EmailEvent(
                id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type=f"reply_{reply_type}",
                occurred_at=datetime.now(timezone.utc),
                event_metadata={"reply_text": reply_text[:500]},
            )
            db.add(event)
            db.commit()
