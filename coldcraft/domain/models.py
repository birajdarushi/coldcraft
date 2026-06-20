from dataclasses import dataclass
from typing import Optional


@dataclass
class CampaignRequest:
    job_id: str
    recipient_email: str
    recipient_name: str
    company_intel: dict
    sender_profile: dict
    triggered_by: str = "user"


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
    status: str = "draft"


@dataclass
class ValidationResult:
    passed: bool
    violations: list[str]
    warnings: list[str]
    scores: dict


@dataclass
class NormalizedJob:
    id: str
    title: str
    company: str | None
    url: str
    location: str | None
    description: str | None
    source: str
