from __future__ import annotations

import json
import time

import pytest

from nightshift.lock import Lock, LockBusy


def test_acquire_creates_and_release_removes(tmp_path):
    lock = Lock(tmp_path / "lock", timeout_s=600)
    lock.acquire()
    assert (tmp_path / "lock").exists()
    lock.release()
    assert not (tmp_path / "lock").exists()


def test_second_acquire_is_refused(tmp_path):
    path = tmp_path / "lock"
    first = Lock(path, timeout_s=600)
    first.acquire()
    with pytest.raises(LockBusy, match="in progress"):
        Lock(path, timeout_s=600).acquire()
    first.release()


def test_release_after_refusal_lets_the_next_run_in(tmp_path):
    path = tmp_path / "lock"
    first = Lock(path, timeout_s=600)
    first.acquire()
    first.release()
    second = Lock(path, timeout_s=600)
    second.acquire()  # must not raise
    second.release()


def test_context_manager_releases_on_exception(tmp_path):
    path = tmp_path / "lock"
    with pytest.raises(RuntimeError):
        with Lock(path, timeout_s=600):
            raise RuntimeError("boom")
    assert not path.exists()


def test_stale_lock_is_broken_and_reacquired(tmp_path):
    path = tmp_path / "lock"
    # A run that was killed 3× the timeout ago and never cleaned up.
    stale_age = time.time() - (600 * 3)
    path.write_text(json.dumps({"pid": 999999, "acquired_at": stale_age}), encoding="utf-8")

    lock = Lock(path, timeout_s=600)
    assert lock.is_stale() is True
    lock.acquire()  # must not raise
    assert lock.read().pid != 999999
    lock.release()


def test_lock_just_under_stale_threshold_still_blocks(tmp_path):
    path = tmp_path / "lock"
    # 2× timeout is the threshold; a hair under it is still a live run.
    recent = time.time() - (600 * 2) + 30
    path.write_text(json.dumps({"pid": 999999, "acquired_at": recent}), encoding="utf-8")
    lock = Lock(path, timeout_s=600)
    assert lock.is_stale() is False
    with pytest.raises(LockBusy):
        lock.acquire()


def test_stale_threshold_scales_with_configured_timeout(tmp_path):
    path = tmp_path / "lock"
    age = time.time() - 700
    path.write_text(json.dumps({"pid": 1, "acquired_at": age}), encoding="utf-8")

    # A 600s-timeout run goes stale at 1200s — 700s is still live.
    assert Lock(path, timeout_s=600).is_stale() is False
    # A 60s-timeout run goes stale at 120s — 700s is long abandoned.
    assert Lock(path, timeout_s=60).is_stale() is True


def test_unreadable_lock_falls_back_to_mtime_and_can_go_stale(tmp_path):
    path = tmp_path / "lock"
    path.write_text("this is not json", encoding="utf-8")
    import os

    old = time.time() - (600 * 3)
    os.utime(path, (old, old))

    lock = Lock(path, timeout_s=600)
    assert lock.is_stale() is True
    lock.acquire()  # a garbage lock must not wedge nightshift forever
    lock.release()


def test_fresh_unreadable_lock_still_blocks(tmp_path):
    path = tmp_path / "lock"
    path.write_text("this is not json", encoding="utf-8")
    with pytest.raises(LockBusy):
        Lock(path, timeout_s=600).acquire()


def test_release_is_idempotent_and_never_steals(tmp_path):
    path = tmp_path / "lock"
    holder = Lock(path, timeout_s=600)
    holder.acquire()

    # A Lock that never acquired must not delete someone else's lockfile.
    other = Lock(path, timeout_s=600)
    other.release()
    assert path.exists()

    holder.release()
    holder.release()
    assert not path.exists()


def test_read_returns_none_when_absent(tmp_path):
    assert Lock(tmp_path / "nope", timeout_s=600).read() is None
    assert Lock(tmp_path / "nope", timeout_s=600).is_stale() is False
