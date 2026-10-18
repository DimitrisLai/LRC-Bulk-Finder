"""Offline-only arbitrary-folder scan regression tests. No external networking."""
import csv,io,sqlite3,sys,tempfile,types,unittest
from pathlib import Path
from contextlib import closing, redirect_stdout
from unittest import mock
sys.modules.setdefault('syncedlyrics', types.SimpleNamespace(search=lambda *a,**kw:None))
import LRC_Bulk_Finder as app
from lrclib_local import LocalLRCLIB

LYR='[00:05.00] Hello world\n[00:25.00] How are you\n[02:59.00] Song ends\n'

def fixture(folder):
    db=Path(folder)/'snapshot.sqlite3'
    with closing(sqlite3.connect(db)) as con, con:
        con.executescript('CREATE TABLE tracks (id INTEGER PRIMARY KEY,name TEXT,name_lower TEXT,artist_name TEXT,artist_name_lower TEXT,duration REAL,last_lyrics_id INTEGER);CREATE TABLE lyrics (id INTEGER PRIMARY KEY,synced_lyrics TEXT);CREATE INDEX names ON tracks(name_lower);')
        con.execute('INSERT INTO tracks VALUES (1,?,?,?,?,?,1)',('Hello','hello','Tester','tester',180))
        con.execute('INSERT INTO lyrics VALUES (1,?)',(LYR,))
    return db

class OfflineFolderTests(unittest.TestCase):
    def setUp(self):
        app.LOCAL_LRCLIB=None;app.GREEK_MODE=False;app.MB_ENABLED=False
        app.G2G_ENABLED=False;app.G2G_TOOL=None;app.ACTIVE_HTTP_TRACE=None
    def tearDown(self):
        app.LOCAL_LRCLIB=None;app.G2G_TOOL=None;app.ACTIVE_HTTP_TRACE=None

    def test_reuses_existing_path_without_copy(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);program=base/'program';program.mkdir()
            db=fixture(base)
            with mock.patch.object(app,'configure_local_lrclib') as configure, mock.patch.object(app,'LocalLRCLIB',return_value=LocalLRCLIB(db)),mock.patch('builtins.input',return_value=str(db)),redirect_stdout(io.StringIO()):
                self.assertTrue(app.ensure_local_lrclib_config(program))
            self.assertEqual(Path((program/'LRCLIB_LOCAL_DB.txt').read_text().strip()).resolve(),db.resolve())
            self.assertIsNotNone(app.LOCAL_LRCLIB)
            self.assertEqual(db.stat().st_size,(base/'snapshot.sqlite3').stat().st_size)

    def test_bad_path_not_written(self):
        with tempfile.TemporaryDirectory() as td:
            prog=Path(td)
            with mock.patch.object(app,'configure_local_lrclib'),mock.patch('builtins.input',return_value=str(prog/'missing.sqlite3')),redirect_stdout(io.StringIO()):
                self.assertFalse(app.ensure_local_lrclib_config(prog))
            self.assertFalse((prog/'LRCLIB_LOCAL_DB.txt').exists())

    def test_existing_lrc_and_live_skipped_and_no_http(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);db=fixture(root);music=root/'music';music.mkdir()
            (music/'Hello.mp3').write_bytes(b'FAKE')
            (music/'Other.mp3').write_bytes(b'FAKE')
            (music/'Already.mp3').write_bytes(b'FAKE')
            (music/'Already.lrc').write_text('existing')
            (music/'LIVE show.mp3').write_bytes(b'FAKE')
            app.LOCAL_LRCLIB=LocalLRCLIB(db)
            def fake_info(f):
                if f.stem=='Hello':return 'Hello','Tester','',180
                return 'Other','Tester','',180
            with mock.patch('builtins.input',side_effect=['n','y','a','y']),mock.patch.object(app,'song_info',side_effect=fake_info),mock.patch.object(app,'direct_get',side_effect=AssertionError('NETWORK')),mock.patch.object(app,'direct_json',side_effect=AssertionError('NETWORK')), mock.patch.object(app,'search_song',side_effect=AssertionError('NETWORK')), redirect_stdout(io.StringIO()):
                app.run_offline_lrclib_folder(music)
            self.assertTrue((music/'Hello.lrc').exists())
            self.assertFalse((music/'Other.lrc').exists())
            self.assertEqual((music/'Already.lrc').read_text(),'existing')
            self.assertFalse((music/'LIVE show.lrc').exists())
            rows=list(csv.DictReader((music/'LRC_Offline_Only_Report_v2_1_15.csv').open(encoding='utf-8-sig')))
            self.assertEqual(len(rows),2)
            self.assertEqual({r['outcome'] for r in rows},{'SAVED','NO_MATCH'})

    def test_20_limit_and_no_extra_prompts(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);db=fixture(root);music=root/'music';music.mkdir()
            for i in range(25):(music/f'{i:02d}.mp3').write_bytes(b'FAKE')
            app.LOCAL_LRCLIB=LocalLRCLIB(db)
            with mock.patch('builtins.input',side_effect=['n','n','','y']), mock.patch.object(app,'song_info',return_value=('Other','Tester','',180)), redirect_stdout(io.StringIO()):
                app.run_offline_lrclib_folder(music)
            rows=list(csv.DictReader((music/'LRC_Offline_Only_Report_v2_1_15.csv').open(encoding='utf-8-sig')))
            self.assertEqual(len(rows),20)

    def test_option4_main_routes_correctly(self):
        with tempfile.TemporaryDirectory() as td:
            with mock.patch('builtins.input',return_value='4'),mock.patch.object(app,'select_folder',return_value=Path(td)),mock.patch.object(app,'load_aliases'),mock.patch.object(app,'load_greek_words'),mock.patch.object(app,'ensure_local_lrclib_config',return_value=True) as check,mock.patch.object(app,'run_offline_lrclib_folder') as offline,redirect_stdout(io.StringIO()):
                app.main()
            check.assert_called_once();offline.assert_called_once()

if __name__=='__main__':unittest.main()
