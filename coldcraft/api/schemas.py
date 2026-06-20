from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from ..domain.models import DraftResult


class DraftRequest(BaseModel):
    job_id: str
    recipient_email: str
    recipient_name: str
    company_intel: dict
    sender_profile: dict | None = None  # optional: falls back to stored profile via /profile API
    triggered_by: str = "user"


class ReplyRequest(BaseModel):
    reply_type: str
    reply_text: str


class ConfigUpdate(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_pass: str | None = None  # plain text on input only; encrypted server-side; omitted on updates to keep existing
    from_email: str
    from_name: str
    tracking_domain: str | None = None
    delivery_mode: str = "smtp"  # 'smtp' (live) | 'mailpit' (local test capture)


class ConfigResponse(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_user: str
    from_email: str
    from_name: str
    tracking_domain: str | None = None
    delivery_mode: str = "smtp"
    # deliberately excludes smtp_pass / smtp_pass_enc


def serialize_draft(draft: "DraftResult") -> dict:
    return {
        "campaign_id": draft.campaign_id,
        "subject": draft.subject,
        "body_text": draft.body_text,
        "body_html": draft.body_html,
        "word_count": draft.word_count,
        "personalization_signals": draft.personalization_signals,
        "status": draft.status,
        "qa_result": draft.qa_result,
    }


def serialize_config(cfg) -> dict:
    """Safe serialization for UserConfig row: never includes password material."""
    if cfg is None:
        return {}
    return {
        "smtp_host": cfg.smtp_host,
        "smtp_port": cfg.smtp_port,
        "smtp_user": cfg.smtp_user,
        "from_email": cfg.from_email,
        "from_name": cfg.from_name,
        "tracking_domain": cfg.tracking_domain,
        "delivery_mode": getattr(cfg, "delivery_mode", "smtp") or "smtp",
    }


class ProfileUpdate(BaseModel):
    name: str
    email: str
    skills: list
    proof_points: list
    tone: str | None = None


class ProfileResponse(BaseModel):
    name: str
    email: str
    skills: list
    proof_points: list
    tone: str | None = None


def serialize_profile(profile) -> dict:
    """Serialization for SenderProfile row (or dict)."""
    if profile is None:
        return {}
    if isinstance(profile, dict):
        return profile
    return {
        "name": profile.name,
        "email": profile.email,
        "skills": profile.skills or [],
        "proof_points": profile.proof_points or [],
        "tone": profile.tone,
    }


class PolicyUpdate(BaseModel):
    daily_send_limit: int | None = None
    max_company_emails_30d: int | None = None
    subject_max_chars: int | None = None
    followup_days: list | None = None


class PolicyResponse(BaseModel):
    daily_send_limit: int | None = None
    max_company_emails_30d: int | None = None
    subject_max_chars: int | None = None
    followup_days: list | None = None
    constitution_floors: dict


def serialize_policies(cfg, constitution_floors: dict) -> dict:
    """Return current (overrides or None) + constitution_floors."""
    current = {
        "daily_send_limit": cfg.get("daily_send_limit") if cfg else None,
        "max_company_emails_30d": cfg.get("max_company_emails_30d") if cfg else None,
        "subject_max_chars": cfg.get("subject_max_chars") if cfg else None,
        "followup_days": cfg.get("followup_days") if cfg else None,
    }
    return {
        **current,
        "constitution_floors": constitution_floors,
    }


class FeatureUpdate(BaseModel):
    tracking_enabled: bool | None = None
    auto_followups: bool | None = None


class FeatureResponse(BaseModel):
    tracking_enabled: bool
    auto_followups: bool


def serialize_features(features: dict) -> dict:
    return {
        "tracking_enabled": features.get("tracking_enabled", True),
        "auto_followups": features.get("auto_followups", True),
    }


class IntegrationUpdate(BaseModel):
    apify_token: str | None = None  # plain on input (for create/update); encrypted server-side; None to keep existing
    scraper_sources: list | None = None


class IntegrationResponse(BaseModel):
    apify_token: str | None = None  # redacted (*** or None) on output; never the real secret
    scraper_sources: list


class ScrapeRequest(BaseModel):
    url: str
    source: str | None = None


class JobResponse(BaseModel):
    id: str
    title: str
    company: str | None = None
    url: str
    location: str | None = None
    description: str | None = None
    source: str
    match_score: float | None = None
    scraped_at: str | None = None


class ScrapeResponse(BaseModel):
    scraped: int
    skipped: int
    jobs: list[JobResponse]


class IntelSection(BaseModel):
    title: str
    content: str
    sources: list[str] = []
    caveat: str | None = None


class IntelReportRequest(BaseModel):
    company: str
    force_refresh: bool = False


class IntelReportResponse(BaseModel):
    company: str
    sections: dict[str, IntelSection]
    generated_at: str
    cached: bool


def serialize_integrations(data: dict | None) -> dict:
    """Return redacted view: never includes raw apify_token or other secrets."""
    if not data:
        return {"apify_token": None, "scraper_sources": []}
    has_apify = bool(data.get("apify_token_enc"))
    return {
        "apify_token": "***" if has_apify else None,
        "scraper_sources": data.get("scraper_sources") or [],
    }
