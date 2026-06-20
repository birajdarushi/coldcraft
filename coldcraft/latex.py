"""LaTeX → PDF compilation via a local TeX toolchain.

Behaves like Overleaf: uses latexmk and auto-selects the engine
(pdflatex / xelatex / lualatex) based on the document, so templates that need
fontspec / FontAwesome / custom fonts compile the same way they do there.
Compiles in an isolated temp dir with shell-escape disabled, and raises
LatexError with the tail of the log on failure.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile


class LatexError(RuntimeError):
    def __init__(self, message: str, log: str = ""):
        super().__init__(message)
        self.log = log


_FONT_PKG_RE = re.compile(
    r"\\usepackage(?:\[[^\]]*\])?\{[^}]*\b(?:fontspec|unicode-math|fontawesome5?|fontawesome)\b[^}]*\}"
)
_PROGRAM_RE = re.compile(r"%\s*!\s*TEX\s+program\s*=\s*([A-Za-z]+)", re.IGNORECASE)


def detect_engine(source: str) -> str:
    """Pick pdflatex / xelatex / lualatex like Overleaf would."""
    m = _PROGRAM_RE.search(source or "")
    if m:
        prog = m.group(1).lower()
        if "xe" in prog:
            return "xelatex"
        if "lua" in prog:
            return "lualatex"
        return "pdflatex"
    if _FONT_PKG_RE.search(source or "") or "\\setmainfont" in source or "\\setsansfont" in source:
        return "xelatex"
    return "pdflatex"


_LATEXMK_FLAG = {"pdflatex": "-pdf", "xelatex": "-xelatex", "lualatex": "-lualatex"}


def compile_latex(source: str) -> bytes:
    """Compile LaTeX source to PDF bytes."""
    if not source or not source.strip():
        raise LatexError("Empty LaTeX source.")

    engine = detect_engine(source)
    have_latexmk = shutil.which("latexmk")
    have_engine = shutil.which(engine)
    # Fall back to pdflatex if the chosen engine isn't installed
    if not have_engine:
        engine = "pdflatex"
        have_engine = shutil.which("pdflatex")
    if not have_engine:
        raise LatexError("No LaTeX engine installed on the server.")

    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "doc.tex"), "w", encoding="utf-8") as f:
            f.write(source)

        if have_latexmk:
            cmd = ["latexmk", _LATEXMK_FLAG[engine], "-no-shell-escape",
                   "-interaction=nonstopmode", "-halt-on-error", "-f", "doc.tex"]
            runs = [cmd]
        else:
            base = [engine, "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "doc.tex"]
            runs = [base, base]  # two passes for refs/layout

        log = ""
        for run in runs:
            try:
                proc = subprocess.run(run, cwd=tmp, capture_output=True, text=True, timeout=120)
            except subprocess.TimeoutExpired:
                raise LatexError("LaTeX compilation timed out (120s).")
            log = proc.stdout + "\n" + proc.stderr

        pdf_path = os.path.join(tmp, "doc.pdf")
        if not os.path.exists(pdf_path):
            tail = "\n".join(log.strip().splitlines()[-45:])
            raise LatexError(f"LaTeX compilation failed (engine: {engine}).", log=tail)

        with open(pdf_path, "rb") as f:
            return f.read()
