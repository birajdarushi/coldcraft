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

# API override ceilings (to prevent abuse while allowing some flexibility)
POLICY_CEILINGS = {
    "daily_send_limit": 50,
    "max_company_emails_30d": 10,
    "subject_max_chars": 100,  # but hard floor prevents below 50
}
