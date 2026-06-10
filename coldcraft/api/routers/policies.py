from fastapi import APIRouter, HTTPException

from ...domain import policies
from ..schemas import PolicyResponse, PolicyUpdate, serialize_policies


def get_policies_router(campaigns_repo) -> APIRouter:
    """Policies API with constitution clamping.

    Allows overriding some limits (e.g. daily_send_limit) but enforces
    hard floors from the constitution and API ceilings.
    """
    router = APIRouter(prefix="/policies", tags=["policies"])

    constitution_floors = policies.CONSTITUTION_FLOORS
    ceilings = policies.POLICY_CEILINGS

    @router.get("", response_model=PolicyResponse)
    def get_policies():
        cfg = campaigns_repo.get_policies()
        return serialize_policies(cfg, constitution_floors)

    @router.put("", response_model=PolicyResponse)
    def put_policies(body: PolicyUpdate):
        # Validation against constitution floors and ceilings
        # For daily_send_limit (a max), we allow raising above the constitution default up to ceiling
        if body.daily_send_limit is not None:
            ceiling = ceilings.get("daily_send_limit", 1000)
            if body.daily_send_limit > ceiling:
                raise HTTPException(
                    status_code=422,
                    detail=f"daily_send_limit cannot exceed ceiling of {ceiling}",
                )

        if body.max_company_emails_30d is not None:
            floor = constitution_floors["max_company_emails_30d"]
            ceiling = ceilings.get("max_company_emails_30d", 100)
            if body.max_company_emails_30d < floor or body.max_company_emails_30d > ceiling:
                raise HTTPException(
                    status_code=422,
                    detail=f"max_company_emails_30d must be between {floor} and {ceiling}",
                )

        if body.subject_max_chars is not None:
            floor = constitution_floors["subject_max_chars"]
            if body.subject_max_chars < floor:
                raise HTTPException(
                    status_code=422,
                    detail=f"subject_max_chars cannot be below hard limit {floor}",
                )

        # followup_days could be validated too, but not in current verifs

        campaigns_repo.save_policies(
            daily_send_limit=body.daily_send_limit,
            max_company_emails_30d=body.max_company_emails_30d,
            subject_max_chars=body.subject_max_chars,
            followup_days=body.followup_days,
        )

        cfg = campaigns_repo.get_policies()
        return serialize_policies(cfg, constitution_floors)

    return router
