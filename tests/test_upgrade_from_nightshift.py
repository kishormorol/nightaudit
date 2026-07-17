"""Upgrading from 0.3.0 must not cost the user anything.

The rename changed every name a 0.3.0 install depends on at once: the command
cron calls, the directory holding config and budget history, the environment
variable, and the markers on the crontab block. Nothing failed loudly. `pipx
upgrade` deleted the `nightshift` binary, cron kept calling it hourly, and the
only evidence was a "command not found" in a log the tool exists to stop you
reading. No digest arrives — which is exactly what a quiet night looks like.

So these are not tests of a nicety. They cover the difference between an upgrade
and a silent stop, for users who will never read a release note.
"""

from __future__ import annotations

import click
import pytest

from nightaudit import cron
from nightaudit.cli import _warn_if_invoked_by_the_old_name
from nightaudit.config import state_dir


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A machine with no state and no overrides. `isolated_home` sets
    NIGHTAUDIT_HOME for every test, which would short-circuit all of this."""
    monkeypatch.delenv("NIGHTAUDIT_HOME", raising=False)
    monkeypatch.delenv("NIGHTSHIFT_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("os.path.expanduser", lambda p: p.replace("~", str(tmp_path), 1))
    return tmp_path


# ---- where the state lives -------------------------------------------


def test_a_03_install_keeps_its_history(home):
    """The upgrade case: only the old directory exists."""
    (home / ".nightshift").mkdir()

    assert state_dir() == home / ".nightshift"


def test_a_fresh_install_uses_the_new_name(home):
    assert state_dir() == home / ".nightaudit"


def test_the_new_directory_wins_when_both_exist(home):
    """`mv ~/.nightshift ~/.nightaudit` must be honoured, and a half-finished
    one must not silently keep reading the old ledger."""
    (home / ".nightshift").mkdir()
    (home / ".nightaudit").mkdir()

    assert state_dir() == home / ".nightaudit"


def test_the_old_env_var_is_still_an_explicit_answer(home, monkeypatch):
    """Someone who set NIGHTSHIFT_HOME meant it, and the upgrade did not
    un-mean it. Leftover directories must not outrank it."""
    (home / ".nightshift").mkdir()
    (home / ".nightaudit").mkdir()
    monkeypatch.setenv("NIGHTSHIFT_HOME", str(home / "elsewhere"))

    assert state_dir() == home / "elsewhere"


def test_the_new_env_var_beats_the_old_one(home, monkeypatch):
    monkeypatch.setenv("NIGHTSHIFT_HOME", str(home / "old"))
    monkeypatch.setenv("NIGHTAUDIT_HOME", str(home / "new"))

    assert state_dir() == home / "new"


def test_a_file_named_like_the_legacy_dir_is_not_a_state_dir(home):
    (home / ".nightshift").write_text("not a directory", encoding="utf-8")

    assert state_dir() == home / ".nightaudit"


def test_nothing_is_moved_or_created_just_by_asking(home):
    """state_dir() is a question, not an instruction.

    It is called by `status`, by every read, and by cron mid-run. If asking
    where the state lives relocated it, a run could rename the directory out
    from under another run that is writing to it.
    """
    (home / ".nightshift").mkdir()
    (home / ".nightshift" / "ledger.json").write_text("{}", encoding="utf-8")

    state_dir()
    state_dir()

    assert (home / ".nightshift" / "ledger.json").exists()
    assert not (home / ".nightaudit").exists()


# ---- the crontab block -----------------------------------------------


LEGACY_CRONTAB = """\
MAILTO=""
0 9 * * 1 /usr/bin/backup.sh
# nightshift (managed — edit via `nightshift init`)
0 * * * * /home/u/.local/bin/nightshift run    >> /tmp/nightshift-cron.log 2>&1
30 7 * * * /home/u/.local/bin/nightshift digest >> /tmp/nightshift-cron.log 2>&1
# end nightshift
"""


def test_init_replaces_the_old_block_rather_than_adding_a_second(home):
    """Both blocks present would leave the dead one failing hourly, under a
    marker promising it is managed."""
    result = cron.merged(LEGACY_CRONTAB, binary="/home/u/.local/bin/nightaudit")

    assert "nightshift run" not in result
    assert cron.LEGACY_MARKER not in result
    assert result.count(cron.MARKER) == 1


def test_replacing_the_old_block_keeps_the_users_own_lines(home):
    result = cron.merged(LEGACY_CRONTAB, binary="/home/u/.local/bin/nightaudit")

    assert "0 9 * * 1 /usr/bin/backup.sh" in result
    assert 'MAILTO=""' in result


def test_the_old_block_can_be_removed_outright(home):
    """Uninstall has to reach it too, or `crontab -e` is the only way out."""
    assert "nightshift" not in cron.strip_block(LEGACY_CRONTAB)


def test_an_unclosed_block_does_not_eat_the_rest_of_the_crontab(home):
    """A malformed block is the user's crontab, and losing their lines to a
    tidy-up is worse than leaving ours behind."""
    stripped = cron.strip_block(
        "# end nightshift\n0 9 * * 1 /usr/bin/backup.sh\n"
    )

    assert "backup.sh" in stripped


# ---- the deprecated alias --------------------------------------------


def test_the_old_command_says_it_was_renamed(monkeypatch, capsys):
    """0.3.0's cron calls this by absolute path. It is the only channel the tool
    has to an install whose owner is, by design, not watching."""
    monkeypatch.setattr("sys.argv", ["/home/u/.local/bin/nightshift", "run"])

    _warn_if_invoked_by_the_old_name()

    err = capsys.readouterr().err
    assert "`nightshift` is now `nightaudit`" in err
    assert "nightaudit init" in err


def test_the_notice_goes_to_stderr_so_it_cannot_corrupt_a_digest(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["nightshift", "digest", "--stdout"])

    _warn_if_invoked_by_the_old_name()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "nightaudit" in captured.err


def test_the_new_command_says_nothing(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["/home/u/.local/bin/nightaudit", "run"])

    _warn_if_invoked_by_the_old_name()

    assert capsys.readouterr().err == ""


def test_the_notice_never_fails_the_run(monkeypatch):
    """A deprecation notice that can break a run is worse than no notice.

    This fires on every cron tick of exactly the installs the alias exists to
    keep working, so a broken pipe or a closed stderr must cost the notice and
    nothing else.
    """
    monkeypatch.setattr("sys.argv", ["nightshift", "run"])
    monkeypatch.setattr(
        click, "echo", lambda *a, **k: (_ for _ in ()).throw(OSError("broken pipe"))
    )

    _warn_if_invoked_by_the_old_name()  # must not raise
