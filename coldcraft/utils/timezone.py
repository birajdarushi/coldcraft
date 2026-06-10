from zoneinfo import ZoneInfo

DOMAIN_TZ_HINTS = {
    ".co.uk": "Europe/London",
    ".uk": "Europe/London",
    ".de": "Europe/Berlin",
    ".fr": "Europe/Paris",
    ".in": "Asia/Kolkata",
    ".au": "Australia/Sydney",
    ".ca": "America/Toronto",
    ".jp": "Asia/Tokyo",
}


def infer_recipient_timezone(recipient_email: str, company_intel: dict | None = None):
    company_intel = company_intel or {}

    explicit = company_intel.get("recipient_timezone")
    if explicit:
        try:
            return ZoneInfo(explicit)
        except Exception:
            pass

    hq = company_intel.get("company_hq_timezone")
    if hq:
        try:
            return ZoneInfo(hq)
        except Exception:
            pass

    domain = recipient_email.split("@")[-1].lower() if "@" in recipient_email else ""
    for suffix, tz_name in DOMAIN_TZ_HINTS.items():
        if domain.endswith(suffix):
            return ZoneInfo(tz_name)

    return ZoneInfo("UTC")