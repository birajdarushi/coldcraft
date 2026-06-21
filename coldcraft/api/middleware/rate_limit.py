"""
rate_limit.py — Sliding-window in-memory rate limiter for SMTP send endpoints.

Hard limits (per MAILER_CONSTITUTION):
  - Guest (unauthenticated / IP-keyed): 5 sends per hour
  - Authenticated user:                50 sends per day

These are enforced here and CANNOT be exceeded regardless of config API settings.
Config API can only lower these floors, never raise them above the HARD LIMITs.

Thread-safety note: uses a simple dict + deque which is safe for single-process
FastAPI (uvicorn single worker). For multi-worker / multi-process deployments,
replace the in-memory store with Redis.
"""
import logging
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

# ── HARD LIMITS (per MAILER_CONSTITUTION) ───────────────────────────────────
GUEST_HARD_LIMIT = 5           # sends per window
GUEST_WINDOW_SECONDS = 3600   # 1 hour

AUTH_HARD_LIMIT = 200          # sends per window (absolute ceiling)
AUTH_WINDOW_SECONDS = 86400   # 24 hours

# Default operational limits (configurable via config API, clamped to hard limits)
GUEST_DEFAULT_LIMIT = 5
AUTH_DEFAULT_LIMIT = 50


class RateLimiter:
    """
    Sliding-window in-memory rate limiter.

    Stores timestamps of recent calls per key in a deque.
    Old entries outside the window are evicted on each check.
    """

    def __init__(self):
        # key -> deque of float (unix timestamps)
        self._windows: dict[str, deque] = defaultdict(deque)

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        """
        Return True if the call is within the rate limit, False if exceeded.
        Advances the sliding window by evicting stale entries.
        """
        now = time.monotonic()
        cutoff = now - window_seconds
        dq = self._windows[key]

        # Evict entries older than the window
        while dq and dq[0] < cutoff:
            dq.popleft()

        if len(dq) >= limit:
            return False

        dq.append(now)
        return True

    def remaining(self, key: str, limit: int, window_seconds: int) -> int:
        """Return how many more calls are allowed in the current window."""
        now = time.monotonic()
        cutoff = now - window_seconds
        dq = self._windows[key]
        while dq and dq[0] < cutoff:
            dq.popleft()
        return max(0, limit - len(dq))

    def retry_after(self, key: str, window_seconds: int) -> int:
        """Seconds until the oldest entry in the window expires."""
        dq = self._windows.get(key)
        if not dq:
            return 0
        now = time.monotonic()
        oldest = dq[0]
        return max(0, int(window_seconds - (now - oldest)) + 1)


# Module-level singleton — shared across all requests in the same process
_limiter = RateLimiter()


def check_send_rate_limit(
    request: Request,
    user_email: str | None = None,
    guest_limit: int = GUEST_DEFAULT_LIMIT,
    auth_limit: int = AUTH_DEFAULT_LIMIT,
) -> None:
    """
    Call this at the start of any send endpoint.

    - If the caller has a valid auth token (user_email is set): enforces per-user
      daily limit (clamped to AUTH_HARD_LIMIT).
    - Otherwise: enforces per-IP hourly limit (clamped to GUEST_HARD_LIMIT).

    Raises HTTP 429 with Retry-After header if the limit is exceeded.
    """
    # Clamp configurable limits to hard limits
    effective_guest_limit = min(guest_limit, GUEST_HARD_LIMIT)
    effective_auth_limit = min(auth_limit, AUTH_HARD_LIMIT)

    client_ip = request.client.host if request.client else "unknown"

    if user_email:
        key = f"user:{user_email}"
        limit = effective_auth_limit
        window = AUTH_WINDOW_SECONDS
        scope = "authenticated user"
    else:
        key = f"ip:{client_ip}"
        limit = effective_guest_limit
        window = GUEST_WINDOW_SECONDS
        scope = "guest IP"

    allowed = _limiter.is_allowed(key, limit, window)
    if not allowed:
        retry_after = _limiter.retry_after(key, window)
        logger.warning(
            f"Rate limit exceeded for {scope} key={key} "
            f"limit={limit}/{window}s retry_after={retry_after}s"
        )
        raise HTTPException(
            status_code=429,
            detail=(
                f"Send rate limit exceeded ({limit} sends per "
                f"{'hour' if window == 3600 else 'day'} for {scope}). "
                f"Retry after {retry_after} seconds."
            ),
            headers={"Retry-After": str(retry_after)},
        )

    remaining = _limiter.remaining(key, limit, window)
    logger.debug(f"Rate limit OK for {scope} key={key}. Remaining: {remaining}/{limit}")
