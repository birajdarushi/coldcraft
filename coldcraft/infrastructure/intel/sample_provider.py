"""Development intel provider — structured sample reports with explicit caveats.

Live web research (Apify, scraping pipelines) is deferred; reports are curated
templates so the mailer workflow and APIs can be built and verified end-to-end.
"""

from __future__ import annotations

INTEL_SECTION_KEYS = (
    "company_fundamentals",
    "engineering_culture",
    "hiring_signals",
    "recent_activity",
    "recipient_intelligence",
    "outreach_readiness",
    "sources_and_limitations",
)

_SAMPLE_CAVEAT = (
    "Sample intel for development. Live research pipeline not wired yet — "
    "verify facts before sending outreach."
)


def _section(title: str, content: str, sources: list[str] | None = None, caveat: str | None = None) -> dict:
    out: dict = {"title": title, "content": content, "sources": sources or []}
    if caveat:
        out["caveat"] = caveat
    return out


def _37signals_sections() -> dict[str, dict]:
    return {
        "company_fundamentals": _section(
            "Company fundamentals",
            "37signals builds Basecamp (project management) and HEY (email). "
            "Bootstrapped, profitable SaaS company based in Chicago. "
            "Known for small teams, remote-first culture, and opinionated product design.",
            sources=["https://37signals.com", "https://basecamp.com"],
            caveat=_SAMPLE_CAVEAT,
        ),
        "engineering_culture": _section(
            "Engineering culture",
            "Ruby on Rails originators; stack remains Ruby-heavy with pragmatic shipping. "
            "Engineering blog emphasizes calm work, small batches, and maintainability over hype.",
            sources=["https://dev.37signals.com"],
            caveat=_SAMPLE_CAVEAT,
        ),
        "hiring_signals": _section(
            "Hiring signals",
            "Roles tend to emphasize ownership, writing, and async collaboration. "
            "Job posts stress clarity, customer empathy, and long-term product thinking.",
            sources=["https://37signals.com/jobs"],
            caveat=_SAMPLE_CAVEAT,
        ),
        "recent_activity": _section(
            "Recent activity (90d)",
            "Product iteration on HEY and Basecamp; periodic essays on remote work and company philosophy. "
            "Check dev blog for latest posts before referencing a specific launch.",
            sources=["https://37signals.com/policies", "https://dev.37signals.com"],
            caveat=_SAMPLE_CAVEAT,
        ),
        "recipient_intelligence": _section(
            "Recipient intelligence",
            "Identify the hiring manager or team lead for the target role. "
            "Review public writing (blog, talks) for tone: direct, anti-hype, craft-focused.",
            sources=["LinkedIn / public profiles — not auto-fetched in sample mode"],
            caveat=_SAMPLE_CAVEAT,
        ),
        "outreach_readiness": _section(
            "Outreach readiness",
            "Strong fit when email is concise, specific, and free of growth-hack language. "
            "Lead with a concrete observation about their product or writing. "
            "Minimum intel for drafting: product description, one recent signal, recipient role + public work.",
            sources=["MAILER_CONSTITUTION.md §2"],
        ),
        "sources_and_limitations": _section(
            "Sources and limitations",
            "This report was generated from curated sample data for API verification. "
            "Replace with live research before production outreach.",
            sources=["coldcraft/infrastructure/intel/sample_provider.py"],
            caveat=_SAMPLE_CAVEAT,
        ),
    }


def _generic_sections(company: str) -> dict[str, dict]:
    return {
        "company_fundamentals": _section(
            "Company fundamentals",
            f"No curated sample for '{company}'. Add a template or connect the research pipeline.",
            caveat=_SAMPLE_CAVEAT,
        ),
        "engineering_culture": _section(
            "Engineering culture",
            "Unknown — gather stack signals from careers page, GitHub, and engineering blog.",
            caveat=_SAMPLE_CAVEAT,
        ),
        "hiring_signals": _section(
            "Hiring signals",
            "Scrape or import open roles via POST /api/v1/jobs/scrape when a careers URL is known.",
            caveat=_SAMPLE_CAVEAT,
        ),
        "recent_activity": _section(
            "Recent activity (90d)",
            "No dated signals in sample mode. Required before drafting per constitution.",
            caveat=_SAMPLE_CAVEAT,
        ),
        "recipient_intelligence": _section(
            "Recipient intelligence",
            "Recipient role and public work must be supplied manually until LinkedIn/Apify path ships.",
            caveat=_SAMPLE_CAVEAT,
        ),
        "outreach_readiness": _section(
            "Outreach readiness",
            "RESEARCH_INSUFFICIENT until product description, recent signal, and recipient public work are present.",
            caveat=_SAMPLE_CAVEAT,
        ),
        "sources_and_limitations": _section(
            "Sources and limitations",
            "Generic placeholder report. Live intel not available for this company slug yet.",
            sources=["coldcraft/infrastructure/intel/sample_provider.py"],
            caveat=_SAMPLE_CAVEAT,
        ),
    }


class SampleIntelProvider:
    """Builds constitution-aligned 7-section readiness reports."""

    def generate(self, company: str) -> dict[str, dict]:
        slug = company.strip().lower()
        if slug in {"37signals", "basecamp"}:
            sections = _37signals_sections()
        else:
            sections = _generic_sections(company)
        return {key: sections[key] for key in INTEL_SECTION_KEYS}