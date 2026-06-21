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
    github_token: str | None = None
    github_username: str | None = None


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
    status: str = "scraped"
    applied_at: str | None = None




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
        return {"apify_token": None, "scraper_sources": [], "github_token": None, "github_username": None}
    has_apify = bool(data.get("apify_token_enc"))
    has_github = bool(data.get("github_token_enc"))
    return {
        "apify_token": "***" if has_apify else None,
        "scraper_sources": data.get("scraper_sources") or [],
        "github_token": "***" if has_github else None,
        "github_username": data.get("github_username"),
    }


# ---- Contact Schemas ----
class ContactCreate(BaseModel):
    name: str
    current_company: str | None = None
    role: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    x_handle: str | None = None
    relationship: str = "cold"
    notes: str | None = None


class ContactUpdate(BaseModel):
    name: str | None = None
    current_company: str | None = None
    role: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    x_handle: str | None = None
    relationship: str | None = None
    notes: str | None = None


class ContactResponse(BaseModel):
    id: str
    name: str
    current_company: str | None = None
    role: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    x_handle: str | None = None
    relationship: str
    notes: str | None = None
    created_at: str


def serialize_contact(c) -> dict:
    if c is None:
        return {}
    return {
        "id": c.get("id") if isinstance(c, dict) else getattr(c, "id", None),
        "name": c.get("name") if isinstance(c, dict) else getattr(c, "name", None),
        "current_company": c.get("current_company") if isinstance(c, dict) else getattr(c, "current_company", None),
        "role": c.get("role") if isinstance(c, dict) else getattr(c, "role", None),
        "email": c.get("email") if isinstance(c, dict) else getattr(c, "email", None),
        "linkedin_url": c.get("linkedin_url") if isinstance(c, dict) else getattr(c, "linkedin_url", None),
        "x_handle": c.get("x_handle") if isinstance(c, dict) else getattr(c, "x_handle", None),
        "relationship": c.get("relationship") if isinstance(c, dict) else getattr(c, "relationship", "cold"),
        "notes": c.get("notes") if isinstance(c, dict) else getattr(c, "notes", None),
        "created_at": c.get("created_at") if isinstance(c, dict) else (c.created_at.isoformat() if getattr(c, "created_at", None) else None),
    }


# ---- Memory Bank Schemas ----
class MemoryEntryCreate(BaseModel):
    type: str
    key: str
    value: str
    source: str = "user_input"


class MemoryEntryUpdate(BaseModel):
    value: str
    source: str = "user_input"


class MemoryEntryResponse(BaseModel):
    id: str
    type: str
    key: str
    value: str
    source: str
    updated_at: str


def serialize_memory_entry(m) -> dict:
    if m is None:
        return {}
    return {
        "id": m.get("id") if isinstance(m, dict) else getattr(m, "id", None),
        "type": m.get("type") if isinstance(m, dict) else getattr(m, "type", None),
        "key": m.get("key") if isinstance(m, dict) else getattr(m, "key", None),
        "value": m.get("value") if isinstance(m, dict) else getattr(m, "value", None),
        "source": m.get("source") if isinstance(m, dict) else getattr(m, "source", "user_input"),
        "updated_at": m.get("updated_at") if isinstance(m, dict) else (m.updated_at.isoformat() if getattr(m, "updated_at", None) else None),
    }


# ---- Roadmap Schemas ----
class RoadmapCreate(BaseModel):
    title: str
    syllabus: str | None = None


class NodeStatusUpdate(BaseModel):
    completed: bool | None = None
    status: str | None = None


class RoadmapNode(BaseModel):
    id: str
    label: str
    status: str = "not_started"
    resources: list[dict] = []
    dependencies: list[str] = []


class RoadmapEdge(BaseModel):
    source: str
    target: str


class RoadmapNodeRich(BaseModel):
    id: str
    label: str
    description: str | None = None
    status: str = "not_started"
    duration: str | None = None
    subtopics: list[str] = []
    resources: list[dict] = []


class RoadmapPhase(BaseModel):
    phase_number: int
    title: str
    description: str | None = None
    nodes: list[RoadmapNodeRich] = []


class RoadmapGraph(BaseModel):
    nodes: list[RoadmapNode]
    edges: list[RoadmapEdge] = []
    phases: list[RoadmapPhase] = []


class RoadmapResponse(BaseModel):
    id: str
    title: str
    generated_at: str
    nodes: RoadmapGraph

