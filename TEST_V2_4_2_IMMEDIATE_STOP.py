"""Focused v2.4.2 regression: instant child-tree STOP and the five counters.

All real processes are disposable synthetic workers. No provider HTTP calls.
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

from stage_counters import StageCounters
from worker_stop import kill_search_process


class CounterConsistencyTests(unittest.TestCase):
    def test_three_reset_and_two_persistent_unique_song_totals(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            counts=StageCounters()
            counts.start(1)
            a=folder/"A.mp3";b=folder/"B.mp3";c=folder/"C.mp3"
            counts.add(a,"SAVED")
            for _ in range(3):
                counts.add(b,"REVIEW_AVAILABLE",reviewed=True)
            counts.add(c,"NOT_FOUND")
            self.assertEqual(tuple(counts.values()[x] for x in (
                "found","candidate","not_found","total_found","total_candidate")),(1,1,1,1,1))
            counts.start(2)
            self.assertEqual(tuple(counts.values()[x] for x in (
                "found","candidate","not_found","total_found","total_candidate")),(0,0,0,1,1))
            counts.add(b,"SAVED")
            self.assertEqual(tuple(counts.values()[x] for x in (
                "found","candidate","not_found","total_found","total_candidate")),(1,0,0,2,1))
            counts.start(3)
            self.assertEqual(tuple(counts.values()[x] for x in (
                "found","candidate","not_found","total_found","total_candidate")),(0,0,0,2,1))

    def test_candidate_without_saved_sidecar_not_counted(self):
        with tempfile.TemporaryDirectory() as td:
            counts=StageCounters()
            counts.start(1)
            song=Path(td)/"Song.mp3"
            counts.add(song,"REVIEW_AVAILABLE",reviewed=False)
            self.assertEqual(counts.values()["candidate"],0)
            self.assertEqual(counts.values()["total_candidate"],0)
            counts.add(song,"REVIEW_AVAILABLE",reviewed=True)
            counts.add(song,"REVIEW_AVAILABLE",reviewed=True)
            self.assertEqual((counts.values()["candidate"],counts.values()["total_candidate"]),(1,1))

    def test_errors_timeouts_not_counted_as_not_found(self):
        c=StageCounters();c.start(1)
        with tempfile.TemporaryDirectory() as td:
            for status in ("TIMEOUT","SERVER_ERROR","INTERRUPTED","DEFERRED_RATE_LIMIT"):
                c.add(Path(td)/(status+".mp3"),status)
        self.assertEqual(c.values()["not_found"],0)


class HardStopTests(unittest.TestCase):
    def test_real_long_running_worker_is_killed_without_killing_controller(self):
        options={}
        if os.name=="nt":options["creationflags"]=subprocess.CREATE_NEW_PROCESS_GROUP
        else:options["start_new_session"]=True
        worker=subprocess.Popen([sys.executable,"-u","-c","import time;time.sleep(180)"],
                                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,**options)
        try:
            self.assertIsNone(worker.poll())
            success,detail=kill_search_process(worker)
            self.assertTrue(success,detail)
            worker.wait(timeout=20)
            self.assertIsNotNone(worker.poll())
            self.assertTrue(True,"Controller remains alive after worker process is killed.")
        finally:
            if worker.poll() is None:worker.kill()
            worker.communicate(timeout=10)


@unittest.skipUnless(os.name=="nt","Windows GUI requires Windows Tk desktop")
class HardStopWindowsGuiTests(unittest.TestCase):
    def test_gui_stop_kills_actual_worker_and_gui_remains_open(self):
        from LRC_Control_Center import ControlCenter
        with tempfile.TemporaryDirectory() as td, mock.patch.dict(os.environ,{"APPDATA":td}):
            gui=ControlCenter()
            gui.withdraw()
            worker=None
            try:
                worker=subprocess.Popen([sys.executable,"-u","-c",
                         "import time;print('running',flush=True);time.sleep(180)"],
                        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                gui.process=worker
                gui.stop_requested=False
                gui.stop_button.configure(state="normal")
                with mock.patch("tkinter.messagebox.askyesno",return_value=True):
                    gui._stop()
                self.assertTrue(gui.stop_requested)
                self.assertEqual(str(gui.stop_button.cget("state")),"disabled")
                worker.wait(timeout=25)
                time.sleep(.5)
                gui._poll()
                self.assertTrue(gui.winfo_exists(),"STOP must not destroy the Control Center")
                self.assertIsNotNone(worker.returncode)
                self.assertEqual(gui.counter_vars["total_found"].get(),"0")
            finally:
                if worker is not None:
                    if worker.poll() is None:worker.kill()
                    worker.communicate(timeout=10)
                gui.destroy()

    def test_separate_3_plus_2_counter_frames_and_stage_reset(self):
        from LRC_Control_Center import ControlCenter
        with tempfile.TemporaryDirectory() as td, mock.patch.dict(os.environ,{"APPDATA":td}):
            gui=ControlCenter()
            gui.withdraw()
            try:
                self.assertEqual(set(gui.counter_vars),{
                    "found","candidate","not_found","total_found","total_candidate","skipped"})
                x=StageCounters()
                x.start(1);x.add(Path(td)/"A.mp3","SAVED")
                x.add(Path(td)/"B.mp3","REVIEW_AVAILABLE",reviewed=True)
                gui._line(x.line())
                self.assertEqual(gui.counter_vars["found"].get(),"1")
                self.assertEqual(gui.counter_vars["candidate"].get(),"1")
                x.start(2)
                gui._line(x.line())
                self.assertEqual(gui.counter_vars["found"].get(),"0")
                self.assertEqual(gui.counter_vars["candidate"].get(),"0")
                self.assertEqual(gui.counter_vars["total_found"].get(),"1")
                self.assertEqual(gui.counter_vars["total_candidate"].get(),"1")
            finally:gui.destroy()


if __name__=="__main__":unittest.main(verbosity=2)
