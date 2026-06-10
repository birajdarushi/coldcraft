from fastapi import APIRouter, HTTPException, Response, Query
from fastapi.responses import RedirectResponse

# Public tracking routes (mounted at root, no /api/v1 prefix for pixel compat)
# See app.py for include at prefix=""

tracking_router = APIRouter(tags=["tracking"])

# 1x1 transparent GIF bytes
_GIF_1X1 = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff"
    b"\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
    b"\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
)


@tracking_router.get("/track/open/{campaign_id}")
def track_open(campaign_id: str, campaigns_repo=None):  # campaigns_repo injected via dependency or global in app
    # For simplicity in router, we expect campaigns_repo passed at mount or use direct
    # In practice wired via closure or app state; here assume available in context (see app wiring note)
    # To make work: the router will be included, and for test we use repo in app context.
    # Simple: always record for verif, respect checked at send time for injection.
    # But to support respect in endpoints too: if we had access.
    # For now implement core record + gif; respect via send path.
    try:
        # Record (use direct or assume repo; for standalone, use session here? To match pattern, enhance.
        # Since repo passed in other routers, for this public one we can add simple record.
        from ..infrastructure.persistence.repositories import SQLAlchemyCampaignRepository
        repo = SQLAlchemyCampaignRepository()
        feats = repo.get_features() or {}
        if feats.get("tracking_enabled", True):
            repo.record_event(campaign_id, "opened", {})
            repo.mark_campaign_opened(campaign_id)
    except Exception:
        pass  # don't break pixel on error
    return Response(content=_GIF_1X1, media_type="image/gif")


@tracking_router.get("/track/click/{campaign_id}")
def track_click(campaign_id: str, url: str = Query(...)):
    try:
        from ..infrastructure.persistence.repositories import SQLAlchemyCampaignRepository
        repo = SQLAlchemyCampaignRepository()
        feats = repo.get_features() or {}
        if feats.get("tracking_enabled", True):
            repo.record_event(campaign_id, "clicked", {"url": url})
    except Exception:
        pass
    # Redirect even if disabled or error
    return RedirectResponse(url=url, status_code=302)

