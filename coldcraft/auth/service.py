"""
OTP login service.

Flow:
  1. request_otp(email)  -> generates a 6-digit code, stores it hashed with a
     short expiry, and emails the code via the configured SMTP transport.
  2. verify_otp(email, code) -> validates the code and returns a signed session
     token (Fernet) the client stores and sends back as a Bearer credential.
  3. verify_token(token) -> returns the email for a valid, unexpired token.

Codes are never stored or logged in plaintext. Tokens are signed+timestamped
with the same bootstrap key already used for SMTP secret encryption.
"""

import hashlib
import logging
import os
import secrets as _secrets
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken

from ..config.secrets import get_smtp_encryption_key
from ..db.models import AuthOTP
from ..db.session import get_session
from ..smtp_client import SMTPClient

logger = logging.getLogger(__name__)

CODE_TTL_MINUTES = 10
MAX_ATTEMPTS = 5
TOKEN_TTL_SECONDS = 7 * 24 * 3600  # 7 days
_TOKEN_PREFIX = "cclogin:"


# --------------------------------------------------------------------------- #
# Codes
# --------------------------------------------------------------------------- #
def _hash_code(email: str, code: str) -> str:
    # Bind the hash to the email so a code is only valid for the address it was sent to.
    return hashlib.sha256(f"{email.lower()}:{code}".encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def request_otp(email: str) -> dict:
    email = email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("A valid email address is required.")

    code = f"{_secrets.randbelow(1_000_000):06d}"
    now = _now()
    with get_session() as s:
        # Invalidate any outstanding codes for this email, then store the new one.
        for row in s.query(AuthOTP).filter(AuthOTP.email == email, AuthOTP.consumed == 0).all():
            row.consumed = 1
        s.add(
            AuthOTP(
                email=email,
                code_hash=_hash_code(email, code),
                expires_at=now + timedelta(minutes=CODE_TTL_MINUTES),
                attempts=0,
                consumed=0,
                created_at=now,
            )
        )
        s.commit()

    _send_otp_email(email, code)
    return {"ok": True, "expires_in": CODE_TTL_MINUTES * 60}


def verify_otp(email: str, code: str) -> str:
    email = email.strip().lower()
    code = (code or "").strip()
    with get_session() as s:
        row = (
            s.query(AuthOTP)
            .filter(AuthOTP.email == email, AuthOTP.consumed == 0)
            .order_by(AuthOTP.created_at.desc())
            .first()
        )
        if row is None:
            raise ValueError("No active code. Request a new one.")
        if row.expires_at.replace(tzinfo=timezone.utc) < _now():
            row.consumed = 1
            s.commit()
            raise ValueError("Code expired. Request a new one.")
        if row.attempts >= MAX_ATTEMPTS:
            row.consumed = 1
            s.commit()
            raise ValueError("Too many attempts. Request a new code.")

        if not _secrets.compare_digest(row.code_hash, _hash_code(email, code)):
            row.attempts += 1
            s.commit()
            raise ValueError("Incorrect code.")

        row.consumed = 1
        s.commit()

    return issue_token(email)


def delete_account(email: str) -> dict:
    """Remove all login artifacts for an email. The token is stateless, so the
    client must also discard it; any existing token expires on its own TTL."""
    email = email.strip().lower()
    with get_session() as s:
        deleted = s.query(AuthOTP).filter(AuthOTP.email == email).delete()
        s.commit()
    logger.info("Deleted account login artifacts for %s (%d code rows)", email, deleted)
    return {"ok": True, "deleted": deleted}


# --------------------------------------------------------------------------- #
# Session tokens (stateless, signed)
# --------------------------------------------------------------------------- #
def _fernet() -> Fernet:
    key = get_smtp_encryption_key()
    if not key:
        raise RuntimeError("GTM_SMTP_ENCRYPTION_KEY not set — cannot sign login tokens.")
    return Fernet(key.encode())


def issue_token(email: str) -> str:
    return _fernet().encrypt(f"{_TOKEN_PREFIX}{email.lower()}".encode()).decode()


def verify_token(token: str) -> str | None:
    if not token:
        return None
    try:
        raw = _fernet().decrypt(token.encode(), ttl=TOKEN_TTL_SECONDS).decode()
    except (InvalidToken, Exception):
        return None
    if not raw.startswith(_TOKEN_PREFIX):
        return None
    return raw[len(_TOKEN_PREFIX):]


# --------------------------------------------------------------------------- #
# Email delivery
# --------------------------------------------------------------------------- #
class _OTPMailConfig:
    """Lightweight SMTP config built from environment for transactional OTP mail."""

    def __init__(self):
        self.from_email = os.environ.get("FROM_EMAIL", "coldcraft@localhost")
        self.from_name = os.environ.get("FROM_NAME", "Coldcraft")
        self.smtp_host = os.environ.get("SMTP_HOST", "localhost")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "1025"))
        self.smtp_user = os.environ.get("SMTP_USER", "")
        self.smtp_pass_enc = os.environ.get("SMTP_PASS_ENC", "")
        self.tracking_domain = None
        # Default to mailpit capture when no real SMTP password is configured.
        self.delivery_mode = os.environ.get(
            "OTP_DELIVERY_MODE",
            "smtp" if self.smtp_pass_enc else "mailpit",
        )


def _resolve_mail_config():
    """Prefer the SMTP config already saved in Settings (e.g. the live Gmail
    sender used for campaigns) so login codes go out for real with no extra
    setup. Fall back to env config (Mailpit in dev) when nothing is saved."""
    try:
        from ..infrastructure.persistence.repositories import (
            SQLAlchemyCampaignRepository,
        )

        cfg = SQLAlchemyCampaignRepository().get_user_config()
        if cfg and getattr(cfg, "smtp_host", None):
            return cfg
    except Exception:
        logger.exception("Could not load saved SMTP config; using env fallback")
    return _OTPMailConfig()


def _send_otp_email(email: str, code: str) -> None:
    subject = f"Your Coldcraft login code: {code}"
    text = (
        f"Your Coldcraft login code is {code}\n\n"
        f"It expires in {CODE_TTL_MINUTES} minutes. If you didn't request this, "
        f"you can ignore this email."
    )
    html = f"""\
<div style="font-family:ui-monospace,Consolas,monospace;background:#0A0A0A;color:#FAFAFA;padding:40px;text-align:center">
  <div style="font-size:18px;font-weight:800;letter-spacing:-0.5px;text-transform:uppercase">Coldcraft</div>
  <div style="font-size:11px;letter-spacing:3px;color:#A3A3A3;margin-top:4px">GTM·ENGINE</div>
  <p style="margin:28px 0 8px;color:#A3A3A3;font-size:13px">Your login code</p>
  <div style="font-size:40px;font-weight:700;letter-spacing:10px;color:#3B82F6">{code}</div>
  <p style="margin-top:24px;color:#A3A3A3;font-size:12px">Expires in {CODE_TTL_MINUTES} minutes. Ignore this email if you didn't request it.</p>
</div>"""
    try:
        SMTPClient(_resolve_mail_config()).send(
            to_email=email,
            to_name=email.split("@")[0],
            subject=subject,
            body_html=html,
            body_text=text,
        )
        logger.info("OTP email dispatched to %s", email)
    except Exception:
        # Never leak whether an address exists / SMTP internals to the caller.
        logger.exception("Failed to send OTP email to %s", email)
        raise RuntimeError("Could not send the login email. Try again shortly.")
