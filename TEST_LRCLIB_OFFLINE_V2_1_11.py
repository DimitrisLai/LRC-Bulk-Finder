"""v2.1.11 regression tests: local SQLite + circuit, no HTTP or real sleep."""
from __future__ import annotations
import csv, io, sqlite3, sys, tempfile, types, unittest
from pathlib import Path
from unittest import mock
from contextlib import redirect_stdout
sys.modules.setdefault('syncedlyrics',types.SimpleNamespace(search=lambda *a, **kw:None))
import LRC_Bulk_Finder as app
from lrclib_local import LocalLRCLIB, load_local_config

LYR='[00:05.00] Hello world\n[00:25.00] How are you\n[02:59.00] Song ends\n'

def fixture(folder, name='snapshot.sqlite3'):
    db=Path(folder)/name
    with sqlite3.connect(db) as con:
        con.executescript('''
          CREATE TABLE tracks (id INTEGER PRIMARY KEY, name TEXT, name_lower TEXT,
            artist_name TEXT, artist_name_lower TEXT, duration FLOAT, last_lyrics_id INTEGER);
          CREATE TABLE lyrics (id INTEGER PRIMARY KEY, synced_lyrics TEXT);
          CREATE INDEX track_title ON tracks(name_lower);
        ''')
        con.execute('INSERT INTO tracks VALUES (1, ?, ?, ?, ?, ?, ?)',('Hello','hello','Tester','tester',180,1))
        con.execute('INSERT INTO lyrics VALUES (?, ?)',(1,LYR))
        con.execute('INSERT INTO tracks VALUES (2, ?, ?, ?, ?, ?, ?)',('Hello (Club Remix)','hello (club remix)','Tester','tester',180,2))
        con.execute('INSERT INTO lyrics VALUES (?, ?)',(2,LYR))
    return db

