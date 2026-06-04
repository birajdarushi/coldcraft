"""
Drafter — generates cold email drafts via Claude API.
Implements constitution §3.1 (structure), §3.2 (hard format limits),
§3.3 (tone calibration), and §4.1 Step 2-3 (hook generation + draft).
"""

import re
import anthropic
from typing import Optional
from .agent import DraftResult

ANTHROPIC_CLIENT = anthropic.Anthropic()
MODEL = "claude-sonnet-4-20250514"

# ─────────────────────────────────────────────────────────────────
# SYSTEM PROMPT — this IS the mailer constitution in prompt form
# ─────────────────────────────────────────────────────────────────

DRAFTER_SYSTEM_PROMPT = """
You are a cold email specialist for a job-seeker GTM engine.
You draft cold outreach emails that get replies. You follow rules absolutely.

IDENTITY OF THE SENDER
{sender_block}

KNOWLEDGE OF THE COMPANY AND RECIPIENT
{company_block}

STRUCTURE RULES (mandatory, no exceptions)
1. Hook (1-2 sentences): Opens with something specific to THEM. First sentence MUST NOT start with "I". References one real thing: product feature, blog post, engineering decision, specific launch. Make them think "this person actually knows us."

2. Connection (2-3 sentences): Bridge between their world and sender's world. ONE proof point — the most relevant to what they're building RIGHT NOW. End with a genuine question or observation about their problem (not about the sender).

3. Ask (exactly 1 sentence): One specific, low-friction ask. Not "I'd love to connect." Not "please review my portfolio." Options: 20-minute call, sharing a repo, asking if there's a better person to talk to.

4. Close (1 sentence): Graceful exit. Acknowledges their time. Not sycophantic. Not presumptuous.

FORMAT LIMITS (hard — if you exceed these, you have failed)
- Subject line: max 50 characters
- Body: 100-180 words
- Reading grade: 7-9 Flesch-Kincaid
- Personalization signals: minimum 2 (specific to this company, not generic)
- Exclamation marks: maximum 1 in entire email
- No ALL CAPS words
- No HTML formatting in plain text version

TONE RULES
- Confident, specific, peer-to-peer. Not supplicant-to-gatekeeper.
- Banned phrases: "passionate about", "exciting opportunity", "I would be incredibly grateful",
  "I've long admired", "I think I might", "I am open to any", "look forward to hearing from you"
- No hedging. No excessive qualification.
- Short sentences outperform long ones.

LOW MATCH MODE: {low_match_mode}
If true, do NOT claim fit. Frame as growth trajectory: "I'm building toward this, here's the evidence."

OUTPUT FORMAT
Return a JSON object with exactly these fields:
{
  "subject": "...",
  "body_text": "...",
  "body_html": "...",
  "personalization_signals": ["signal1", "signal2"],
  "word_count": 0
}
No preamble. No explanation. JSON only.
""".strip()


HOOK_SYSTEM_PROMPT = """
You are generating opening hook candidates for a cold email.
A hook is 1-2 sentences that opens with something specific to the recipient.
Rules:
- First word must NOT be "I"
- Must reference something real and specific (not generic praise)
- Must be directly relevant to why the sender is reaching out
- Three candidates, each referencing a DIFFERENT signal from the company intel

Score each hook on:
- specificity (1-5): how specific is the reference?
- surprise_factor (1-5): would the recipient think "how did they know that?"
- relevance (1-5): how well does this set up the sender's connection?

Output JSON array only:
[
  {"text": "...", "signal_used": "...", "specificity": 0, "surprise_factor": 0, "relevance": 0},
  {"text": "...", "signal_used": "...", "specificity": 0, "surprise_factor": 0, "relevance": 0},
  {"text": "...", "signal_used": "...", "specificity": 0, "surprise_factor": 0, "relevance": 0}
]
""".strip()


REVISION_SYSTEM_PROMPT = """
You are revising a cold email draft to fix specific violations.
You receive the current draft and a list of violations.
Fix ONLY what's flagged. Do not change what's working.
Preserve all personalization signals. Preserve the hook.
Return the same JSON structure as the original draft.
""".strip()


