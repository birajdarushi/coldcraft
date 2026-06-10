import logging

from fastapi import APIRouter, HTTPException

from ...config.secrets import encrypt_secret
from ..schemas import IntegrationResponse, IntegrationUpdate, serialize_integrations

logger = logging.getLogger(__name__)


def get_integrations_router(campaigns_repo) -> APIRouter:
    """Integration config router.

    GET/PUT /api/v1/integrations for scraper, Apify, IMAP etc.

    - Secrets (apify_token etc.) are encrypted on write and **never** returned in GET responses.
    - Uses the same encryption key as SMTP config.
    - Singleton row (upsert pattern).
    """
    router = APIRouter(prefix="/integrations", tags=["integrations"])

    @router.get("", response_model=IntegrationResponse)
    def get_integrations():
        data = campaigns_repo.get_integrations()
        return serialize_integrations(data)

    @router.put("", response_model=IntegrationResponse)
    def put_integrations(body: IntegrationUpdate):
        apify_enc = None
        if body.apify_token:
            try:
                apify_enc = encrypt_secret(body.apify_token)
            except RuntimeError:
                logger.exception("Failed to encrypt integration secret")
                raise HTTPException(status_code=500, detail="Internal server error") from None
        # If no new token provided, we pass None so repo preserves existing enc value

        campaigns_repo.save_integrations(
            apify_token_enc=apify_enc,
            scraper_sources=body.scraper_sources,
        )

        data = campaigns_repo.get_integrations()
        return serialize_integrations(data)

    return router
