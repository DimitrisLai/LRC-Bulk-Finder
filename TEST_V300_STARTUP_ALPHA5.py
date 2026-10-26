"""Alpha 5 regression: real startup readers, discovery and outcome semantics.

Only synthetic local files, clocks and HTTP responses are used.
"""
from __future__ import annotations
from collections import Counter
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest import mock

import LRC_Bulk_Finder as engine
import incremental_library as library
import startup_io


class StartupReaderTests(unittest.TestCase):
    def test_invalid_cache_values_cannot_crash_stats_or_supply_fake_metadata(self):
        from search_performance import MusicBrainzDiskCache,ProviderPerformance
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);stamp=time.time()-1
            performance=root/'LRC_Provider_Performance_v2_2.jsonl'
            performance.write_text(''.join(json.dumps({'key':str(n),'at':stamp,'provider':'LRCLIB',
                'kind':'NO_MATCH','seconds':value})+'\n' for n,value in enumerate(('bad','nan',-1,1.5))))
            cache=root/'LRC_MusicBrainz_Cache_v2_2.jsonl'
            cache.write_text(json.dumps({'key':'bad','at':stamp,'value':[{},5]})+'\n')
            before={p:p.read_bytes() for p in (performance,cache)}
            data=ProviderPerformance(root,('LRCLIB',))
            self.assertEqual(data.statistics()['LRCLIB']['attempts'],1)
            self.assertEqual(MusicBrainzDiskCache(root).data,{})
            self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_deadline_discards_private_result_and_cannot_publish_late(self):
        release=threading.Event();done=threading.Event();messages=[]
        def work(update,check):
            update(entries=250)
            release.wait(2)
            try:
                check()
                return {"should_never_be_published":True}
            finally:done.set()
        try:
            started=time.monotonic()
            with self.assertRaises(startup_io.StartupBudgetExceeded):
                startup_io.observed_read("PREFLIGHT FIXTURE",work,seconds=.04,progress=messages.append)
            self.assertLess(time.monotonic()-started,1)
            self.assertIn("started",messages[0])
            self.assertTrue(any("discarded" in line for line in messages))
        finally:
            release.set();self.assertTrue(done.wait(2))

    def test_cooperative_stop_interrupts_blocked_read(self):
        with tempfile.TemporaryDirectory() as td:
            marker=Path(td)/"stop"
            release=threading.Event();entered=threading.Event();done=threading.Event()
            def read(update,check):
                entered.set()
                release.wait(2)
                try:check()
                finally:done.set()
            def request():
                entered.wait(2)
                marker.write_text("STOP")
            request_thread=threading.Thread(target=request)
            with mock.patch.dict(os.environ,{"LRC_STOP_FILE":str(marker)}):
                request_thread.start()
                try:
                    with self.assertRaises(KeyboardInterrupt):
                        startup_io.observed_read("PREFLIGHT FIXTURE",read,seconds=2)
                finally:
                    release.set();request_thread.join(2);done.wait(2)

    def test_complete_history_preserves_latest_invalidation_and_original_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"history.jsonl"
            now=time.time()-1
            rows=[{"key":"old","at":now-9*86400,"state":"NO_MATCH"},
                  {"key":"valid","at":now,"state":"NO_MATCH"},
                  {"key":"review","at":now,"state":"NO_MATCH"},
                  {"key":"review","at":now,"state":"REVIEW_AVAILABLE"},
                  {"key":"future","at":now+9999,"state":"NO_MATCH"},
                  {"key":"nan","at":float('nan'),"state":"NO_MATCH"}]
            p.write_text("\n".join(json.dumps(row) for row in rows)+"\n",encoding="utf-8")
            before=p.read_bytes();messages=[]
            with mock.patch.object(engine,"HISTORY_CACHE",{}),mock.patch.object(engine,"HISTORY_PATH",None):
                engine.load_search_history(p,progress=messages.append)
                self.assertEqual(set(engine.HISTORY_CACHE),{"valid"})
            self.assertEqual(p.read_bytes(),before)
            self.assertTrue(messages[0].startswith("PREFLIGHT HISTORY: started"))
            self.assertIn("complete",messages[-1])

    def test_oversize_record_cannot_publish_earlier_no_match_without_later_invalidation(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"history.jsonl"
            p.write_text(json.dumps({"key":"x","state":"NO_MATCH","at":time.time()-1})+
                         "\n"+"X"*(startup_io.MAX_RECORD_BYTES+1)+"\n",encoding="utf-8")
            digest=hashlib.sha256(p.read_bytes()).hexdigest()
            with mock.patch.object(engine,"HISTORY_CACHE",{}),mock.patch.object(engine,"HISTORY_PATH",None):
                engine.load_search_history(p)
                self.assertEqual(engine.HISTORY_CACHE,{})
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),digest)

    def test_blocked_history_open_is_bounded_and_preserved(self):
        release=threading.Event();entered=threading.Event();done=threading.Event()
        original_open=Path.open
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"history.jsonl"
            p.write_text('{"key":"x","state":"NO_MATCH","at":1}\n')
            before=p.read_bytes()
            def blocked_open(path,*args,**kwargs):
                if path==p:
                    entered.set();release.wait(2)
                    stream=original_open(path,*args,**kwargs)
                    done.set()
                    return stream
                return original_open(path,*args,**kwargs)
            with mock.patch.object(engine,"HISTORY_CACHE",{}),mock.patch.object(engine,"HISTORY_PATH",None), \
                 mock.patch.object(Path,"open",blocked_open):
                try:
                    engine.load_search_history(p,timeout_seconds=.04)
                    self.assertTrue(entered.is_set())
                    self.assertEqual(engine.HISTORY_CACHE,{})
                finally:
                    release.set();done.wait(2)
            self.assertEqual(p.read_bytes(),before)

    def test_jsonl_byte_budget_never_returns_a_partial_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"cache.jsonl";p.write_text('{"x":1}\n'*10)
            with self.assertRaises(startup_io.StartupBudgetExceeded):
                startup_io.read_jsonl_snapshot(p,dict,lambda d,r:d.update(r),label="PREFLIGHT FIXTURE",max_bytes=10)


