"""The README's hero image may only show output the CLI prints.

`docs/demo.svg` is the first thing anyone sees, on the README and on the PyPI
page. Its transcript is a constant in `docs/make-demo.py`, whose docstring said
"every line below is output the CLI genuinely prints" while the lines read
``path · 267 — text`` and `_echo_finding` printed ``path:line · text``.

It had been wrong for a while. Nothing caught it, because a list of strings in a
.py file is compared to nothing — the same reason the hero replayed an invented
log for months, and the og:image cited findings from a run that no longer
existed. Every one of those was true when it was typed. That is the failure
mode, and typing is the common factor.

The captures in `docs/shots/` are the only thing in this repo that came out of
the CLI rather than out of someone's memory. So they are the reference.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "shots"
MAKE_DEMO = ROOT / "docs" / "make-demo.py"

SGR = re.compile(r"\x1b\[[0-9;]*m")

#: A shell prompt is the person typing, not the CLI answering.
PROMPT = re.compile(r"^\$ ")
#: Lines whose shape the CLI composes rather than copies — checked separately.
CONSTRUCTED = re.compile(r"^\s*(ok|failed|timeout)\s|^\s+\d+ finding|^~/nightaudit-reports/")


@pytest.fixture(scope="module")
def captured() -> str:
    """Every line the CLI has actually printed, across all captures."""
    text = []
    for shot in sorted(SHOTS.glob("*.txt")):
        text.append(SGR.sub("", shot.read_text(encoding="utf-8")))
    return "\n".join(text)


@pytest.fixture(scope="module")
def transcript() -> list[str]:
    """The demo's lines, read out of the module rather than imported.

    make-demo.py is a script with a hyphen in its name; importing it needs
    importlib gymnastics that would obscure what this test is doing.
    """
    source = MAKE_DEMO.read_text(encoding="utf-8")
    block = re.search(r"TRANSCRIPT: list\[.*?\] = \[(.*?)^\]", source, re.S | re.M)
    assert block, "cannot find TRANSCRIPT in make-demo.py"
    return [
        m.group(1).replace('\\"', '"').replace("\\\\", "\\")
        for m in re.finditer(r'\("((?:[^"\\]|\\.)*)"', block.group(1))
    ]


def test_the_transcript_was_found(transcript):
    assert len(transcript) > 5, f"only parsed {len(transcript)} lines; the regex has drifted"


def test_every_line_of_the_demo_was_printed_by_the_cli(transcript, captured):
    """The one that would have caught it.

    A line that is not in any capture is a line someone typed from memory, and
    memory is what put a two-month-old format at the top of the README.
    """
    invented = [
        line
        for line in transcript
        if not PROMPT.match(line) and not CONSTRUCTED.match(line) and line not in captured
    ]

    assert not invented, (
        "docs/demo.svg shows lines no capture contains:\n  "
        + "\n  ".join(invented)
        + "\n\nCopy them from docs/shots/, or recapture — see docs/RECORDING.md."
    )


def test_the_findings_use_the_format_the_cli_prints_today(transcript):
    """Pinned to `_echo_finding`'s shape: `emoji SEV path:line · text`.

    The old transcript read `path · 267 — text`, which is a format this CLI has
    not printed for some time. Asserting the current one means the next change
    to `_echo_finding` fails here rather than shipping to the README.
    """
    findings = [l for l in transcript if re.search(r"(🔴|🟠|🟡)", l)]

    assert findings, "the demo shows no findings; it is meant to show the payoff"
    for line in findings:
        assert re.search(r"(🔴|🟠|🟡)\s+(HIGH|MED|LOW)\s+\S+\.py:\d+ · ", line), (
            f"not the format _echo_finding prints: {line!r}"
        )


def test_the_summary_numbers_match_the_run_it_claims(transcript, captured):
    """The `ok … (claude_code, 2m52s)` / `4 findings` pair is composed from
    cli.py's f-string, so it cannot be matched verbatim against a capture. Its
    numbers still have to be a run that happened — the transcript said `2m18s`
    and `7 findings` about a review that had already been replaced."""
    summary = " ".join(l for l in transcript if CONSTRUCTED.match(l))
    duration = re.search(r"\((?:\w+), (\d+m\d+s)\)", summary)
    count = re.search(r"(\d+) findings?", summary)

    assert duration and count, f"cannot read the summary numbers from: {summary!r}"
    assert duration.group(1) in captured, (
        f"the demo claims a {duration.group(1)} run; no capture shows one"
    )
    assert f"{count.group(1)} findings" in captured, (
        f"the demo claims {count.group(1)} findings; no capture shows that"
    )
