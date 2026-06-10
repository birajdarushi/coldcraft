from importlib import import_module

__all__ = [
    "MailerAgent",
    "CampaignRequest",
    "DraftResult",
    "Drafter",
    "SMTPClient",
    "Tracker",
    "MailerValidator",
]


def __getattr__(name):
    if name in {"MailerAgent", "CampaignRequest", "DraftResult"}:
        module = import_module(".agent", __name__)
        return getattr(module, name)
    if name == "Drafter":
        module = import_module(".drafter", __name__)
        return getattr(module, name)
    if name == "SMTPClient":
        module = import_module(".smtp_client", __name__)
        return getattr(module, name)
    if name == "Tracker":
        module = import_module(".tracker", __name__)
        return getattr(module, name)
    if name == "MailerValidator":
        module = import_module(".validators", __name__)
        return getattr(module, name)
    raise AttributeError(name)
