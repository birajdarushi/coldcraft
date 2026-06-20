#!/usr/bin/env python3
"""Seed development database with Mailpit SMTP config."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coldcraft.config.secrets import encrypt_smtp_password, get_smtp_encryption_key
from coldcraft.db.models import UserConfig
from coldcraft.db.session import get_session, init_db


def main() -> None:
    init_db()

    key = get_smtp_encryption_key()
    if not key:
        # Dev convenience: generate and print so user can export for the process
        from cryptography.fernet import Fernet

        key = Fernet.generate_key().decode()
        print(f"Generated GTM_SMTP_ENCRYPTION_KEY={key}")
        # Note: for this seed run we temporarily use it; caller should export for API runtime
        os.environ["GTM_SMTP_ENCRYPTION_KEY"] = key

    encrypted_password = encrypt_smtp_password("mailpit")

    with get_session() as db:
        existing = db.query(UserConfig).first()
        if existing:
            print("UserConfig already seeded — skipping")
            return

        db.add(
            UserConfig(
                smtp_host=os.environ.get("SMTP_HOST", "mailpit"),
                smtp_port=int(os.environ.get("SMTP_PORT", "1025")),
                smtp_user=os.environ.get("SMTP_USER", "coldcraft"),
                smtp_pass_enc=encrypted_password,
                from_email=os.environ.get("FROM_EMAIL", "coldcraft@localhost"),
                from_name=os.environ.get("FROM_NAME", "Coldcraft Dev"),
                tracking_domain=os.environ.get("TRACKING_DOMAIN"),
            )
        )
        db.commit()
        print("Seeded UserConfig for development SMTP")


if __name__ == "__main__":
    main()