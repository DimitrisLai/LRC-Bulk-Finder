"""Independent smoke, integration and safety audit against the published v2.3 ZIP.

This module is only on audit/v2.3.0-release-readiness; nothing in production
is modified. All files are scratch fixtures, web calls are mocked.
"""
import builtins,csv,hashlib,io,json,os,sqlite3,sys,tempfile,time,types,unittest
from contextlib import closing,redirect_stdout
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parent/"release_unpacked"/"LRC_Bulk_Finder_v2_3_0"
assert ROOT.is_dir(),"Published v2.3.0 archive is not extracted"
sys.path.insert(0,str(ROOT))
sys.modules.setdefault("syncedlyrics",types.SimpleNamespace(search=lambda *args,**kw:None))
import LRC_Bulk_Finder as app
from lrclib_local import LocalLRCLIB
from search_profiles import (load_profiles,save_profiles,validate_profile,
                             ProfileAnswers,DEFAULT,PROVIDER_FULL)
from run_saved_profile import run_profile
from progress_eta import RoundProgress
from review_candidates_gui import (list_review_candidates,preview_candidate,
                                   explicitly_promote)
from search_checkpoint import SearchCheckpoint,checkpoint_signature
from search_performance import MusicBrainzDiskCache,ProviderPerformance

LYRICS="[00:02.00] Phrases\n[00:35.00] Important chorus\n[01:07.00] Another chorus\n[02:58.00] Ending\n"


def make_db(path):
    with closing(sqlite3.connect(path)) as connection,connection:
        connection.executescript("""
          CREATE TABLE tracks(id INTEGER PRIMARY KEY,name TEXT,name_lower TEXT,
               artist_name TEXT,artist_name_lower TEXT,duration REAL,last_lyrics_id INTEGER);
          CREATE TABLE lyrics(id INTEGER PRIMARY KEY,synced_lyrics TEXT);
          CREATE INDEX idx_track_name ON tracks(name_lower);
        """)
        connection.execute("INSERT INTO tracks VALUES(1,?,?,?,?,?,1)",
                  ("Κύματα","κύματα","Γιώργος Αλκαίος","γιώργος αλκαίος",180))
        connection.execute("INSERT INTO lyrics VALUES(1,?)",(LYRICS,))


