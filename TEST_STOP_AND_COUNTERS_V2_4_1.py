"""v2.4.1: song-level counters, stage reset, safe worker termination.

No live provider calls or user MP3 files. Windows Tk tests use a disposable
sleeping child worker and verify Control Center stays alive after STOP.
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

from search_counters import SearchCounters,parse_counter_line
from worker_stop import kill_search_process


class CounterTests(unittest.TestCase):
    def test_three_stages_reset_but_totals_continue_and_deduplicate(self):
        counts=SearchCounters()
        with tempfile.TemporaryDirectory() as temp:
            path=lambda n:Path(temp)/(n+".mp3")
            counts.begin_round(1)
            for n in range(10):
                counts.record(path(f"saved{n}"),"SAVED")
            for n in range(5):
                counts.record(path(f"review{n}"),"REVIEW_AVAILABLE",candidate=True)
                counts.record(path(f"review{n}"),"REVIEW_AVAILABLE",candidate=True)
            for n in range(8):
                counts.record(path(f"none{n}"),"NOT_FOUND")
            self.assertEqual(counts.snapshot(),{
                "round":"1","round_lrc":10,"round_candidate":5,"round_not_found":8,
                "total_lrc":10,"total_candidate":5})
            round1_end=counts.end_round()
            self.assertEqual(tuple(round1_end[k] for k in (
                "round_lrc","round_candidate","round_not_found")),(0,0,0))
            self.assertEqual((round1_end["total_lrc"],round1_end["total_candidate"]),(10,5))

            counts.begin_round(2)
            counts.record(path("review0"),"SAVED")
            counts.record(path("review1"),"REVIEW_PARTIAL",candidate=False)
            counts.record(path("review2"),"REVIEW_AVAILABLE",candidate=True)
            counts.record(path("later"),"REVIEW_AVAILABLE",candidate=True)
            self.assertEqual(counts.snapshot(),{
                "round":"2","round_lrc":1,"round_candidate":2,"round_not_found":1,
                "total_lrc":11,"total_candidate":6})
            counts.end_round()
            counts.begin_round(3)
            counts.record(path("review1"),"SAVED")
            counts.record(path("review1"),"SAVED")
            counts.record(path("review2"),"TIMEOUT")
            self.assertEqual(counts.snapshot(),{
                "round":"3","round_lrc":1,"round_candidate":0,"round_not_found":0,
                "total_lrc":12,"total_candidate":6})
            counts.end_round()
            self.assertEqual((counts.snapshot()["round_lrc"],counts.snapshot()["total_lrc"]),(0,12))

    def test_no_false_not_found_for_errors_timeouts_or_skipped(self):
        with tempfile.TemporaryDirectory() as temp:
            c=SearchCounters()
            c.begin_round("OFFLINE")
            for kind in ("TIMEOUT","SERVER_ERROR","INTERRUPTED","DEFERRED_RATE_LIMIT","EXISTS"):
                c.record(Path(temp)/(kind+".mp3"),kind)
            self.assertEqual(c.snapshot()["round_not_found"],0)
            c.record(Path(temp)/"realnone.mp3","NO_MATCH")
            c.record(Path(temp)/"oldreview.mp3","REVIEW_PARTIAL")
            self.assertEqual(c.snapshot()["round_not_found"],2)
            self.assertEqual(c.snapshot()["total_candidate"],0)

    def test_machine_messages_validate_shape(self):
        counters=SearchCounters()
        counters.begin_round(1)
        counters.record("/tmp/sample.mp3","SAVED")
        result=parse_counter_line(counters.output())
        self.assertEqual(result["round"],"1")
        self.assertEqual(result["round_lrc"],1)
        for text in ("", "LRC_COUNTER {}", 'LRC_COUNTER {"round":"1","round_lrc":true}',
                     "LRC_COUNTER broken JSON","random text"):
            self.assertIsNone(parse_counter_line(text))

    def test_checkpoint_replay_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            c=SearchCounters()
            song=Path(temp)/"A.mp3"
            c.begin_round(1)
            # A checkpoint may contain several review_rows from one song.
            for _ in range(4):
                c.record(song,"REVIEW_AVAILABLE",candidate=True)
            self.assertEqual(c.snapshot()["round_candidate"],1)
            self.assertEqual(c.snapshot()["total_candidate"],1)
            c.end_round()
            c.begin_round(2)
            c.record(song,"SAVED",candidate=False)
            self.assertEqual(c.snapshot()["total_candidate"],1)
            self.assertEqual(c.snapshot()["total_lrc"],1)


class ProcessTerminationTests(unittest.TestCase):
    def test_real_sleeping_worker_is_killed_and_test_process_survives(self):
        options={}
        if os.name=="nt":
            options["creationflags"]=subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            options["start_new_session"]=True
        with subprocess.Popen([sys.executable,"-u","-c",
                "import time; time.sleep(180)"],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,**options) as worker:
            self.assertIsNone(worker.poll())
            success,description=kill_search_process(worker)
            self.assertTrue(success,description)
            worker.wait(timeout=15)
            self.assertIsNotNone(worker.returncode)
            self.assertTrue(True,"Current test/GUI process is still alive")


@unittest.skipUnless(os.name=="nt","Tk desktop GUI stop smoke test needs Windows")
class WindowsControlCenterTests(unittest.TestCase):
    def test_live_counters_reset_on_stage_message(self):
        from LRC_Control_Center import ControlCenter
        with tempfile.TemporaryDirectory() as temp, mock.patch.dict(os.environ,{"APPDATA":temp}):
            ui=ControlCenter()
            ui.withdraw()
            try:
                c=SearchCounters()
                c.begin_round(1)
                c.record(Path(temp)/"A.mp3","SAVED")
                c.record(Path(temp)/"B.mp3","REVIEW_AVAILABLE",candidate=True)
                c.record(Path(temp)/"C.mp3","NOT_FOUND")
                ui._line(c.output())
                self.assertEqual(ui.counter_vars["round_lrc"].get(),"1")
                self.assertEqual(ui.counter_vars["round_candidate"].get(),"1")
                self.assertEqual(ui.counter_vars["round_not_found"].get(),"1")
                self.assertEqual(ui.counter_vars["total_candidate"].get(),"1")
                ui._line("===== ROUND 2/3 | 3 songs | ONLINE =====")
                c.begin_round(2)
                ui._line(c.output())
                self.assertEqual(ui.counter_vars["round_candidate"].get(),"0")
                self.assertEqual(ui.counter_vars["round_not_found"].get(),"0")
                self.assertEqual(ui.counter_vars["total_candidate"].get(),"1")
                c.record(Path(temp)/"B.mp3","SAVED")
                ui._line(c.output())
                self.assertEqual(ui.counter_vars["total_lrc"].get(),"2")
                self.assertEqual(ui.counter_vars["total_candidate"].get(),"1")
            finally:
                ui.destroy()

    def test_stop_button_hard_kills_real_worker_but_not_gui(self):
        from LRC_Control_Center import ControlCenter
        with tempfile.TemporaryDirectory() as temp, mock.patch.dict(os.environ,{"APPDATA":temp}):
            ui=ControlCenter()
            ui.withdraw()
            proc=None
            try:
                proc=subprocess.Popen([sys.executable,"-u","-c",
                         "import time;print('working',flush=True);time.sleep(180)"],
                         stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                         text=True,creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                ui.process=proc
                ui.run_serial=7
                ui.stopping=False
                ui.stop_button.configure(state="normal")
                with mock.patch("tkinter.messagebox.askyesno",return_value=True):
                    ui._stop()
                self.assertTrue(ui.stopping)
                self.assertEqual(str(ui.stop_button.cget("state")),"disabled")
                proc.wait(timeout=25)
                time.sleep(.5)
                ui._poll()
                self.assertTrue(ui.winfo_exists(),"Stop must not close Control Center")
                self.assertIsNotNone(proc.poll(),"Worker must be dead")
                self.assertEqual(ui.counter_vars["total_lrc"].get(),"0")
            finally:
                if proc is not None and proc.poll() is None:
                    kill_search_process(proc)
                ui.destroy()


if __name__=="__main__":
    unittest.main(verbosity=2)
