"""AI resume tooling — generate a tailored resume from a job description
(grounded on the user's existing resumes), and auto-fix LaTeX that fails to
compile. All via Gemini (coldcraft.llm). Only LaTeX source is produced/stored;
PDFs are compiled on demand.
"""

from __future__ import annotations

import logging

from . import llm
from .latex import LatexError, compile_latex

logger = logging.getLogger(__name__)

_GEN_SYSTEM = (
    "You are an expert technical resume writer and LaTeX engineer. "
    "You produce clean, ATS-friendly, single-page resumes that compile on the first try "
    "with pdflatex (only standard packages: geometry, titlesec, enumitem, hyperref, xcolor, mathptmx). "
    "Never use fontspec or fonts that require XeLaTeX. Define every custom color with \\definecolor "
    "BEFORE it is used. Respond ONLY with a JSON object."
)

_FIX_SYSTEM = (
    "You are a LaTeX debugging expert. You are given a LaTeX document and its compiler error log. "
    "Find the root cause and return a corrected, fully compilable document. Preserve the original "
    "content, layout, and styling as much as possible — change only what is needed to fix the error. "
    "Respond ONLY with a JSON object."
)


def generate_latex(job_description: str, context_resumes: list[str] | None = None) -> str:
    """Generate a full LaTeX resume tailored to a job description.

    `context_resumes` are the user's existing resume sources, used as style and
    factual reference so the output matches their template and real experience.
    """
    refs = ""
    for i, src in enumerate((context_resumes or [])[:2], 1):
        refs += f"\n\n--- REFERENCE RESUME {i} (match this style/template and reuse the real facts) ---\n{src[:6000]}"

    prompt = (
        "Write a tailored one-page resume in LaTeX for the following job.\n\n"
        f"JOB DESCRIPTION:\n{job_description}\n"
        f"{refs}\n\n"
        "Rules:\n"
        "- If reference resumes are provided, reuse the candidate's REAL experience, projects, "
        "education, and contact details from them — do not invent employers or degrees. "
        "Reorder, rephrase, and emphasize to match the job description.\n"
        "- If no references are provided, produce a strong generic template with clearly-labeled placeholders.\n"
        "- Match the visual style/template of the reference when present.\n"
        "- Must compile with pdflatex; define all colors before use.\n"
        'Return JSON: {"latex": "<the FULL compilable LaTeX document>"}.'
    )
    out = llm.generate_json(system=_GEN_SYSTEM, prompt=prompt, max_tokens=8000)
    latex = (out or {}).get("latex", "")
    if not latex.strip():
        raise LatexError("Model returned empty LaTeX.")
    return latex


def fix_latex(source: str, error_log: str) -> str:
    """Ask Gemini to fix LaTeX that failed to compile."""
    prompt = (
        "This LaTeX document failed to compile. Fix the root cause and return the full corrected document.\n\n"
        f"COMPILER ERROR LOG (tail):\n{error_log[-2500:]}\n\n"
        f"DOCUMENT:\n{source}\n\n"
        'Return JSON: {"latex": "<the FULL corrected LaTeX document>"}.'
    )
    out = llm.generate_json(system=_FIX_SYSTEM, prompt=prompt, max_tokens=8000)
    latex = (out or {}).get("latex", "")
    if not latex.strip():
        raise LatexError("Model returned empty LaTeX while fixing.")
    return latex


def compile_with_autofix(source: str, attempts: int = 2):
    """Compile; on failure, ask Gemini to fix and retry up to `attempts` times.

    Returns (final_source, pdf_bytes, fixes_applied). Raises LatexError if still
    failing after all attempts (carrying the final log and the last source).
    """
    fixes = 0
    log = ""
    current = source
    for i in range(attempts + 1):
        try:
            pdf = compile_latex(current)
            return current, pdf, fixes
        except LatexError as exc:
            log = exc.log or str(exc)
            if i == attempts:
                err = LatexError(str(exc), log=log)
                err.last_source = current
                raise err
            logger.info("Autofix attempt %d/%d", i + 1, attempts)
            current = fix_latex(current, log)
            fixes += 1
