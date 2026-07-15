"""Claude Code adapter, driven entirely through a mocked ``subprocess``.

Nothing here launches a real CLI or spends a token.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta

import pytest

from nightshift.adapters.claude_code import (
    ALLOWED_TOOLS,
    DISALLOWED_TOOLS,
    ClaudeCodeAdapter,
)


@pytest.fixture
def adapter():
    return ClaudeCodeAdapter()


class FakeProc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def envelope(text: str) -> str:
    return json.dumps({"type": "result", "is_error": False, "result": text})


@pytest.fixture
def spy(monkeypatch):
    """Capture the subprocess call and return a scripted result."""
    calls: list[dict] = []
    box = {"proc": FakeProc(stdout=envelope("- LOW a.py:1 — x")), "raises": None}

    def fake_run(cmd, **kwargs):
        calls.append({"cmd": cmd, **kwargs})
        if box["raises"] is not None:
            raise box["raises"]
        return box["proc"]

    monkeypatch.setattr(subprocess, "run", fake_run)
    return type("Spy", (), {"calls": calls, "box": box})()


# ---- read-only enforcement -------------------------------------------


def test_read_only_is_enforced_by_cli_flags(adapter, spy, project_dir):
    adapter.run("review this", project_dir, 600)
    cmd = spy.calls[0]["cmd"]

    assert "--allowed-tools" in cmd
    assert "--disallowed-tools" in cmd

    allowed = cmd[cmd.index("--allowed-tools") + 1 : cmd.index("--disallowed-tools")]
    assert allowed == list(ALLOWED_TOOLS)


def test_no_write_capable_tool_is_ever_allowed(adapter, spy, project_dir):
    adapter.run("review this", project_dir, 600)
    cmd = spy.calls[0]["cmd"]
    allowed = cmd[cmd.index("--allowed-tools") + 1 : cmd.index("--disallowed-tools")]

    # This is the product promise: 0 files touched.
    for tool in ("Bash", "Edit", "MultiEdit", "Write", "NotebookEdit"):
        assert tool not in allowed


def test_mutating_tools_are_explicitly_denied(adapter, spy, project_dir):
    adapter.run("review this", project_dir, 600)
    cmd = spy.calls[0]["cmd"]
    denied = cmd[cmd.index("--disallowed-tools") + 1 :]
    for tool in ("Bash", "Edit", "Write", "NotebookEdit"):
        assert tool in denied
    assert set(DISALLOWED_TOOLS).isdisjoint(set(ALLOWED_TOOLS))


def test_never_skips_permissions(adapter, spy, project_dir):
    adapter.run("review this", project_dir, 600)
    joined = " ".join(spy.calls[0]["cmd"])
    assert "--dangerously-skip-permissions" not in joined
    assert "--allow-dangerously-skip-permissions" not in joined
    assert "bypassPermissions" not in joined


def test_runs_headless_with_json_output(adapter, spy, project_dir):
    adapter.run("review this", project_dir, 600)
    cmd = spy.calls[0]["cmd"]
    assert cmd[0] == "claude"
    assert "--print" in cmd
    assert cmd[cmd.index("--output-format") + 1] == "json"


def test_prompt_carries_the_read_only_preamble(adapter, spy, project_dir):
    adapter.run("review this", project_dir, 600)
    prompt = spy.calls[0]["cmd"][2]
    assert "read-only" in prompt.lower()
    assert "review this" in prompt


def test_runs_in_the_project_directory(adapter, spy, project_dir):
    adapter.run("review this", project_dir, 600)
    assert spy.calls[0]["cwd"] == str(project_dir)


def test_stdin_is_closed_so_a_prompt_cannot_hang_cron(adapter, spy, project_dir):
    adapter.run("review this", project_dir, 600)
    assert spy.calls[0]["stdin"] is subprocess.DEVNULL


def test_timeout_is_passed_through(adapter, spy, project_dir):
    adapter.run("review this", project_dir, 42)
    assert spy.calls[0]["timeout"] == 42


def test_child_gets_its_own_process_group(adapter, spy, project_dir):
    # So a timeout kills the whole tree instead of orphaning children.
    adapter.run("review this", project_dir, 600)
    assert spy.calls[0]["start_new_session"] is True


# ---- output handling --------------------------------------------------


def test_extracts_result_text_from_the_json_envelope(adapter, spy, project_dir):
    spy.box["proc"] = FakeProc(stdout=envelope("- HIGH auth.py:1 — no expiry"))
    result = adapter.run("p", project_dir, 600)
    assert result.status == "ok"
    assert result.findings_md == "- HIGH auth.py:1 — no expiry"


def test_malformed_json_keeps_raw_stdout_as_findings(adapter, spy, project_dir):
    # A completed run cost quota — never discard it.
    spy.box["proc"] = FakeProc(stdout="- HIGH a.py:1 — not json but useful")
    result = adapter.run("p", project_dir, 600)
    assert result.status == "ok"
    assert result.findings_md == "- HIGH a.py:1 — not json but useful"


def test_unexpected_envelope_shape_keeps_raw_stdout(adapter, spy, project_dir):
    spy.box["proc"] = FakeProc(stdout=json.dumps({"surprise": "new schema"}))
    result = adapter.run("p", project_dir, 600)
    assert result.status == "ok"
    assert "new schema" in result.findings_md


def test_json_array_output_keeps_raw_stdout(adapter, spy, project_dir):
    spy.box["proc"] = FakeProc(stdout=json.dumps([{"result": "x"}]))
    result = adapter.run("p", project_dir, 600)
    assert result.status == "ok"
    assert result.findings_md.startswith("[")


def test_empty_output_is_a_failure(adapter, spy, project_dir):
    spy.box["proc"] = FakeProc(stdout="   ")
    result = adapter.run("p", project_dir, 600)
    assert result.status == "failed"
    assert result.detail == "no output"


def test_records_duration_and_start_time(adapter, spy, project_dir):
    before = datetime.now()
    result = adapter.run("p", project_dir, 600)
    assert before <= result.started_at <= datetime.now()
    assert result.duration_s >= 0


# ---- failure modes ----------------------------------------------------


def test_timeout_is_reported_as_timeout(adapter, spy, project_dir):
    spy.box["raises"] = subprocess.TimeoutExpired(cmd="claude", timeout=600)
    result = adapter.run("p", project_dir, 600)
    assert result.status == "timeout"
    assert "600s" in result.detail


def test_nonzero_exit_is_a_failure_naming_the_reason(adapter, spy, project_dir):
    spy.box["proc"] = FakeProc(returncode=1, stderr="Invalid API key\nmore detail")
    result = adapter.run("p", project_dir, 600)
    assert result.status == "failed"
    assert result.detail == "Invalid API key"


def test_nonzero_exit_still_keeps_any_output(adapter, spy, project_dir):
    spy.box["proc"] = FakeProc(returncode=2, stdout="partial findings", stderr="boom")
    result = adapter.run("p", project_dir, 600)
    assert result.status == "failed"
    assert result.findings_md == "partial findings"


def test_missing_binary_is_a_failure_not_a_crash(adapter, spy, project_dir):
    spy.box["raises"] = FileNotFoundError()
    result = adapter.run("p", project_dir, 600)
    assert result.status == "failed"
    assert "not on PATH" in result.detail


def test_os_error_is_a_failure_not_a_crash(adapter, spy, project_dir):
    spy.box["raises"] = OSError("exec format error")
    result = adapter.run("p", project_dir, 600)
    assert result.status == "failed"
    assert "could not start" in result.detail


def test_missing_project_dir_fails_before_spawning(adapter, spy, tmp_path):
    result = adapter.run("p", tmp_path / "gone", 600)
    assert result.status == "failed"
    assert "does not exist" in result.detail
    assert spy.calls == []  # never spent quota


# ---- availability -----------------------------------------------------


def test_unavailable_when_not_on_path(adapter, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    availability = adapter.availability()
    assert availability.ok is False
    assert "not on PATH" in availability.reason
    assert adapter.available() is False


def test_available_when_version_succeeds(adapter, spy, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/usr/local/bin/claude")
    spy.box["proc"] = FakeProc(stdout="2.0.1 (Claude Code)")
    assert adapter.available() is True
    assert adapter.availability().reason == "2.0.1 (Claude Code)"


def test_unavailable_when_version_fails(adapter, spy, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/usr/local/bin/claude")
    spy.box["proc"] = FakeProc(returncode=1, stderr="not logged in")
    availability = adapter.availability()
    assert availability.ok is False
    assert "not logged in" in availability.reason


def test_unavailable_when_version_hangs(adapter, spy, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/usr/local/bin/claude")
    spy.box["raises"] = subprocess.TimeoutExpired(cmd="claude", timeout=20)
    assert adapter.availability().ok is False


# ---- idle detection ---------------------------------------------------


def test_last_human_use_is_none_when_claude_never_ran(adapter, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "nightshift.adapters.claude_code.CLAUDE_PROJECTS_DIR", tmp_path / "absent"
    )
    # No directory means a fresh install, which reads as idle — not as busy.
    assert adapter.last_human_use() is None


def test_last_human_use_is_none_for_an_empty_dir(adapter, tmp_path, monkeypatch):
    empty = tmp_path / "projects"
    empty.mkdir()
    monkeypatch.setattr("nightshift.adapters.claude_code.CLAUDE_PROJECTS_DIR", empty)
    assert adapter.last_human_use() is None


def _age(path, when: datetime) -> None:
    import os

    os.utime(path, (when.timestamp(), when.timestamp()))


def test_last_human_use_finds_the_newest_mtime(adapter, tmp_path, monkeypatch):
    root = tmp_path / "projects"
    (root / "proj-a").mkdir(parents=True)
    old = root / "proj-a" / "old.jsonl"
    new = root / "proj-a" / "new.jsonl"
    old.write_text("{}", encoding="utf-8")
    new.write_text("{}", encoding="utf-8")

    now = datetime.now()
    recent = now - timedelta(minutes=3)
    # Age the whole tree: a session five hours old leaves no fresh mtimes
    # anywhere, directories included.
    _age(old, now - timedelta(hours=5))
    _age(root / "proj-a", now - timedelta(hours=5))
    _age(new, recent)

    monkeypatch.setattr("nightshift.adapters.claude_code.CLAUDE_PROJECTS_DIR", root)
    found = adapter.last_human_use()
    assert found is not None
    assert abs(found.timestamp() - recent.timestamp()) < 2


def test_directory_mtimes_count_as_human_use(adapter, tmp_path, monkeypatch):
    # Writing a session file bumps its parent directory too, so directories are
    # evidence of activity in their own right. Erring toward "busy" keeps
    # nightshift out of the user's way.
    root = tmp_path / "projects"
    (root / "proj-a").mkdir(parents=True)

    now = datetime.now()
    _age(root / "proj-a", now - timedelta(minutes=2))

    monkeypatch.setattr("nightshift.adapters.claude_code.CLAUDE_PROJECTS_DIR", root)
    found = adapter.last_human_use()
    assert found is not None
    assert abs(found.timestamp() - (now - timedelta(minutes=2)).timestamp()) < 2
