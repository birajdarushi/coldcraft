"""Tests for the email-OTP login service and API endpoints."""
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet


def _fresh_db_env():
    """Point the app at a throwaway SQLite DB and a fresh signing key, and
    rebuild the cached engine so it binds to that DB."""
    os.environ["GTM_SMTP_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    db_file = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_URL"] = "sqlite:///" + db_file
    from coldcraft.db import session as db_session

    db_session._engine = None
    db_session._SessionLocal = None
    db_session.init_db()
    return db_file


class OtpServiceTests(unittest.TestCase):
    def setUp(self):
        self.db_file = _fresh_db_env()
        from coldcraft.auth import service

        self.service = service
        # Capture the generated code instead of sending a real email.
        self.captured = {}
        self._orig_send = service._send_otp_email
        service._send_otp_email = lambda email, code: self.captured.update(
            email=email, code=code
        )

    def tearDown(self):
        self.service._send_otp_email = self._orig_send
        try:
            os.remove(self.db_file)
        except OSError:
            pass

    def _request(self, email="user@example.com"):
        res = self.service.request_otp(email)
        return res, self.captured["code"]

    def test_request_generates_six_digit_code_and_expiry(self):
        res, code = self._request()
        self.assertTrue(res["ok"])
        self.assertEqual(res["expires_in"], self.service.CODE_TTL_MINUTES * 60)
        self.assertRegex(code, r"^\d{6}$")

    def test_code_is_stored_hashed_not_plaintext(self):
        _, code = self._request("hash@example.com")
        from coldcraft.db.models import AuthOTP
        from coldcraft.db.session import get_session

        with get_session() as s:
            row = s.query(AuthOTP).filter(AuthOTP.email == "hash@example.com").one()
            self.assertNotIn(code, row.code_hash)
            self.assertEqual(len(row.code_hash), 64)  # sha256 hex

    def test_verify_correct_code_returns_valid_token(self):
        _, code = self._request("ok@example.com")
        token = self.service.verify_otp("ok@example.com", code)
        self.assertEqual(self.service.verify_token(token), "ok@example.com")

    def test_email_is_normalized(self):
        _, code = self._request("  MixedCase@Example.com  ")
        token = self.service.verify_otp("mixedcase@example.com", code)
        self.assertEqual(self.service.verify_token(token), "mixedcase@example.com")

    def test_wrong_code_rejected_and_counts_attempt(self):
        self._request("bad@example.com")
        with self.assertRaises(ValueError):
            self.service.verify_otp("bad@example.com", "000000")
        from coldcraft.db.models import AuthOTP
        from coldcraft.db.session import get_session

        with get_session() as s:
            row = s.query(AuthOTP).filter(AuthOTP.email == "bad@example.com").one()
            self.assertEqual(row.attempts, 1)
            self.assertEqual(row.consumed, 0)

    def test_locks_after_max_attempts(self):
        _, code = self._request("lock@example.com")
        for _ in range(self.service.MAX_ATTEMPTS):
            with self.assertRaises(ValueError):
                self.service.verify_otp("lock@example.com", "111111")
        # Even the correct code is now rejected — the row is locked.
        with self.assertRaises(ValueError) as ctx:
            self.service.verify_otp("lock@example.com", code)
        self.assertIn("Too many", str(ctx.exception))

    def test_expired_code_rejected(self):
        _, code = self._request("exp@example.com")
        from coldcraft.db.models import AuthOTP
        from coldcraft.db.session import get_session

        with get_session() as s:
            row = s.query(AuthOTP).filter(AuthOTP.email == "exp@example.com").one()
            row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            s.commit()
        with self.assertRaises(ValueError) as ctx:
            self.service.verify_otp("exp@example.com", code)
        self.assertIn("expired", str(ctx.exception).lower())

    def test_code_is_single_use(self):
        _, code = self._request("once@example.com")
        self.service.verify_otp("once@example.com", code)
        with self.assertRaises(ValueError):
            self.service.verify_otp("once@example.com", code)

    def test_new_request_invalidates_previous_code(self):
        _, code1 = self._request("rot@example.com")
        _, code2 = self._request("rot@example.com")
        self.assertNotEqual(code1, code2)
        with self.assertRaises(ValueError):
            self.service.verify_otp("rot@example.com", code1)
        # The newest code still works.
        token = self.service.verify_otp("rot@example.com", code2)
        self.assertEqual(self.service.verify_token(token), "rot@example.com")

    def test_invalid_email_rejected(self):
        for bad in ["", "nope", "no@domain", "a@b"]:
            with self.assertRaises(ValueError):
                self.service.request_otp(bad)

    def test_garbage_token_is_rejected(self):
        self.assertIsNone(self.service.verify_token("not-a-token"))
        self.assertIsNone(self.service.verify_token(""))
        # A validly-signed token whose payload lacks the login prefix is rejected.
        forged = self.service._fernet().encrypt(b"evil@example.com").decode()
        self.assertIsNone(self.service.verify_token(forged))

    def test_delete_account_removes_codes(self):
        self._request("del@example.com")
        out = self.service.delete_account("del@example.com")
        self.assertTrue(out["ok"])
        self.assertGreaterEqual(out["deleted"], 1)
        from coldcraft.db.models import AuthOTP
        from coldcraft.db.session import get_session

        with get_session() as s:
            self.assertEqual(
                s.query(AuthOTP).filter(AuthOTP.email == "del@example.com").count(), 0
            )

    def test_otp_reuses_saved_campaign_smtp(self):
        # When a campaign SMTP config is saved, OTP mail uses it (not env).
        self.service._send_otp_email = self._orig_send  # exercise real resolver
        from coldcraft.infrastructure.persistence.repositories import (
            SQLAlchemyCampaignRepository,
        )

        SQLAlchemyCampaignRepository().save_user_config(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="u",
            smtp_pass_enc="x",
            from_email="from@example.com",
            from_name="From",
            delivery_mode="smtp",
        )
        captured = {}

        class FakeClient:
            def __init__(self, config):
                captured["config"] = config

            def send(self, **kw):
                captured.update(kw)
                return "<id>"

        orig_client = self.service.SMTPClient
        self.service.SMTPClient = FakeClient
        try:
            self.service.request_otp("recipient@example.com")
        finally:
            self.service.SMTPClient = orig_client

        self.assertEqual(captured["config"].smtp_host, "smtp.example.com")
        self.assertEqual(captured["to_email"], "recipient@example.com")

    def test_send_failure_surfaces_as_runtime_error(self):
        def boom(email, code):
            raise RuntimeError("smtp down")

        self.service._send_otp_email = boom
        with self.assertRaises(RuntimeError):
            self.service.request_otp("fail@example.com")


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        self.db_file = _fresh_db_env()
        from fastapi.testclient import TestClient
        from coldcraft.api.app import app
        from coldcraft.auth import service

        self.service = service
        self.captured = {}
        self._orig_send = service._send_otp_email
        service._send_otp_email = lambda email, code: self.captured.update(code=code)
        self.client_cm = TestClient(app)
        self.client = self.client_cm.__enter__()

    def tearDown(self):
        self.client_cm.__exit__(None, None, None)
        self.service._send_otp_email = self._orig_send
        try:
            os.remove(self.db_file)
        except OSError:
            pass

    def test_full_login_flow(self):
        r = self.client.post(
            "/api/v1/auth/request-otp", json={"email": "api@example.com"}
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])

        r = self.client.post(
            "/api/v1/auth/verify-otp",
            json={"email": "api@example.com", "code": self.captured["code"]},
        )
        self.assertEqual(r.status_code, 200)
        token = r.json()["token"]

        r = self.client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["email"], "api@example.com")

    def test_me_requires_auth(self):
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 401)
        self.assertEqual(
            self.client.get(
                "/api/v1/auth/me", headers={"Authorization": "Bearer garbage"}
            ).status_code,
            401,
        )

    def test_verify_wrong_code_returns_400(self):
        self.client.post("/api/v1/auth/request-otp", json={"email": "w@example.com"})
        r = self.client.post(
            "/api/v1/auth/verify-otp",
            json={"email": "w@example.com", "code": "000000"},
        )
        self.assertEqual(r.status_code, 400)

    def test_delete_account_requires_auth_then_succeeds(self):
        self.assertEqual(self.client.delete("/api/v1/auth/account").status_code, 401)

        self.client.post("/api/v1/auth/request-otp", json={"email": "d@example.com"})
        token = self.client.post(
            "/api/v1/auth/verify-otp",
            json={"email": "d@example.com", "code": self.captured["code"]},
        ).json()["token"]
        r = self.client.delete(
            "/api/v1/auth/account", headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])


if __name__ == "__main__":
    unittest.main()
