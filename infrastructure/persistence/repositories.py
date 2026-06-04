import uuid
from datetime import datetime, timezone, timedelta

from ...db.session import get_session
from ...db.models import Campaign, EmailEvent, UserConfig, Job


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

    def get_user_config(self):
        with get_session() as db:
            config = db.query(UserConfig).first()
            if config:
                db.expunge(config)
            return config

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
                metadata={"message_id": message_id},
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
                metadata={"reply_text": reply_text[:500]},
            )
            db.add(event)
            db.commit()
