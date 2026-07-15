"""Provider adapters.

Each adapter wraps one AI coding CLI the user already pays for. Adapters are
strictly read-only: they may inspect a project, never modify it.
"""

from __future__ import annotations

from nightshift.adapters.base import Adapter, AdapterError, RunResult, Status
from nightshift.adapters.claude_code import ClaudeCodeAdapter
from nightshift.adapters.codex import CodexAdapter
from nightshift.adapters.copilot import CopilotAdapter

_REGISTRY: dict[str, type] = {
    "claude_code": ClaudeCodeAdapter,
    "codex": CodexAdapter,
    "copilot": CopilotAdapter,
}


def get(name: str) -> Adapter:
    """Instantiate the adapter registered under ``name``."""
    try:
        cls = _REGISTRY[name]
    except KeyError:
        known = ", ".join(sorted(_REGISTRY))
        raise AdapterError(f"unknown provider {name!r} — known: {known}") from None
    return cls()  # type: ignore[return-value]


def names() -> list[str]:
    return sorted(_REGISTRY)


__all__ = [
    "Adapter",
    "AdapterError",
    "ClaudeCodeAdapter",
    "CodexAdapter",
    "CopilotAdapter",
    "RunResult",
    "Status",
    "get",
    "names",
]
