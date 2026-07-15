"""Which Claude Code sessions were ours.

:meth:`ClaudeCodeAdapter.last_human_use` decides whether a human is at the
keyboard by reading the newest mtime under ``~/.claude/projects``. nightshift's
own ``claude --print`` runs write their transcripts into that same directory —
the same directory, not merely a similar one — so without this every run would
leave a fresh mtime that the next cron tick reads as human activity, and
nightshift would gate itself out for ``idle_minutes`` after each run. It would
put itself to sleep.

Filtering by project path cannot fix that: a human running Claude Code inside a
registered project is precisely when nightshift must stay away. The only honest
discriminator is which session the transcript belongs to, and the CLI hands us
its ``session_id`` on both output formats.

This is a cache, not a record. Losing it makes nightshift shy for an hour, not
wrong, so every function here fails quiet.
"""

from __future__ import annotations

from nightshift.config import state_dir
from nightshift.store import read_json, write_json

#: Session ids kept. Only ones newer than the idle window matter, so this need
#: only outlive a night's runs — it is not history.
KEEP = 64


def path():
    return state_dir() / "sessions.json"


def ours() -> set[str]:
    """Session ids nightshift started."""
    data = read_json(path(), {})
    ids = data.get("ids") if isinstance(data, dict) else None
    return {str(i) for i in ids} if isinstance(ids, list) else set()


def record(session_id: str) -> None:
    """Remember that ``session_id`` was ours, not a human's."""
    session_id = (session_id or "").strip()
    if not session_id:
        return
    data = read_json(path(), {})
    ids = data.get("ids") if isinstance(data, dict) else None
    kept = [str(i) for i in ids] if isinstance(ids, list) else []
    if session_id in kept:
        return
    kept.append(session_id)
    try:
        write_json(path(), {"ids": kept[-KEEP:]})
    except OSError:
        # A run that cannot write this is still a correct run; the cost is one
        # idle window of unnecessary shyness.
        pass
