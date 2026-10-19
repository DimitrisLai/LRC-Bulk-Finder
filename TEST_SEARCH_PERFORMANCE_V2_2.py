"""Offline, portable regression tests for v2.2 search speed and recovery."""
from __future__ import annotations
import csv
import io
import json
import tempfile
import time
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock
import sys
sys.modules.setdefault("syncedlyrics",types.SimpleNamespace(search=lambda *args,**kwargs:None))
import LRC_Bulk_Finder as app
from search_checkpoint import SearchCheckpoint
from search_performance import MusicBrainzDiskCache,ProviderPerformance,choose_provider_order


class PerformanceTests(unittest.TestCase):
    def setUp(self):
        app.MB_CACHE.clear()
        app.MB_CACHE_DURATIONS.clear()
        app.MB_DISK_CACHE=None
        app.MB_DISABLED_REASON=None
        app.MB_ENABLED=True
        app.GREEK_MODE=False

    def tearDown(self):
        app.MB_DISK_CACHE=None
        app.MB_ENABLED=False
        app.MB_DISABLED_REASON=None

    def test_cache_persists_success_without_network_next_process(self):
        with tempfile.TemporaryDirectory() as root:
            response={"recordings":[{
                "title":"Blinding Lights","artist-credit":[{"name":"The Weeknd"}],
                "length":200000}]}
            app.MB_DISK_CACHE=MusicBrainzDiskCache(root)
            with mock.patch.object(app,"direct_json",return_value=response) as net:
                self.assertEqual(app.musicbrainz_variant("Blinding Lites","The Weeknd",200),
                                 ("Blinding Lights","The Weeknd"))
            net.assert_called_once()
            app.MB_CACHE.clear()
            app.MB_CACHE_DURATIONS.clear()
            app.MB_DISK_CACHE=MusicBrainzDiskCache(root)
            with mock.patch.object(app,"direct_json",side_effect=AssertionError("NETWORK CALLED")):
                self.assertEqual(app.musicbrainz_variant("Blinding Lites","The Weeknd",200),
                                 ("Blinding Lights","The Weeknd"))
            self.assertEqual(app.MB_DISK_CACHE.hits,1)

    def test_duration_is_part_of_musicbrainz_cache_key(self):
        with tempfile.TemporaryDirectory() as root:
            cache=MusicBrainzDiskCache(root)
            cache.save("Track","Artist",180,False,("Correct","Artist"))
            self.assertEqual(cache.lookup("Track","Artist",180,False),
                             (True,("Correct","Artist")))
            self.assertEqual(cache.lookup("Track","Artist",198,False),(False,None))
            self.assertEqual(cache.lookup("Track","Artist",180,True),(False,None))

    def test_clean_no_match_cached_but_transport_error_not_cached(self):
        with tempfile.TemporaryDirectory() as root:
            app.MB_DISK_CACHE=MusicBrainzDiskCache(root)
            with mock.patch.object(app,"direct_json",return_value={"recordings":[]}) as net:
                self.assertIsNone(app.musicbrainz_variant("No match","Artist",180))
            net.assert_called_once()
            app.MB_CACHE.clear();app.MB_CACHE_DURATIONS.clear()
            app.MB_DISK_CACHE=MusicBrainzDiskCache(root)
            with mock.patch.object(app,"direct_json",side_effect=AssertionError("unexpected web")):
                self.assertIsNone(app.musicbrainz_variant("No match","Artist",180))
            app.MB_CACHE.clear();app.MB_CACHE_DURATIONS.clear()
            with mock.patch.object(app,"direct_json",side_effect=app.ProviderFailure("HTTP 503: overloaded")):
                self.assertIsNone(app.musicbrainz_variant("New track","Artist",180))
            self.assertEqual(app.MB_DISK_CACHE.lookup("New track","Artist",180,False),(False,None))

    def test_expired_musicbrainz_misses_are_not_reused(self):
        with tempfile.TemporaryDirectory() as root:
            x=MusicBrainzDiskCache(root)
            x.save("Song","Artist",100,False,None)
            key=x.key("Song","Artist",100,False)
            x.data[key]=(time.time()-8*86400,None)
            self.assertEqual(x.lookup("Song","Artist",100,False),(False,None))

    def test_default_order_unchanged(self):
        providers=("LRCLIB","SyncLRC","NetEase","Unison")
        self.assertEqual(choose_provider_order(providers,""),(providers,"DEFAULT"))

    def test_custom_order_must_be_permutation_without_omissions(self):
        names=("LRCLIB","SyncLRC","Unison")
        order,label=choose_provider_order(names,"c","unison,LRCLIB,synclrc")
        self.assertEqual(order,("Unison","LRCLIB","SyncLRC"))
        self.assertEqual(label,"CUSTOM")
        for invalid in ("Unison,LRCLIB","Unison,Unison,LRCLIB","Unison,LRCLIB,Fake"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    choose_provider_order(names,"c",invalid)

    def test_real_statistics_verified_only_and_resumed_run_is_not_double_counted(self):
        with tempfile.TemporaryDirectory() as root:
            perf=ProviderPerformance(root,("LRCLIB","SyncLRC","Unison"))
            rows=[
                ["song.mp3",2,"LRCLIB","SAVED","",2.0,"HTTP 200",1],
                ["song2.mp3",2,"SyncLRC","REVIEW_AVAILABLE","",1.0,"HTTP 200",1],
                ["song3.mp3",2,"Unison","NO_MATCH","",4.0,"HTTP 404",1],
                ["song4.mp3",2,"SyncLRC","SKIPPED (HTTP 429)","",0.0,"",0],
                ["song5.mp3",2,"LRCLIB","CACHED_NO_MATCH","",0.0,"",0],
            ]
            self.assertEqual(perf.record_rows(rows,"config1",123),3)
            self.assertEqual(perf.record_rows(rows,"config1",123),0)
            again=ProviderPerformance(root,("LRCLIB","SyncLRC","Unison"))
            stats=again.statistics()
            self.assertEqual(stats["LRCLIB"]["saved"],1)
            self.assertEqual(stats["LRCLIB"]["attempts"],1)
            self.assertEqual(stats["SyncLRC"]["review"],1)
            self.assertEqual(stats["Unison"]["no_match"],1)
            output=again.export_csv()
            with output.open(encoding="utf-8-sig",newline="") as src:
                data=list(csv.DictReader(src))
            self.assertEqual(data[0]["verified success rate %"],"100.0")
            self.assertEqual(data[1]["verified success rate %"],"0.0")

    def test_smart_order_preserves_lrclib_first_and_unsampled_at_end(self):
        with tempfile.TemporaryDirectory() as root:
            perf=ProviderPerformance(root,("LRCLIB","Slow","Fast","Unknown"))
            entries=[]
            for i in range(12):
                entries.append([f"fast{i}.mp3",2,"Fast","SAVED","",1.0,"200",1])
                entries.append([f"slow{i}.mp3",2,"Slow","NO_MATCH","",7.0,"404",1])
            perf.record_rows(entries,"scoring",1)
            self.assertEqual(perf.sorted_smart(("LRCLIB","Slow","Unknown","Fast")),
                             ["LRCLIB","Fast","Slow","Unknown"])

    def test_truncated_checkpoint_tail_repaired_before_next_record(self):
        with tempfile.TemporaryDirectory() as root:
            a=Path(root)/"a.mp3";b=Path(root)/"b.mp3"
            a.write_bytes(b"A");b.write_bytes(b"B")
            state=SearchCheckpoint(root,"2.2.0","same")
            self.assertTrue(state.save(a,1,"NOT_FOUND","missing",set(),False,[],[],[],[]))
            with state.path.open("a",encoding="utf-8") as stream:
                stream.write('{"schema":1,"broken":')
            self.assertTrue(state.save(b,1,"NOT_FOUND","missing",set(),False,[],[],[],[]))
            resumed=SearchCheckpoint(root,"2.2.0","same")
            self.assertIsNotNone(resumed.get(a,1))
            self.assertIsNotNone(resumed.get(b,1))
            self.assertEqual(resumed.invalid_lines,0)

    def test_custom_order_console_prompt_and_return_without_search(self):
        with tempfile.TemporaryDirectory() as root:
            music=Path(root)
            (music/"Track.mp3").write_bytes(b"AUDIO")
            answers=iter(["1","n","n","fast","c",
                          "Unison,LRCLIB,SyncLRC,NetEase,LrcAPI",
                          "n","n","n","0"])
            with mock.patch("builtins.input",side_effect=lambda prompt:next(answers)), \
                 mock.patch.object(app,"select_folder",return_value=music), \
                 mock.patch.object(app,"song_info",return_value=("Track","Artist","",180)), \
                 mock.patch.object(app,"configure_local_lrclib"), \
                 mock.patch.object(app,"configure_lrclib_contact",return_value=True), \
                 mock.patch.object(app,"load_provider_cooldowns"), \
                 mock.patch.object(app,"show_provider_availability"), \
                 redirect_stdout(io.StringIO()):
                app.main()
            self.assertEqual(app.ACTIVE_PROVIDERS,
                             ("Unison","LRCLIB","SyncLRC","NetEase","LrcAPI"))


if __name__=="__main__":
    unittest.main(verbosity=2)
