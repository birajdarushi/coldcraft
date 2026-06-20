"""
Drafter — generates cold email drafts via the Gemini API.
"""

from . import llm
from .domain.models import DraftResult
from .prompts.registry import (
    DRAFTER_SYSTEM_PROMPT,
    HOOK_SYSTEM_PROMPT,
    REVISION_SYSTEM_PROMPT,
    FOLLOWUP_SYSTEM_PROMPT,
)


class Drafter:
    def generate_hooks(self, company_intel: dict, sender_profile: dict, count: int = 3) -> list[dict]:
        signals = self._extract_available_signals(company_intel)
        prompt = (
            f"Company: {company_intel.get('company_name')}\n"
            f"Product: {company_intel.get('product_description')}\n"
            f"Recent signals available: {signals}\n"
            f"Recipient: {company_intel.get('recipient_role')} — {company_intel.get('recipient_public_work', '')[:300]}\n"
            f"Sender: {sender_profile.get('name')}, {sender_profile.get('current_status')}\n"
            f"Generate {count} hook candidates."
        )
        return llm.generate_json(system=HOOK_SYSTEM_PROMPT, prompt=prompt, max_tokens=800)

    def draft(self, hook: dict, company_intel: dict, sender_profile: dict, recipient_name: str) -> DraftResult:
        system = DRAFTER_SYSTEM_PROMPT.format(
            sender_block=self._build_sender_block(sender_profile),
            company_block=self._build_company_block(company_intel, recipient_name),
            low_match_mode=str(company_intel.get("low_match_mode", False)),
        )
        prompt = (
            f"Winning hook to build from:\n\"{hook['text']}\"\n\n"
            f"Signal this hook references: {hook.get('signal_used')}\n\n"
            "Now write the full email using this hook."
        )
        data = llm.generate_json(system=system, prompt=prompt, max_tokens=1000)
        return DraftResult(
            campaign_id="",
            subject=data["subject"],
            body_html=data["body_html"],
            body_text=data["body_text"],
            word_count=data["word_count"],
            personalization_signals=data["personalization_signals"],
            hook_candidates=[],
            selected_hook=hook,
        )

    def draft_oneshot(self, company_intel: dict, sender_profile: dict, recipient_name: str) -> DraftResult:
        """Brainstorm the best hook AND write the email in a single Gemini call
        (instead of generate_hooks + draft). Halves the base call count."""
        system = DRAFTER_SYSTEM_PROMPT.format(
            sender_block=self._build_sender_block(sender_profile),
            company_block=self._build_company_block(company_intel, recipient_name),
            low_match_mode=str(company_intel.get("low_match_mode", False)),
        )
        prompt = (
            "First, internally brainstorm the single strongest, most specific opening hook "
            "from the available company signals (specificity > surprise > relevance). "
            "Then write the full email built on that hook. Output only the final email JSON."
        )
        data = llm.generate_json(system=system, prompt=prompt, max_tokens=1000)
        return DraftResult(
            campaign_id="",
            subject=data["subject"],
            body_html=data["body_html"],
            body_text=data["body_text"],
            word_count=data["word_count"],
            personalization_signals=data["personalization_signals"],
            hook_candidates=[],
            selected_hook={"text": "(model-selected)", "signal_used": None},
        )

    def revise(self, draft: DraftResult, violations: list[str]) -> DraftResult:
        import json

        current = {
            "subject": draft.subject,
            "body_text": draft.body_text,
            "body_html": draft.body_html,
            "personalization_signals": draft.personalization_signals,
            "word_count": draft.word_count,
        }
        prompt = (
            f"Current draft:\n{json.dumps(current, indent=2)}\n\n"
            f"Violations to fix:\n" + "\n".join(f"- {v}" for v in violations)
        )
        data = llm.generate_json(system=REVISION_SYSTEM_PROMPT, prompt=prompt, max_tokens=1000)
        draft.subject = data["subject"]
        draft.body_text = data["body_text"]
        draft.body_html = data["body_html"]
        draft.personalization_signals = data["personalization_signals"]
        draft.word_count = data["word_count"]
        return draft

    def draft_followup(self, campaign: dict, followup_number: int, day_offset: int) -> dict:
        system = FOLLOWUP_SYSTEM_PROMPT.format(followup_number=followup_number, day_offset=day_offset)
        prompt = (
            f"Original email:\nSubject: {campaign['subject']}\n{campaign['body_text']}\n\n"
            f"Company: {campaign.get('company_name')}\n"
            f"Recipient: {campaign.get('recipient_name')}\n"
            f"New signal to add (if any): {campaign.get('new_signal', 'none')}"
        )
        return llm.generate_json(system=system, prompt=prompt, max_tokens=500)

    def _build_sender_block(self, profile: dict) -> str:
        proof_points = "\n".join(
            f"  - {p['name']}: {p['outcome']} | Stack: {p['tech']}" for p in profile.get("proof_points", [])
        )
        gaps = ", ".join(profile.get("gap_areas", [])) or "none documented"
        return (
            f"Name: {profile.get('name')}\n"
            f"Status: {profile.get('current_status')}\n"
            f"Primary skills: {', '.join(profile.get('skills', []))}\n"
            f"Honest seniority: {profile.get('seniority_level', 'junior')}\n"
            f"Proof points:\n{proof_points}\n"
            f"Do NOT claim: {gaps}\n"
            f"Targeting: {profile.get('target_roles', 'SDE / QA Automation')}\n"
            f"Tone: {profile.get('tone', 'direct, confident, concise')}"
        )

    def _build_company_block(self, intel: dict, recipient_name: str) -> str:
        return (
            f"Company: {intel.get('company_name')}\n"
            f"Product (real, not marketing): {intel.get('product_description')}\n"
            f"Tech stack: {', '.join(intel.get('tech_stack', []))}\n"
            f"Culture signals: {intel.get('culture_signals', '')}\n"
            f"Recent signal (last 90 days): {intel.get('recent_signal', {})}\n"
            f"Pain points from JD: {intel.get('jd_pain_points', '')}\n"
            f"Recipient name: {recipient_name}\n"
            f"Recipient role: {intel.get('recipient_role')}\n"
            f"Recipient public work: {str(intel.get('recipient_public_work', ''))[:400]}\n"
            f"Recipient communication style: {intel.get('recipient_comm_style', 'unknown')}"
        )

    def _extract_available_signals(self, intel: dict) -> list[str]:
        signals = []
        if intel.get("recent_signal"):
            s = intel["recent_signal"]
            signals.append(f"{s.get('type', 'post')}: {s.get('description', '')[:100]} ({s.get('date', '')})")
        if intel.get("tech_stack"):
            signals.append(f"Tech decision: {', '.join(intel['tech_stack'][:3])}")
        if intel.get("recipient_public_work"):
            signals.append(f"Recipient's public work: {str(intel['recipient_public_work'])[:100]}")
        if intel.get("jd_pain_points"):
            signals.append(f"JD pain point: {intel['jd_pain_points'][:80]}")
        return signals
