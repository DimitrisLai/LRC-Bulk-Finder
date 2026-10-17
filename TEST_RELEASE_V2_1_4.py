"""v2.1.4 regression tests: no live requests and no audio mutation."""
import csv
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock
sys.modules.setdefault('syncedlyrics',types.SimpleNamespace(search=lambda *a,**k:None))
import LRC_Bulk_Finder as app
LRC='[00:01.00] first\n[00:30.00] second\n[01:30.00] third\n'

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        app.blocked.clear();app.errors.clear();app.next_available.clear()
        app.HISTORY_ENABLED=False;app.HISTORY_CACHE.clear();app.HISTORY_PATH=None
        app.GREEK_MODE=False;app.MB_ENABLED=False;app.ACTIVE_PROVIDERS=None
        app.COOLDOWN_PATH=None;app.COOLDOWN_UNTIL={}
        app.LRCLIB_IDENTIFIED=False;app.LRCLIB_USER_AGENT=''
    def test_review_never_cached_as_no_match(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'history.jsonl';app.load_search_history(f);app.HISTORY_ENABLED=True
            calls=[]
            def add_review(t,a,al,d,review):
                calls.append(1)
                review.add('LRCLIB','Song','Artist','unverified',lyrics=LRC)
                return None
            with mock.patch.object(app,'provider_lrclib',side_effect=add_review):
                for _ in range(2):
                    timings=[]
                    _,status,_,outcomes=app.search_song('Song','Artist','',95,app.CandidateReview(),only_providers=('LRCLIB',),timings=timings)
                    self.assertEqual(status,'REVIEW_AVAILABLE')
                    self.assertEqual(outcomes,['LRCLIB=REVIEW_AVAILABLE'])
                    self.assertEqual(len(timings),1)
            self.assertEqual(len(calls),2)
            app.load_search_history(f)
            self.assertEqual(app.HISTORY_CACHE,{})
            self.assertTrue(all(json.loads(line)['state']=='REVIEW_AVAILABLE' for line in f.read_text().splitlines()))
    def test_real_no_match_still_cached(self):
        with tempfile.TemporaryDirectory() as td:
            app.load_search_history(Path(td)/'history.jsonl');app.HISTORY_ENABLED=True
            with mock.patch.object(app,'provider_lrclib',return_value=None) as f:
                app.search_song('Song','Artist','',95,app.CandidateReview(),only_providers=('LRCLIB',))
                app.search_song('Song','Artist','',95,app.CandidateReview(),only_providers=('LRCLIB',))
                self.assertEqual(f.call_count,1)
    def test_timeout_only_specific_provider(self):
        retry=set()
        with mock.patch.object(app,'provider_unison',side_effect=app.ProviderFailure('timeout',timeout=True)),mock.patch.object(app,'provider_lrclib',return_value=None):
            _,status,_,calls=app.search_song('Song','Artist','',95,app.CandidateReview(),only_providers=('Unison','LRCLIB'),retry_targets=retry)
        self.assertEqual(status,'TIMEOUT');self.assertEqual(retry,{'Unison'})
        self.assertEqual(len(calls),2)
    def test_cooldown_saved_across_restarts(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'cooldowns.json';app.load_provider_cooldowns(f)
            app.record_rate_limit('LRCLIB','120')
            self.assertTrue(f.is_file())
            self.assertTrue(json.loads(f.read_text())['LRCLIB']>0)
            app.blocked.clear();app.load_provider_cooldowns(f)
            self.assertIn('LRCLIB',app.blocked)
            self.assertGreater(app.COOLDOWN_UNTIL['LRCLIB'],0)
    def test_retry_after_parses_seconds_and_http_date(self):
        self.assertEqual(app.retry_after_seconds('25',now=1000),25)
        self.assertGreaterEqual(app.retry_after_seconds('Thu, 01 Jan 1970 00:18:20 GMT',now=1000),99)
        self.assertEqual(app.retry_after_seconds(None,now=1000),900)
    def test_missing_contact_disables_lrclib(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertFalse(app.configure_lrclib_contact(td))
            self.assertIn('LRCLIB',app.blocked)
    def test_real_contact_enables_and_escapes_other_providers(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td)/'LRCLIB_CONTACT.txt').write_text('https://example.org/lrc-tool\n')
            self.assertTrue(app.configure_lrclib_contact(td))
            self.assertIn('example.org',app.LRCLIB_USER_AGENT)
            class Resp:
                def __enter__(self):return self
                def __exit__(self,*_):pass
                def read(self,*_):return b'[]'
            urls=[]
            def fake(req,timeout=0):
                urls.append(req)
                return Resp()
            with mock.patch.object(app,'wait_for'),mock.patch('urllib.request.urlopen',side_effect=fake):
                app.direct_get('SyncLRC','https://example.org/a',{'q':'x'})
                app.direct_get('LRCLIB','https://example.org/a',{'q':'x'})
            self.assertNotIn('example.org/lrc-tool',urls[0].get_header('User-agent'))
            self.assertIn('example.org/lrc-tool',urls[1].get_header('User-agent'))
    def test_review_list_separate_from_not_found(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            a=root/'A.mp3';b=root/'B.mp3';c=root/'C.mp3'
            for track in (a,b,c):track.write_bytes(b'UNCHANGED')
            states={a:('REVIEW_AVAILABLE','one candidate'),b:('NOT_FOUND','no match'),c:('TIMEOUT','read timeout')}
            nf,t=app.write_summary(root,[a,b,c],states)
            self.assertEqual((nf,t),(1,1))
            self.assertIn('A.mp3',(root/'LRC_Review_Needed.txt').read_text('utf-8-sig'))
            self.assertNotIn('A.mp3',(root/'LRC_Not_Found.txt').read_text('utf-8-sig'))
            self.assertEqual(a.read_bytes(),b'UNCHANGED')
    def test_429_no_retries_and_persisted_cooldown(self):
        with tempfile.TemporaryDirectory() as td:
            app.load_provider_cooldowns(Path(td)/'cooldowns.json')
            with mock.patch.object(app,'provider_lrclib',side_effect=app.ProviderFailure('429',rate_limit=True,retry_after='60')):
                retry=set()
                _,status,_,outcomes=app.search_song('Song','Artist','',95,app.CandidateReview(),only_providers=('LRCLIB',),retry_targets=retry)
                self.assertEqual(retry,set())
                self.assertIn('LRCLIB',app.blocked)
                self.assertIn('ERROR',outcomes[0])
            self.assertIn('LRCLIB',json.loads((Path(td)/'cooldowns.json').read_text()))

if __name__=='__main__':unittest.main(verbosity=2)