class FileDiscoveryTests(unittest.TestCase):
    def test_recursive_unicode_formats_collisions_and_read_only_5000_entries(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);album=root/"Ελληνικά";album.mkdir()
            for n in range(5000):(album/f"cover{n}.jpg").touch()
            a=album/"Τραγούδι.MP3";a.write_bytes(b"original")
            (root/"Overlap.mp3").write_bytes(b"a")
            (root/"Overlap.flac").write_bytes(b"b")
            (root/"Other.opus").write_bytes(b"c")
            messages=[]
            safe,collisions=library.safe_audio_files(root,progress=messages.append)
            self.assertEqual(set(safe),{a,root/"Other.opus"})
            self.assertEqual(len(collisions),2)
            self.assertEqual(a.read_bytes(),b"original")
            self.assertTrue(messages[0].startswith("PREFLIGHT ENUMERATION: started"))
            self.assertIn("audio=4",messages[-1])
            self.assertNotIn(a,library.audio_files(root,False))

    def test_non_audio_entries_do_not_trigger_is_file_stat(self):
        audio=mock.Mock(name="audio");audio.name="song.mp3";audio.path="fixture/song.mp3"
        audio.is_dir.return_value=False;audio.is_file.return_value=True
        image=mock.Mock(name="image");image.name="cover.jpg";image.path="fixture/cover.jpg"
        image.is_dir.return_value=False
        image.is_file.side_effect=AssertionError("Non-audio file stat must be avoided")
        scan=mock.MagicMock();scan.__enter__.return_value=iter([image,audio])
        with mock.patch.object(library.os,"scandir",return_value=scan):
            self.assertEqual(library.audio_files("fixture"),[Path("fixture/song.mp3")])
        image.is_file.assert_not_called()

    def test_blocked_enumeration_aborts_without_partial_track_selection(self):
        release=threading.Event();done=threading.Event();messages=[]
        def blocked(path):
            release.wait(2);done.set()
            raise OSError("synthetic inaccessible directory")
        with mock.patch.object(library.os,"scandir",side_effect=blocked):
            try:
                with self.assertRaises(startup_io.StartupBudgetExceeded):
                    library.safe_audio_files("fixture",timeout_seconds=.04,progress=messages.append)
            finally:release.set();done.wait(2)
        self.assertIn("started",messages[0])


