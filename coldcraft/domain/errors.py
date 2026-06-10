class MailerAgentError(Exception):
    pass


class ResearchInsufficientError(MailerAgentError):
    pass


class SenderProfileIncompleteError(MailerAgentError):
    pass


class DoNotContactError(MailerAgentError):
    pass


class ATSConflictError(MailerAgentError):
    pass


class DailyLimitError(MailerAgentError):
    pass


class CompanyLimitError(MailerAgentError):
    pass


class NoOutreachPolicyError(MailerAgentError):
    pass


class DuplicateSendError(MailerAgentError):
    pass


class SelfReviewError(MailerAgentError):
    pass


class QAEscalationError(MailerAgentError):
    pass


class SendBlockedError(MailerAgentError):
    pass


class SendTimingError(MailerAgentError):
    pass


class ScraperError(Exception):
    pass
