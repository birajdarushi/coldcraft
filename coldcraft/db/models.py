from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64), index=True)
    company_name: Mapped[str | None] = mapped_column(String(255))
    recipient_email: Mapped[str] = mapped_column(String(255), index=True)
    recipient_name: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255))
    body_html: Mapped[str] = mapped_column(Text)
    body_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)


class EmailEvent(Base):
    __tablename__ = "email_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(String(36), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    event_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class UserConfig(Base):
    __tablename__ = "user_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    smtp_host: Mapped[str] = mapped_column(String(255))
    smtp_port: Mapped[int] = mapped_column(Integer)
    smtp_user: Mapped[str] = mapped_column(String(255))
    smtp_pass_enc: Mapped[str] = mapped_column(Text)
    from_email: Mapped[str] = mapped_column(String(255))
    from_name: Mapped[str] = mapped_column(String(255))
    tracking_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # 'smtp' = live send via configured server; 'mailpit' = capture locally (no real delivery)
    delivery_mode: Mapped[str] = mapped_column(String(16), default="smtp", server_default="smtp")


class SenderProfile(Base):
    __tablename__ = "sender_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    skills: Mapped[list] = mapped_column(JSON)
    proof_points: Mapped[list] = mapped_column(JSON)
    tone: Mapped[str | None] = mapped_column(String(255), nullable=True)


class PolicyConfig(Base):
    __tablename__ = "policy_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    daily_send_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_company_emails_30d: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subject_max_chars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    followup_days: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # other overridable limits can be added here


class FeatureConfig(Base):
    __tablename__ = "feature_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tracking_enabled: Mapped[bool] = mapped_column(default=True)
    auto_followups: Mapped[bool] = mapped_column(default=True)
    # add more flags as needed


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(512), default="")
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, index=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="careers_page")
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class DoNotContact(Base):
    __tablename__ = "do_not_contact"

    email: Mapped[str] = mapped_column(String(255), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(String(255))


class ATSApplication(Base):
    __tablename__ = "ats_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipient_email: Mapped[str] = mapped_column(String(255), index=True)
    job_id: Mapped[str] = mapped_column(String(64), index=True)


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[str] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    task_type: Mapped[str] = mapped_column(String(32), default="followup")
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IntegrationConfig(Base):
    __tablename__ = "integration_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    apify_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    scraper_sources: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Encrypted LLM provider API key (Gemini) — powers drafting/intel.
    gemini_api_key_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Future integration fields (IMAP, etc.) can be added as additional columns or evolve to a data JSON column.


class IntelReport(Base):
    __tablename__ = "intel_reports"

    company: Mapped[str] = mapped_column(String(255), primary_key=True)
    sections: Mapped[dict] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), default="Untitled")
    kind: Mapped[str] = mapped_column(String(32), default="resume")  # 'resume' | 'cover_letter'
    latex_source: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))