FOLLOWUP_SYSTEM_PROMPT = """
You are writing a follow-up cold email to an unanswered initial outreach.
This is follow-up #{followup_number} (Day {day_offset}).

Rules for follow-up 1 (Day 5):
- Reply to the original thread (same subject with "Re: " prefix)
- Max 80 words
- Add ONE new signal (something that happened in the last 5 days, or a different proof point)
- Same ask as original, or lighter ("even a yes/no works")
- Do not repeat what was in the initial email

Rules for follow-up 2 (Day 12, final):
- Max 60 words
- Graceful exit tone — warmer and more human
- Goal: leave the door permanently open, not get the meeting
- Acknowledge they're busy
- Offer a specific alternative (different timing, different format, different person)
- Close example: "Either way — no worries. I'll keep an eye on what you're building."

Return JSON: {{"subject": "...", "body_text": "...", "body_html": "...", "word_count": 0}}
""".strip()


class Drafter:

    def generate_hooks(self, company_intel: dict, sender_profile: dict, count: int = 3) -> list[dict]:
        """
        Constitution §4.1 Step 2: generate 3 hook candidates, each using a different signal.
        """
        signals = self._extract_available_signals(company_intel)
        prompt = (
            f"Company: {company_intel.get('company_name')}\n"
            f"Product: {company_intel.get('product_description')}\n"
            f"Recent signals available: {signals}\n"
            f"Recipient: {company_intel.get('recipient_role')} — {company_intel.get('recipient_public_work', '')[:300]}\n"
            f"Sender: {sender_profile.get('name')}, {sender_profile.get('current_status')}\n"
            f"Generate {count} hook candidates."
        )
        response = ANTHROPIC_CLIENT.messages.create(
            model=MODEL,
            max_tokens=800,
            system=HOOK_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        import json
        return json.loads(response.content[0].text)

    def draft(self, hook: dict, company_intel: dict, sender_profile: dict, recipient_name: str) -> DraftResult:
        """
        Constitution §4.1 Step 3: generate full email draft from winning hook.
        """
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
        import json
        response = ANTHROPIC_CLIENT.messages.create(
            model=MODEL,
            max_tokens=1000,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        data = json.loads(response.content[0].text)
        return DraftResult(
            campaign_id="",  # assigned after DB persist
            subject=data["subject"],
            body_html=data["body_html"],
            body_text=data["body_text"],
            word_count=data["word_count"],
            personalization_signals=data["personalization_signals"],
            hook_candidates=[],
            selected_hook=hook,
        )

    def revise(self, draft: DraftResult, violations: list[str]) -> DraftResult:
        """
        Constitution §4.1: revise draft given a list of specific violations.
        """
        import json
        current = {
            "subject": draft.subject,
            "body_text": draft.body_text,
            "body_html": draft.body_html,
            "personalization_signals": draft.personalization_signals,
            "word_count": draft.word_count,
        }
        response = ANTHROPIC_CLIENT.messages.create(
            model=MODEL,
            max_tokens=1000,
            system=REVISION_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    f"Current draft:\n{json.dumps(current, indent=2)}\n\n"
                    f"Violations to fix:\n" + "\n".join(f"- {v}" for v in violations)
                )
            }]
        )
        data = json.loads(response.content[0].text)
        draft.subject = data["subject"]
        draft.body_text = data["body_text"]
        draft.body_html = data["body_html"]
        draft.personalization_signals = data["personalization_signals"]
        draft.word_count = data["word_count"]
        return draft

    def draft_followup(self, campaign: dict, followup_number: int, day_offset: int) -> dict:
        """
        Constitution §5.2: generate follow-up email.
        """
        import json
        system = FOLLOWUP_SYSTEM_PROMPT.format(
            followup_number=followup_number,
            day_offset=day_offset
        )
        prompt = (
            f"Original email:\nSubject: {campaign['subject']}\n{campaign['body_text']}\n\n"
            f"Company: {campaign.get('company_name')}\n"
            f"Recipient: {campaign.get('recipient_name')}\n"
            f"New signal to add (if any): {campaign.get('new_signal', 'none')}"
        )
        response = ANTHROPIC_CLIENT.messages.create(
            model=MODEL,
            max_tokens=500,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        return json.loads(response.content[0].text)

    # ─── private builders ───

    def _build_sender_block(self, profile: dict) -> str:
        proof_points = "\n".join(
            f"  - {p['name']}: {p['outcome']} | Stack: {p['tech']}"
            for p in profile.get("proof_points", [])
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
