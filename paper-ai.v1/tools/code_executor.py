"""Sandboxed code execution for Experimenter agent.

Safety model:
    - Always execute in a TEMPORARY working directory that is created fresh
      per run and deleted after, unless the caller sets `persist_dir=`.
    - Hard timeout via subprocess.run(timeout=...).
    - Configurable language (Python default, also C/C++, MATLAB Octave).
    - Stdout/stderr captured; return code recorded.
    - No network access policy enforced here — users control that at OS
      level (WSL2 firewall) or via `env=` override.

This is intentionally LESS sandboxed than full Docker isolation because:
    - The user runs paper-ai on their own machine (trust boundary = user).
    - libsumo needs access to the user's SUMO install and /dev/shm.
    - Adding a Docker layer doubles the ops complexity.

If you need hard isolation, the `run()` signature is Docker-ready: wrap
any invocation in `docker run --rm -v {workdir}:/work ...`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.logger import get_logger

log = get_logger("code_executor")


# Registered language → (file extension, invoke command)
LANGUAGES: dict[str, tuple[str, list[str]]] = {
    "python": (".py", [sys.executable]),
    "bash":   (".sh", ["bash"]),
    "octave": (".m",  ["octave", "--no-gui", "--quiet"]),
}

# Max output bytes to retain in memory (prevents huge stdout from eating RAM)
MAX_STDOUT_BYTES = 4 * 1024 * 1024    # 4 MiB


@dataclass
class ExecutionReport:
    success: bool
    returncode: int
    stdout: str = ""
    stderr: str = ""
    workdir: str = ""
    elapsed_seconds: float = 0.0
    language: str = "python"
    artifacts: list[str] = field(default_factory=list)   # files left in workdir
    timed_out: bool = False


class CodeExecutor:
    """Run short code blocks or whole files with resource limits."""

    def __init__(
        self,
        *,
        default_timeout: float = 120.0,
        default_language: str = "python",
        persist_root: Path | str | None = None,
    ):
        self.default_timeout = default_timeout
        self.default_language = default_language
        self.persist_root = Path(persist_root) if persist_root else None

    # ---------------------------------------------------------- run

    def run(
        self,
        code: str,
        *,
        language: str | None = None,
        stdin: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
        extra_args: list[str] | None = None,
        persist_dir: Path | str | None = None,
    ) -> ExecutionReport:
        """Execute `code`. Returns an ExecutionReport.

        If persist_dir is supplied, the working directory is NOT cleaned
        up — Experimenter uses this to let Validator inspect artifacts.
        """
        lang = (language or self.default_language).lower()
        if lang not in LANGUAGES:
            return ExecutionReport(
                success=False, returncode=-1,
                stderr=f"unsupported language: {lang}",
                language=lang,
            )
        ext, base_cmd = LANGUAGES[lang]

        # Pick working directory
        if persist_dir:
            workdir = Path(persist_dir)
            workdir.mkdir(parents=True, exist_ok=True)
            temp_mode = False
        elif self.persist_root:
            self.persist_root.mkdir(parents=True, exist_ok=True)
            workdir = Path(tempfile.mkdtemp(prefix="paperai_", dir=self.persist_root))
            temp_mode = False
        else:
            workdir = Path(tempfile.mkdtemp(prefix="paperai_"))
            temp_mode = True

        script_path = workdir / f"script{ext}"
        script_path.write_text(textwrap.dedent(code), encoding="utf-8")

        cmd = list(base_cmd) + [str(script_path)]
        if extra_args:
            cmd.extend(extra_args)

        final_env = os.environ.copy()
        if env:
            final_env.update(env)

        log.info("code_exec_start",
                 lang=lang, workdir=str(workdir),
                 timeout=timeout or self.default_timeout)

        import time as _t
        t0 = _t.perf_counter()
        timed_out = False
        try:
            proc = subprocess.run(
                cmd,
                input=stdin if stdin else None,
                cwd=str(workdir),
                env=final_env,
                capture_output=True,
                text=True,
                timeout=timeout or self.default_timeout,
                check=False,
            )
            stdout = proc.stdout
            stderr = proc.stderr
            returncode = proc.returncode
        except subprocess.TimeoutExpired as e:
            timed_out = True
            stdout = e.stdout.decode(errors="replace") if e.stdout else ""
            stderr = (e.stderr.decode(errors="replace") if e.stderr else "") \
                     + f"\n[paper-ai] TIMEOUT after {timeout or self.default_timeout}s"
            returncode = -999
        except FileNotFoundError as e:
            # Interpreter binary itself missing (bash on Windows, octave
            # not installed, etc.) — distinguish from TimeoutExpired and
            # generic exceptions so the caller can give a useful hint.
            timed_out = False
            stdout = ""
            stderr = (
                f"[paper-ai] interpreter not found for language={lang!r}: "
                f"{e!r}. Ensure the binary is installed and on PATH."
            )
            returncode = -2
        except Exception as e:
            timed_out = False
            stdout = ""
            stderr = f"[paper-ai] exception: {e!r}"
            returncode = -1
        elapsed = _t.perf_counter() - t0

        # Truncate huge output
        stdout = _truncate_bytes(stdout, MAX_STDOUT_BYTES)
        stderr = _truncate_bytes(stderr, MAX_STDOUT_BYTES)

        # List artifacts left in workdir (excluding the script)
        artifacts = [
            str(p.relative_to(workdir)) for p in workdir.iterdir()
            if p.name != script_path.name
        ]

        report = ExecutionReport(
            success=(returncode == 0 and not timed_out),
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            workdir=str(workdir),
            elapsed_seconds=elapsed,
            language=lang,
            artifacts=artifacts,
            timed_out=timed_out,
        )
        log.info("code_exec_done",
                 success=report.success,
                 returncode=returncode,
                 elapsed=round(elapsed, 2),
                 timed_out=timed_out,
                 artifacts_n=len(artifacts))

        # Clean up if temp
        if temp_mode and not persist_dir:
            try:
                shutil.rmtree(workdir)
            except OSError as e:
                log.warning("workdir_cleanup_failed", err=str(e))

        return report

    # ---------------------------------------------------------- run_file

    def run_file(
        self,
        path: Path | str,
        *,
        language: str | None = None,
        **kwargs: Any,
    ) -> ExecutionReport:
        """Convenience: read file then .run()."""
        path = Path(path)
        code = path.read_text(encoding="utf-8")
        # Infer language from extension if not supplied
        if language is None:
            for lang, (ext, _cmd) in LANGUAGES.items():
                if path.suffix == ext:
                    language = lang
                    break
        return self.run(code, language=language, **kwargs)


# -------------------------------------------------------------- helpers

def _truncate_bytes(s: str, n: int) -> str:
    b = s.encode("utf-8", errors="replace")
    if len(b) <= n:
        return s
    cut = b[:n].decode("utf-8", errors="replace")
    return cut + f"\n... [truncated {len(b) - n} bytes]"
