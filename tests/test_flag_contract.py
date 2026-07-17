"""Every flag we pass must exist on the CLI we pass it to.

This file exists because the Codex adapter shipped unusable. It passed
``--ask-for-approval never`` — a real flag, documented in the published
reference, next to flags this adapter also uses. It is interactive-only, and
``codex exec`` rejects it:

    error: unexpected argument '--ask-for-approval' found

So every Codex run died at argument parsing, before the model, every time. The
38 mocked tests were green throughout: they assert the flag reaches ``Popen``,
and it did. Mocking ``Popen`` means the CLI is never consulted about whether it
would have accepted any of it — the fake agrees with whatever we assumed. That
is the one question the rest of the suite structurally cannot ask, so it is the
only one asked here.

These tests spawn the real binaries, which is what ``no_real_subprocesses``
normally forbids. The invariant that fixture protects is *no test spends quota*,
not *no test ever spawns a CLI*: ``--help`` parses arguments and exits, reaching
no model and costing no tokens. Nothing here sends a prompt.

They skip when a CLI is absent rather than fail, so a contributor without both
installed is not blocked. That means CI only enforces this if CI installs them —
worth doing, because a skipped contract test protects nobody.
"""

from __future__ import annotations

import re
import shutil
import subprocess

import pytest

from nightaudit.adapters.claude_code import ClaudeCodeAdapter
from nightaudit.adapters.codex import CodexAdapter


def _flags(command: list[str]) -> list[str]:
    """The flag tokens in a built command, in order.

    A flag is a token that opens with a dash. Values do not: ``read-only`` and
    ``approval_policy=never`` are values, and the prompt is one long token of
    prose. Order is kept so a failure names flags the way a human would read
    them off the command line.
    """
    return [tok for tok in command if re.match(r"^-{1,2}[a-zA-Z]", tok)]


def _subcommands(command: list[str]) -> list[str]:
    """The words between the binary and the first flag.

    ``codex exec --sandbox …`` is help-documented at ``codex exec --help``, and
    the flags we care about are not on ``codex --help`` — that is precisely how
    ``--ask-for-approval`` slipped through, since it is real one level up.
    ``claude --print …`` has no subcommand and yields ``[]``.
    """
    out: list[str] = []
    for tok in command[1:]:
        if tok.startswith("-"):
            break
        out.append(tok)
    return out


def _help_text(command: list[str]) -> str:
    proc = subprocess.run(
        [command[0], *_subcommands(command), "--help"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return (proc.stdout or "") + (proc.stderr or "")


def _documents(help_text: str, flag: str) -> bool:
    """Does ``help_text`` list ``flag`` as a flag of its own?

    Bounded on both sides: a substring test would let ``--sandbox`` pass on a
    CLI that only offers ``--sandbox-mode``, and would find ``-c`` inside every
    hyphenated word in the prose.
    """
    return re.search(rf"(?<![\w-]){re.escape(flag)}(?![\w-])", help_text) is not None


def _require(binary: str) -> None:
    if shutil.which(binary) is None:
        pytest.skip(f"`{binary}` is not installed; nothing to check the contract against")


# The adapters, and every command shape each one builds. The Claude adapter
# emits a different flag set when streaming, and only one of the two is exercised
# by any given run — so both are named here rather than whichever came to mind.
CONTRACTS = [
    pytest.param(CodexAdapter(), lambda a: a.command("review this"), id="codex"),
    pytest.param(
        ClaudeCodeAdapter(), lambda a: a.command("review this"), id="claude_code-buffered"
    ),
    pytest.param(
        ClaudeCodeAdapter(),
        lambda a: a.command("review this", stream=True),
        id="claude_code-streaming",
    ),
]


@pytest.mark.parametrize("adapter,build", CONTRACTS)
def test_every_flag_we_pass_exists_on_the_cli(adapter, build, real_subprocess):
    command = build(adapter)
    _require(command[0])

    help_text = _help_text(command)
    unknown = [flag for flag in _flags(command) if not _documents(help_text, flag)]

    assert not unknown, (
        f"`{' '.join([command[0], *_subcommands(command)])}` does not document: "
        f"{', '.join(unknown)}.\n"
        f"The adapter would die at argument parsing on every run. Either the flag "
        f"was never valid here, or the CLI dropped it."
    )


@pytest.mark.parametrize("adapter,build", CONTRACTS)
def test_the_version_probe_behind_availability_works(adapter, build, real_subprocess):
    """``availability()`` gates every run on ``<binary> --version`` succeeding.

    It reports unavailable rather than raising when that probe fails, so a
    provider that broke here would not crash — it would go quiet, and quiet is
    indistinguishable from "no work due" in a digest nobody is watching.
    """
    _require(build(adapter)[0])

    result = adapter.availability()

    assert result.ok, f"{adapter.name} reports unavailable despite being installed: {result.reason}"


def test_the_contract_check_can_actually_fail(real_subprocess):
    """Guard the guard: a test that cannot fail is decoration.

    Pinned to the real bug. ``--ask-for-approval`` is what shipped, and it must
    still be rejected by whatever `codex exec` currently offers.
    """
    _require("codex")

    help_text = _help_text(["codex", "exec"])

    assert _documents(help_text, "--sandbox")
    assert not _documents(help_text, "--ask-for-approval")
