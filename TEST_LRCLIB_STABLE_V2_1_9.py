"""v2.1.9 regression suite. No live traffic; Python mocks only."""
from __future__ import annotations
import csv
import io
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock
sys.modules.setdefault('syncedlyrics', types.SimpleNamespace(search=lambda *a,**kw: None))
import LRC_Bulk_Finder as app

TIMED='[00:05.00] Music now\n[00:25.00] It is working\n[02:59.00] The end\n'

class NewLRCLIBTests(unittest.TestCase):
    def setUp(self):
        app.LRCLIB_EXACT_FALLBACK=False
        app.LRCLIB_503_STREAK=0
        app.LRCLIB_503_RETRY_AT=0.0
        app.HISTORY_ENABLED=False
        app.GREEK_MODE=False
        app.MB_ENABLED=False
        app.blocked.clear();app.errors.clear();app.next_available.clear()
        app.ACTIVE_PROVIDERS=('LRCLIB',)

    def test_fallback_disabled_default_preserves_legacy_requests(self):
        with mock.patch.object(app,'direct_json',return_value=[]) as req:
            self.assertIsNone(app.provider_lrclib('Hello','Tester','My Album',180,app.CandidateReview()))
        self.assertEqual(req.call_count,1)  # one original spelling
        self.assertEqual(req.call_args.args[1],'https://lrclib.net/api/search')

    def test_fallback_enabled_only_after_legacy_search_miss(self):
        app.LRCLIB_EXACT_FALLBACK=True
        def fake(provider,url,args):
            if url.endswith('/api/get'):
                self.assertEqual(args['artist_name'],'Tester')
                self.assertEqual(args['track_name'],'Hello')
                self.assertEqual(args['duration'],180)
                self.assertEqual(args['album_name'],'My Album')
                return {'trackName':'Hello','artistName':'Tester','duration':180,
                        'syncedLyrics':TIMED}
            return []
        with mock.patch.object(app,'direct_json',side_effect=fake) as req:
            hit=app.provider_lrclib('Hello','Tester','My Album',180,app.CandidateReview())
        self.assertTrue(hit.verified)
        self.assertEqual(hit.provider,'LRCLIB')
        self.assertEqual([c.args[1].split('/')[-1] for c in req.call_args_list],['search','get'])

    def test_exact_does_not_override_legacy_hit(self):
        app.LRCLIB_EXACT_FALLBACK=True
        row={'trackName':'Hello','artistName':'Tester','duration':180,
             'syncedLyrics':TIMED}
        with mock.patch.object(app,'direct_json',return_value=[row]) as req:
            hit=app.provider_lrclib('Hello','Tester','',180,app.CandidateReview())
        self.assertIsNotNone(hit)
        self.assertEqual(req.call_count,1)

    def test_exact_wrong_version_goes_to_candidate(self):
        app.LRCLIB_EXACT_FALLBACK=True
        def fake(provider,url,args):
            if url.endswith('/get'):
                return {'trackName':'Hello (Club Remix)','artistName':'Tester','duration':180,
                        'syncedLyrics':TIMED}
            return []
        review=app.CandidateReview()
        with mock.patch.object(app,'direct_json',side_effect=fake):
            result=app.provider_lrclib('Hello','Tester','',180,review)
        self.assertIsNone(result)
        self.assertEqual(review.count['LRCLIB'],1)
        self.assertIn('Recording version',review.items[0][3])

    def test_exact_wrong_duration_cannot_auto_install(self):
        app.LRCLIB_EXACT_FALLBACK=True
        with mock.patch.object(app,'direct_json',side_effect=[[],
                {'trackName':'Hello','artistName':'Tester','duration':210,
                 'syncedLyrics':TIMED}]):
            review=app.CandidateReview()
            self.assertIsNone(app.provider_lrclib('Hello','Tester','',180,review))
        self.assertEqual(review.count['LRCLIB'],1)

    def test_invalid_duration_or_missing_artist_skips_extra_request(self):
        app.LRCLIB_EXACT_FALLBACK=True
        for duration in (0,3601,-5):
            with self.subTest(duration=duration),mock.patch.object(app,'direct_json',return_value=[]) as req:
                app.provider_lrclib('Hello','Tester','',duration,app.CandidateReview())
                self.assertEqual(req.call_count,1)

    def test_503_retry_after_respected_conservatively(self):
        self.assertEqual(app.lrclib_503_delay('1',1),5)
        self.assertEqual(app.lrclib_503_delay('30',3),30)
        self.assertEqual(app.lrclib_503_delay(None,1),60)
        self.assertEqual(app.lrclib_503_delay(None,2),120)
        self.assertEqual(app.lrclib_503_delay(None,7),600)
        with mock.patch.object(app,'provider_lrclib',side_effect=app.ProviderFailure(
            'HTTP 503: Server overloaded',retry_after='2')):
            with mock.patch.object(app.time,'monotonic',return_value=100):
                app.search_song('Hello','Tester','',180,app.CandidateReview(),only_providers=('LRCLIB',))
        self.assertEqual(app.LRCLIB_503_RETRY_AT,105)
        self.assertNotIn('LRCLIB',app.blocked)

    def test_429_not_retried_and_no_exact_extra(self):
        app.LRCLIB_EXACT_FALLBACK=True
        with mock.patch.object(app,'direct_json',side_effect=app.ProviderFailure(
             'HTTP 429',rate_limit=True,retry_after='80')) as req,\
             mock.patch.object(app,'record_rate_limit') as saved:
            retry=set()
            app.search_song('Hello','Tester','',180,app.CandidateReview(),
                            only_providers=('LRCLIB',),retry_targets=retry)
        self.assertEqual(req.call_count,1)
        saved.assert_called_once()
        self.assertEqual(retry,set())

    def test_catchup_queue_only_incomplete_lrclib_and_not_when_approved(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            paths=[folder/f'{i}.mp3' for i in range(6)]
            for p in paths:p.write_bytes(b'unchanged')
            paths[3].with_suffix('.lrc').write_text('already',encoding='utf-8')
            outcomes=[
                (paths[0],['LRCLIB=SKIPPED (temporary HTTP 503 recovery)', 'SyncLRC=NO_MATCH']),
                (paths[1],['LRCLIB=ERROR (HTTP 503: busy)','SyncLRC=NO_MATCH']),
                (paths[2],['LRCLIB=SKIPPED (429 for this run)', 'SyncLRC=NO_MATCH']),
                (paths[3],['LRCLIB=SKIPPED (temporary HTTP 503 recovery)']),
                (paths[4],['LRCLIB=NO_MATCH']),
                (paths[5],['LRCLIB=SKIPPED (temporary HTTP 503 recovery)']),
                (paths[5],['LRCLIB=REVIEW_AVAILABLE'])]
            file,n=app.write_lrclib_catchup_queue(folder,paths,outcomes)
            self.assertEqual(n,3)
            with file.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
            self.assertEqual({r['MP3 path'] for r in rows},{str(p) for p in paths[:3]})

    def test_last_finished_gap_is_enforced_even_after_long_request(self):
        app.LRCLIB_LAST_FINISHED=100.0
        app.next_available['LRCLIB']=0
        ticks=iter([100.1,100.1,100.5])
        with mock.patch.object(app.time,'monotonic',side_effect=lambda:next(ticks)),\
             mock.patch.object(app.time,'sleep') as asleep:
            app.wait_for('LRCLIB')
        asleep.assert_called_once()
        self.assertAlmostEqual(asleep.call_args.args[0],0.4)
        app.LRCLIB_LAST_FINISHED=0

    def test_previous_catchup_queue_survives_shorter_later_run(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            old=folder/'Old.mp3';new=folder/'New.mp3'
            old.write_bytes(b'old');new.write_bytes(b'new')
            file=app.lrclib_catchup_queue_path(folder)
            with file.open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.writer(f);w.writerow(['MP3 path','why LRCLIB was incomplete']);w.writerow([str(old),'old 503'])
            output,count=app.write_lrclib_catchup_queue(folder,[new],[(new,['LRCLIB=SKIPPED (temporary HTTP 503 recovery)'])])
            self.assertEqual(count,2)
            with output.open(encoding='utf-8-sig',newline='') as f:
                entries=list(csv.DictReader(f))
            self.assertEqual({r['MP3 path'] for r in entries},{str(old),str(new)})

    def test_manual_catchup_only_one_source_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            mp3=folder/'Music.mp3';mp3.write_bytes(b'mp3-content')
            existing=folder/'Done.mp3';existing.write_bytes(b'done-content')
            existing.with_suffix('.lrc').write_text(TIMED,encoding='utf-8')
            path=app.lrclib_catchup_queue_path(folder)
            with path.open('w',encoding='utf-8-sig',newline='') as f:
                writer=csv.writer(f);writer.writerow(['MP3 path','why LRCLIB was incomplete'])
                writer.writerows([(str(mp3),'skipped'),(str(existing),'skipped')])
            hit=app.Hit(TIMED,'LRCLIB','verified','ORIGINAL',True)
            answers=iter(['n','n','y'])
            fake_search=mock.Mock(return_value=(hit,'SAVED','LRCLIB', ['LRCLIB=SAVED']))
            # direct mocked search: no external network, untouched base metadata.
            with mock.patch.object(app,'configure_lrclib_contact',return_value=True),\
                 mock.patch.object(app,'load_provider_cooldowns'),\
                 mock.patch.object(app,'song_info',return_value=('Music','Tester','',180)),\
                 mock.patch.object(app,'search_song',fake_search),\
                 mock.patch('builtins.input',side_effect=lambda _:next(answers)),\
                 redirect_stdout(io.StringIO()):
                app.run_lrclib_catchup(folder)
            self.assertEqual(fake_search.call_count,1)
            self.assertEqual(fake_search.call_args.kwargs['only_providers'],('LRCLIB',))
            self.assertEqual(mp3.read_bytes(),b'mp3-content')
            self.assertEqual(existing.read_bytes(),b'done-content')
            self.assertEqual(existing.with_suffix('.lrc').read_text(),TIMED)
            self.assertTrue(mp3.with_suffix('.lrc').exists())
            with path.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
            self.assertEqual(rows,[])

if __name__=='__main__':unittest.main(verbosity=2)