class OfflineTests(unittest.TestCase):
    def setUp(self):
        app.LOCAL_LRCLIB=None;app.LRCLIB_ONLINE_FALLBACK=True
        app.LRCLIB_EXACT_FALLBACK=False;app.HISTORY_ENABLED=False
        app.LRCLIB_503_STREAK=0;app.LRCLIB_503_RETRY_AT=0.0
        app.COMPLETE_FIRST_PASS=False;app.GREEK_MODE=False;app.MB_ENABLED=False
        app.blocked.clear();app.PROVIDER_RECOVERY_AT.clear();app.PROVIDER_ERROR_STREAK.clear()
        app.ACTIVE_HTTP_TRACE=None

    def tearDown(self):app.LOCAL_LRCLIB=None;app.LRCLIB_ONLINE_FALLBACK=True

    def test_schema_and_read_only_lookup(self):
        with tempfile.TemporaryDirectory() as td:
            local=LocalLRCLIB(fixture(td))
            rows=local.search([('Hello','Tester')],180)
            self.assertEqual(len(rows),2)
            self.assertEqual(rows[0]['syncedLyrics'],LYR)

    def test_snapshot_works_with_offline_only_no_network(self):
        with tempfile.TemporaryDirectory() as td:
            app.LOCAL_LRCLIB=LocalLRCLIB(fixture(td));app.LRCLIB_ONLINE_FALLBACK=False
            with mock.patch.object(app,'direct_json') as http,redirect_stdout(io.StringIO()):
                hit=app.provider_lrclib('Hello','Tester','',180,app.CandidateReview())
            self.assertIsNotNone(hit);self.assertTrue(hit.verified)
            self.assertEqual(hit.search_variation,'LOCAL_SQLITE');http.assert_not_called()

    def test_local_wrong_remix_cannot_autosave(self):
        with tempfile.TemporaryDirectory() as td:
            app.LOCAL_LRCLIB=LocalLRCLIB(fixture(td));app.LRCLIB_ONLINE_FALLBACK=False
            review=app.CandidateReview()
            with mock.patch.object(app,'direct_json') as http,redirect_stdout(io.StringIO()):
                hit=app.provider_lrclib('Hello (Club Remix)','Tester','',180,review)
            self.assertIsNotNone(hit);http.assert_not_called()
            # If only the remix row were available, base mix cannot auto-save.
            conn=sqlite3.connect(app.LOCAL_LRCLIB.path)
            conn.execute('UPDATE lyrics SET synced_lyrics=NULL WHERE id=1');conn.commit();conn.close()
            review=app.CandidateReview()
            with redirect_stdout(io.StringIO()):
                hit=app.provider_lrclib('Hello','Tester','',180,review)
            self.assertIsNone(hit);self.assertGreater(review.count['LRCLIB local'],0)

    def test_missing_or_invalid_snapshot_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):LocalLRCLIB(Path(td)/'missing.sqlite3')
            bad=Path(td)/'bad.sqlite3';bad.write_bytes(b'bad sqlite')
            with self.assertRaises(ValueError):LocalLRCLIB(bad)

    def test_local_config_path_read(self):
        with tempfile.TemporaryDirectory() as td:
            target=fixture(td)
            conf=Path(td)/'LRCLIB_LOCAL_DB.txt';conf.write_text('# comment\n'+str(target)+'\n')
            self.assertEqual(load_local_config(conf),target)

    def test_three_503_open_circuit_no_extra_requests(self):
        app.ACTIVE_PROVIDERS=('LRCLIB',)
        app.COMPLETE_FIRST_PASS=True
        call_count=[0]
        def overloaded(*args,**kwargs):
            call_count[0]+=1
            raise app.ProviderFailure('HTTP 503: Service Unavailable',retry_after='1')
        with mock.patch.object(app,'provider_lrclib',side_effect=overloaded),mock.patch.object(app,'wait_for_recovery'),redirect_stdout(io.StringIO()):
            for i in range(5):
                app.search_song('Different '+str(i),'Tester','',180,app.CandidateReview(),only_providers=['LRCLIB'])
        self.assertEqual(call_count[0],3)
        self.assertIn('circuit open',app.blocked['LRCLIB'])

    def test_circuit_keeps_local_lookups_available(self):
        with tempfile.TemporaryDirectory() as td:
            app.LOCAL_LRCLIB=LocalLRCLIB(fixture(td));app.LRCLIB_ONLINE_FALLBACK=True
            app.blocked['LRCLIB']='HTTP 503 circuit open after 3 overloads'
            with mock.patch.object(app,'direct_json') as http,redirect_stdout(io.StringIO()):
                hit,status,detail,calls=app.search_song('Hello','Tester','',180,app.CandidateReview(),only_providers=['LRCLIB'])
            self.assertIsNotNone(hit)
            self.assertEqual(status,'SAVED')
            http.assert_not_called()

    def test_circuit_unsearched_songs_go_to_queue(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);first=folder/'a.mp3'; second=folder/'b.mp3'
            for f in (first,second):f.touch()
            path,count=app.write_lrclib_catchup_queue(folder,[first,second],[
                (first,['LRCLIB=ERROR (HTTP 503: Unavailable)']),
                (second,['LRCLIB=SKIPPED (HTTP 503 circuit open)'])])
            self.assertEqual(count,2)
            self.assertTrue(path.is_file())

    def test_offline_catchup_saves_match_and_keeps_other_queue_entry(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            good=folder/'Hello.mp3';other=folder/'Unmatched.mp3'
            good.touch();other.touch()
            old=folder/'LRC_LRCLIB_Catchup_Queue_v2_1_10.csv'
            with old.open('w',newline='',encoding='utf-8') as out:
                wr=csv.writer(out);wr.writerow(['MP3 path','why LRCLIB was incomplete'])
                wr.writerows([[str(good),'503'],[str(other),'503']])
            db=LocalLRCLIB(fixture(td))
            def configure(_):app.LOCAL_LRCLIB=db
            with mock.patch.object(app,'configure_local_lrclib',side_effect=configure),\
                 mock.patch.object(app,'song_info',side_effect=lambda p:(p.stem,'Tester','',180)),\
                 mock.patch.object(app,'direct_json') as http,\
                 mock.patch('builtins.input',side_effect=['n','n','n','y']),\
                 redirect_stdout(io.StringIO()):
                app.run_lrclib_catchup(folder)
            http.assert_not_called()
            self.assertTrue(good.with_suffix('.lrc').is_file())
            self.assertFalse(other.with_suffix('.lrc').exists())
            with (folder/'LRC_LRCLIB_Catchup_Queue_v2_1_15.csv').open(encoding='utf-8-sig') as out:
                pending=list(csv.DictReader(out))
            self.assertEqual([row['MP3 path'] for row in pending],[str(other)])
            self.assertTrue(old.exists())

    def test_catchup_legacy_210_queue_migrates(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);f=folder/'a.mp3';f.touch()
            old=folder/'LRC_LRCLIB_Catchup_Queue_v2_1_10.csv'
            with old.open('w',newline='',encoding='utf-8') as out:
                wr=csv.writer(out);wr.writerow(['MP3 path','why LRCLIB was incomplete']);wr.writerow([str(f),'HTTP 503'])
            new,count=app.write_lrclib_catchup_queue(folder,[],[])
            self.assertEqual(count,1);self.assertTrue(old.exists());self.assertTrue(new.exists())

if __name__=='__main__':unittest.main(verbosity=2)
