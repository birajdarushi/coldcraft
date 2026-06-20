from ..validators import MailerValidator


class QAAgent:
    """Independent QA gate backed by constitution rule checks."""

    def __init__(self):
        self.validator = MailerValidator()

    def validate_email(self, payload: dict) -> dict:
        result = self.validator.validate_email(
            subject=payload.get("subject", ""),
            body_text=payload.get("body_text", ""),
            body_html=payload.get("body_html", ""),
            personalization_signals=payload.get("personalization_signals", []),
        )
        if result.passed:
            return {"status": "PASS", "violations": [], "warnings": result.warnings}
        return {"status": "FAIL", "violations": result.violations, "warnings": result.warnings}