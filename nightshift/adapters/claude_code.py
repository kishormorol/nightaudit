"""The Claude Code adapter.

Read-only is not a convention here, it is enforced by the CLI's own permission
system: we hand Claude Code an allowlist of read-class tools and an explicit
denylist of every tool that can mutate a repo. If those flags ever stop
working, the correct behaviour is to fail the run, not to fall back to an
unrestricted invocation.

Flag names were checked against `claude --help` (CLI v2.x) rather than assumed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from nightshift.adapters.base import Availability, RunResult

#: Tools Claude Code may use: inspect the repo, nothing else.
ALLOWED_TOOLS = ("Read", "Grep", "Glob", "NotebookRead")

#: Tools that can change a repo or reach the network. Belt and braces — the
#: allowlist above should already exclude these, but a denylist survives a
#: future release adding a new write-capable tool to the default set.
DISALLOWED_TOOLS = (
    "Bash",
    "Edit",
    "MultiEdit",
    "Write",
    "NotebookEdit",
    "WebFetch",
    "WebSearch",
    "Task",
)

#: Where Claude Code records the user's own sessions; the newest mtime under
#: here is our proxy for "a human is using this right now".
CLAUDE_PROJECTS_DIR = Path("~/.claude/projects")

_READ_ONLY_PREAMBLE = (
    "You are running unattended as part of an automated read-only review.\n"
    "You have no write, edit, or shell tools — do not attempt to use them, and "
    "do not ask questions. Inspect the repository and report findings only.\n\n"
)


class ClaudeCodeAdapter:
    name = "claude_code"

    def __init__(self, binary: str = "claude"):
        self.binary = binary

    # ---- availability -------------------------------------------------

    def _which(self) -> str | None:
        return shutil.which(self.binary)

    def availability(self) -> Availability:
        path = self._which()
        if path is None:
            return Availability(
                ok=False,
                reason=f"`{self.binary}` is not on PATH — install Claude Code, see "
                f"https://claude.com/claude-code",
            )
        try:
            proc = subprocess.run(
                [self.binary, "--version"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return Availability(ok=False, reason=f"`{self.binary} --version` failed: {exc}")
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip().splitlines()
            first = detail[0] if detail else f"exit {proc.returncode}"
            return Availability(ok=False, reason=f"`{self.binary} --version` failed: {first}")
        return Availability(ok=True, reason=(proc.stdout or "").strip())

    def available(self) -> bool:
        return self.availability().ok

    # ---- idle detection -----------------------------------------------

    def _projects_dir(self) -> Path:
        return Path(os.path.expanduser(str(CLAUDE_PROJECTS_DIR)))

    def last_human_use(self) -> datetime | None:
        """Newest mtime under ``~/.claude/projects``.

        Returns ``None`` when the directory is absent — a fresh install has
        simply never been used, which reads as idle rather than as busy.
        """
        root = self._projects_dir()
        if not root.is_dir():
            return None
        newest: float | None = None
        try:
            for path in root.rglob("*"):
                try:
                    mtime = path.stat().st_mtime
                except OSError:
                    continue
                if newest is None or mtime > newest:
                    newest = mtime
        except OSError:
            return None
        if newest is None:
            return None
        return datetime.fromtimestamp(newest)

    # ---- running ------------------------------------------------------

    def command(self, prompt: str) -> list[str]:
        return [
            self.binary,
            "--print",
            _READ_ONLY_PREAMBLE + prompt,
            "--output-format",
            "json",
            "--allowed-tools",
            *ALLOWED_TOOLS,
            "--disallowed-tools",
            *DISALLOWED_TOOLS,
        ]

    def run(self, prompt: str, project_dir: Path, timeout_s: int) -> RunResult:
        started = datetime.now()

        def finish(status: str, findings_md: str, detail: str = "") -> RunResult:
            return RunResult(
                provider=self.name,
                project=project_dir.name,
                task="",
                status=status,  # type: ignore[arg-type]
                findings_md=findings_md,
                started_at=started,
                duration_s=(datetime.now() - started).total_seconds(),
                detail=detail,
            )

        if not project_dir.is_dir():
            return finish("failed", "", f"project path does not exist: {project_dir}")

        try:
            proc = subprocess.run(
                self.command(prompt),
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        except subprocess.TimeoutExpired:
            # start_new_session put the CLI in its own process group, so the
            # kill that subprocess.run already issued takes any children with
            # it rather than leaving orphans holding the quota.
            return finish("timeout", "", f"no output after {timeout_s}s")
        except FileNotFoundError:
            return finish("failed", "", f"`{self.binary}` is not on PATH")
        except OSError as exc:
            return finish("failed", "", f"could not start `{self.binary}`: {exc}")

        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()

        if proc.returncode != 0:
            detail = stderr.splitlines()[0] if stderr else f"exit {proc.returncode}"
            # A non-zero exit that still produced output is worth keeping.
            return finish("failed", stdout, detail)

        if not stdout:
            return finish("failed", "", "no output")

        return finish("ok", self._extract(stdout))

    @staticmethod
    def _extract(stdout: str) -> str:
        """Pull the result text out of ``--output-format json``.

        Never discards a completed run: if the envelope isn't the shape we
        expect, the raw stdout *is* the findings. A run that cost quota must
        always leave something in the digest.
        """
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            return stdout

        if isinstance(payload, dict):
            for key in ("result", "text", "content", "output"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            if payload.get("is_error") and isinstance(payload.get("error"), str):
                return payload["error"].strip()
        return stdout
