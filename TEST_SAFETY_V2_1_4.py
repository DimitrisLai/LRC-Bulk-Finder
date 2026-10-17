"""Offline-only safety regressions; no online lyrics queries or real MP3 modification."""
import csv
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest import mock
import sys
sys.modules.setdefault('syncedlyrics',types.SimpleNamespace(search=lambda *a,**k:None))
import LRC_Bulk_Finder as app

LRC='[00:00.20] Start\n[01:13.00] Middle\n[03:15.00] End\n'

class SafetyTests(unittest.TestCase):
    def setUp(self):
        app.blocked.clear();app.errors.clear();app.GREEK_MODE=False
        app.ACTIVE_PROVIDERS=None;app.HISTORY_ENABLED=False
        app.HISTORY_CACHE.clear();app.HISTORY_PATH=None
    def test_exact_verified_metadata(self):
        ok,_=app.acceptable('Song','Artist',200,'Song','Artist',200.5,LRC)
        self.assertTrue(ok)
    def test_duration_over_three_seconds_rejected(self):
        ok,note=app.acceptable('Song','Artist',200,'Song','Artist',204,LRC)
        self.assertFalse(ok);self.assertIn('3s',note)
    def test_missing_duration_rejected(self):
        ok,_=app.acceptable('Song','Artist',200,'Song','Artist',None,LRC)
        self.assertFalse(ok)
    def test_missing_artist_rejected(self):
        ok,_=app.acceptable('Song','Artist',200,'Song','',200,LRC)
        self.assertFalse(ok)
    def test_standard_vs_remix_rejected(self):
        ok,_=app.acceptable('Song - DJ Mix','Artist',200,'Song','Artist',200,LRC)
        self.assertFalse(ok)
    def test_named_remix_rejected(self):
        ok,_=app.acceptable('Song - Paradise Mix','Artist',200,'Song - Sunrise Mix','Artist',200,LRC)
        self.assertFalse(ok)
    def test_equal_remix_accepted(self):
        ok,_=app.acceptable('Song - Paradise Mix','Artist',200,'Song (Paradise Mix)','Artist',201,LRC)
        self.assertTrue(ok)
    def test_radio_vs_extended_rejected(self):
        ok,_=app.acceptable('Song - Radio Edit','Artist',200,'Song - Extended Mix','Artist',201,LRC)
        self.assertFalse(ok)
    def test_lrc_offset_and_duplicate_lines(self):
        input='[offset:+500]\n[00:12.30]hello\n[00:12.30]hello\n[00:13.30]world\n'
        self.assertEqual(app.sanitize_lrc(input),'[00:12.80] hello\n[00:13.80] world\n')
    def test_reject_invalid_offset(self):
        self.assertEqual(app.lrc_lines('[offset:999999]\n[00:01.00]a'),[])
    def test_review_candidate_doesnt_create_actual_lrc(self):
        with tempfile.TemporaryDirectory() as td:
            track=Path(td)/'Song.mp3';track.write_bytes(b'KEEP AUDIO')
            review=app.CandidateReview();review.add('Provider','Song','Artist','Unverified',lyrics=LRC)
            rows=app.export_review_candidates(track,1,review,Path(td)/'review')
            self.assertTrue(Path(rows[0][-1]).exists())
            self.assertFalse(track.with_suffix('.lrc').exists())
            self.assertEqual(track.read_bytes(),b'KEEP AUDIO')
    def test_syncedlyrics_never_auto_saves_unverified(self):
        with mock.patch.object(app.syncedlyrics,'search',return_value=LRC), mock.patch.object(app,'wait_for'):
            hit=app.provider_syncedlyrics('NetEase','Song','Artist','',200,app.CandidateReview())
        self.assertIsNone(hit)
    def test_better_provider_never_auto_saves_unverified(self):
        review=app.CandidateReview()
        with mock.patch.object(app,'direct_json',return_value={'lyrics':LRC}):
            hit=app.provider_better('BetterKuGou','Song','Artist','',200,review)
        self.assertIsNone(hit);self.assertTrue(review.items)
    def test_timeout_only_retries(self):
        with mock.patch.object(app,'provider_lrclib',side_effect=app.ProviderFailure('socket timeout',timeout=True)):
            retry=set()
            _,state,_,calls=app.search_song('Song','Artist','',200,app.CandidateReview(),only_providers=('LRCLIB',),retry_targets=retry)
        self.assertEqual(state,'TIMEOUT');self.assertEqual(retry,{'LRCLIB'})
    def test_429_does_not_retry(self):
        with mock.patch.object(app,'provider_lrclib',side_effect=app.ProviderFailure('429',rate_limit=True)):
            retry=set()
            _,_,_,_=app.search_song('Song','Artist','',200,app.CandidateReview(),only_providers=('LRCLIB',),retry_targets=retry)
        self.assertEqual(retry,set())
    def test_no_match_history_persists_and_is_reused(self):
        with tempfile.TemporaryDirectory() as td:
            filename=Path(td)/'history.jsonl';app.load_search_history(filename);app.HISTORY_ENABLED=True
            with mock.patch.object(app,'provider_lrclib',return_value=None) as f:
                _,status,_,_=app.search_song('Song','Artist','',200,app.CandidateReview(),only_providers=('LRCLIB',))
                self.assertEqual(status,'NOT_FOUND')
                self.assertEqual(f.call_count,1)
            app.HISTORY_CACHE.clear();app.load_search_history(filename)
            with mock.patch.object(app,'provider_lrclib',side_effect=AssertionError('Should use cached result')):
                _,status,_,calls=app.search_song('Song','Artist','',200,app.CandidateReview(),only_providers=('LRCLIB',))
                self.assertEqual(status,'NOT_FOUND')
                self.assertEqual(calls,['LRCLIB=CACHED_NO_MATCH'])
    def test_history_key_changes_on_alias(self):
        initial=app.search_history_key('LRCLIB','Song','Artist','',200)
        app.GREEK_MODE=True
        app.GREEK_TITLE_ALIASES['song']='Σονγκ'
        app.G2G_SONG_PLANS.clear()
        try:self.assertNotEqual(initial,app.search_history_key('LRCLIB','Song','Artist','',200))
        finally:app.GREEK_TITLE_ALIASES.pop('song',None)
    def test_ai_preserves_version_suffix(self):
        class FakeAI:
            def convert(self,text,typ):return ('Τραγούδι' if typ=='title' else 'Καλλιτέχνης','')
        app.GREEK_MODE=True
        app.G2G_SONG_PLANS.clear()
        detail=app.precompute_greek_plan('Tragoudi - Some DJ Remix','Singer',FakeAI())
        self.assertEqual(detail['Greek title alternative'],'Τραγούδι - Some DJ Remix')
        self.assertTrue(any('Some DJ Remix' in t for t,a in app.query_variants('Tragoudi - Some DJ Remix','Singer')))

if __name__=='__main__':unittest.main(verbosity=2)
