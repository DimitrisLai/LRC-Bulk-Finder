"""Regression tests for Alpha 3 gaps. Synthetic processes/network/files only."""
from __future__ import annotations

import os
import queue
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import LRC_Bulk_Finder as engine
from LRC_Control_Center import ControlCenter
from TEST_V300_LRCLIB_DEADLINE import SlowResponse
import worker_stop


class Value:
    def __init__(self, value=""):
        self.value = value
    def get(self):
        return self.value
    def set(self, value):
        self.value = value


class StopStateTests(unittest.TestCase):
    """Use real ControlCenter methods without requiring a graphical desktop."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        a = self.app = ControlCenter.__new__(ControlCenter)
        a.tk = None
        a.process = None
        a._stopping_process = None
        a._stop_context = None
        a._stop_verification_failed = False
        a._hardstop_pending = True
        a._stop_cleanup_deferred = False
        a._stop_kill_attempted = True
        a.stop_requested = True
        a.active_profile = a.active_folder = a.active_action = None
        a.messages = queue.Queue()
        a.phase = Value()
        a.progress_text = Value()
        a.stop_button = mock.Mock()
        a.after = mock.Mock()
        a._line = mock.Mock()
        a._refresh_review_background = mock.Mock()
        a._manager_cleanup_selection = mock.Mock()
        a._dialog = mock.Mock(return_value=True)
        a.stop_directory = Path(self.tmp.name) / "stop"
        a.stop_directory.mkdir()
        a.stop_path = a.stop_directory / "stop.request"
        a.stop_path.write_text("STOP", encoding="ascii")
        self.proc = mock.Mock()
        self.proc.poll.return_value = 137
        a.process = a._stopping_process = self.proc

    def test_exited_worker_stays_verifying_until_tree_result(self):
        self.app._poll()
        self.assertIn("verif", self.app.phase.get().lower())
        self.assertNotIn("Stopped by user", self.app.phase.get())

    def test_failed_tree_result_blocks_restart_retains_marker_and_offers_retry(self):
        self.app.messages.put(("hardstop_result", (self.proc, False, "child still alive")))
        self.app._poll()
        self.assertTrue(self.app._stop_verification_failed)
        self.assertIn("NOT VERIFIED", self.app.phase.get())
        self.assertTrue(self.app.stop_path.is_file())
        self.app.stop_button.configure.assert_any_call(state="normal", text="RETRY STOP")
        self.app._run_profile()
        self.app._dialog.assert_called_once()

    def test_stale_stop_result_cannot_clear_new_stop_or_its_marker(self):
        old = mock.Mock()
        old.poll.return_value = 137
        self.proc.poll.return_value = None
        self.app.messages.put(("hardstop_result", (old, True, "old run")))
        self.app._poll()
        self.assertTrue(self.app._hardstop_pending)
        self.assertTrue(self.app.stop_path.is_file())

    def test_retry_is_available_even_when_direct_worker_has_exited(self):
        a = self.app
        a.process = None
        a._hardstop_pending = False
        a._stop_verification_failed = True
        a.stop_requested = True
        with mock.patch.object(a, "_hard_stop_worker") as stop:
            a._stop()
            until = time.monotonic() + 1
            while not stop.called and time.monotonic() < until:
                time.sleep(.01)
        stop.assert_called_once_with(self.proc)

    def test_stop_thread_exception_reports_failure_instead_of_staying_pending(self):
        with mock.patch("LRC_Control_Center.kill_search_process", side_effect=OSError("synthetic failure")):
            self.app._hard_stop_worker(self.proc)
        kind, (proc, success, detail) = self.app.messages.get_nowait()
        self.assertEqual(kind, "hardstop_result")
        self.assertIs(proc, self.proc)
        self.assertFalse(success)
        self.assertIn("synthetic failure", detail)


class NetworkBudgetGaps(unittest.TestCase):
    def test_rate_limit_wait_cannot_outlast_active_lrclib_budget(self):
        with mock.patch.object(engine, "next_available", {"LRCLIB": time.monotonic() + .4}), \
             mock.patch.object(engine, "LRCLIB_LAST_FINISHED", 0), \
             mock.patch.object(engine, "LRCLIB_ACTIVE_DEADLINE", time.monotonic() + .035), \
             mock.patch.object(engine.urllib.request, "urlopen") as request:
            started = time.monotonic()
            with self.assertRaises(engine.ProviderFailure):
                engine.direct_get("LRCLIB", "https://example.invalid/search", {"q": "synthetic"})
            self.assertLess(time.monotonic() - started, .2)
            request.assert_not_called()

    def test_local_database_time_does_not_consume_online_http_budget(self):
        def offline(*args):
            time.sleep(.06)
        with mock.patch.object(engine, "LOCAL_LRCLIB", object()), \
             mock.patch.object(engine, "STAGED_ONLINE_MODE", False), \
             mock.patch.object(engine, "LRCLIB_ONLINE_FALLBACK", True), \
             mock.patch.object(engine, "LRCLIB_EXACT_FALLBACK", False), \
             mock.patch.object(engine, "LRCLIB_SONG_BUDGET_SECONDS", .035), \
             mock.patch.object(engine, "LRCLIB_ACTIVE_DEADLINE", time.monotonic() + .035), \
             mock.patch.object(engine, "LRCLIB_LAST_FINISHED", 0), \
             mock.patch.object(engine, "local_lrclib_search", side_effect=offline), \
             mock.patch.object(engine, "query_variants", return_value=[("Song", "Artist")]), \
             mock.patch.object(engine, "wait_for"), \
             mock.patch.object(engine.urllib.request, "urlopen", return_value=SlowResponse(0)):
            self.assertIsNone(engine.provider_lrclib("Song", "Artist", "", 120, engine.CandidateReview()))

    def test_completion_after_deadline_cannot_be_accepted_as_no_match(self):
        clock = [0.0]
        def start_thread(*, target, **kwargs):
            def complete():
                target()
                clock[0] = 2.0
            return mock.Mock(start=complete)
        with mock.patch.object(engine.time, "monotonic", side_effect=lambda: clock[0]), \
             mock.patch.object(engine.threading, "Thread", side_effect=start_thread), \
             mock.patch.object(engine.urllib.request, "urlopen", return_value=SlowResponse(0)):
            with self.assertRaises(engine.ProviderFailure):
                engine.bounded_lrclib_http(object(), 1.0)


class StopContextTests(unittest.TestCase):
    def test_cooperative_parent_exit_still_terminates_pinned_children(self):
        worker = mock.Mock(pid=4100)
        alive = [True]
        worker.poll.side_effect = lambda: None if alive[0] else 0
        context = worker_stop.StopContext()
        order = []
        def snapshot():
            order.append("snapshot")
            return {4100: 1, 4101: 4100} if alive[0] else {4101: 1}
        def cancel():
            order.append("marker")
            alive[0] = False
        with mock.patch.object(worker_stop,"_windows_snapshot_with_retry",side_effect=snapshot), \
             mock.patch.object(worker_stop,"_pin_windows_children",return_value={4101: "pinned-handle"}), \
             mock.patch.object(worker_stop,"_pinned_windows_children_running",return_value=set()) as terminate:
            ok, detail = worker_stop.kill_search_process(worker, "nt", context=context, request_stop=cancel)
        self.assertTrue(ok,detail)
        self.assertEqual(order[:2],["snapshot","marker"])
        terminate.assert_called_once_with({4101:"pinned-handle"},terminate=True)

    def test_retry_keeps_original_child_identity_after_parent_exit(self):
        worker = mock.Mock(pid=4100)
        worker.poll.return_value = 0
        context = worker_stop.StopContext()
        context.captured = True
        context.owned = {4101}
        context.handles = {4101:"original-process-handle"}
        with mock.patch.object(worker_stop,"_windows_snapshot_with_retry",return_value={4101:1}), \
             mock.patch.object(worker_stop,"_pinned_windows_children_running",side_effect=[{4101},set()]):
            first, _ = worker_stop.kill_search_process(worker,"nt",context=context)
            second, _ = worker_stop.kill_search_process(worker,"nt",context=context)
        self.assertFalse(first)
        self.assertTrue(second)

    def test_already_exited_unknown_tree_never_claimed_verified(self):
        worker = mock.Mock()
        worker.poll.return_value = 0
        ok,detail = worker_stop.kill_search_process(worker)
        self.assertFalse(ok)
        self.assertIn("could not be verified",detail)


if __name__ == "__main__":
    unittest.main()
