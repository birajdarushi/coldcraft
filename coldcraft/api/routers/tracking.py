import logging
import re
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import RedirectResponse

logger = logging.getLogger(__name__)

# 1x1 transparent GIF bytes
_GIF_1X1 = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff"
    b"\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
    b"\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
)

_CAMPAIGN_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _validate_redirect_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid redirect URL")
    return url


def get_tracking_router(campaigns_repo) -> APIRouter:
    """Public tracking routes (mounted at root for pixel compatibility in emails)."""
    router = APIRouter(tags=["tracking"])

    @router.get("/track/open/{campaign_id}")
    def track_open(campaign_id: str):
        if not _CAMPAIGN_ID_RE.match(campaign_id):
            raise HTTPException(status_code=400, detail="Invalid campaign ID")
        try:
            feats = campaigns_repo.get_features() or {}
            if feats.get("tracking_enabled", True):
                campaigns_repo.record_event(campaign_id, "opened", {})
                campaigns_repo.mark_campaign_opened(campaign_id)
        except Exception:
            logger.exception("Failed to record open event for campaign %s", campaign_id)
        return Response(content=_GIF_1X1, media_type="image/gif")

    @router.get("/track/click/{campaign_id}")
    def track_click(campaign_id: str, url: str = Query(...)):
        if not _CAMPAIGN_ID_RE.match(campaign_id):
            raise HTTPException(status_code=400, detail="Invalid campaign ID")
        safe_url = _validate_redirect_url(url)
        try:
            feats = campaigns_repo.get_features() or {}
            if feats.get("tracking_enabled", True):
                campaigns_repo.record_event(campaign_id, "clicked", {"url": safe_url})
        except Exception:
            logger.exception("Failed to record click event for campaign %s", campaign_id)
        return RedirectResponse(url=safe_url, status_code=302)

    return router