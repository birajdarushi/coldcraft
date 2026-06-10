from fastapi import APIRouter, HTTPException

from ...config.secrets import encrypt_smtp_password
from ..schemas import ConfigResponse, ConfigUpdate, serialize_config


def get_config_router(campaigns_repo) -> APIRouter:
    """Config router for SMTP and tracking settings.

    - GET returns redacted view (no password material ever).
    - PUT accepts plain smtp_pass (required on first create), encrypts server-side, persists.
    - Single-row singleton config (upsert).
    """
    router = APIRouter(prefix="/config", tags=["config"])

    @router.get("", response_model=ConfigResponse)
    def get_config():
        cfg = campaigns_repo.get_user_config()
        if not cfg:
            raise HTTPException(
                status_code=404,
                detail="No SMTP config found. Use PUT to initialize (password will be encrypted server-side).",
            )
        return serialize_config(cfg)

    @router.put("", response_model=ConfigResponse)
    def put_config(body: ConfigUpdate):
        if not body.smtp_pass:
            existing = campaigns_repo.get_user_config()
            if not existing:
                raise HTTPException(
                    status_code=422,
                    detail="smtp_pass is required when creating initial config",
                )
            pass_enc = existing.smtp_pass_enc
        else:
            try:
                pass_enc = encrypt_smtp_password(body.smtp_pass)
            except RuntimeError as e:
                raise HTTPException(status_code=500, detail=str(e)) from e

        campaigns_repo.save_user_config(
            smtp_host=body.smtp_host,
            smtp_port=body.smtp_port,
            smtp_user=body.smtp_user,
            smtp_pass_enc=pass_enc,
            from_email=body.from_email,
            from_name=body.from_name,
            tracking_domain=body.tracking_domain,
        )

        cfg = campaigns_repo.get_user_config()
        return serialize_config(cfg)

    return router

