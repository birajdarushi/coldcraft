MAX_SUBJECT_CHARS = 50
MIN_WORDS = 100
MAX_WORDS = 180
MIN_PERSONALIZATION = 2
MAX_EXCLAMATIONS = 1

DAILY_SEND_LIMIT = 20
HOURLY_SEND_LIMIT = 5
MAX_FOLLOWUPS = 2
MAX_COMPANY_EMAILS_30D = 3
FOLLOWUP_DAYS = [5, 12]
MIN_MATCH_SCORE = 40
QA_MAX_RETRIES = 2

BANNED_PHRASES = [
    "passionate about",
    "exciting opportunity",
    "i would be incredibly",
    "i've long admired",
    "incredible work on",
    "i think i might",
    "i am open to any",
    "look forward to hearing from you",
    "unsubscribe",
    "click here",
    "limited time",
    "act now",
    "no obligation",
    "free trial",
    "100%",
    "guaranteed",
]

SPAM_TRIGGER_WORDS = [
    "urgent", "winner", "congratulations", "prize", "cash",
    "make money", "work from home", "earn extra", "risk free",
    "buy now", "order now", "special promotion",
]

# Constitution hard floors (cannot be weakened by overrides)
CONSTITUTION_FLOORS = {
    "daily_send_limit": DAILY_SEND_LIMIT,
    "max_company_emails_30d": MAX_COMPANY_EMAILS_30D,
    "subject_max_chars": MAX_SUBJECT_CHARS,
    "followup_days": FOLLOWUP_DAYS,
    "min_words": MIN_WORDS,
    "max_words": MAX_WORDS,
    "min_personalization": MIN_PERSONALIZATION,
    "max_exclamations": MAX_EXCLAMATIONS,
    "min_match_score": MIN_MATCH_SCORE,
    "qa_max_retries": QA_MAX_RETRIES,
}

# API override ceilings match constitution hard maximums (cannot weaken via API)
POLICY_CEILINGS = {
    "daily_send_limit": DAILY_SEND_LIMIT,
    "max_company_emails_30d": MAX_COMPANY_EMAILS_30D,
    "subject_max_chars": MAX_SUBJECT_CHARS,
}


def clamp_policy_value(key: str, value: int) -> int:
    """Clamp a policy override to constitution hard maximum."""
    ceiling = POLICY_CEILINGS.get(key)
    if ceiling is not None:
        return min(value, ceiling)
    return value


def validate_policy_overrides(
    daily_send_limit: int | None = None,
    max_company_emails_30d: int | None = None,
    subject_max_chars: int | None = None,
) -> None:
    """Raise ValueError when overrides exceed constitution hard limits."""
    if daily_send_limit is not None and daily_send_limit > DAILY_SEND_LIMIT:
        raise ValueError(f"daily_send_limit cannot exceed hard limit of {DAILY_SEND_LIMIT}")
    if max_company_emails_30d is not None and max_company_emails_30d > MAX_COMPANY_EMAILS_30D:
        raise ValueError(
            f"max_company_emails_30d cannot exceed hard limit of {MAX_COMPANY_EMAILS_30D}"
        )
    if subject_max_chars is not None and subject_max_chars > MAX_SUBJECT_CHARS:
        raise ValueError(f"subject_max_chars cannot exceed hard limit of {MAX_SUBJECT_CHARS}")
