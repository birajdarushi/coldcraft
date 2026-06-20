"""
Validators — format, content, and deliverability checks.
"""

import re

from .domain.models import ValidationResult
from .domain import policies


class MailerValidator:
    def validate_email(self, subject: str, body_text: str, body_html: str, personalization_signals: list[str]) -> ValidationResult:
        violations = []
        warnings = []
        scores = {}

        if len(subject) > policies.MAX_SUBJECT_CHARS:
            violations.append(
                f"Subject is {len(subject)} chars — max is {policies.MAX_SUBJECT_CHARS}. Current: '{subject}'"
            )

        if subject.lower().startswith("quick question"):
            violations.append("Subject 'Quick question' is overused — choose something specific")

        words = body_text.split()
        word_count = len(words)
        scores["word_count"] = word_count
        if word_count < policies.MIN_WORDS:
            violations.append(f"Body is {word_count} words — minimum is {policies.MIN_WORDS}")
        if word_count > policies.MAX_WORDS:
            violations.append(f"Body is {word_count} words — maximum is {policies.MAX_WORDS}. Compress, don't just trim.")

        first_sentence = body_text.strip().split(".")[0].strip()
        if first_sentence.startswith("I ") or first_sentence.startswith("I'"):
            violations.append(
                f"First sentence starts with 'I': '{first_sentence[:60]}...'. Rewrite to open with something about them."
            )

        if len(personalization_signals) < policies.MIN_PERSONALIZATION:
            violations.append(
                f"Only {len(personalization_signals)} personalization signal(s) — minimum is {policies.MIN_PERSONALIZATION}. "
                "Email must reference at least 2 things specific to this company."
            )
        scores["personalization_count"] = len(personalization_signals)

        excl_count = body_text.count("!")
        if excl_count > policies.MAX_EXCLAMATIONS:
            violations.append(f"Found {excl_count} exclamation marks — maximum is {policies.MAX_EXCLAMATIONS}")

        caps_words = re.findall(r"\b[A-Z]{3,}\b", body_text)
        caps_words = [w for w in caps_words if w not in {"CEO", "CTO", "API", "SaaS", "UI", "UX", "QA"}]
        if caps_words:
            violations.append(f"ALL CAPS words found: {caps_words}. Remove them.")

        body_lower = body_text.lower()
        for phrase in policies.BANNED_PHRASES:
            if phrase in body_lower:
                violations.append(f"Banned phrase found: '{phrase}'. Remove or rephrase.")

        spam_found = [w for w in policies.SPAM_TRIGGER_WORDS if w in body_lower]
        if spam_found:
            violations.append(f"Spam trigger words found: {spam_found}")

        question_count = body_text.count("?")
        if question_count > 2:
            violations.append(
                f"Found {question_count} question marks — suggests more than one ask. Keep exactly one ask."
            )
        elif question_count == 0:
            violations.append("No question mark found — the email needs exactly one ask.")

        link_count = len(re.findall(r'href="https?://', body_html))
        if link_count > 1:
            violations.append(
                f"Found {link_count} links in body — maximum is 1. Include only LinkedIn or GitHub, not both."
            )

        grade = self._flesch_kincaid_grade(body_text)
        scores["reading_grade"] = round(grade, 1)
        if grade > 10:
            violations.append(f"Reading grade level is {grade:.1f} — target is 7-9. Simplify sentence structure.")
        elif grade < 5:
            warnings.append(
                f"Reading grade level is {grade:.1f} — may read as too informal. Consider slightly longer sentences."
            )

        spam_score = self._estimate_spam_score(subject, body_text, body_html)
        scores["spam_score_estimate"] = spam_score
        if spam_score > 5:
            violations.append(f"Estimated spam score {spam_score}/10 is too high. Check for spam trigger patterns.")
        elif spam_score > 3:
            warnings.append(f"Spam score {spam_score}/10 is borderline. Review before sending.")

        return ValidationResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            scores=scores,
        )

    def check_self_review(self, draft) -> list[str]:
        result = self.validate_email(
            subject=draft.subject,
            body_text=draft.body_text,
            body_html=draft.body_html,
            personalization_signals=draft.personalization_signals,
        )
        return result.violations

    def _flesch_kincaid_grade(self, text: str) -> float:
        sentences = max(1, len(re.findall(r"[.!?]+", text)))
        words = text.split()
        if not words:
            return 0.0
        syllables = sum(self._syllable_count(w) for w in words)
        asl = len(words) / sentences
        asw = syllables / len(words)
        return max(0.0, 0.39 * asl + 11.8 * asw - 15.59)

    def _syllable_count(self, word: str) -> int:
        word = word.lower().strip(".,!?;:\"'()")
        if not word:
            return 0
        vowels = "aeiouy"
        count = 0
        prev_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        if word.endswith("e") and count > 1:
            count -= 1
        return max(1, count)

    def _estimate_spam_score(self, subject: str, body_text: str, body_html: str) -> float:
        score = 0.0
        combined = (subject + " " + body_text).lower()

        for phrase in policies.SPAM_TRIGGER_WORDS:
            if phrase in combined:
                score += 1.0

        if subject.count("!") > 0:
            score += 1.0
        if "!!!" in body_text:
            score += 1.5

        html_tags = len(re.findall(r"<[^>]+>", body_html))
        if html_tags > 20:
            score += 1.0

        if subject == subject.upper() and len(subject) > 3:
            score += 2.0

        if subject.lower().startswith("re:") and "reply" not in body_text.lower():
            score += 0.5

        return min(10.0, score)