class ProviderAuditTests(unittest.TestCase):
    def test_stalled_optional_musicbrainz_runs_once_and_preserves_original_searches(self):
        with mock.patch.multiple(engine,MB_ENABLED=True,MB_DISABLED_REASON=None,MB_CACHE={},
                MB_CACHE_DURATIONS={},MB_DISK_CACHE=None,GREEK_MODE=False,HISTORY_ENABLED=False,
                blocked={},errors=Counter(),PROVIDER_RECOVERY_AT={},LRCLIB_503_RETRY_AT=0):
            with mock.patch.object(engine,'direct_json',side_effect=engine.ProviderFailure('MusicBrainz stalled',stall=True)) as metadata, \
                 mock.patch.object(engine,'provider_lrclib',return_value=None) as lyrics:
                for title in ('Song','Song 2'):
                    _,status,_,_=engine.search_song(title,'Artist','',120,engine.CandidateReview(),only_providers=('LRCLIB',))
                    self.assertEqual(status,'NOT_FOUND')
                self.assertEqual(metadata.call_count,1)
                self.assertEqual([call.args[:4] for call in lyrics.call_args_list],
                                 [('Song','Artist','',120),('Song 2','Artist','',120)])
                self.assertIn(('Song','Artist'),engine.query_variants('Song','Artist'))

    def test_http_error_body_is_closed_without_losing_retry_after(self):
        import urllib.error
        body=io.BytesIO(b'not needed')
        error=urllib.error.HTTPError('https://example.invalid',503,'Unavailable',{'Retry-After':'5'},body)
        with mock.patch.object(engine,'LRCLIB_ACTIVE_DEADLINE',None),mock.patch.object(engine,'wait_for'), \
             mock.patch.object(engine.urllib.request,'urlopen',side_effect=error):
            with self.assertRaises(engine.ProviderFailure) as ex:
                engine.direct_get('LRCLIB','https://example.invalid',{})
        self.assertEqual(ex.exception.retry_after,'5')
        self.assertFalse(ex.exception.timeout)
        self.assertTrue(body.closed)

    def test_third_503_reports_disabled_without_contradictory_enabled_message(self):
        from v243_health import ProviderHealth
        with mock.patch.multiple(engine,blocked={},errors=Counter(),HISTORY_ENABLED=False,
                MB_ENABLED=False,LOCAL_LRCLIB=None,LRCLIB_503_STREAK=2,LRCLIB_503_RETRY_AT=0,
                PROVIDER_RECOVERY_AT={}):
            log=io.StringIO();retry=set()
            with redirect_stdout(log),mock.patch.object(engine,"provider_lrclib",side_effect=engine.ProviderFailure("HTTP 503: unavailable",retry_after="5")):
                engine.search_song("Song","Artist","",120,engine.CandidateReview(),only_providers=("LRCLIB",),retry_targets=retry)
            self.assertIn("HTTP_503_DISABLED",log.getvalue())
            self.assertNotIn("remains enabled",log.getvalue())
            self.assertEqual(retry,set())
            health=ProviderHealth(("LRCLIB",))
            for line in log.getvalue().splitlines():health.observe(line)
            self.assertEqual(health.rows["LRCLIB"]["status"],"Blocked / HTTP 503 circuit open")

    def test_other_direct_http_body_stalls_are_bounded_without_timeout_retry(self):
        class Slow:
            status=200
            def __enter__(self):return self
            def __exit__(self,*args):done.set()
            def read(self,*args):release.wait(2);return b'[]'
        release=threading.Event();done=threading.Event()
        with mock.patch.multiple(engine,blocked={},errors=Counter(),MB_ENABLED=False,HISTORY_ENABLED=False,
                PROVIDER_RECOVERY_AT={},HTTP_REQUEST_BUDGET_SECONDS=.04), \
             mock.patch.object(engine,"wait_for"),mock.patch.object(engine.urllib.request,"urlopen",return_value=Slow()):
            try:
                retry=set()
                _,status,_,_=engine.search_song("Song","Artist","",120,engine.CandidateReview(),only_providers=("SyncLRC",),retry_targets=retry)
                self.assertEqual(status,"SERVER_ERROR")
                self.assertEqual(retry,set());self.assertIn("SyncLRC",engine.blocked)
            finally:release.set();done.wait(2)

    def test_library_wall_deadline_is_not_labelled_a_real_socket_timeout(self):
        release=threading.Event();done=threading.Event()
        def wait():
            release.wait(2);done.set()
        with mock.patch.object(engine,"blocked",{}):
            try:
                with self.assertRaises(engine.ProviderFailure) as ex:
                    engine.bounded_blocking_search("Fixture",wait,.04)
                self.assertTrue(ex.exception.stall)
                self.assertFalse(ex.exception.timeout)
            finally:release.set();done.wait(2)

    def test_candidate_numbers_ten_through_nineteen_and_higher_are_visible_without_writes(self):
        from review_candidates_gui import candidate_index,list_review_candidates
        from v250_manager import CANDIDATE_RE
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);audio=root/"Song.mp3";audio.write_bytes(b"audio")
            for n in (2,9,10,11,19,20,99,100,1000):
                p=root/f"Song.candidate.{n}.lrc";p.write_text("[00:01.00] synthetic\n")
                self.assertEqual(candidate_index(p),n)
                self.assertTrue(CANDIDATE_RE.fullmatch(p.name))
            before={p:p.read_bytes() for p in root.iterdir()}
            self.assertEqual(len(list_review_candidates(root)),9)
            self.assertEqual([n for n,p in engine._numbered_promotion_candidates(root/"Song.candidate.lrc","Song")],[2,9,10,11,19,20,99,100,1000])
            self.assertEqual(before,{p:p.read_bytes() for p in root.iterdir()})
            for label in ("Song.candidate.1.lrc","Song.candidate.01.lrc"):
                self.assertIsNone(candidate_index(label))


