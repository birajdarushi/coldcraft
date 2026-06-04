from ..agent import MailerAgent
from ..domain.models import CampaignRequest


class MailerAPI:
    """Thin interface layer that maps API-style calls to use-case-backed facade."""

    def __init__(self, config):
        self.agent = MailerAgent(config)

    def create_draft(self, payload: dict):
        request = CampaignRequest(**payload)
        return self.agent.run(request)

    def send_campaign(self, campaign_id: str):
        return self.agent.send(campaign_id)

    def schedule_followups(self, campaign_id: str):
        return self.agent.schedule_followups(campaign_id)

    def handle_reply(self, campaign_id: str, reply_type: str, reply_text: str):
        return self.agent.handle_reply(campaign_id, reply_type, reply_text)
