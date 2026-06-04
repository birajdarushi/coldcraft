import unittest

from coldcraft.validators import MailerValidator


class MailerValidatorTests(unittest.TestCase):
    def test_flags_first_sentence_starting_with_i(self):
        validator = MailerValidator()
        result = validator.validate_email(
            subject="Short subject",
            body_text="I built a system for this role. Could we talk next week?",
            body_html="<p>I built a system for this role. Could we talk next week?</p>",
            personalization_signals=["sig1", "sig2"],
        )
        self.assertFalse(result.passed)
        self.assertTrue(any("First sentence" in v for v in result.violations))


if __name__ == "__main__":
    unittest.main()
