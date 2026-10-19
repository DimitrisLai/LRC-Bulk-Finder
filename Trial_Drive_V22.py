"""Independent integration smoke test for the exact published v2.2.0 ZIP.

This file lives only on the trial branch. Production files, GitHub main and
existing release assets are unmodified. No online provider is queried here.
"""
import csv
import io
import sqlite3
import sys
import tempfile
import time
import types
import unittest
from contextlib import closing,redirect_stdout
from pathlib import Path
from unittest import mock

# Import the extracted PUBLISHED ZIP, never branch or main source.
ROOT=Path(__file__).resolve().parent/"trial_release_files"/"unpacked"/"LRC_Bulk_Finder_v2_2_0"
assert ROOT.is_dir(), "The published ZIP has not been extracted"
sys.path.insert(0,str(ROOT))
sys.modules.setdefault("syncedlyrics",types.SimpleNamespace(search=lambda *x,**k:None))
import LRC_Bulk_Finder as app
from lrclib_local import LocalLRCLIB
from search_checkpoint import SearchCheckpoint,checkpoint_signature
from search_performance import MusicBrainzDiskCache,ProviderPerformance,choose_provider_order

LRC="[00:03.00] Verse one\n[00:23.00] Verse two\n[01:20.00] Chorus\n[02:52.00] End\n"


def tiny_db(path):
    with closing(sqlite3.connect(path)) as con,con:
        con.executescript("""
        CREATE TABLE tracks(
            id INTEGER PRIMARY KEY, name TEXT, name_lower TEXT,
            artist_name TEXT, artist_name_lower TEXT,
            duration REAL, last_lyrics_id INTEGER
        );
        CREATE TABLE lyrics (id INTEGER PRIMARY KEY,synced_lyrics TEXT);
        CREATE INDEX lookup_title ON tracks(name_lower);
        """)
        con.execute("INSERT INTO tracks VALUES(1,?,?,?,?,?,1)",(
            "Κύματα","κύματα","Γιώργος Αλκαίος",
            "γιώργος αλκαίος",180))
        con.execute("INSERT INTO lyrics VALUES(1,?)",(LRC,))


