from fastapi import APIRouter, HTTPException

from ...domain.errors import MailerAgentError
from ...domain.models import CampaignRequest
from ..schemas import DraftRequest, serialize_draft


def get_drafts_router(agent, campaigns_repo=None) -> APIRouter:
    router = APIRouter(prefix="/drafts", tags=["campaigns"])

    @router.post("")
    def create_draft(request: DraftRequest):
        try:
            sender_profile = request.sender_profile
            # Fallback to stored profile from /api/v1/profile when sender_profile omitted
            if (not sender_profile or not sender_profile.get("name")) and campaigns_repo:
                stored = campaigns_repo.get_sender_profile()
                if stored:
                    sender_profile = stored

            # Adapt API request to domain CampaignRequest (use case expects attribute access)
            domain_req = CampaignRequest(
                job_id=request.job_id,
                recipient_email=request.recipient_email,
                recipient_name=request.recipient_name,
                company_intel=request.company_intel,
                sender_profile=sender_profile or {},
                triggered_by=request.triggered_by,
            )
            draft = agent.run(domain_req)
            return serialize_draft(draft)
        except MailerAgentError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return router
