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


    def test_actual_three_stage_counter_events_with_multicandidate_tracks(self):
        import io
        from contextlib import redirect_stdout
        import LRC_Bulk_Finder as app
        lyrics=("[00:04.00] First lyric\n[00:35.00] Second line\n"
                "[01:30.00] Chorus here\n[02:58.00] Finish song\n")
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            for name in ("A","B","C","D"):
                (folder/(name+".mp3")).write_bytes(b"PROTECTED")
            app.GREEK_MODE=False
            app.G2G_TOOL=None
            app.MB_ENABLED=False
            app.LOCAL_LRCLIB=None
            app.G2G_SONG_PLANS.clear()
            app.blocked.clear()
            def local(title,artist,duration,review):
                if title=="A":
                    return app.Hit(lyrics,"LRCLIB","verified","LOCAL",True)
                if title=="B":
                    review.add("Local-1",title,artist,"review one",lyrics)
                    review.add("Local-2",title,artist,"review two",lyrics.replace("First","Different"))
                return None
            def remote(title,artist,album,duration,review,*,only_providers=None,
                       retry_targets=None,timings=None,request_traces=None):
                if title=="B":
                    return app.Hit(lyrics,"SyncLRC","verified","ORIGINAL",True),"SAVED","verified",["SyncLRC=SAVED"]
                if title=="C" and only_providers is None:
                    retry_targets.add("LiriQo")
                    return None,"TIMEOUT","one timeout",["LiriQo=ERROR (timeout)"]
                if title=="D":
                    review.add("NetEase",title,artist,"review",lyrics)
                    return None,"REVIEW_AVAILABLE","candidate",["NetEase=REVIEW_AVAILABLE"]
                return None,"NOT_FOUND","no match",["LiriQo=NO_MATCH"]
            def save(song,hit):
                song.with_suffix(".lrc").write_text(hit.lyrics,encoding="utf-8")
            answers=iter(["5","n","n","full","d","n","n","n","a","n"])
            with mock.patch("builtins.input",side_effect=lambda _:next(answers)),\
                 mock.patch.object(app,"select_folder",return_value=folder),\
                 mock.patch.object(app,"ensure_local_lrclib_config",return_value=True),\
                 mock.patch.object(app,"load_provider_cooldowns"),\
                 mock.patch.object(app,"configure_lrclib_contact",return_value=True),\
                 mock.patch.object(app,"show_provider_availability"),\
                 mock.patch.object(app,"song_info",side_effect=lambda path:(path.stem,"Artist","",180)),\
                 mock.patch.object(app,"local_lrclib_search",side_effect=local),\
                 mock.patch.object(app,"search_song",side_effect=remote),\
                 mock.patch.object(app,"save_hit",side_effect=save),\
                 redirect_stdout(io.StringIO()) as out:
                app.main()
            events=[parse_counter_line(line) for line in out.getvalue().splitlines()]
            events=[e for e in events if e is not None]
            self.assertEqual([e["round"] for e in events if
                e["round_lrc"]==e["round_candidate"]==e["round_not_found"]==0][:1],["1"])
            for stage in ("1","2","3"):
                stage_events=[e for e in events if e["round"]==stage]
                self.assertGreaterEqual(len(stage_events),3)
                self.assertEqual(tuple(stage_events[-1][k] for k in
                    ("round_lrc","round_candidate","round_not_found")),(0,0,0))
            stage1=[e for e in events if e["round"]=="1"]
            self.assertTrue(any(e["round_lrc"]==1 and e["round_candidate"]==1 for e in stage1))
            self.assertTrue(any(e["round_not_found"]==2 for e in stage1))
            stage2=[e for e in events if e["round"]=="2"]
            self.assertTrue(any(e["round_lrc"]==1 and e["round_candidate"]==1 for e in stage2))
            self.assertEqual((events[-1]["total_lrc"],events[-1]["total_candidate"]),(2,2))
            self.assertTrue((folder/"B.candidate.lrc").exists())
            self.assertTrue((folder/"B.candidate.2.lrc").exists())
            self.assertTrue((folder/"D.candidate.lrc").exists())
            for name in "ABCD":
                self.assertEqual((folder/(name+".mp3")).read_bytes(),b"PROTECTED")



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
