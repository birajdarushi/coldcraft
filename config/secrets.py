import os


def get_smtp_encryption_key() -> str | None:
    return os.environ.get("GTM_SMTP_ENCRYPTION_KEY")
