"""
Unit tests for the sliding-window rate limiter.

Tests:
  1. RateLimiter allows calls within the limit.
  2. RateLimiter blocks at exactly the limit.
  3. Window slides — old entries expire and new calls are allowed.
  4. check_send_rate_limit raises HTTP 429 when exceeded.
  5. check_send_rate_limit uses IP key for guests, user email for auth.
  6. Unsubscribe edge case: domain with >=1 read mail is excluded from scan.
"""
import time
import unittest
from unittest.mock import MagicMock, patch


class TestRateLimiter(unittest.TestCase):
    def _make_limiter(self):
        from coldcraft.api.middleware.rate_limit import RateLimiter
        return RateLimiter()

    def test_allows_within_limit(self):
        limiter = self._make_limiter()
        for _ in range(5):
            self.assertTrue(limiter.is_allowed("key1", limit=5, window_seconds=60))

    def test_blocks_at_limit(self):
        limiter = self._make_limiter()
        for _ in range(5):
            limiter.is_allowed("key2", limit=5, window_seconds=60)
        # 6th call must be blocked
        self.assertFalse(limiter.is_allowed("key2", limit=5, window_seconds=60))

    def test_window_slides(self):
        """After the window expires, calls should be allowed again."""
        limiter = self._make_limiter()
        # Exhaust limit
        for _ in range(3):
            limiter.is_allowed("key3", limit=3, window_seconds=1)
        self.assertFalse(limiter.is_allowed("key3", limit=3, window_seconds=1))
        # Fast-forward past the window
        time.sleep(1.1)
        # Should be allowed again
        self.assertTrue(limiter.is_allowed("key3", limit=3, window_seconds=1))

    def test_remaining_decrements(self):
        limiter = self._make_limiter()
        self.assertEqual(limiter.remaining("key4", limit=5, window_seconds=60), 5)
        limiter.is_allowed("key4", limit=5, window_seconds=60)
        self.assertEqual(limiter.remaining("key4", limit=5, window_seconds=60), 4)

    def test_different_keys_independent(self):
        limiter = self._make_limiter()
        for _ in range(3):
            limiter.is_allowed("keyA", limit=3, window_seconds=60)
        # keyA exhausted, keyB still fresh
        self.assertFalse(limiter.is_allowed("keyA", limit=3, window_seconds=60))
        self.assertTrue(limiter.is_allowed("keyB", limit=3, window_seconds=60))

    def test_retry_after_positive_when_exhausted(self):
        limiter = self._make_limiter()
        for _ in range(5):
            limiter.is_allowed("key5", limit=5, window_seconds=60)
        retry = limiter.retry_after("key5", window_seconds=60)
        self.assertGreater(retry, 0)
        self.assertLessEqual(retry, 61)


class TestCheckSendRateLimit(unittest.TestCase):
    def _make_request(self, ip="1.2.3.4", auth_header=None):
        req = MagicMock()
        req.client.host = ip
        headers = {}
        if auth_header:
            headers["authorization"] = auth_header
        req.headers.get = lambda k, d="": headers.get(k, d)
        return req

    def test_guest_429_after_hard_limit(self):
        """Guest should be blocked after GUEST_HARD_LIMIT sends."""
        # Reset the module-level limiter between test runs by patching
        from coldcraft.api.middleware import rate_limit as rl
        from coldcraft.api.middleware.rate_limit import check_send_rate_limit
        from fastapi import HTTPException

        original_limiter = rl._limiter
        rl._limiter = rl.RateLimiter()
        try:
            req = self._make_request(ip="9.9.9.9")
            # Exhaust the hard limit (5 for guests)
            for _ in range(5):
                check_send_rate_limit(req, user_email=None,
                                      guest_limit=5, auth_limit=50)
            # 6th should raise 429
            with self.assertRaises(HTTPException) as ctx:
                check_send_rate_limit(req, user_email=None,
                                      guest_limit=5, auth_limit=50)
            self.assertEqual(ctx.exception.status_code, 429)
        finally:
            rl._limiter = original_limiter

    def test_auth_user_uses_email_key(self):
        """Authenticated users should be keyed by email, not IP."""
        from coldcraft.api.middleware import rate_limit as rl
        from coldcraft.api.middleware.rate_limit import check_send_rate_limit
        from fastapi import HTTPException

        original_limiter = rl._limiter
        rl._limiter = rl.RateLimiter()
        try:
            req = self._make_request(ip="1.1.1.1")
            user = "test@example.com"
            # Exhaust with small limit
            for _ in range(3):
                check_send_rate_limit(req, user_email=user,
                                      guest_limit=5, auth_limit=3)
            with self.assertRaises(HTTPException) as ctx:
                check_send_rate_limit(req, user_email=user,
                                      guest_limit=5, auth_limit=3)
            self.assertEqual(ctx.exception.status_code, 429)
            # A different user on same IP should still be OK
            check_send_rate_limit(req, user_email="other@example.com",
                                  guest_limit=5, auth_limit=3)
        finally:
            rl._limiter = original_limiter

    def test_configurable_limit_clamped_to_hard_limit(self):
        """Passing a guest_limit above GUEST_HARD_LIMIT must be clamped down."""
        from coldcraft.api.middleware import rate_limit as rl
        from coldcraft.api.middleware.rate_limit import check_send_rate_limit, GUEST_HARD_LIMIT
        from fastapi import HTTPException

        original_limiter = rl._limiter
        rl._limiter = rl.RateLimiter()
        try:
            req = self._make_request(ip="7.7.7.7")
            # Exhaust at HARD LIMIT even if caller asks for 100
            for _ in range(GUEST_HARD_LIMIT):
                check_send_rate_limit(req, user_email=None, guest_limit=100)
            with self.assertRaises(HTTPException):
                check_send_rate_limit(req, user_email=None, guest_limit=100)
        finally:
            rl._limiter = original_limiter