class PublishedReleaseTrial(unittest.TestCase):
    def setUp(self):
        app.GREEK_MODE=False
        app.G2G_ENABLED=False
        app.G2G_TOOL=None
        app.MB_ENABLED=False
        app.MB_DISK_CACHE=None
        app.MB_CACHE.clear()
        app.MB_CACHE_DURATIONS.clear()
        app.MB_DISABLED_REASON=None
        app.STAGED_ONLINE_MODE=False
        app.LOCAL_LRCLIB=None
        app.blocked.clear()
        app.G2G_SONG_PLANS.clear()

    def tearDown(self):
        app.STAGED_ONLINE_MODE=False
        app.LOCAL_LRCLIB=None
        app.MB_DISK_CACHE=None

    def test_01_imports_genuinely_published_zip(self):
        self.assertEqual(app.VERSION,"2.2.0")
        self.assertEqual(Path(app.__file__).resolve(),
                         (ROOT/"LRC_Bulk_Finder.py").resolve())
        self.assertIn("2.2.0",app.HEADERS["User-Agent"])
        self.assertTrue((ROOT/"START_HERE.cmd").is_file())
        self.assertTrue((ROOT/"Run_LRC_Finder.cmd").is_file())
        self.assertTrue((ROOT/"Start_LRC_Finder.bat").is_file())

    def test_02_native_greek_and_greeklish_sqlite_match(self):
        with tempfile.TemporaryDirectory() as temp:
            db=Path(temp)/"lrclib.sqlite3"
            tiny_db(db)
            app.LOCAL_LRCLIB=LocalLRCLIB(db)
            app.GREEK_MODE=True
            app.load_aliases()
            app.load_greek_words()
            app.precompute_greek_plan("Kimata","Giorgos Alkaios",None)
            variants=app.query_variants("Kimata","Giorgos Alkaios")
            self.assertIn(("Κύματα","Γιώργος Αλκαίος"),variants)
            hit=app.local_lrclib_search("Κύματα","Γιώργος Αλκαίος",
                                        180,app.CandidateReview())
            self.assertIsNotNone(hit,"A native-Greek database row must verify")
            self.assertTrue(hit.verified)
            review=app.CandidateReview()
            latin_hit=app.local_lrclib_search("Kimata","Giorgos Alkaios",180,review)
            self.assertTrue(latin_hit is not None or review.items,
                            "Greeklish must find verified or reviewable local result")

    def test_03_cache_reuses_across_instances_and_does_not_cache_error(self):
        with tempfile.TemporaryDirectory() as temp:
            cache=MusicBrainzDiskCache(temp)
            cache.save("Title","Artist",180,False,("Official title","Artist"))
            cache.save("No Result","Artist",180,False,None)
            another=MusicBrainzDiskCache(temp)
            self.assertEqual(another.lookup("Title","Artist",180,False),
                             (True,("Official title","Artist")))
            self.assertEqual(another.lookup("Title","Artist",202,False),
                             (False,None))
            self.assertEqual(another.lookup("No Result","Artist",180,False),
                             (True,None))
            self.assertEqual(another.lookup("No Result","Artist",180,True),
                             (False,None))
            with mock.patch.object(app,"direct_json",
                    side_effect=app.ProviderFailure("HTTP 503 overloaded")):
                app.MB_ENABLED=True
                app.MB_DISK_CACHE=another
                self.assertIsNone(app.musicbrainz_variant("Failure","Artist",180))
            self.assertEqual(MusicBrainzDiskCache(temp).lookup(
                "Failure","Artist",180,False),(False,None))

    def test_04_smart_ranking_never_drops_providers_or_confuses_candidates(self):
        with tempfile.TemporaryDirectory() as temp:
            providers=("LRCLIB","SyncLRC","Unison","NetEase")
            perf=ProviderPerformance(temp,providers)
            rows=[]
            for i in range(12):
                rows.extend([
                    [f"fast{i}.mp3",2,"NetEase","SAVED","",1.5,"unknown",1],
                    [f"slow{i}.mp3",2,"SyncLRC","REVIEW_AVAILABLE","",5.0,"HTTP 200",1],
                    [f"none{i}.mp3",2,"Unison","NO_MATCH","",8.0,"HTTP 404",1],
                    [f"skip{i}.mp3",2,"NetEase","SKIPPED","",0.0,"",0],
                ])
            self.assertEqual(perf.record_rows(rows,"fresh-run-id",14),36)
            self.assertEqual(perf.record_rows(rows,"fresh-run-id",14),0)
            saved=ProviderPerformance(temp,providers)
            sorted_list=tuple(saved.sorted_smart(providers))
            self.assertEqual(sorted_list[0],"LRCLIB")
            self.assertEqual(set(sorted_list),set(providers))
            self.assertLess(sorted_list.index("NetEase"),sorted_list.index("SyncLRC"))
            stats=saved.statistics()
            self.assertEqual(stats["NetEase"]["saved"],12)
            self.assertEqual(stats["SyncLRC"]["saved"],0)
            self.assertEqual(stats["SyncLRC"]["review"],12)
            self.assertEqual(sum(v["attempts"] for v in stats.values()),36)
            with self.assertRaises(ValueError):
                choose_provider_order(providers,"c","LRCLIB,Unison")

    def test_05_checkpoint_tail_repair_and_changed_track_invalidation(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            song=folder/"Song.mp3"
            song.write_bytes(b"ORIGINAL_AUDIO_BYTES")
            signature=checkpoint_signature("2.2.0",{"mode":"staged"})
            cp=SearchCheckpoint(folder,"2.2.0",signature)
            self.assertTrue(cp.save(song,1,"NOT_FOUND","local miss",set(),False,
                                    ["Song",1,"NOT_FOUND"],[],[],[]))
            with cp.path.open("ab") as dest:
                dest.write(b'{"incomplete":')
            self.assertTrue(cp.save(song,2,"NOT_FOUND","online miss",set(),False,
                                    ["Song",2,"NOT_FOUND"],[],[],[]))
            restored=SearchCheckpoint(folder,"2.2.0",signature)
            self.assertEqual(restored.invalid_lines,0)
            self.assertEqual(restored.get(song,1)["status"],"NOT_FOUND")
            self.assertEqual(restored.get(song,2)["status"],"NOT_FOUND")
            self.assertEqual(restored.run_id,cp.run_id)
            song.write_bytes(b"CHANGED_AUDIO")
            self.assertIsNone(restored.get(song,1))
            self.assertIsNone(restored.get(song,2))

    def test_06_preserves_existing_lyrics_and_mp3_when_saving(self):
        with tempfile.TemporaryDirectory() as temp:
            song=Path(temp)/"Song.mp3"
            song.write_bytes(b"IMPORTANT ORIGINAL MP3")
            existing=song.with_suffix(".lrc")
            existing.write_text("[00:01.00] user existing lyrics\n",encoding="utf-8")
            hit=app.Hit(LRC,"LOCAL_SQLITE","verified","LOCAL",True)
            with self.assertRaises(FileExistsError):
                app.save_hit(song,hit)
            self.assertEqual(song.read_bytes(),b"IMPORTANT ORIGINAL MP3")
            self.assertEqual(existing.read_text(encoding="utf-8"),
                             "[00:01.00] user existing lyrics\n")

    def test_07_three_stage_full_runtime_with_real_local_sqlite_and_mock_network(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            originals={
                "Fallback.mp3":b"ORIGINAL F",
                "Kimata.mp3":b"ORIGINAL K",
                "Timeout.mp3":b"ORIGINAL T",
            }
            for name,data in originals.items():
                (folder/name).write_bytes(data)
            db=folder/"fixture.db"
            tiny_db(db)
            app.LOCAL_LRCLIB=LocalLRCLIB(db)
            calls=[]
            interrupted={"done":False}
            def metadata(path):
                if path.stem=="Kimata":
                    return "Κύματα","Γιώργος Αλκαίος","",180
                return path.stem,"Test Artist","",180
            def online(title,artist,album,duration,review,*,only_providers=None,
                       retry_targets=None,timings=None,request_traces=None):
                # Offline stage must have finished ALL tracks before this.
                calls.append(("online" if only_providers is None else "retry",
                              title,tuple(sorted(only_providers or []))))
                if timings is not None:timings.append(("SyncLRC",.05))
                if request_traces is not None:request_traces.append([])
                if title=="Fallback":
                    return app.Hit(LRC,"SyncLRC","verified","ORIGINAL",True),\
                           "SAVED","verified match",["SyncLRC=SAVED"]
                if title=="Timeout" and only_providers is None:
                    retry_targets.add("LiriQo")
                    return None,"TIMEOUT","LiriQo timed out",["LiriQo=ERROR (timeout)"]
                return None,"NOT_FOUND","no match",["LiriQo=NO_MATCH"]
            def run():
                answers=iter(["5","n","n","n","full","d","n","n","n","a","n"])
                with mock.patch("builtins.input",side_effect=lambda p:next(answers)), \
                     mock.patch.object(app,"select_folder",return_value=folder), \
                     mock.patch.object(app,"ensure_local_lrclib_config",return_value=True), \
                     mock.patch.object(app,"configure_lrclib_contact",return_value=True), \
                     mock.patch.object(app,"load_provider_cooldowns"), \
                     mock.patch.object(app,"show_provider_availability"), \
                     mock.patch.object(app,"song_info",side_effect=metadata), \
                     mock.patch.object(app,"search_song",side_effect=online), \
                     redirect_stdout(io.StringIO()) as log:
                    app.main()
                return log.getvalue()
            log=run()
            self.assertTrue((folder/"Kimata.lrc").is_file(),"Native Greek local SQLite must save")
            self.assertTrue((folder/"Fallback.lrc").is_file(),"Online provider fallback must save")
            self.assertFalse((folder/"Timeout.lrc").exists())
            self.assertEqual(calls,[
                ("online","Fallback",()),("online","Timeout",()),
                ("retry","Timeout",("LiriQo",))])
            for name,original in originals.items():
                self.assertEqual((folder/name).read_bytes(),original)
            checkpoint=folder/"LRC_Run_Checkpoint_v2_2_0.jsonl"
            self.assertTrue(checkpoint.is_file())
            self.assertIn("Round 3",log)
            firstcalls=list(calls)
            log2=run()
            self.assertEqual(calls,firstcalls,
                             "Restart must not redo finished online requests")
            self.assertIn("CHECKPOINT:",log2)
            self.assertTrue((folder/"LRC_Provider_Performance_v2_2.csv").is_file())


if __name__=="__main__":
    unittest.main(verbosity=2)
