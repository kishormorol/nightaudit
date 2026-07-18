"""Crontab entries for the two scheduled commands.

nightaudit has no daemon: cron calls ``run`` hourly and the command decides for
itself whether to act.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

MARKER = "# nightaudit (managed — edit via `nightaudit init`)"
END_MARKER = "# end nightaudit"

#: Kept present in the pinned PATH even if the caller's own PATH is exotic, so a
#: cron job never loses the base system tools cron would otherwise have given it.
_FALLBACK_PATH = "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

#: What 0.3.0 and earlier wrote. Recognised so `init` replaces that block rather
#: than adding a second one beside it: the old lines call a `nightshift` binary
#: the upgrade removed, so leaving them in place means an hourly failure in a log
#: nobody reads, under a marker claiming the block is managed.
LEGACY_MARKER = "# nightshift (managed — edit via `nightshift init`)"
LEGACY_END_MARKER = "# end nightshift"

_MARKERS = (MARKER, LEGACY_MARKER)
_END_MARKERS = (END_MARKER, LEGACY_END_MARKER)

HOURLY_RUN = "0 * * * *"
DAILY_DIGEST = "30 7 * * *"


def executable() -> str:
    """Absolute path to the installed ``nightaudit`` entry point."""
    found = shutil.which("nightaudit")
    if found:
        return found
    # Running from a source checkout or a venv that isn't on cron's PATH.
    return f"{Path(sys.executable)} -m nightaudit"


def path_value() -> str:
    """PATH to pin in the crontab so cron resolves what ``init`` resolved.

    cron runs jobs with a bare PATH (typically ``/usr/bin:/bin``), so provider
    binaries installed elsewhere — ``claude`` under ``~/.local/bin``, ``codex``
    under ``/opt/homebrew/bin``, anything behind a version manager — are invisible
    to the hourly ``run`` even though the interactive shell finds them fine. That
    silently produces zero-run nights. ``init`` runs from the user's shell, so its
    PATH is exactly the one that resolved these tools; freezing it into the block
    keeps cron and the shell in agreement. Re-run ``init`` after moving a binary.
    """
    current = os.environ.get("PATH", "").strip()
    dirs = current.split(os.pathsep) if current else []
    for fallback in _FALLBACK_PATH.split(":"):
        if fallback not in dirs:
            dirs.append(fallback)
    return os.pathsep.join(dirs)


def entries(binary: str | None = None) -> list[str]:
    exe = binary or executable()
    return [
        f"{HOURLY_RUN} {exe} run >> /tmp/nightaudit-cron.log 2>&1",
        f"{DAILY_DIGEST} {exe} digest >> /tmp/nightaudit-cron.log 2>&1",
    ]


def block(binary: str | None = None) -> str:
    # The PATH assignment must sit above the entries: a crontab env line applies
    # only to the jobs below it, which keeps it scoped to our two lines and away
    # from any entries of the user's own that `merged` places ahead of this block.
    lines = [MARKER, f"PATH={path_value()}", *entries(binary), END_MARKER]
    return "\n".join(lines) + "\n"


def read_crontab() -> str:
    """Current crontab, or empty string if there isn't one."""
    try:
        proc = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout


def strip_block(existing: str) -> str:
    """Remove a previously installed block, under either name.

    Either end marker closes either block. A crontab carrying an opening line we
    recognise and no matching close is already malformed, and swallowing to the
    end of the file would take the user's own entries with it.
    """
    out: list[str] = []
    skipping = False
    for line in existing.splitlines():
        if line.strip() in _MARKERS:
            skipping = True
            continue
        if skipping:
            if line.strip() in _END_MARKERS:
                skipping = False
            continue
        out.append(line)
    return "\n".join(out).strip("\n")


def merged(existing: str, binary: str | None = None) -> str:
    """The crontab that would result from installing our block."""
    base = strip_block(existing)
    parts = [p for p in (base, block(binary).rstrip("\n")) if p]
    return "\n".join(parts) + "\n"


def install(binary: str | None = None) -> None:
    """Replace the user's crontab with one containing our block.

    Raises ``RuntimeError`` if ``crontab`` isn't usable — the caller prints the
    lines so the user can paste them in by hand.
    """
    if shutil.which("crontab") is None:
        raise RuntimeError("`crontab` is not on PATH")
    new = merged(read_crontab(), binary)
    try:
        proc = subprocess.run(
            ["crontab", "-"], input=new, text=True, capture_output=True, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"could not run `crontab -`: {exc}") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"`crontab -` failed: {detail}")
