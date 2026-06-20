from dataclasses import dataclass


@dataclass
class SMTPSettings:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_pass_enc: str
    from_email: str
    from_name: str
    tracking_domain: str | None = None

    @classmethod
    def from_user_config(cls, config):
        return cls(
            smtp_host=config.smtp_host,
            smtp_port=config.smtp_port,
            smtp_user=config.smtp_user,
            smtp_pass_enc=config.smtp_pass_enc,
            from_email=config.from_email,
            from_name=config.from_name,
            tracking_domain=getattr(config, "tracking_domain", None),
        )
