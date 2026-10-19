"""v2.4.1 cross-platform cooperative GUI Stop request.

The GUI places a marker in a unique temporary directory passed by env var.
Works from windowed frozen EXEs on Windows WITHOUT a shared console;
does not rely on Ctrl+Break. Network request timeouts remain bounded.
"""
from __future__ import annotations
import os
import time
from pathlib import Path

def stop_file():
    value=os.environ.get("LRC_STOP_FILE","").strip()
    return Path(value) if value else None

def stop_requested():
    p=stop_file()
    return p is not None and p.is_file()

def check_stop():
    if stop_requested():
        raise KeyboardInterrupt("Stop requested by the Control Center")

def interruptible_sleep(seconds,poll=0.15):
    if stop_file() is None:
        # Preserve historical timing/rate-limit semantics for the CLI and
        # deterministic legacy tests. Polling is needed only for a GUI worker.
        time.sleep(max(0.0,float(seconds)))
        return
    deadline=time.monotonic()+max(0.0,float(seconds))
    while True:
        check_stop()
        remaining=deadline-time.monotonic()
        if remaining<=0:return
        time.sleep(min(poll,remaining))
