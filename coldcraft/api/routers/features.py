from fastapi import APIRouter

from ..schemas import FeatureResponse, FeatureUpdate, serialize_features


def get_features_router(campaigns_repo) -> APIRouter:
    """Feature flags API.

    Toggles like tracking_enabled affect send behavior (e.g. pixel injection).
    """
    router = APIRouter(prefix="/features", tags=["features"])

    @router.get("", response_model=FeatureResponse)
    def get_features():
        feats = campaigns_repo.get_features()
        return serialize_features(feats)

    @router.put("", response_model=FeatureResponse)
    def put_features(body: FeatureUpdate):
        campaigns_repo.save_features(
            tracking_enabled=body.tracking_enabled,
            auto_followups=body.auto_followups,
        )
        feats = campaigns_repo.get_features()
        return serialize_features(feats)

    return router
