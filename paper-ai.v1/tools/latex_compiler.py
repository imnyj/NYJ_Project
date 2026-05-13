"""LaTeX compilation wrapper.

Writer produces `drafts/main.tex`. This tool compiles it to PDF,
running pdflatex → bibtex → pdflatex → pdflatex (the canonical 4-pass
sequence that resolves citations and cross-references). Captures log
output for Reviewer PROOFREADER mode to audit.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from core.logger import get_logger

log = get_logger("latex_compiler")


def which(name: str) -> str | None:
    return shutil.which(name)


@dataclass
class CompileReport:
    success: bool
    pdf_path: str | None = None
    log_tail: str = ""             # last ~200 lines of .log
    errors: list[str] = field(default_factory=list)   # extracted from log
    warnings: list[str] = field(default_factory=list)
    passes_run: int = 0


class LaTeXCompiler:
    def __init__(
        self,
        *,
        pdflatex: str = "pdflatex",
        bibtex: str = "bibtex",
        timeout: float = 180.0,
    ):
        self.pdflatex = pdflatex
        self.bibtex = bibtex
        self.timeout = timeout

    def preflight(self) -> dict:
        return {
            "pdflatex": which(self.pdflatex),
            "bibtex":   which(self.bibtex),
        }

    # ------------------------------------------------------------ compile

    def compile(
        self,
        tex_path: Path | str,
        *,
        run_bibtex: bool = True,
    ) -> CompileReport:
        tex_path = Path(tex_path)
        if not tex_path.is_file():
            return CompileReport(success=False,
                                 errors=[f"tex file not found: {tex_path}"])
        if which(self.pdflatex) is None:
            return CompileReport(
                success=False,
                errors=[f"{self.pdflatex} not on PATH. "
                        "Install texlive-latex-base on WSL2."],
            )

        workdir = tex_path.parent
        stem = tex_path.stem

        def _run_pdflatex() -> subprocess.CompletedProcess:
            return subprocess.run(
                [self.pdflatex,
                 "-interaction=nonstopmode",
                 "-halt-on-error",
                 tex_path.name],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )

        def _run_bibtex() -> subprocess.CompletedProcess | None:
            if not run_bibtex or which(self.bibtex) is None:
                return None
            return subprocess.run(
                [self.bibtex, stem],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

        passes = 0
        try:
            _run_pdflatex(); passes += 1
            if run_bibtex:
                _run_bibtex()
            _run_pdflatex(); passes += 1
            last = _run_pdflatex(); passes += 1
        except subprocess.TimeoutExpired as e:
            return CompileReport(
                success=False, passes_run=passes,
                errors=[f"pdflatex timeout at pass {passes + 1}: {e}"],
            )
        except Exception as e:
            return CompileReport(
                success=False, passes_run=passes,
                errors=[f"pdflatex exception: {e!r}"],
            )

        pdf_path = workdir / f"{stem}.pdf"
        log_path = workdir / f"{stem}.log"
        log_tail = ""
        errors: list[str] = []
        warnings: list[str] = []
        if log_path.exists():
            log_text = log_path.read_text(encoding="utf-8", errors="replace")
            log_tail = "\n".join(log_text.splitlines()[-200:])
            errors, warnings = _parse_log(log_text)

        if last.returncode != 0:
            # pdflatex sometimes returns non-zero even with a PDF produced;
            # we still mark success if pdf exists and there are no ERRORs.
            success = pdf_path.exists() and not errors
        else:
            success = pdf_path.exists()

        log.info("latex_compile_done",
                 success=success,
                 pdf=str(pdf_path),
                 passes=passes,
                 n_errors=len(errors),
                 n_warnings=len(warnings))

        return CompileReport(
            success=success,
            pdf_path=str(pdf_path) if pdf_path.exists() else None,
            log_tail=log_tail,
            errors=errors,
            warnings=warnings,
            passes_run=passes,
        )


# ------------------------------------------------- log parsing

def _parse_log(log_text: str) -> tuple[list[str], list[str]]:
    """Extract TeX ERROR and WARNING lines for the Reviewer."""
    errors: list[str] = []
    warnings: list[str] = []
    for line in log_text.splitlines():
        low = line.strip()
        if not low:
            continue
        if low.startswith("!"):
            errors.append(low[:500])
        elif "Error:" in low:
            errors.append(low[:500])
        elif "Warning:" in low or "Overfull" in low or "Underfull" in low:
            warnings.append(low[:500])
    return errors, warnings
