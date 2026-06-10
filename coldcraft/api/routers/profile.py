from fastapi import APIRouter, HTTPException

from ..schemas import ProfileResponse, ProfileUpdate, serialize_profile


def get_profile_router(campaigns_repo) -> APIRouter:
    """Sender profile router.

    Stores the sender's identity (name, email, skills, proof_points, tone)
    so it can be reused across drafts without passing sender_profile every time.
    """
    router = APIRouter(prefix="/profile", tags=["profile"])

    @router.get("", response_model=ProfileResponse)
    def get_profile():
        profile = campaigns_repo.get_sender_profile()
        if not profile:
            raise HTTPException(
                status_code=404,
                detail="No sender profile found. Use PUT to initialize.",
            )
        return serialize_profile(profile)

    @router.put("", response_model=ProfileResponse)
    def put_profile(body: ProfileUpdate):
        campaigns_repo.save_sender_profile(
            name=body.name,
            email=body.email,
            skills=body.skills,
            proof_points=body.proof_points,
            tone=body.tone,
        )
        profile = campaigns_repo.get_sender_profile()
        return serialize_profile(profile)

    return router
