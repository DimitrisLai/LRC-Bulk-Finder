"""Stage 1 alpha 3: UI STOP must finish even when worker stdout never closes.

All GUI fixtures and processes are synthetic and disposable. No provider calls.
"""
from __future__ import annotations
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


class FakeExited:
    def __init__(self,code=137):
        self.returncode=code
    def poll(self):
        return self.returncode


def gui_available():
    try:
        import tkinter as tk
        app=tk.Tk();app.withdraw();app.destroy()
        return True
    except Exception:
        return False


@unittest.skipUnless(gui_available(),"Graphical desktop required")
class FastStopGuiTests(unittest.TestCase):
    def setUp(self):
        from LRC_Control_Center import ControlCenter
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env=mock.patch.dict(os.environ,{"APPDATA":self.temp.name})
        self.env.start();self.addCleanup(self.env.stop)
        self.app=ControlCenter()
        self.app.withdraw()
        self.addCleanup(self.app.destroy)
        self.root=Path(self.temp.name)/"music"
        self.root.mkdir()
        self.app.folder.set(str(self.root))

    def test_independent_process_exit_finalizes_without_pipe_eof(self):
        """No queued 'ended' event; old implementation stayed Stopping forever."""
        proc=FakeExited()
        self.app.process=proc
        self.app.stop_requested=True
        self.app.stop_button.configure(state="disabled")
        self.app._poll()
        self.assertIsNone(self.app.process)
        self.assertIn("Stopped by user",self.app.phase.get())
        self.assertEqual(str(self.app.stop_button.cget("state")),"disabled")

    def test_old_reader_ended_cannot_end_a_new_search(self):
        old=FakeExited()
        new=FakeExited(code=0)
        self.app.process=new
        self.app.messages.put(("ended",(old,137)))
        self.app._poll()
        self.assertIs(self.app.process,new)

    def test_old_reader_lines_do_not_pollute_new_search(self):
        old=FakeExited()
        new=FakeExited(code=0)
        self.app.process=new
        before=self.app.phase.get()
        self.app.messages.put(("line",(old,"PREFLIGHT DISCOVERY: OLD RUN")))
        self.app._poll()
        self.assertEqual(self.app.phase.get(),before)

    def test_refresh_after_stop_is_nonblocking(self):
        proc=FakeExited()
        self.app.process=proc
        self.app.stop_requested=True
        def slow_scan(folder,recursive):
            time.sleep(.45)
            return []
        with mock.patch("LRC_Control_Center.list_review_candidates",side_effect=slow_scan):
            start=time.monotonic()
            self.app._poll()
            elapsed=time.monotonic()-start
            self.assertLess(elapsed,.30,"STOP must not wait for a 5,000-file candidate scan")
            self.assertIsNone(self.app.process)

    def test_hard_stop_result_finalizes_and_cleans_deferred_marker(self):
        proc=FakeExited()
        directory=Path(self.temp.name)/"stop-marker"
        directory.mkdir()
        self.app.stop_directory=directory
        self.app.stop_path=directory/"stop.request"
        self.app.stop_path.write_text("STOP")
        self.app.process=proc
        self.app.stop_requested=True
        self.app._hardstop_pending=True
        self.app._poll()
        self.assertIsNone(self.app.process)
        self.assertTrue(directory.exists(),"Keep stop marker until kill verification completes")
        self.app.messages.put(("hardstop_result",(proc,True,"worker stopped")))
        self.app._poll()
        self.assertFalse(directory.exists())
        self.assertIsNone(self.app.stop_path)

    def test_gui_requests_stop_marker_before_force_kill(self):
        proc=type("FakeWorker",(),{"poll":lambda self:None,"pid":13371337})()
        folder=Path(self.temp.name)/"stop-request"
        folder.mkdir()
        marker=folder/"stop.request"
        self.app.stop_directory=folder
        self.app.stop_path=marker
        self.app.process=proc
        observed=[]
        def fake_stop(target, *, context, request_stop):
            request_stop()
            observed.append((target,marker.exists()))
            return True,"simulated termination"
        with mock.patch.object(self.app,"_dialog",return_value=True), \
             mock.patch("LRC_Control_Center.kill_search_process",side_effect=fake_stop):
            self.app._stop()
            limit=time.monotonic()+2
            while not observed and time.monotonic()<limit:
                time.sleep(.02)
        self.assertEqual(observed,[(proc,True)])
        self.assertTrue(marker.exists())


if __name__=="__main__":
    unittest.main()
