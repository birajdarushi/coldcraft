"""Email-OTP login endpoints (mounted under /api/v1/auth)."""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from ...auth import service as auth_service

logger = logging.getLogger(__name__)


class RequestOTPBody(BaseModel):
    email: str


class VerifyOTPBody(BaseModel):
    email: str
    code: str


def get_current_email(authorization: str | None = Header(default=None)) -> str:
    """Dependency: resolve the logged-in email from a Bearer token or 401."""
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    email = auth_service.verify_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return email


def get_auth_router() -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["auth"])

    @router.post("/request-otp")
    def request_otp(body: RequestOTPBody):
        try:
            return auth_service.request_otp(str(body.email))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e))

    @router.post("/verify-otp")
    def verify_otp(body: VerifyOTPBody):
        try:
            token = auth_service.verify_otp(str(body.email), body.code)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"token": token, "email": str(body.email).strip().lower()}

    @router.get("/me")
    def me(email: str = Depends(get_current_email)):
        return {"email": email}

    @router.delete("/account")
    def delete_account(email: str = Depends(get_current_email)):
        return auth_service.delete_account(email)

    return router