class GuiOwnershipTests(unittest.TestCase):
    def app(self):
        from LRC_Control_Center import ControlCenter
        app=ControlCenter.__new__(ControlCenter);app.tk=None
        app._hardstop_pending=False;app._stop_verification_failed=False;app.process=None
        app.review_bulk_running=False;app._review_refresh_generation=0
        app._review_snapshot_folder=None;app._review_open_pending=None
        app.folder=mock.Mock();app.folder.get.return_value="fixture"
        app.boolvars={"recursive":mock.Mock()};app.boolvars["recursive"].get.return_value=True
        app.review_batch_status=mock.Mock();app._dialog=mock.Mock()
        app._render_review=mock.Mock();app.after=mock.Mock()
        import queue
        app.messages=queue.Queue()
        return app

    def test_post_stop_refresh_does_not_stat_folder_on_gui_thread(self):
        app=self.app()
        with mock.patch("LRC_Control_Center.Path.is_dir",side_effect=AssertionError("GUI thread touched filesystem")), \
             mock.patch("LRC_Control_Center.threading.Thread") as thread:
            app._refresh_review_background()
            thread.return_value.start.assert_called_once()

    def test_older_candidate_scan_cannot_replace_newer_inventory(self):
        app=self.app();app._review_refresh_generation=2
        app.messages.put(("review_refresh_ready",(1,"fixture",True,[{"old":True}],None)))
        app.stop_requested=False;app._stop_kill_attempted=False
        app._poll()
        app._render_review.assert_not_called()

    def test_manager_undo_and_retry_are_blocked_during_unverified_stop(self):
        app=self.app();app._stop_verification_failed=True
        with mock.patch("v250_gui.undo_session") as undo:
            app._manager_undo();app._manager_retry_selected()
            undo.assert_not_called()
        self.assertEqual(app._dialog.call_count,2)

    def test_frozen_startup_error_is_written_without_windowed_error_dialog(self):
        import QA_V300_FROZEN_STARTUP as qa
        with tempfile.TemporaryDirectory() as td:
            report=Path(td)/"failure.json"
            with mock.patch.object(qa,"smoke",side_effect=RuntimeError("synthetic startup failure")):
                self.assertEqual(qa.smoke_entry(report,object()),1)
            data=json.loads(report.read_text())
            self.assertFalse(data['passed']);self.assertIn('synthetic startup failure',data['error'])


if __name__=="__main__":unittest.main()
