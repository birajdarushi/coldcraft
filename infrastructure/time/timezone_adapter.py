from ...utils.timezone import infer_recipient_timezone


class TimezoneAdapter:
    def infer_recipient_timezone(self, recipient_email: str, company_intel: dict):
        return infer_recipient_timezone(recipient_email, company_intel)
