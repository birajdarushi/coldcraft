import os

from cryptography.fernet import Fernet


def get_smtp_encryption_key() -> str | None:
    return os.environ.get("GTM_SMTP_ENCRYPTION_KEY")


def encrypt_smtp_password(plain_password: str) -> str:
    """Encrypt plain SMTP password for storage. Key must be in env (bootstrap secret)."""
    key = get_smtp_encryption_key()
    if not key:
        raise RuntimeError(
            "GTM_SMTP_ENCRYPTION_KEY not set. "
            "Required for encrypting SMTP credentials on write."
        )
    f = Fernet(key.encode())
    return f.encrypt(plain_password.encode()).decode()


def encrypt_secret(plain: str) -> str:
    """Encrypt a general secret (apify token, imap creds, etc) using the same bootstrap key."""
    key = get_smtp_encryption_key()
    if not key:
        raise RuntimeError(
            "GTM_SMTP_ENCRYPTION_KEY not set. "
            "Required for encrypting integration secrets on write."
        )
    f = Fernet(key.encode())
    return f.encrypt(plain.encode()).decode()


def decrypt_secret(enc: str) -> str:
    """Decrypt a secret stored via encrypt_secret."""
    key = get_smtp_encryption_key()
    if not key:
        raise RuntimeError(
            "GTM_SMTP_ENCRYPTION_KEY not set. "
            "Required for decrypting integration secrets."
        )
    f = Fernet(key.encode())
    return f.decrypt(enc.encode()).decode()
