import uuid
from datetime import datetime, timezone, timedelta

from ...db.session import get_session
from ...db.models import Campaign, EmailEvent, UserConfig, Job, SenderProfile, PolicyConfig, FeatureConfig, ScheduledTask, IntegrationConfig, Contact, MemoryEntry, Roadmap


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
                Campaign.sent_at >= datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc),
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
            if campaign and campaign.status == "sent":
                campaign.status = "opened"
                db.commit()

    def count_by_status(self, status: str) -> int:
        with get_session() as db:
            return db.query(Campaign).filter(Campaign.status == status).count()

    def create_scheduled_task(self, campaign_id: str, task_type: str, scheduled_for: str) -> None:
        with get_session() as db:
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
        delivery_mode: str = "smtp",
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
                existing.delivery_mode = delivery_mode
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
                        delivery_mode=delivery_mode,
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
        from ...domain import policies as domain_policies

        domain_policies.validate_policy_overrides(
            daily_send_limit=daily_send_limit,
            max_company_emails_30d=max_company_emails_30d,
            subject_max_chars=subject_max_chars,
        )
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

    def get_integrations(self) -> dict:
        from ...db.models import IntegrationConfig
        with get_session() as db:
            cfg = db.query(IntegrationConfig).first()
            if cfg:
                return {
                    "apify_token_enc": cfg.apify_token_enc,
                    "scraper_sources": cfg.scraper_sources or [],
                    "gemini_api_key_enc": cfg.gemini_api_key_enc,
                    "github_token_enc": cfg.github_token_enc,
                    "github_username": cfg.github_username,
                }
            # defaults
            return {
                "apify_token_enc": None,
                "scraper_sources": [],
                "gemini_api_key_enc": None,
                "github_token_enc": None,
                "github_username": None,
            }

    def save_integrations(
        self,
        apify_token_enc: str | None = None,
        scraper_sources: list | None = None,
        gemini_api_key_enc: str | None = None,
        github_token_enc: str | None = None,
        github_username: str | None = None,
        clear_github: bool = False,
    ) -> None:
        from ...db.models import IntegrationConfig
        with get_session() as db:
            existing = db.query(IntegrationConfig).first()
            if existing:
                if apify_token_enc is not None:
                    existing.apify_token_enc = apify_token_enc
                if scraper_sources is not None:
                    existing.scraper_sources = scraper_sources
                if gemini_api_key_enc is not None:
                    existing.gemini_api_key_enc = gemini_api_key_enc
                if clear_github:
                    # Explicit disconnect — null both columns
                    existing.github_token_enc = None
                    existing.github_username = None
                else:
                    if github_token_enc is not None:
                        existing.github_token_enc = github_token_enc
                    if github_username is not None:
                        existing.github_username = github_username
            else:
                db.add(
                    IntegrationConfig(
                        apify_token_enc=apify_token_enc,
                        scraper_sources=scraper_sources if scraper_sources is not None else [],
                        gemini_api_key_enc=gemini_api_key_enc,
                        github_token_enc=None if clear_github else github_token_enc,
                        github_username=None if clear_github else github_username,
                    )
                )
            db.commit()


    def get_gemini_api_key(self) -> str | None:
        """Return the decrypted Gemini API key from config, or None if unset."""
        from ...config.secrets import decrypt_secret

        cfg = self.get_integrations()
        enc = cfg.get("gemini_api_key_enc")
        if not enc:
            return None
        try:
            return decrypt_secret(enc)
        except Exception:
            return None

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

    def get_job_by_url(self, url: str) -> dict | None:
        with get_session() as db:
            job = db.query(Job).filter_by(url=url).first()
            if not job:
                return None
            return self._job_to_dict(job)

    def save_job(self, job) -> tuple[str, bool]:
        with get_session() as db:
            existing = db.query(Job).filter_by(url=job.url).first()
            if existing:
                return existing.id, False
            row = Job(
                id=job.id,
                title=job.title,
                company=job.company,
                url=job.url,
                location=job.location,
                description=job.description,
                source=job.source,
                scraped_at=datetime.now(timezone.utc),
                match_score=None,
            )
            db.add(row)
            db.commit()
            return row.id, True

    def list_jobs(self, company: str | None = None, limit: int = 100, offset: int = 0) -> list:
        with get_session() as db:
            q = db.query(Job)
            if company:
                q = q.filter(Job.company.ilike(f"%{company}%"))
            q = q.order_by(Job.scraped_at.desc().nullslast()).offset(offset).limit(limit)
            return [self._job_to_dict(job) for job in q.all()]

    def delete_jobs(self, ids: list[str]) -> int:
        """Delete jobs by id. Returns the number actually removed."""
        if not ids:
            return 0
        with get_session() as db:
            deleted = db.query(Job).filter(Job.id.in_(ids)).delete(synchronize_session=False)
            db.commit()
            return int(deleted or 0)

    # ---- Resumes / cover letters (LaTeX documents) ----
    @staticmethod
    def _resume_to_dict(r) -> dict:
        return {
            "id": r.id,
            "name": r.name,
            "kind": r.kind,
            "latex_source": r.latex_source,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }

    def list_resumes(self, kind: str | None = None) -> list:
        from ...db.models import Resume
        with get_session() as db:
            q = db.query(Resume)
            if kind:
                q = q.filter(Resume.kind == kind)
            q = q.order_by(Resume.updated_at.desc())
            return [self._resume_to_dict(r) for r in q.all()]

    def get_resume(self, resume_id: str) -> dict | None:
        from ...db.models import Resume
        with get_session() as db:
            r = db.query(Resume).filter_by(id=resume_id).first()
            return self._resume_to_dict(r) if r else None

    def create_resume(self, name: str, latex_source: str, kind: str = "resume") -> dict:
        from ...db.models import Resume
        now = datetime.now(timezone.utc)
        rid = uuid.uuid4().hex
        with get_session() as db:
            db.add(Resume(id=rid, name=name or "Untitled", kind=kind, latex_source=latex_source or "", created_at=now, updated_at=now))
            db.commit()
        return self.get_resume(rid)

    def update_resume(self, resume_id: str, name: str | None = None, latex_source: str | None = None) -> dict | None:
        from ...db.models import Resume
        with get_session() as db:
            r = db.query(Resume).filter_by(id=resume_id).first()
            if not r:
                return None
            if name is not None:
                r.name = name
            if latex_source is not None:
                r.latex_source = latex_source
            r.updated_at = datetime.now(timezone.utc)
            db.commit()
        return self.get_resume(resume_id)

    def delete_resume(self, resume_id: str) -> bool:
        from ...db.models import Resume
        with get_session() as db:
            deleted = db.query(Resume).filter_by(id=resume_id).delete()
            db.commit()
            return bool(deleted)

    @staticmethod
    def _job_to_dict(job: Job) -> dict:
        return {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "url": job.url,
            "location": job.location,
            "description": job.description,
            "source": job.source,
            "match_score": job.match_score,
            "scraped_at": job.scraped_at.isoformat() if job.scraped_at else None,
            "status": job.status,
            "applied_at": job.applied_at.isoformat() if job.applied_at else None,
        }

    def get_intel_report(self, company: str) -> dict | None:
        from ...db.models import IntelReport

        slug = company.strip().lower()
        with get_session() as db:
            row = db.query(IntelReport).filter_by(company=slug).first()
            if not row:
                return None
            return {
                "company": row.company,
                "sections": row.sections,
                "generated_at": row.generated_at.isoformat(),
            }

    def save_intel_report(self, company: str, sections: dict, generated_at) -> None:
        from ...db.models import IntelReport

        slug = company.strip().lower()
        with get_session() as db:
            existing = db.query(IntelReport).filter_by(company=slug).first()
            if existing:
                existing.sections = sections
                existing.generated_at = generated_at
            else:
                db.add(IntelReport(company=slug, sections=sections, generated_at=generated_at))
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

    def get_gmail_credentials(self, email: str | None = None) -> dict | None:
        from ...db.models import GmailCredential
        with get_session() as db:
            if email:
                cred = db.query(GmailCredential).filter_by(email=email).first()
                if not cred:
                    cred = db.query(GmailCredential).first()
            else:
                cred = db.query(GmailCredential).first()
            if cred:
                db.expunge(cred)
                return {
                    "email": getattr(cred, "email", None),
                    "client_id_enc": cred.client_id_enc,
                    "client_secret_enc": cred.client_secret_enc,
                    "access_token_enc": cred.access_token_enc,
                    "refresh_token_enc": cred.refresh_token_enc,
                    "token_uri": cred.token_uri,
                    "scopes": cred.scopes,
                    "updated_at": cred.updated_at,
                }
            return None

    def save_gmail_credentials(
        self,
        email: str | None = None,
        client_id_enc: str | None = None,
        client_secret_enc: str | None = None,
        access_token_enc: str | None = None,
        refresh_token_enc: str | None = None,
        token_uri: str | None = None,
        scopes: list | None = None,
    ) -> None:
        from ...db.models import GmailCredential
        with get_session() as db:
            if email:
                existing = db.query(GmailCredential).filter_by(email=email).first()
            else:
                existing = db.query(GmailCredential).first()
            now = datetime.now(timezone.utc)
            if existing:
                if email is not None:
                    existing.email = email
                if client_id_enc is not None:
                    existing.client_id_enc = client_id_enc
                if client_secret_enc is not None:
                    existing.client_secret_enc = client_secret_enc
                if access_token_enc is not None:
                    existing.access_token_enc = access_token_enc
                if refresh_token_enc is not None:
                    existing.refresh_token_enc = refresh_token_enc
                if token_uri is not None:
                    existing.token_uri = token_uri
                if scopes is not None:
                    existing.scopes = scopes
                existing.updated_at = now
            else:
                db.add(
                    GmailCredential(
                        email=email,
                        client_id_enc=client_id_enc,
                        client_secret_enc=client_secret_enc,
                        access_token_enc=access_token_enc,
                        refresh_token_enc=refresh_token_enc,
                        token_uri=token_uri,
                        scopes=scopes,
                        updated_at=now,
                    )
                )
            db.commit()

    def get_decrypted_gmail_credentials(self, email: str | None = None) -> dict | None:
        from ...config.secrets import decrypt_secret
        creds = self.get_gmail_credentials(email)
        if not creds:
            return None
        def safe_decrypt(val: str | None) -> str | None:
            if not val:
                return None
            try:
                return decrypt_secret(val)
            except Exception:
                return None
        return {
            "email": creds.get("email"),
            "client_id": safe_decrypt(creds["client_id_enc"]),
            "client_secret": safe_decrypt(creds["client_secret_enc"]),
            "access_token": safe_decrypt(creds["access_token_enc"]),
            "refresh_token": safe_decrypt(creds["refresh_token_enc"]),
            "token_uri": creds["token_uri"],
            "scopes": creds["scopes"],
            "updated_at": creds["updated_at"],
        }

    def get_all_decrypted_gmail_credentials(self) -> list[dict]:
        from ...config.secrets import decrypt_secret
        from ...db.models import GmailCredential
        with get_session() as db:
            rows = db.query(GmailCredential).all()
        def safe_decrypt(val: str | None) -> str | None:
            if not val:
                return None
            try:
                return decrypt_secret(val)
            except Exception:
                return None
        result = []
        for cred in rows:
            result.append({
                "email": getattr(cred, "email", None),
                "client_id": safe_decrypt(cred.client_id_enc),
                "client_secret": safe_decrypt(cred.client_secret_enc),
                "access_token": safe_decrypt(cred.access_token_enc),
                "refresh_token": safe_decrypt(cred.refresh_token_enc),
                "token_uri": cred.token_uri,
                "scopes": cred.scopes,
                "updated_at": cred.updated_at,
            })
        return result

    # ---- Contacts ----
    @staticmethod
    def _contact_to_dict(c) -> dict:
        return {
            "id": c.id,
            "name": c.name,
            "current_company": c.current_company,
            "role": c.role,
            "email": c.email,
            "linkedin_url": c.linkedin_url,
            "x_handle": c.x_handle,
            "relationship": c.relationship,
            "notes": c.notes,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }

    def list_contacts(self, limit: int = 100, offset: int = 0) -> list[dict]:
        from ...db.models import Contact
        with get_session() as db:
            q = db.query(Contact).order_by(Contact.created_at.desc()).offset(offset).limit(limit)
            return [self._contact_to_dict(c) for c in q.all()]

    def get_contact(self, contact_id: str) -> dict | None:
        from ...db.models import Contact
        with get_session() as db:
            c = db.query(Contact).filter_by(id=contact_id).first()
            return self._contact_to_dict(c) if c else None

    def create_contact(self, name: str, current_company: str | None = None, role: str | None = None, email: str | None = None, linkedin_url: str | None = None, x_handle: str | None = None, relationship: str = "cold", notes: str | None = None) -> dict:
        from ...db.models import Contact
        cid = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        with get_session() as db:
            c = Contact(
                id=cid,
                name=name,
                current_company=current_company,
                role=role,
                email=email,
                linkedin_url=linkedin_url,
                x_handle=x_handle,
                relationship=relationship,
                notes=notes,
                created_at=now,
            )
            db.add(c)
            db.commit()
        return self.get_contact(cid)

    def update_contact(self, contact_id: str, data: dict) -> dict | None:
        from ...db.models import Contact
        with get_session() as db:
            c = db.query(Contact).filter_by(id=contact_id).first()
            if not c:
                return None
            for k, v in data.items():
                if v is not None:
                    setattr(c, k, v)
            db.commit()
        return self.get_contact(contact_id)

    def delete_contact(self, contact_id: str) -> bool:
        from ...db.models import Contact
        with get_session() as db:
            deleted = db.query(Contact).filter_by(id=contact_id).delete()
            db.commit()
            return bool(deleted)

    def search_contacts_by_company(self, company: str) -> list[dict]:
        from ...db.models import Contact
        with get_session() as db:
            q = db.query(Contact).filter(Contact.current_company.ilike(f"%{company}%")).order_by(Contact.name.asc())
            return [self._contact_to_dict(c) for c in q.all()]

    # ---- Memory Bank ----
    @staticmethod
    def _memory_entry_to_dict(m) -> dict:
        return {
            "id": m.id,
            "type": m.type,
            "key": m.key,
            "value": m.value,
            "source": m.source,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        }

    def list_memory_entries(self) -> list[dict]:
        from ...db.models import MemoryEntry
        with get_session() as db:
            q = db.query(MemoryEntry).order_by(MemoryEntry.updated_at.desc())
            return [self._memory_entry_to_dict(m) for m in q.all()]

    def save_memory_entry(self, type: str, key: str, value: str, source: str = "user_input") -> dict:
        from ...db.models import MemoryEntry
        now = datetime.now(timezone.utc)
        with get_session() as db:
            existing = db.query(MemoryEntry).filter_by(type=type, key=key).first()
            if existing:
                existing.value = value
                existing.source = source
                existing.updated_at = now
                mid = existing.id
            else:
                mid = str(uuid.uuid4())
                db.add(
                    MemoryEntry(
                        id=mid,
                        type=type,
                        key=key,
                        value=value,
                        source=source,
                        updated_at=now,
                    )
                )
            db.commit()
        return self.get_memory_entry(mid)

    def get_memory_entry(self, entry_id: str) -> dict | None:
        from ...db.models import MemoryEntry
        with get_session() as db:
            m = db.query(MemoryEntry).filter_by(id=entry_id).first()
            return self._memory_entry_to_dict(m) if m else None

    # ---- Roadmaps ----
    @staticmethod
    def _roadmap_to_dict(r) -> dict:
        return {
            "id": r.id,
            "title": r.title,
            "generated_at": r.generated_at.isoformat() if r.generated_at else None,
            "nodes": r.nodes or {},
        }

    def create_roadmap(self, title: str, nodes: dict) -> dict:
        from ...db.models import Roadmap
        rid = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        with get_session() as db:
            r = Roadmap(
                id=rid,
                title=title,
                nodes=nodes,
                generated_at=now,
            )
            db.add(r)
            db.commit()
        return self.get_roadmap(rid)

    def get_roadmap(self, roadmap_id: str) -> dict | None:
        from ...db.models import Roadmap
        with get_session() as db:
            r = db.query(Roadmap).filter_by(id=roadmap_id).first()
            return self._roadmap_to_dict(r) if r else None

    def update_roadmap_nodes(self, roadmap_id: str, nodes: dict) -> dict | None:
        from ...db.models import Roadmap
        with get_session() as db:
            r = db.query(Roadmap).filter_by(id=roadmap_id).first()
            if not r:
                return None
            r.nodes = nodes
            db.commit()
        return self.get_roadmap(roadmap_id)

    def update_roadmap_node_status(self, roadmap_id: str, node_id: str, completed: bool | None = None, status: str | None = None) -> dict | None:
        from ...db.models import Roadmap
        with get_session() as db:
            r = db.query(Roadmap).filter_by(id=roadmap_id).first()
            if not r:
                return None
            nodes_data = r.nodes or {}
            updated = False
            
            def update_status(node):
                if completed is not None:
                    node["status"] = "completed" if completed else "not_started"
                elif status is not None:
                    node["status"] = status
                else:
                    node["status"] = "not_started" if node.get("status") == "completed" else "completed"

            # 1. Update in phases structure
            if "phases" in nodes_data and isinstance(nodes_data["phases"], list):
                for phase in nodes_data["phases"]:
                    if "nodes" in phase and isinstance(phase["nodes"], list):
                        for node in phase["nodes"]:
                            if str(node.get("id")) == str(node_id):
                                update_status(node)
                                updated = True
                                break

            # 2. Update in flat nodes structure
            if "nodes" in nodes_data and isinstance(nodes_data["nodes"], list):
                for node in nodes_data["nodes"]:
                    if str(node.get("id")) == str(node_id):
                        update_status(node)
                        updated = True
                        break
            
            # 3. Update in old dict format
            elif not updated and str(node_id) in nodes_data:
                node = nodes_data[str(node_id)]
                update_status(node)
                updated = True

            if updated:
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(r, "nodes")
                db.commit()
        return self.get_roadmap(roadmap_id)

    # ---- Job status & stats updates ----
    def get_jobs_stats(self) -> dict[str, int]:
        from sqlalchemy import func
        from ...db.models import Job
        with get_session() as db:
            statuses = ["scraped", "cold_emailed", "applied", "rejected", "in_process", "offer"]
            result = {status: 0 for status in statuses}
            rows = db.query(Job.status, func.count(Job.id)).group_by(Job.status).all()
            for status, count in rows:
                if status in result:
                    result[status] = count
            return result

    def update_job_status(self, job_id: str, status: str) -> dict | None:
        from ...db.models import Job
        with get_session() as db:
            job = db.query(Job).filter_by(id=job_id).first()
            if not job:
                return None
            job.status = status
            if status == "applied":
                job.applied_at = datetime.now(timezone.utc)
            db.commit()
            return self._job_to_dict(job)




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
