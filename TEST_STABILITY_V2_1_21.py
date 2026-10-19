"""v2.1.21 offline accuracy + durable resume + cross-round candidate tests.

Every fixture is a tiny scratch SQLite/MP3 surrogate. No real network, audio,
database downloads or modifications to user files.
"""
import csv
import io
import json
import sqlite3
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout, closing
from pathlib import Path
from unittest import mock
sys.modules.setdefault("syncedlyrics",types.SimpleNamespace(search=lambda *a,**kw:None))
import LRC_Bulk_Finder as app
from lrclib_local import LocalLRCLIB
from search_checkpoint import SearchCheckpoint, checkpoint_signature

TIMED="[00:05.00] One\n[00:30.00] Two\n[02:59.00] Three\n"


class StabilityTests(unittest.TestCase):
    def setUp(self):
        app.GREEK_MODE=False
        app.G2G_ENABLED=False
        app.G2G_TOOL=None
        app.MB_ENABLED=False
        app.STAGED_ONLINE_MODE=False
        app.LOCAL_LRCLIB=None
        app.blocked.clear()
        app.HISTORY_ENABLED=False
        app.G2G_SONG_PLANS.clear()

    def tearDown(self):
        app.STAGED_ONLINE_MODE=False
        app.LOCAL_LRCLIB=None

    def test_approved_greek_third_variant_passed_to_local_search(self):
        app.GREEK_MODE=True
        app.load_aliases()
        app.load_greek_words()
        p=app.precompute_greek_plan("Kimata","Giorgos Alkaios",None)
        self.assertEqual(p["Greek artist alternative"],"Γιώργος Αλκαίος")
        self.assertEqual(p["Greek title alternative"],"Κύματα")
        class Probe:
            def search(self,variants,duration):
                self.variants=variants
                return []
        probe=Probe()
        app.LOCAL_LRCLIB=probe
        app.local_lrclib_search("Kimata","Giorgos Alkaios",180,app.CandidateReview())
        self.assertIn(("Κύματα","Γιώργος Αλκαίος"),probe.variants)
        self.assertGreaterEqual(len(probe.variants),3)

    def test_real_sqlite_finds_only_third_greek_variant(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/"lyrics.sqlite3"
            with closing(sqlite3.connect(db)) as con, con:
                con.executescript("""
                CREATE TABLE tracks (id INTEGER PRIMARY KEY,name TEXT,name_lower TEXT,
                    artist_name TEXT,artist_name_lower TEXT,duration REAL,last_lyrics_id INTEGER);
                CREATE TABLE lyrics (id INTEGER PRIMARY KEY,synced_lyrics TEXT);
                CREATE INDEX lookup_title ON tracks(name_lower);
                """)
                con.execute("INSERT INTO tracks VALUES(1,?,?,?,?,?,1)",(
                  "Κύματα","κύματα","Γιώργος Αλκαίος","γιώργος αλκαίος",180))
                con.execute("INSERT INTO lyrics VALUES(1,?)",(TIMED,))
            source=LocalLRCLIB(db)
            variants=[("Kimata","Giorgos Alkaios"),
                      ("Kimata","Γιώργος Αλκαίος"),
                      ("Κύματα","Γιώργος Αλκαίος")]
            self.assertEqual(source.search(variants[:2]),[])
            rows=source.search(variants)
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]["syncedLyrics"],TIMED)

    def test_checkpoint_discards_truncated_tail_and_changed_mp3(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            song=folder/"A.mp3"
            song.write_bytes(b"UNCHANGED")
            signature=checkpoint_signature("2.1.21",{"mode":"staged"})
            state=SearchCheckpoint(folder,"2.1.21",signature)
            record=[str(song),1,"NOT_FOUND","missing","","",""]
            self.assertTrue(state.save(song,1,"NOT_FOUND","missing",set(),False,record,[],[],[]))
            with state.path.open("a",encoding="utf-8") as output:
                output.write('{"schema":')
            restored=SearchCheckpoint(folder,"2.1.21",signature)
            self.assertEqual(restored.get(song,1)["status"],"NOT_FOUND")
            self.assertIsNone(SearchCheckpoint(folder,"2.1.21","different").get(song,1))
            song.write_bytes(b"DIFFERENT")
            self.assertIsNone(restored.get(song,1))

    @staticmethod
    def run_stage(folder,offline,online):
        answers=iter(["5","n","n","full","d","n","n","n","a","n"])
        with mock.patch("builtins.input",side_effect=lambda _:next(answers)), \
             mock.patch.object(app,"select_folder",return_value=folder), \
             mock.patch.object(app,"ensure_local_lrclib_config",return_value=True), \
             mock.patch.object(app,"load_provider_cooldowns"), \
             mock.patch.object(app,"configure_lrclib_contact",return_value=True), \
             mock.patch.object(app,"show_provider_availability"), \
             mock.patch.object(app,"song_info",side_effect=lambda p:(p.stem,"Test Artist","",180)), \
             mock.patch.object(app,"local_lrclib_search",side_effect=offline), \
             mock.patch.object(app,"search_song",side_effect=online), \
             redirect_stdout(io.StringIO()) as output:
            app.main()
        return output.getvalue()

    def test_candidates_remain_review_after_timeout_retry_no_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            mp3=folder/"B.mp3"
            mp3.write_bytes(b"ORIGINAL AUDIO")
            calls=[]
            def offline(title,artist,duration,review):
                calls.append(("offline",title))
                review.add("LRCLIB local",title,artist,"timing uncertain",lyrics=TIMED)
                return None
            def online(title,artist,album,duration,review,*,only_providers=None,
                       retry_targets=None,timings=None,request_traces=None):
                if only_providers is None:
                    calls.append(("online",title))
                    retry_targets.add("LiriQo")
                    if timings is not None:timings.append(("LiriQo",.2))
                    if request_traces is not None:request_traces.append([])
                    return None,"TIMEOUT","LiriQo timed out",["LiriQo=ERROR (timeout)"]
                calls.append(("retry",title))
                if timings is not None:timings.append(("LiriQo",.1))
                if request_traces is not None:request_traces.append([])
                return None,"NOT_FOUND","LiriQo no match",["LiriQo=NO_MATCH"]
            self.run_stage(folder,offline,online)
            rows=list(csv.DictReader((folder/"LRC_Finder_Report_v2_1_15.csv").open(
                  encoding="utf-8-sig")))
            self.assertEqual(rows[-1]["status"],"REVIEW_PARTIAL")
            self.assertEqual(calls,[("offline","B"),("online","B"),("retry","B")])
            self.assertEqual(mp3.read_bytes(),b"ORIGINAL AUDIO")
            self.assertTrue(app.candidate_path(mp3).is_file())
            self.assertIn("B", (folder/"LRC_Review_Needed.txt").read_text(encoding="utf-8-sig"))

    def test_restart_skips_completed_stages_and_rebuilds_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            for name in ("A","B"):
                (folder/(name+".mp3")).write_bytes(b"AUDIO-"+name.encode())
            events=[]
            def offline(title,artist,duration,review):
                events.append(("offline",title))
                return None
            interrupted={"value":False}
            def online(title,artist,album,duration,review,*,only_providers=None,
                       retry_targets=None,timings=None,request_traces=None):
                events.append(("online",title))
                if title=="B" and not interrupted["value"]:
                    interrupted["value"]=True
                    raise KeyboardInterrupt()
                if timings is not None:timings.append(("SyncLRC",.1))
                if request_traces is not None:request_traces.append([])
                return None,"NOT_FOUND","no match",["SyncLRC=NO_MATCH"]
            self.run_stage(folder,offline,online)
            self.assertEqual(events,[("offline","A"),("offline","B"),
                                     ("online","A"),("online","B")])
            events.clear()
            resumed=self.run_stage(folder,offline,online)
            self.assertEqual(events,[("online","B")])
            self.assertIn("CHECKPOINT:",resumed)
            rows=list(csv.DictReader((folder/"LRC_Finder_Report_v2_1_15.csv").open(
                  encoding="utf-8-sig")))
            self.assertEqual(len(rows),4) # offline A/B, online A/B reconstructed
            self.assertEqual(len([r for r in rows if r["round"]=="1"]),2)
            self.assertEqual(len([r for r in rows if r["round"]=="2"]),2)
            self.assertEqual((folder/"B.mp3").read_bytes(),b"AUDIO-B")

if __name__=="__main__":
    unittest.main(verbosity=2)
