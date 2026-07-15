"""A cooperative lockfile so two cron ticks never run at once."""

from __future__ import annotations

import errno
import json
import os
import time as _time
from dataclasses import dataclass
from pathlib import Path

from nightshift.config import state_dir

#: A lock older than ``STALE_MULTIPLIER × run.timeout_s`` is presumed abandoned.
STALE_MULTIPLIER = 2


def lock_path() -> Path:
    return state_dir() / "lock"


class LockBusy(Exception):
    """Another nightshift run holds the lock."""


@dataclass
class LockInfo:
    pid: int
    acquired_at: float

    @property
    def age_s(self) -> float:
        return max(0.0, _time.time() - self.acquired_at)


class Lock:
    """An exclusive lock built on ``O_CREAT | O_EXCL``.

    Stale locks — left behind by a run that was killed before it could clean up
    — are broken automatically once they exceed twice the run timeout, which is
    strictly longer than any healthy run can survive.
    """

    def __init__(self, path: Path | None = None, timeout_s: int = 600):
        self.path = path or lock_path()
        self.timeout_s = timeout_s
        self._held = False

    @property
    def stale_after_s(self) -> float:
        return self.timeout_s * STALE_MULTIPLIER

    def read(self) -> LockInfo | None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return LockInfo(pid=int(data["pid"]), acquired_at=float(data["acquired_at"]))
        except FileNotFoundError:
            return None
        except (json.JSONDecodeError, KeyError, ValueError, OSError, TypeError):
            # An unreadable lock is indistinguishable from an abandoned one; fall
            # back to its mtime so it can still go stale and be broken.
            try:
                return LockInfo(pid=-1, acquired_at=self.path.stat().st_mtime)
            except OSError:
                return None

    def is_stale(self, info: LockInfo | None = None) -> bool:
        info = info or self.read()
        return info is not None and info.age_s > self.stale_after_s

    def _write(self) -> None:
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"pid": os.getpid(), "acquired_at": _time.time()}, fh)

    def acquire(self) -> None:
        """Take the lock, breaking it first if it has gone stale.

        Raises :class:`LockBusy` if a live run holds it.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._write()
            self._held = True
            return
        except FileExistsError:
            pass
        except OSError as exc:  # pragma: no cover - platform dependent
            if exc.errno != errno.EEXIST:
                raise

        info = self.read()
        if info is None:
            # Vanished between the failed create and the read — retry once.
            try:
                self._write()
                self._held = True
                return
            except FileExistsError:
                raise LockBusy("another nightshift run just took the lock") from None

        if not self.is_stale(info):
            raise LockBusy(
                f"another nightshift run is in progress (pid {info.pid}, "
                f"started {info.age_s:.0f}s ago)"
            )

        self.break_stale()
        try:
            self._write()
            self._held = True
        except FileExistsError:
            raise LockBusy("another nightshift run just took the lock") from None

    def break_stale(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    def release(self) -> None:
        if not self._held:
            return
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        self._held = False

    def __enter__(self) -> Lock:
        self.acquire()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.release()
