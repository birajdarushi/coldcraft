from fastapi import APIRouter, HTTPException

from ...domain import policies
from ..schemas import PolicyResponse, PolicyUpdate, serialize_policies


def get_policies_router(campaigns_repo) -> APIRouter:
    """Policies API with constitution clamping.

    Overrides may only be stricter than constitution hard limits, never weaker.
    """
    router = APIRouter(prefix="/policies", tags=["policies"])

    constitution_floors = policies.CONSTITUTION_FLOORS

    @router.get("", response_model=PolicyResponse)
    def get_policies():
        cfg = campaigns_repo.get_policies()
        return serialize_policies(cfg, constitution_floors)

    @router.put("", response_model=PolicyResponse)
    def put_policies(body: PolicyUpdate):
        try:
            policies.validate_policy_overrides(
                daily_send_limit=body.daily_send_limit,
                max_company_emails_30d=body.max_company_emails_30d,
                subject_max_chars=body.subject_max_chars,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        if body.daily_send_limit is not None and body.daily_send_limit < 1:
            raise HTTPException(status_code=422, detail="daily_send_limit must be at least 1")

        if body.max_company_emails_30d is not None and body.max_company_emails_30d < 1:
            raise HTTPException(status_code=422, detail="max_company_emails_30d must be at least 1")

        if body.subject_max_chars is not None and body.subject_max_chars < 1:
            raise HTTPException(status_code=422, detail="subject_max_chars must be at least 1")

        campaigns_repo.save_policies(
            daily_send_limit=body.daily_send_limit,
            max_company_emails_30d=body.max_company_emails_30d,
            subject_max_chars=body.subject_max_chars,
            followup_days=body.followup_days,
        )

        cfg = campaigns_repo.get_policies()
        return serialize_policies(cfg, constitution_floors)

    return router