"""Explicit offline QA entry points for the two frozen Windows executables.

Only disposable fixtures below tempfile.gettempdir() are accepted. No external
providers or user music are read. Fixture stage names describe synthetic
blocking workloads, not recordings of real provider outages.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time


def fixture(root, stage, depth):
    root = Path(root).resolve()
    if (root.parent != Path(tempfile.gettempdir()).resolve() or
            not root.name.startswith("lrc_alpha4_smoke_") or depth not in (0, 1, 2)):
        raise ValueError("Only disposable Alpha 4 QA fixtures are permitted")
    if depth < 2:
        subprocess.Popen([sys.executable, "--qa-stop-fixture", str(root),
                          "--qa-stage", stage, "--qa-depth", str(depth + 1)])
    (root / f"pid-{depth}").write_text(str(os.getpid()), encoding="ascii")
    print(f"QA synthetic {stage} depth={depth}", flush=True)
    # Every process inherits stdout. STOP must terminate the full observed
    # frozen parent/child/grandchild tree, without relying on pipe EOF.
    time.sleep(120)
    return 0


def smoke(report):
    if os.name != "nt" or not getattr(sys, "frozen", False):
        raise RuntimeError("Run this QA through the frozen Windows Control Center")
    # The worker's QA fixture does not need to bundle the entire GUI stack.
    from importlib import import_module
    ControlCenter = import_module("LRC_Control_Center").ControlCenter
    from worker_stop import _windows_process_table_toolhelp
    from runtime_paths import program_folder
    results = []
    with tempfile.TemporaryDirectory(prefix="lrc_alpha4_smoke_") as td:
        root = Path(td)
        os.environ["APPDATA"] = str(root / "appdata")
        music = root / "music"
        music.mkdir()
        # 5,000 candidates exercise the genuine background inventory scanner.
        for index in range(5000):
            (music / f"Song {index}.candidate.lrc").write_text("[00:01.00] synthetic\n", encoding="utf-8")
        original = music / "Δοκιμή — original.wav"
        original.write_bytes(b"synthetic immutable audio sentinel")
        lrc = original.with_suffix(".lrc")
        lrc.write_text("[00:01.00] original preserved\n", encoding="utf-8")
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in music.iterdir()}
        app = ControlCenter()
        app.withdraw()
        app.folder.set(str(music))
        app._dialog = lambda *args, **kwargs: True
        heartbeat = [0]
        def tick():
            heartbeat[0] += 1
            app.after(30, tick)
        app.after(30, tick)
        try:
            for stage in ("preflight", "slow-network-read", "provider-cooldown"):
                for pidfile in root.glob("pid-*"):
                    pidfile.unlink()
                app.stop_requested = False
                app._stop_verification_failed = False
                app._stopping_process = None
                app._stop_context = None
                app.stop_directory = root / "marker"
                app.stop_directory.mkdir(exist_ok=True)
                app.stop_path = app.stop_directory / "stop.request"
                worker = subprocess.Popen(
                    [str(program_folder() / "LRC_Bulk_Finder_Worker.exe"),
                     "--qa-stop-fixture", str(root), "--qa-stage", stage],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    encoding="utf-8", errors="replace",
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                app.process = worker
                threading.Thread(target=app._read_process, args=(worker,), daemon=True).start()
                try:
                    limit = time.monotonic() + 40
                    while len(list(root.glob("pid-*"))) < 3:
                        app.update()
                        if worker.poll() is not None or time.monotonic() >= limit:
                            raise AssertionError("Synthetic frozen process tree did not start")
                        time.sleep(.01)
                    owned = {int(p.read_text()) for p in root.glob("pid-*")}
                    started = time.monotonic()
                    ticks = heartbeat[0]
                    app._stop()  # REAL GUI STOP and REAL worker_stop, no mocks.
                    callback_seconds = time.monotonic() - started
                    assert callback_seconds < .5, "STOP blocked the GUI callback"
                    while app._hardstop_pending or app.process is not None:
                        app.update()
                        if time.monotonic() - started > 20:
                            raise AssertionError("Frozen STOP exceeded 20 seconds")
                        time.sleep(.01)
                    assert not app._stop_verification_failed, app.phase.get()
                    assert "verified stopped" in app.phase.get(), app.phase.get()
                    table = _windows_process_table_toolhelp()
                    assert table is not None and not owned.intersection(table), "Owned child survived STOP"
                    assert heartbeat[0] > ticks, "Tk heartbeat stopped"
                    results.append({"stage": stage, "stop_seconds": round(time.monotonic() - started, 3),
                                    "callback_seconds": round(callback_seconds, 3), "heartbeat_ticks": heartbeat[0] - ticks,
                                    "known_worker_pids_absent": True})
                finally:
                    if worker.poll() is None:
                        subprocess.run(["taskkill", "/PID", str(worker.pid), "/T", "/F"],
                                       capture_output=True, timeout=15)
                    worker.wait(timeout=10)
            # Exercise supported appearance/language/scaling initialization.
            for scale in (1.0, 1.25, 1.5, 2.0):
                app.tk.call("tk", "scaling", scale * 96 / 72)
                for language in ("English", "Ελληνικά"):
                    app.language_choice.set(language)
                    app._language_selected()
                    for mode in ("Light", "Dark"):
                        app.appearance_choice.set(mode)
                        app._appearance_selected()
                        app.update()
            after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in music.iterdir()}
            assert before == after, "Synthetic originals or candidates changed"
            Path(report).write_text(json.dumps({"passed": True, "frozen_gui_and_worker": True,
                "synthetic_stages": results, "original_hashes_unchanged": len(before),
                "ui_scaling_language_theme_smoke": True}, indent=2), encoding="utf-8")
        finally:
            app.destroy()
    return 0
