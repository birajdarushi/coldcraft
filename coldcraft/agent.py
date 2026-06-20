"""
Mailer Agent facade.
Provides backward-compatible entrypoints while delegating business flow to use-case services.
"""

from .domain.models import CampaignRequest, DraftResult
from .domain.errors import (
    MailerAgentError,
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
from .drafter import Drafter
from .smtp_client import SMTPClient
from .tracker import Tracker
from .validators import MailerValidator
from .application.use_cases import (
    CreateDraftUseCase,
    SendCampaignUseCase,
    ScheduleFollowupsUseCase,
    HandleReplyUseCase,
)
from .infrastructure.llm.qa_gateway import QAGatewayAdapter
from .infrastructure.persistence.repositories import (
    SQLAlchemyCampaignRepository,
    SQLAlchemyEventRepository,
)
from .infrastructure.time.timezone_adapter import TimezoneAdapter


class MailerAgent:
    """Compatibility facade over the layered architecture."""

    def __init__(self, config):
        self.config = config

        self.drafter = Drafter()
        self.validator = MailerValidator()
        self.tracker = Tracker(config)

        self.campaigns = SQLAlchemyCampaignRepository()
        self.events = SQLAlchemyEventRepository()
        self.qa_gateway = QAGatewayAdapter()
        self.timezone = TimezoneAdapter()

        self.create_draft_use_case = CreateDraftUseCase(
            drafter=self.drafter,
            validator=self.validator,
            qa_gateway=self.qa_gateway,
            campaigns=self.campaigns,
        )
        self.send_use_case = SendCampaignUseCase(
            campaigns=self.campaigns,
            events=self.events,
            tracker=self.tracker,
            timezone_port=self.timezone,
            transport_factory=lambda cfg: SMTPClient(cfg),
        )
        self.schedule_followups_use_case = ScheduleFollowupsUseCase(
            campaigns=self.campaigns,
            timezone_port=self.timezone,
        )
        self.handle_reply_use_case = HandleReplyUseCase(
            campaigns=self.campaigns,
            events=self.events,
        )

    def run(self, request: CampaignRequest) -> DraftResult:
        return self.create_draft_use_case.execute(request)

    def send(self, campaign_id: str) -> dict:
        return self.send_use_case.execute(campaign_id)

    def schedule_followups(self, campaign_id: str) -> list[dict]:
        return self.schedule_followups_use_case.execute(campaign_id)

    def handle_reply(self, campaign_id: str, reply_type: str, reply_text: str) -> dict:
        return self.handle_reply_use_case.execute(campaign_id, reply_type, reply_text)


__all__ = [
    "MailerAgent",
    "CampaignRequest",
    "DraftResult",
    "MailerAgentError",
    "ResearchInsufficientError",
    "SenderProfileIncompleteError",
    "DoNotContactError",
    "ATSConflictError",
    "DailyLimitError",
    "CompanyLimitError",
    "NoOutreachPolicyError",
    "DuplicateSendError",
    "SelfReviewError",
    "QAEscalationError",
    "SendBlockedError",
    "SendTimingError",
]
