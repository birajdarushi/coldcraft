"""Gemini-backed intel provider — generates the 7-section readiness report
from the model's knowledge. Not web-grounded, so every section carries an
explicit verify-before-sending caveat. Falls back to the sample provider when
no Gemini key is configured or the call fails.
"""

from __future__ import annotations

import logging

from ... import llm
from .sample_provider import INTEL_SECTION_KEYS, SampleIntelProvider

logger = logging.getLogger(__name__)

_TITLES = {
    "company_fundamentals": "Company fundamentals",
    "engineering_culture": "Engineering culture",
    "hiring_signals": "Hiring signals",
    "recent_activity": "Recent activity",
    "recipient_intelligence": "Recipient intelligence",
    "outreach_readiness": "Outreach readiness",
    "sources_and_limitations": "Sources & limitations",
}

_AI_CAVEAT = (
    "AI-generated from the model's training knowledge — not live web research. "
    "Verify every fact (especially names, numbers, and recent events) before outreach."
)

_SYSTEM = (
    "You are a company research analyst preparing a concise readiness dossier that a "
    "job seeker will use to write a hyper-personalized cold outreach email. "
    "Be specific and honest. If you are unsure about a fact, say so rather than inventing it. "
    "Respond ONLY with a JSON object."
)


def _prompt(company: str) -> str:
    keys = ", ".join(INTEL_SECTION_KEYS)
    return (
        f"Company: {company}\n\n"
        f"Produce a JSON object with exactly these keys: {keys}.\n"
        "Each value is an object: {\"content\": \"2-4 sentence analysis\", "
        "\"sources\": [\"general source types you'd check, e.g. 'company blog', 'LinkedIn'\"]}.\n"
        "- company_fundamentals: what they do, stage, size, business model.\n"
        "- engineering_culture: stack, team style, how they build.\n"
        "- hiring_signals: roles they tend to hire, growth signals.\n"
        "- recent_activity: launches, news, themes (note if uncertain about recency).\n"
        "- recipient_intelligence: who to contact (likely roles), what resonates with them.\n"
        "- outreach_readiness: is this a good cold-outreach target and how to approach.\n"
        "- sources_and_limitations: what you're confident vs unsure about.\n"
        "No preamble. JSON only."
    )


class GeminiIntelProvider:
    def __init__(self):
        self._fallback = SampleIntelProvider()

    def generate(self, company: str) -> dict[str, dict]:
        try:
            raw = llm.generate_json(system=_SYSTEM, prompt=_prompt(company), max_tokens=1800)
        except Exception as exc:  # no key, quota, parse failure → safe fallback
            logger.warning("Gemini intel failed (%s); falling back to sample provider", exc)
            return self._fallback.generate(company)

        sections: dict[str, dict] = {}
        for key in INTEL_SECTION_KEYS:
            item = raw.get(key) if isinstance(raw, dict) else None
            if isinstance(item, dict):
                content = item.get("content") or ""
                sources = item.get("sources") or []
            elif isinstance(item, str):
                content, sources = item, []
            else:
                content, sources = "Not available.", []
            sections[key] = {
                "title": _TITLES[key],
                "content": content,
                "sources": sources if isinstance(sources, list) else [str(sources)],
                "caveat": _AI_CAVEAT,
            }
        return sections
