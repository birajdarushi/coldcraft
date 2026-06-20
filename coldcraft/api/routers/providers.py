import logging
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...config.secrets import encrypt_secret

logger = logging.getLogger(__name__)


# Providers whose API keys power features in the app. Add new ones here.
PROVIDERS = {
    "gemini": {
        "label": "Google Gemini",
        "feature": "Email drafting · self-review revision · follow-ups · intel",
        "docs": "https://aistudio.google.com/apikey",
        "env": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "enc_field": "gemini_api_key_enc",
    },
    "apify": {
        "label": "Apify",
        "feature": "Job scraping (LinkedIn / careers sources)",
        "docs": "https://console.apify.com/account/integrations",
        "env": ["APIFY_TOKEN"],
        "enc_field": "apify_token_enc",
    },
}


class ProviderUpdate(BaseModel):
    provider: str
    api_key: str  # plain on input only; encrypted server-side, never returned


class ProviderStatus(BaseModel):
    provider: str
    label: str
    feature: str
    docs: str
    configured: bool
    source: str | None  # "env" | "stored" | None


class ProvidersResponse(BaseModel):
    providers: list[ProviderStatus]


def get_providers_router(campaigns_repo) -> APIRouter:
    """API-key management for every provider the app powers features with.

    - GET returns status only (configured? from env or stored?) — never a key.
    - PUT accepts a plain key for one provider, encrypts it, and persists it.
    """
    router = APIRouter(prefix="/providers", tags=["providers"])

    @router.get("", response_model=ProvidersResponse)
    def list_providers():
        integ = campaigns_repo.get_integrations() or {}
        out = []
        for key, meta in PROVIDERS.items():
            env_set = any(os.environ.get(e) for e in meta["env"])
            stored = bool(integ.get(meta["enc_field"]))
            source = "env" if env_set else ("stored" if stored else None)
            out.append(
                ProviderStatus(
                    provider=key,
                    label=meta["label"],
                    feature=meta["feature"],
                    docs=meta["docs"],
                    configured=env_set or stored,
                    source=source,
                )
            )
        return {"providers": out}

    @router.put("", response_model=ProvidersResponse)
    def set_provider(body: ProviderUpdate):
        meta = PROVIDERS.get(body.provider)
        if not meta:
            raise HTTPException(status_code=422, detail=f"Unknown provider '{body.provider}'")
        if not body.api_key or not body.api_key.strip():
            raise HTTPException(status_code=422, detail="api_key is required")
        try:
            enc = encrypt_secret(body.api_key.strip())
        except RuntimeError:
            logger.exception("Failed to encrypt provider key")
            raise HTTPException(status_code=500, detail="Encryption key not configured on server") from None

        campaigns_repo.save_integrations(**{meta["enc_field"]: enc})
        return list_providers()

    return router
