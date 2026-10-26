"""Observable, cancellable read-only startup work.

An abandoned reader never publishes partial results or mutates caller state.
Original cache files are not truncated, rewritten or deleted by this module.
"""
from __future__ import annotations
from datetime import datetime
import json
from pathlib import Path
import threading
import time

from stop_control import check_stop

CACHE_SECONDS = 10.0
SCAN_SECONDS = 120.0
MAX_CACHE_BYTES = 64 * 1024 * 1024
MAX_RECORD_BYTES = 1024 * 1024


class StartupBudgetExceeded(RuntimeError):
    pass


def observed_read(label, work, *, seconds=CACHE_SECONDS, progress=None):
    """Run work(update_counts, check_cancelled) under an absolute deadline.

    The supervisor prints a heartbeat even when a filesystem call is blocked.
    Work must be read-only and must return private, unpublished results.
    """
    started = time.monotonic()
    deadline = started + max(0.0, float(seconds))
    cancelled = threading.Event()
    finished = threading.Event()
    lock = threading.Lock()
    counts = {}
    result = {}

    def update(**values):
        with lock:
            counts.update(values)

    def check():
        if cancelled.is_set():
            raise StartupBudgetExceeded("Startup read cancelled")

    def emit(state):
        if progress is None:
            return
        with lock:
            snapshot = dict(counts)
        detail = "; ".join(f"{key}={value:,}" for key, value in snapshot.items())
        stamp = datetime.now().astimezone().strftime("%H:%M:%S")
        progress(f"{label}: {state} | elapsed {time.monotonic()-started:.1f}s"
                 f" | time {stamp}" + (" | " + detail if detail else ""))

    def read():
        try:
            result["value"] = work(update, check)
        except BaseException as error:
            result["error"] = error
        finally:
            finished.set()

    check_stop()
    emit("started")
    threading.Thread(target=read, daemon=True, name="startup-read-only").start()
    next_heartbeat = started + 1.0
    try:
        while not finished.wait(min(.1, max(0.0, deadline-time.monotonic()))):
            check_stop()
            now = time.monotonic()
            if now >= deadline:
                emit("budget exceeded; incomplete results discarded")
                raise StartupBudgetExceeded(f"{label} exceeded {seconds:g}s; no partial results used")
            if now >= next_heartbeat:
                emit("working")
                next_heartbeat = now + 1.0
        check_stop()
        if time.monotonic() >= deadline:
            raise StartupBudgetExceeded(f"{label} exceeded {seconds:g}s; no partial results used")
        if "error" in result:
            raise result["error"]
        emit("complete")
        return result["value"]
    finally:
        cancelled.set()


def read_jsonl_snapshot(path, build, consume, *, label, progress=None,
                        seconds=CACHE_SECONDS, max_bytes=MAX_CACHE_BYTES,
                        max_record_bytes=MAX_RECORD_BYTES,on_invalid=None):
    """Return a complete cache snapshot; callers may ignore unavailable caches.

    Malformed short rows remain tolerated for compatibility with interrupted
    journals. Oversize input cannot allocate an unbounded string or publish a
    partial cache that misses later invalidations.
    """
    path = Path(path)

    def read(update, check):
        data = build()
        entries = consumed = invalid = 0
        try:
            source = path.open("rb")
        except FileNotFoundError:
            return data
        with source:
            while True:
                check()
                raw = source.readline(max_record_bytes + 1)
                if not raw:
                    break
                consumed += len(raw)
                if len(raw) > max_record_bytes or consumed > max_bytes:
                    raise StartupBudgetExceeded(f"{label} exceeds the safe cache read limit; original file preserved")
                check()
                entries += 1
                try:
                    consume(data, json.loads(raw.decode("utf-8")))
                except (ValueError, KeyError, TypeError, AttributeError, UnicodeError):
                    invalid += 1
                    if on_invalid is not None:on_invalid(data)
                if entries % 250 == 0:
                    update(entries=entries, bytes=consumed, invalid=invalid)
        check()
        update(entries=entries, bytes=consumed, invalid=invalid)
        return data

    return observed_read(label, read, seconds=seconds, progress=progress)