class TestUnsubscribeDomainEdgeCase(unittest.TestCase):
    """
    Domain-level read check in scan_unsubscribed_targets.
    If ANY email from a domain is read, the whole domain should be skipped.
    """

    def test_domain_with_one_read_skipped(self):
        """
        Setup: two threads from example.com — one unread (old), one read.
        Expected: example.com does NOT appear in scan results.
        """
        from coldcraft.infrastructure.gmail_client import GmailClient
        client = GmailClient()

        # Thread listing: two threads from same domain
        unread_thread = {"id": "th1", "threadId": "th1"}
        read_thread_same_domain = {"id": "th2", "threadId": "th2"}

        def mock_list_threads(access_token, query="", max_results=100):
            if "is:unread" in query and "is:read" not in query:
                return [unread_thread]
            if "is:read" in query:
                return [read_thread_same_domain]
            return []

        # Parse thread returns email addresses from example.com for both
        def mock_parse(access_token, thread_id):
            base = {
                "th1": {
                    "id": "th1", "from_email": "newsletter@example.com",
                    "from_name": "Newsletter", "subject": "Unread",
                    "snippet": "...", "timestamp": "2025-01-01T00:00:00Z",
                    "body": "", "status": "applied",
                    "list_unsubscribe": "<mailto:unsub@example.com>",
                },
                "th2": {
                    "id": "th2", "from_email": "news@example.com",
                    "from_name": "News", "subject": "Read One",
                    "snippet": "...", "timestamp": "2025-02-01T00:00:00Z",
                    "body": "", "status": "applied",
                    "list_unsubscribe": None,
                },
            }
            return base.get(thread_id, {})

        with patch.object(client, "list_threads", side_effect=mock_list_threads), \
             patch.object(client, "get_parsed_thread", side_effect=mock_parse):
            results = client.scan_unsubscribed_targets("mock_token")

        # example.com should be excluded because th2 (read) shares the domain
        domains = {r["from_email"].split("@")[-1] for r in results}
        self.assertNotIn("example.com", domains,
                         "Domain with at least one read email should be excluded")

    def test_domain_all_unread_included(self):
        """
        All emails from a domain are unread — should appear in candidates.
        Uses _make_request patching to avoid the mock_ short-circuit path.
        """
        import coldcraft.infrastructure.gmail_client as gcm
        from coldcraft.infrastructure.gmail_client import GmailClient

        client = GmailClient()
        REAL_TOKEN = "real_token_xyz"  # does NOT start with "mock_"

        # Minimal thread list response
        thread_list_response = {"threads": [{"id": "th3", "threadId": "th3"}]}

        # Full thread detail response for th3 (unread, promo@other.com, 35 days old)
        import time as _time
        old_ts = int((_time.time() - 36 * 86400) * 1000)
        thread_detail_response = {
            "messages": [{
                "id": "msg3",
                "labelIds": ["INBOX", "UNREAD"],
                "payload": {
                    "headers": [
                        {"name": "From", "value": "Promo <promo@other.com>"},
                        {"name": "Subject", "value": "Sale"},
                        {"name": "Date", "value": "Mon, 01 Jan 2025 00:00:00 +0000"},
                        {"name": "List-Unsubscribe", "value": "<https://other.com/unsub>"},
                    ],
                    "body": {"data": ""},
                    "parts": [],
                },
                "internalDate": str(old_ts),
                "snippet": "Great sale",
            }]
        }
        # No read emails for this domain
        empty_response = {"threads": []}

        call_count = [0]

        def fake_make_request(url, headers=None):
            call_count[0] += 1
            if "threads?q=is:unread" in url:
                return thread_list_response
            if "threads?q=from%3Aother.com" in url or "from:other.com" in url:
                # is:read check for domain — return empty (no read mails)
                return empty_response
            if "threads/th3" in url:
                return thread_detail_response
            return {}

        with patch.object(gcm, "_make_request", side_effect=fake_make_request):
            results = client.scan_unsubscribed_targets(REAL_TOKEN)

        domains = {r["from_email"].split("@")[-1] for r in results}
        self.assertIn("other.com", domains,
                      "Domain with no read emails should be included in candidates")


if __name__ == "__main__":
    unittest.main()
