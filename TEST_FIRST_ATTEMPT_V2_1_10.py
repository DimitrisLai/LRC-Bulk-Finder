"""v2.1.10 first-attempt coverage, recovery and legacy queue tests (OFFLINE)."""
import csv, io, tempfile, types, sys, unittest
from pathlib import Path
from unittest import mock
from contextlib import redirect_stdout
sys.modules.setdefault('syncedlyrics',types.SimpleNamespace(search=lambda *a,**kw:None))
import LRC_Bulk_Finder as app

class CoverageFixTests(unittest.TestCase):
    def setUp(self):
        app.blocked.clear();app.errors.clear();app.PROVIDER_RECOVERY_AT.clear()
        app.PROVIDER_ERROR_STREAK.clear();app.HISTORY_ENABLED=False
        app.LRCLIB_503_STREAK=0;app.LRCLIB_503_RETRY_AT=0.0
        app.COMPLETE_FIRST_PASS=True;app.MB_ENABLED=False;app.GREEK_MODE=False

    def test_lrclib_waits_before_first_attempt_after_503(self):
        app.LRCLIB_503_RETRY_AT=999999
        with mock.patch.object(app,'wait_for_recovery') as wait, \
             mock.patch.object(app,'provider_lrclib',return_value=None) as provider:
            with redirect_stdout(io.StringIO()):
                hit,status,detail,calls=app.search_song('Track','Artist','',180,app.CandidateReview(),only_providers=['LRCLIB'])
        self.assertIsNone(hit)
        self.assertEqual(status,'NOT_FOUND')
        self.assertEqual(calls,['LRCLIB=NO_MATCH'])
        wait.assert_called_once()
        provider.assert_called_once()

    def test_lrclib_short_mode_marks_incomplete_without_request(self):
        app.COMPLETE_FIRST_PASS=False
        app.LRCLIB_503_RETRY_AT=999999
        with mock.patch.object(app,'provider_lrclib') as provider,redirect_stdout(io.StringIO()):
            _,status,_,calls=app.search_song('Track','Artist','',180,app.CandidateReview(),only_providers=['LRCLIB'])
        self.assertEqual(status,'SERVER_ERROR')
        self.assertIn('SKIPPED',calls[0])
        provider.assert_not_called()

    def test_liriqo_two_503s_are_not_permanent_ban(self):
        with mock.patch.object(app,'provider_liriqo',side_effect=[
                app.ProviderFailure('HTTP 503: Unavailable'),
                app.ProviderFailure('HTTP 503: Unavailable'), None]), \
             mock.patch.object(app,'wait_for_recovery') as wait, \
             redirect_stdout(io.StringIO()):
            for _ in range(3):
                app.search_song('Track','Artist','',180,app.CandidateReview(),only_providers=['LiriQo'])
        self.assertNotIn('LiriQo',app.blocked)
        self.assertEqual(app.PROVIDER_ERROR_STREAK['LiriQo'],0)
        self.assertTrue(wait.called)

    def test_better_401_disables_and_never_retries(self):
        for source in ('BetterKuGou','BetterTTML'):
            app.blocked.clear()
            with mock.patch.object(app,'provider_better',side_effect=app.ProviderFailure('HTTP 401: Unauthorized')) as provider,redirect_stdout(io.StringIO()):
                _,status,_,calls=app.search_song('Title','Artist','',180,app.CandidateReview(),only_providers=[source])
                _,status2,_,calls2=app.search_song('Other title','Artist','',180,app.CandidateReview(),only_providers=[source])
            self.assertEqual(provider.call_count,1)
            self.assertIn(source,app.blocked)
            self.assertIn('SKIPPED',calls2[0])

    def test_503_is_never_automatic_timeout_round(self):
        with mock.patch.object(app,'provider_lrclib',side_effect=app.ProviderFailure('HTTP 503: Unavailable')),redirect_stdout(io.StringIO()):
            pending=set()
            _,status,_,_=app.search_song('Track','Artist','',180,app.CandidateReview(),only_providers=['LRCLIB'],retry_targets=pending)
        self.assertEqual(pending,set())
        self.assertEqual(status,'SERVER_ERROR')

    def test_v219_queue_entries_carried_forward_and_old_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);mp3=folder/'Track.mp3';mp3.write_bytes(b'mp3')
            old=folder/'LRC_LRCLIB_Catchup_Queue_v2_1_9.csv'
            old.write_text('MP3 path,why LRCLIB was incomplete\n'+str(mp3)+',HTTP 503\n',encoding='utf-8')
            new,count=app.write_lrclib_catchup_queue(folder,[],[])
            self.assertEqual(count,1)
            self.assertTrue(old.exists())
            with new.open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
            self.assertEqual(rows[0]['MP3 path'],str(mp3))

    def test_wait_func_sleeps_then_returns_no_extra_request(self):
        with mock.patch.object(app.time,'monotonic',side_effect=[10,10,20]), mock.patch.object(app.time,'sleep') as sleeping,redirect_stdout(io.StringIO()):
            app.wait_for_recovery('LiriQo',20,'test')
        sleeping.assert_called_once_with(10)

if __name__=='__main__':unittest.main(verbosity=2)

