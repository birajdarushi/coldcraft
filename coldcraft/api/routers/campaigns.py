from datetime import date, datetime, timedelta, timezone as dtz

from fastapi import APIRouter, HTTPException, Query

from ...domain.errors import MailerAgentError
from ..schemas import ReplyRequest


def _scheduled_for_str(value) -> str:
    if value is None:
        raise HTTPException(status_code=422, detail="scheduled_for is required")
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, str):
        return value
    raise HTTPException(status_code=422, detail="Invalid scheduled_for type")


def get_campaigns_router(campaigns_repo, agent) -> APIRouter:
    router = APIRouter(prefix="/campaigns", tags=["campaigns"])

    @router.get("")
    def list_campaigns(
        status: str | None = Query(None, description="Filter by status e.g. sent, qa_passed, user_approved"),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        campaigns = campaigns_repo.list_campaigns(status=status, limit=limit, offset=offset)
        return campaigns

    @router.get("/{campaign_id}")
    def get_campaign_detail(campaign_id: str):
        campaign = campaigns_repo.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        pol = campaigns_repo.get_policies() or {}
        followup_days = pol.get("followup_days") or [5, 12]
        anchor = campaign.sent_at or campaign.created_at or datetime.now(dtz.utc)
        schedule = []
        for d in followup_days:
            schedule.append((anchor + timedelta(days=d)).date().isoformat())
        detail = {
            "id": campaign.id,
            "subject": campaign.subject,
            "body_html": campaign.body_html,
            "body_text": campaign.body_text,
            "recipient_email": campaign.recipient_email,
            "recipient_name": campaign.recipient_name,
            "status": campaign.status,
            "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
            "qa_result": None,  # TODO: persist from draft flow in future
            "followup_schedule": schedule,
            "word_count": len(campaign.body_text.split()) if campaign.body_text else 0,
        }
        return detail

    @router.get("/{campaign_id}/events")
    def get_campaign_events(campaign_id: str):
        campaign = campaigns_repo.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        events = campaigns_repo.list_events(campaign_id)
        return events

    @router.post("/{campaign_id}/approve")
    def approve_campaign(campaign_id: str):
        campaign = campaigns_repo.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        if campaign.status not in {"qa_passed", "draft"}:
            raise HTTPException(
                status_code=409,
                detail=f"Campaign status is '{campaign.status}', cannot approve",
            )
        campaigns_repo.mark_user_approved(campaign_id)
        return {"campaign_id": campaign_id, "status": "user_approved"}

    @router.post("/{campaign_id}/send")
    def send_campaign(campaign_id: str):
        try:
            return agent.send(campaign_id)
        except MailerAgentError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/{campaign_id}/followups")
    def schedule_followups(campaign_id: str):
        followups = agent.schedule_followups(campaign_id)
        for f in followups:
            campaigns_repo.create_scheduled_task(
                campaign_id=campaign_id,
                task_type=f.get("type", "followup"),
                scheduled_for=_scheduled_for_str(f.get("scheduled_for")),
            )
        return {"followups": followups}

    @router.post("/{campaign_id}/reply")
    def handle_reply(campaign_id: str, request: ReplyRequest):
        try:
            return agent.handle_reply(campaign_id, request.reply_type, request.reply_text)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return router