class ReleaseAudit(unittest.TestCase):
    def setUp(self):
        app.GREEK_MODE=False;app.G2G_ENABLED=False;app.G2G_TOOL=None
        app.MB_ENABLED=False;app.MB_DISK_CACHE=None
        app.MB_CACHE.clear();app.MB_CACHE_DURATIONS.clear()
        app.MB_DISABLED_REASON=None
        app.STAGED_ONLINE_MODE=False;app.LOCAL_LRCLIB=None
        app.blocked.clear();app.G2G_SONG_PLANS.clear()
        app.HISTORY_ENABLED=False
    def tearDown(self):
        app.STAGED_ONLINE_MODE=False;app.LOCAL_LRCLIB=None
        app.MB_DISK_CACHE=None;app.MB_ENABLED=False

    def test_01_published_source_and_launchers(self):
        self.assertEqual(app.VERSION,"2.3.0")
        self.assertEqual(Path(app.__file__).resolve(),(ROOT/"LRC_Bulk_Finder.py").resolve())
        for name in ("START_HERE.cmd","OPEN_CONTROL_CENTER.cmd","Run_LRC_Finder.cmd",
                     "Start_LRC_Finder.bat","CONNECT_EXISTING_LRCLIB_DATABASE.cmd"):
            self.assertTrue((ROOT/name).is_file(),name)

    def test_02_greeklish_offline_database_and_wrong_version(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"database.sqlite3";make_db(db)
            app.LOCAL_LRCLIB=LocalLRCLIB(db)
            app.GREEK_MODE=True
            app.load_aliases();app.load_greek_words()
            app.precompute_greek_plan("Kimata","Giorgos Alkaios",None)
            self.assertIn(("Κύματα","Γιώργος Αλκαίος"),
                         app.query_variants("Kimata","Giorgos Alkaios"))
            hit=app.local_lrclib_search("Κύματα","Γιώργος Αλκαίος",
                                      180,app.CandidateReview())
            self.assertIsNotNone(hit)
            self.assertTrue(hit.verified)
            wrong=app.local_lrclib_search("Κύματα (Live)","Γιώργος Αλκαίος",
                                         180,app.CandidateReview())
            self.assertIsNone(wrong)

    def test_03_duration_and_remix_safety(self):
        self.assertTrue(app.acceptable("Song","Artist",180,"Song","Artist",182.9,LYRICS)[0])
        self.assertFalse(app.acceptable("Song","Artist",180,"Song","Artist",183.2,LYRICS)[0])
        self.assertFalse(app.acceptable("Song (Remix)","Artist",180,"Song","Artist",180,LYRICS)[0])
        self.assertFalse(app.acceptable("Song","Artist",180,"Song","",180,LYRICS)[0])

    def test_04_profile_json_atomicity_unauthorized_options(self):
        with tempfile.TemporaryDirectory() as td:
            loc=Path(td)/"profiles.json"
            settings={**DEFAULT,"folder":td,"action":"5","limit":"a"}
            save_profiles({"Greek FULL":settings},loc)
            self.assertEqual(load_profiles(loc)["Greek FULL"]["limit"],"a")
            with self.assertRaises(ValueError):
                validate_profile({**settings,"order":"c","custom_order":"LRCLIB,LRCLIB"})
            with self.assertRaises(ValueError):
                validate_profile({**settings,"action":"2"})
            self.assertFalse(loc.with_name(loc.name+".tmp").exists())
            before=loc.read_bytes();loc.write_text("{broken",encoding="utf-8")
            with self.assertRaises(ValueError):load_profiles(loc)
            self.assertEqual(loc.read_text(encoding="utf-8"),"{broken")

    def test_05_profile_runner_does_not_guess_unknown_prompts(self):
        with tempfile.TemporaryDirectory() as td:
            values={**DEFAULT,"folder":td,"action":"4","database":str(Path(td)/"local.sqlite3")}
            obj=ProfileAnswers(values)
            self.assertEqual(obj("Choose [1/2/3/4/5] (default 1): "),"4")
            self.assertEqual(obj("Path to existing .sqlite3 file (Enter to cancel): "),
                             str(Path(td)/"local.sqlite3"))
            with self.assertRaises(RuntimeError):
                obj("Would you like to overwrite existing MP3 tags? [Y/n]: ")

    def test_06_run_profile_cli_no_tracks_and_no_hang(self):
        with tempfile.TemporaryDirectory() as td:
            cfg=Path(td)/"profiles.json"
            save_profiles({"test normal":{**DEFAULT,"folder":td,"action":"1",
                        "greek":False,"musicbrainz":False,"provider_mode":"fast",
                        "order":"d","recursive":False,"history":False,"limit":"1"}},cfg)
            with mock.patch.object(app,"configure_local_lrclib"), \
                 mock.patch.object(app,"configure_lrclib_contact",return_value=True), \
                 mock.patch.object(app,"load_provider_cooldowns"), \
                 mock.patch.object(app,"show_provider_availability"), \
                 redirect_stdout(io.StringIO()) as output:
                run_profile("test normal",cfg)
            self.assertIn("0 eligible",output.getvalue())

    def test_07_option_4_is_offline_and_writes_verified_only(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            song=folder/"Kimata.mp3";song.write_bytes(b"ORIGINAL_BYTES")
            make_db(folder/"lrclib.sqlite3")
            app.LOCAL_LRCLIB=LocalLRCLIB(folder/"lrclib.sqlite3")
            choices=iter(["n","n","a","y"])
            def fake_input(_):return next(choices)
            def metadata(_):return "Κύματα","Γιώργος Αλκαίος","",180
            with mock.patch("builtins.input",side_effect=fake_input), \
                 mock.patch.object(app,"song_info",side_effect=metadata), \
                 mock.patch.object(app,"direct_json",side_effect=AssertionError("NO HTTP ALLOWED")), \
                 redirect_stdout(io.StringIO()) as output:
                app.run_offline_lrclib_folder(folder)
            self.assertTrue(song.with_suffix(".lrc").is_file(),output.getvalue())
            self.assertEqual(song.read_bytes(),b"ORIGINAL_BYTES")
            self.assertIn("OFFLINE",output.getvalue())

    def test_08_option_5_all_offline_first_then_online_then_retry(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            for title in ["SavedOffline","Online","Timeout","Review"]:
                (folder/(title+".mp3")).write_bytes(("AUDIO "+title).encode())
            calls=[];interrupted={"once":False}
            def offline(title,artist,duration,review):
                calls.append(("offline",title))
                if title=="SavedOffline":return app.Hit(LYRICS,"LRCLIB","verified","LOCAL",True)
                if title=="Review":
                    review.add("LRCLIB local",title,artist,"needs review",LYRICS)
                return None
            def online(title,artist,album,duration,review,*,only_providers=None,
                       retry_targets=None,timings=None,request_traces=None):
                calls.append(("retry" if only_providers else "online",title))
                if timings is not None:timings.append(("SyncLRC",.1))
                if request_traces is not None:request_traces.append([])
                if title=="Online":
                    return app.Hit(LYRICS,"SyncLRC","verified","ORIGINAL",True),"SAVED","match",["SyncLRC=SAVED"]
                if title=="Timeout" and only_providers is None:
                    retry_targets.add("LiriQo")
                    return None,"TIMEOUT","LiriQo timeout",["LiriQo=ERROR (timeout)"]
                return None,"NOT_FOUND","no match",["LiriQo=NO_MATCH"]
            def runner():
                answers=iter(["5","n","n","full","d","n","n","n","a","n"])
                with mock.patch("builtins.input",side_effect=lambda _:next(answers)),\
                     mock.patch.object(app,"select_folder",return_value=folder),\
                     mock.patch.object(app,"ensure_local_lrclib_config",return_value=True),\
                     mock.patch.object(app,"load_provider_cooldowns"),\
                     mock.patch.object(app,"configure_lrclib_contact",return_value=True),\
                     mock.patch.object(app,"show_provider_availability"),\
                     mock.patch.object(app,"song_info",side_effect=lambda p:(p.stem,"Test Artist","",180)),\
                     mock.patch.object(app,"local_lrclib_search",side_effect=offline),\
                     mock.patch.object(app,"search_song",side_effect=online),\
                     redirect_stdout(io.StringIO()) as output:
                    app.main()
                return output.getvalue()
            out=runner()
            self.assertEqual([p for p,_ in calls[:4]],["offline"]*4)
            self.assertEqual([p for p,_ in calls[4:]],["online","online","online","retry"])
            self.assertTrue((folder/"SavedOffline.lrc").exists())
            self.assertTrue((folder/"Online.lrc").exists())
            self.assertFalse((folder/"Review.lrc").exists())
            self.assertTrue((folder/"Review.candidate.lrc").exists())
            self.assertFalse((folder/"Timeout.lrc").exists())
            self.assertIn("PROGRESS ROUND",out)
            first=list(calls)
            again=runner()
            self.assertEqual(calls,first,"Checkpoint resume should not retry finished provider work")
            self.assertIn("CHECKPOINT:",again)
            for title in ("Online","SavedOffline","Timeout","Review"):
                self.assertEqual((folder/(title+".mp3")).read_bytes(),("AUDIO "+title).encode())
            path=folder/"LRC_Review_Needed.txt"
            self.assertIn("Review",path.read_text(encoding="utf-8-sig"))

    def test_09_review_promotion_primary_only_and_original_protection(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"Song.mp3").write_bytes(b"CRITICAL AUDIO")
            (root/"Song.candidate.lrc").write_text(LYRICS,encoding="utf-8")
            (root/"Song.candidate.2.lrc").write_text(LYRICS,encoding="utf-8")
            self.assertEqual([p["index"] for p in list_review_candidates(root)],[1,2])
            with self.assertRaises(PermissionError):
                explicitly_promote(root/"Song.candidate.lrc",approved=False)
            with self.assertRaises(ValueError):
                explicitly_promote(root/"Song.candidate.2.lrc",approved=True)
            before=(root/"Song.mp3").read_bytes()
            status,_=explicitly_promote(root/"Song.candidate.lrc",approved=True)
            self.assertEqual(status,"PROMOTED")
            self.assertEqual((root/"Song.mp3").read_bytes(),before)
            self.assertIn("[00:00.00] candidate",(root/"Song.lrc").read_text(encoding="utf-8"))
            self.assertTrue((root/"Song.candidate.lrc").exists())
            self.assertFalse((root/"Song.candidate.2.lrc").exists())
            with self.assertRaises(ValueError):preview_candidate(root/"Song.mp3")

    def test_10_provider_telemetry_no_fake_verified_hits(self):
        with tempfile.TemporaryDirectory() as td:
            perf=ProviderPerformance(td,("LRCLIB","SyncLRC"))
            rows=[["file1",2,"LRCLIB","SAVED","",2,"200",1],
                  ["file2",2,"SyncLRC","REVIEW_AVAILABLE","",1,"200",1],
                  ["file3",2,"SyncLRC","SKIPPED (429)","",0,"429",0]]
            self.assertEqual(perf.record_rows(rows,"session-a",100),2)
            self.assertEqual(perf.record_rows(rows,"session-a",100),0)
            totals=ProviderPerformance(td,("LRCLIB","SyncLRC")).statistics()
            self.assertEqual(totals["LRCLIB"]["saved"],1)
            self.assertEqual(totals["SyncLRC"]["saved"],0)
            self.assertEqual(totals["SyncLRC"]["review"],1)
            self.assertEqual(totals["SyncLRC"]["attempts"],1)

    def test_11_cache_does_not_mix_duration_greek_or_http_error(self):
        with tempfile.TemporaryDirectory() as td:
            cache=MusicBrainzDiskCache(td)
            cache.save("Track","Artist",180,True,("Τραγούδι","Artist"))
            new=MusicBrainzDiskCache(td)
            self.assertEqual(new.lookup("Track","Artist",180,True),
                             (True,("Τραγούδι","Artist")))
            self.assertEqual(new.lookup("Track","Artist",185,True),(False,None))
            self.assertEqual(new.lookup("Track","Artist",180,False),(False,None))

    def test_12_corrupted_resume_log_recovers_and_invalidates_changed_track(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td); mp3=folder/"Song.mp3";mp3.write_bytes(b"AUDIO")
            sig=checkpoint_signature("2.3.0",{"mode":"staged"})
            cp=SearchCheckpoint(folder,"2.3.0",sig)
            cp.save(mp3,1,"NOT_FOUND","no lyrics",set(),False,[],[],[],[])
            with cp.path.open("ab") as stream:stream.write(b'{"corrupt":')
            cp.save(mp3,2,"NOT_FOUND","no lyrics",set(),False,[],[],[],[])
            reread=SearchCheckpoint(folder,"2.3.0",sig)
            self.assertEqual(reread.invalid_lines,0)
            self.assertEqual(reread.get(mp3,2)["status"],"NOT_FOUND")
            mp3.write_bytes(b"NEW AUDIO")
            self.assertIsNone(reread.get(mp3,1))

    def test_13_progress_estimate_only_current_stage(self):
        progress=RoundProgress(8,2,clock=lambda:100)
        self.assertIsNone(progress.status()["remaining"])
        for duration in [10,20,30]:progress.complete(duration)
        self.assertEqual(progress.status()["remaining"],100.0)
        progress.complete(0,checkpoint=True)
        self.assertEqual(progress.status()["samples"],3)
        self.assertEqual(progress.status()["remaining"],80.0)
        self.assertIn("THIS ROUND ETA",progress.line())

    def test_14_source_contains_no_unauthorized_auto_marking(self):
        gui=(ROOT/"LRC_Control_Center.py").read_text(encoding="utf-8")
        self.assertIn("messagebox.askyesno",gui)
        self.assertIn("explicitly_promote",gui)
        self.assertIn("if self.process is not None",gui)
        self.assertTrue((ROOT/"OPEN_CONTROL_CENTER.cmd").is_file())


if __name__=="__main__":unittest.main(verbosity=2)
