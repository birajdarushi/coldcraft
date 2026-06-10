"""
SMTP Client — GTM Engine Mailer Agent
Constitution §6.1 (config requirements), §6.4 (header hygiene), §6.5 (bounce handling).
Uses smtplib with TLS. Credentials loaded fresh per send — never cached in memory.
"""

import smtplib
import uuid
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, make_msgid
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class SMTPClient:

    def __init__(self, config):
        self.config = config
        self._smtp = None

    def send(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        body_html: str,
        body_text: str,
    ) -> str:
        """
        Send email. Returns Message-ID on success.
        Raises on any SMTP error — caller handles retry logic.
        """
        password = self._decrypt_password(self.config.smtp_pass_enc)

        msg = self._build_message(
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
        )

        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.config.smtp_user, password)
                server.sendmail(
                    self.config.from_email,
                    [to_email],
                    msg.as_string()
                )
                message_id = msg["Message-ID"]
                logger.info(f"SMTP send success: to={to_email} message_id={message_id}")
                return message_id

        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"Hard bounce (RCPT refused): {to_email} — {e}")
            raise HardBounceError(f"Recipient refused: {to_email}") from e
        except smtplib.SMTPSenderRefused as e:
            logger.error(f"Sender refused: {self.config.from_email} — {e}")
            raise SMTPConfigError(f"Sender refused — check SMTP config") from e
        except smtplib.SMTPAuthenticationError as e:
            logger.error("SMTP auth failed — check App Password")
            raise SMTPConfigError("SMTP authentication failed") from e
        except smtplib.SMTPException as e:
            logger.warning(f"Soft SMTP error: {e}")
            raise SoftBounceError(str(e)) from e
        finally:
            # Explicitly clear password from local scope
            password = None  # noqa

    def _build_message(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        body_html: str,
        body_text: str,
    ) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")

        # Constitution §6.4: Message-ID from own domain
        msg["Message-ID"] = make_msgid(domain=self.config.from_email.split("@")[1])
        msg["From"] = formataddr((self.config.from_name, self.config.from_email))
        msg["To"] = formataddr((to_name, to_email))
        msg["Reply-To"] = self.config.from_email  # must match From exactly
        msg["Subject"] = subject

        # Constitution §6.4: List-Unsubscribe header
        tracking_domain = getattr(self.config, "tracking_domain", None)
        if tracking_domain:
            unsubscribe_id = str(uuid.uuid4())
            msg["List-Unsubscribe"] = f"<https://{tracking_domain}/unsubscribe/{unsubscribe_id}>"
            msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

        # Plain text first (better deliverability)
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        return msg

    def _decrypt_password(self, encrypted_pass: str) -> str:
        """
        Constitution §6.1: decrypt SMTP password at send time.
        Key must be loaded from environment — never hardcoded.
        """
        from .config.secrets import get_smtp_encryption_key
        key = get_smtp_encryption_key()
        if not key:
            raise SMTPConfigError(
                "GTM_SMTP_ENCRYPTION_KEY not set. "
                "Cannot decrypt SMTP credentials."
            )
        try:
            f = Fernet(key.encode())
            return f.decrypt(encrypted_pass.encode()).decode()
        except Exception as e:
            raise SMTPConfigError(
                "Failed to decrypt SMTP password. "
                "Constitution §6.1 HARD LIMIT: cannot send with plaintext or invalid credentials."
            ) from e

    def verify_dns(self, domain: str) -> dict:
        """
        Constitution §6.2: verify SPF, DKIM, DMARC before first send.
        Returns dict of check results — caller decides whether to warn or block.
        """
        import dns.resolver

        results = {
            "domain": domain,
            "spf": False,
            "dkim": False,
            "dmarc": False,
            "warnings": []
        }

        # SPF check
        try:
            answers = dns.resolver.resolve(domain, "TXT")
            for rdata in answers:
                if "v=spf1" in str(rdata):
                    results["spf"] = True
                    break
        except Exception:
            results["warnings"].append(f"No SPF record found for {domain}")

        # DKIM check (common selector: 'default' or 'google')
        for selector in ["default", "google", "mail", "dkim"]:
            try:
                dns.resolver.resolve(f"{selector}._domainkey.{domain}", "TXT")
                results["dkim"] = True
                break
            except Exception:
                continue
        if not results["dkim"]:
            results["warnings"].append(f"No DKIM record found for {domain}")

        # DMARC check
        try:
            dns.resolver.resolve(f"_dmarc.{domain}", "TXT")
            results["dmarc"] = True
        except Exception:
            results["warnings"].append(f"No DMARC record found for {domain}")

        return results


class SMTPConfigError(Exception): pass
class HardBounceError(Exception): pass
class SoftBounceError(Exception): pass
