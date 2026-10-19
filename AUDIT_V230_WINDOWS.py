"""Windows-only GUI/worker smoke tests of published standalone v2.3.0."""
import json,os,sqlite3,subprocess,sys,tempfile,time,unittest
from contextlib import closing
from pathlib import Path

EXE_DIR=Path(__file__).resolve().parent/"standalone_unpacked"
GUI=EXE_DIR/"LRC_Control_Center.exe"
WORKER=EXE_DIR/"LRC_Bulk_Finder_Worker.exe"
assert GUI.is_file() and WORKER.is_file()


def sqlite_fixture(path):
    with closing(sqlite3.connect(path)) as conn,conn:
        conn.executescript("""CREATE TABLE tracks(id INTEGER PRIMARY KEY,name TEXT,
                  name_lower TEXT,artist_name TEXT,artist_name_lower TEXT,
                  duration REAL,last_lyrics_id INTEGER);
                  CREATE TABLE lyrics(id INTEGER PRIMARY KEY,synced_lyrics TEXT);
                  CREATE INDEX ix_tracks_name ON tracks(name_lower);""")


def launch(profile, music,extra=None):
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/"profiles.json"
        settings={
            "folder":str(music),"action":"4","greek":False,"local_ai":False,
            "musicbrainz":False,"provider_mode":"fast","order":"d","custom_order":"",
            "recovery_wait":False,"recursive":False,"history":False,
            "limit":"1","exact_fallback":False,"auto_search":True,"database":"",
        }
        settings.update(profile)
        path.write_text(json.dumps({"schema":1,"profiles":{"Audit":settings}}),encoding="utf-8")
        return subprocess.run([str(WORKER),"--profile","Audit","--profiles-path",str(path)],
                  cwd=str(EXE_DIR),capture_output=True,text=True,errors="replace",timeout=85)


class WindowsStandaloneReleaseAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=tempfile.TemporaryDirectory()
        cls.folder=Path(cls.root.name)
        cls.db=cls.folder/"fixture.sqlite3"
        sqlite_fixture(cls.db)
        (EXE_DIR/"LRCLIB_LOCAL_DB.txt").write_text(str(cls.db)+"\n",encoding="utf-8")
    @classmethod
    def tearDownClass(cls):
        cls.root.cleanup()
        cfg=EXE_DIR/"LRCLIB_LOCAL_DB.txt"
        if cfg.is_file():cfg.unlink()

    def test_01_no_python_needed_by_frozen_worker_for_help(self):
        result=subprocess.run([str(WORKER),"--help"],cwd=str(EXE_DIR),
                              capture_output=True,text=True,errors="replace",timeout=60)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("--profile",result.stdout)

    def test_02_actual_standalone_worker_offline_profile(self):
        result=launch({},self.folder)
        self.assertEqual(result.returncode,0,result.stdout+"\n"+result.stderr)
        self.assertIn("OFFLINE",result.stdout.upper())
        self.assertIn("0",result.stdout)

    def test_03_actual_standalone_worker_option5_profile(self):
        result=launch({"action":"5","musicbrainz":False,
                       "provider_mode":"full","order":"d","history":False},self.folder)
        self.assertEqual(result.returncode,0,result.stdout+"\n"+result.stderr)
        self.assertIn("0 eligible",result.stdout)

    def test_04_missing_music_folder_rejected(self):
        result=launch({},self.folder/"not_there")
        self.assertNotEqual(result.returncode,0)
        self.assertIn("PROFILE ERROR",result.stderr+result.stdout)

    def test_05_gui_native_process_starts_and_terminates(self):
        proc=subprocess.Popen([str(GUI)],cwd=str(EXE_DIR),
                              stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            time.sleep(5)
            self.assertIsNone(proc.poll(),"Frozen GUI crashed on startup")
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=8)
                except subprocess.TimeoutExpired:proc.kill()

    def test_06_windows_gui_widgets_save_profile_and_browse_candidate(self):
        # Source module imported exclusively from published STANDARD ZIP.
        root=Path(__file__).resolve().parent/"release_unpacked"/"LRC_Bulk_Finder_v2_3_0"
        sys.path.insert(0,str(root))
        import LRC_Control_Center as gui
        import search_profiles
        original=os.environ.get("APPDATA")
        with tempfile.TemporaryDirectory() as td:
            try:
                os.environ["APPDATA"]=td
                folder=Path(td)/"songs";folder.mkdir()
                (folder/"A.mp3").write_bytes(b"TRACK AUDIO")
                lyric=(folder/"A.candidate.lrc")
                lyric.write_text("[00:02.00] One\n[00:28.00] Two\n[01:00.00] Three\n",
                                 encoding="utf-8")
                app=gui.ControlCenter()
                try:
                    app.withdraw()
                    app.name.set("Real Windows GUI")
                    app.folder.set(str(folder))
                    app.action.set("5")
                    app.database.set(str(self.db))
                    self.assertTrue(app._save())
                    app._refresh_profiles()
                    self.assertIn("Real Windows GUI",app.loaded_profiles)
                    app._refresh_review()
                    self.assertEqual(len(app.review_rows),1)
                    app.review_tree.selection_set("0")
                    app._candidate_selected()
                    self.assertIn("One",app.candidate_text.get("1.0","end"))
                    self.assertTrue(lyric.exists(),"Browsing must be read-only")
                finally:app.destroy()
            finally:
                if original is None:os.environ.pop("APPDATA",None)
                else:os.environ["APPDATA"]=original


if __name__=="__main__":unittest.main(verbosity=2)
