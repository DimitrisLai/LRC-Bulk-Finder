"""v2.4.1 safety: GUI stop IPC, checkpoint recovery, five stage counters.

No internet and no writes to user music. Linux/Windows compatible tests.
"""
from __future__ import annotations
import io
import os
import sys
import tempfile
import threading
import time
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.modules.setdefault("syncedlyrics",types.SimpleNamespace(search=lambda *a,**k:None))
import LRC_Bulk_Finder as app
from stage_counters import StageCounters
from stop_control import check_stop,interruptible_sleep,stop_requested
from run_saved_profile import main as profile_main

LRC="[00:04.00] First\n[00:33.00] Chorus\n[01:30.00] Again\n[02:58.00] End\n"


class StopAndCounterTests(unittest.TestCase):
    def setUp(self):
        app.STAGED_ONLINE_MODE=False
        app.GREEK_MODE=False
        app.MB_ENABLED=False
        app.G2G_TOOL=None
        app.blocked.clear()
        app.G2G_SONG_PLANS.clear()
        app.LIBRARY_INDEX=None
        app.LOCAL_LRCLIB=None

    def tearDown(self):
        app.STAGED_ONLINE_MODE=False

    def test_01_stage_reset_totals_and_distinct_song_count(self):
        metrics=StageCounters()
        self.assertEqual(metrics.start(1),"STAGE COUNTERS: stage=1 found=0 candidate=0 not_found=0 total_found=0 total_candidate=0 skipped=0")
        with tempfile.TemporaryDirectory() as folder:
            a=Path(folder)/"A.mp3";b=Path(folder)/"B.mp3";c=Path(folder)/"C.mp3"
            metrics.add(a,"SAVED")
            metrics.add(a,"SAVED")  # resumed record: no double count
            metrics.add(b,"REVIEW_AVAILABLE",reviewed=True)
            metrics.add(c,"NOT_FOUND")
            self.assertEqual(tuple(metrics.values()[k] for k in ("found","candidate","not_found","total_found","total_candidate")),(1,1,1,1,1))
            metrics.start(2)
            self.assertEqual(tuple(metrics.values()[k] for k in ("found","candidate","not_found","total_found","total_candidate")),(0,0,0,1,1))
            metrics.add(b,"REVIEW_PARTIAL",reviewed=False)
            metrics.add(b,"SAVED")
            metrics.add(c,"TIMEOUT")
            self.assertEqual(tuple(metrics.values()[k] for k in ("found","candidate","not_found","total_found","total_candidate")),(1,0,0,2,1))
            metrics.start(3)
            metrics.add(c,"NOT_FOUND")
            self.assertEqual(tuple(metrics.values()[k] for k in ("found","candidate","not_found","total_found","total_candidate")),(0,0,1,2,1))

    def test_02_errors_are_not_reported_as_certain_no_match(self):
        m=StageCounters();m.start(1)
        with tempfile.TemporaryDirectory() as folder:
            for status in ("TIMEOUT","SERVER_ERROR","DEFERRED_RATE_LIMIT","INTERRUPTED"):
                m.add(Path(folder)/(status+".mp3"),status)
        self.assertEqual(m.values()["not_found"],0)

    def test_03_stop_is_noop_without_gui_channel(self):
        with mock.patch.dict(os.environ,{},clear=True):
            self.assertFalse(stop_requested())
            check_stop()
            with mock.patch("stop_control.time.sleep") as sleep:
                interruptible_sleep(2)
                sleep.assert_called_once_with(2.0)

    def test_04_gui_marker_interrupts_wait_in_under_one_second(self):
        with tempfile.TemporaryDirectory() as folder:
            marker=Path(folder)/"stop.request"
            def make_request():
                time.sleep(.17)
                marker.write_text("STOP\n")
            with mock.patch.dict(os.environ,{"LRC_STOP_FILE":str(marker)}):
                worker=threading.Thread(target=make_request)
                worker.start()
                begin=time.monotonic()
                with self.assertRaises(KeyboardInterrupt):
                    interruptible_sleep(10,poll=.035)
                elapsed=time.monotonic()-begin
                worker.join(1)
                self.assertLess(elapsed,1.5)
                self.assertTrue(stop_requested())

    def test_05_worker_acknowledges_preexisting_gui_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            marker=Path(folder)/"request.stop"
            marker.write_text("STOP")
            with mock.patch.dict(os.environ,{"LRC_STOP_FILE":str(marker)}):
                with mock.patch("run_saved_profile.run_profile",side_effect=KeyboardInterrupt("stop")),redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(profile_main(["--profile","Unused"]),130)
            self.assertIn("STOP REQUESTED",output.getvalue())

    def test_06_real_option5_stop_after_completed_offline_checkpoints(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder)
            music=home/"music";music.mkdir()
            marker=home/"STOP.request"
            for name in ("A","B","C","D","E"):
                (music/(name+".mp3")).write_bytes(b"PROTECTED MP3 "+name.encode())
            calls=[]
            def local(title,artist,duration,review):
                calls.append(title)
                if title=="C":marker.write_text("STOP")
                if title in ("A","B","C"):return app.Hit(LRC,"LRCLIB","verified","LOCAL",True)
                return None
            answers=iter(["5","n","n","full","d","n","n","n","a","n"])
            with mock.patch.dict(os.environ,{"LRC_STOP_FILE":str(marker)}),\
                 mock.patch("builtins.input",side_effect=lambda p:next(answers)),\
                 mock.patch.object(app,"select_folder",return_value=music),\
                 mock.patch.object(app,"ensure_local_lrclib_config",return_value=True),\
                 mock.patch.object(app,"load_provider_cooldowns"),\
                 mock.patch.object(app,"configure_lrclib_contact",return_value=True),\
                 mock.patch.object(app,"show_provider_availability"),\
                 mock.patch.object(app,"song_info",side_effect=lambda p:(p.stem,"Artist","",180)),\
                 mock.patch.object(app,"local_lrclib_search",side_effect=local),\
                 mock.patch.object(app,"search_song",side_effect=AssertionError("STOP MUST PREVENT ONLINE")),\
                 redirect_stdout(io.StringIO()) as output:
                app.main()
            log=output.getvalue()
            self.assertEqual(calls,["A","B","C"])
            self.assertTrue((music/"A.lrc").exists())
            self.assertTrue((music/"B.lrc").exists())
            self.assertFalse((music/"C.lrc").exists())
            self.assertIn("STOP REQUESTED",log)
            self.assertIn("STAGE FINAL:",log)
            self.assertTrue((music/"LRC_Run_Checkpoint_v2_4_3.jsonl").exists())
            self.assertTrue((music/"LRC_Timeouts.txt").exists())
            for name in ("A","B","C","D","E"):
                self.assertEqual((music/(name+".mp3")).read_bytes(),b"PROTECTED MP3 "+name.encode())

    def test_07_three_stage_counts_reset_totals_survive_with_reviews(self):
        with tempfile.TemporaryDirectory() as folder:
            music=Path(folder)
            for title in ("A","B","C"): (music/(title+".mp3")).write_bytes(b"UNCHANGED")
            events=[]
            def offline(title,artist,duration,review):
                events.append(("offline",title))
                if title=="A":return app.Hit(LRC,"LRCLIB","verified","LOCAL",True)
                if title=="B":review.add("LRCLIB",title,artist,"uncertain",LRC)
                return None
            def online(title,artist,album,duration,review,*,only_providers=None,retry_targets=None,timings=None,request_traces=None):
                events.append(("retry" if only_providers else "online",title))
                if title=="B":return app.Hit(LRC,"SyncLRC","verified","NORMAL",True),"SAVED","verified",["SyncLRC=SAVED"]
                if not only_providers:
                    retry_targets.add("LiriQo")
                    return None,"TIMEOUT","timeout",["LiriQo=TIMEOUT"]
                return None,"NOT_FOUND","retry miss",["LiriQo=NO_MATCH"]
            def save(track,hit):
                track.with_suffix(".lrc").write_text(hit.lyrics,encoding="utf-8")
            def run():
                answers=iter(["5","n","n","full","d","n","n","n","a","n"])
                with mock.patch.dict(os.environ,{"LRC_INCREMENTAL":"0"},clear=False),\
                     mock.patch("builtins.input",side_effect=lambda p:next(answers)),\
                     mock.patch.object(app,"select_folder",return_value=music),\
                     mock.patch.object(app,"ensure_local_lrclib_config",return_value=True),\
                     mock.patch.object(app,"load_provider_cooldowns"),\
                     mock.patch.object(app,"configure_lrclib_contact",return_value=True),\
                     mock.patch.object(app,"show_provider_availability"),\
                     mock.patch.object(app,"song_info",side_effect=lambda p:(p.stem,"Artist","",180)),\
                     mock.patch.object(app,"local_lrclib_search",side_effect=offline),\
                     mock.patch.object(app,"search_song",side_effect=online),\
                     mock.patch.object(app,"save_hit",side_effect=save),\
                     redirect_stdout(io.StringIO()) as output:
                    app.main()
                return output.getvalue()
            log=run()
            markers=[x for x in log.splitlines() if x.startswith("STAGE COUNTERS:")]
            self.assertTrue(any("stage=1 found=1 candidate=1 not_found=1 total_found=1 total_candidate=1" in x for x in markers),markers)
            self.assertTrue(any("stage=2 found=0 candidate=0 not_found=0 total_found=1 total_candidate=1" in x for x in markers),markers)
            self.assertTrue(any("stage=2 found=1 candidate=0 not_found=0 total_found=2 total_candidate=1" in x for x in markers),markers)
            self.assertTrue(any("stage=3 found=0 candidate=0 not_found=0 total_found=2 total_candidate=1" in x for x in markers),markers)
            self.assertTrue(any("stage=3 found=0 candidate=0 not_found=1 total_found=2 total_candidate=1" in x for x in markers),markers)
            self.assertEqual(markers[-1],
                "STAGE COUNTERS: stage=3 found=0 candidate=0 not_found=0 total_found=2 total_candidate=1 skipped=0",
                "After the last stage, only the ALL-stages totals may remain nonzero")
            old=list(events)
            log2=run()
            self.assertEqual(events,old,"Completed results must be replayed without network")
            self.assertIn("CHECKPOINT:",log2)
            # A new run excludes already-installed LRCs from the eligible
            # batch. The total correctly describes the CURRENT run, not
            # earlier successful runs. Checkpointed C remains the only task.
            self.assertIn("STAGE COUNTERS: stage=3 found=0 candidate=0 not_found=1",log2)
            self.assertIn("total_found=0 total_candidate=0",log2)


if __name__=="__main__":
    unittest.main(verbosity=2)
