import unittest
from unittest import mock
import sys,types
sys.modules.setdefault('syncedlyrics',types.SimpleNamespace(search=lambda *a,**k: None))
import LRC_Bulk_Finder as app

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        app.blocked.clear();app.errors.clear();app.next_available.clear()
        app.LRCLIB_503_STREAK=0;app.LRCLIB_503_RETRY_AT=0.0
        app.HISTORY_ENABLED=False;app.MB_ENABLED=False;app.ACTIVE_PROVIDERS=None
        app.COMPLETE_FIRST_PASS=False
    def test_provider_first_in_all_modes(self):
        self.assertEqual(app.PROVIDERS[0], 'LRCLIB')
        self.assertEqual(app.FAST_PROVIDERS[0], 'LRCLIB')
    def test_503_cooldown_and_recovery_after_expiry(self):
        fail=app.ProviderFailure('HTTP 503: Service Unavailable')
        with mock.patch.object(app,'provider_lrclib', side_effect=fail) as req:
            retry=set()
            app.search_song('Song','Artist','',200,app.CandidateReview(), only_providers=['LRCLIB'],retry_targets=retry)
            self.assertNotIn('LRCLIB', app.blocked)
            self.assertGreater(app.LRCLIB_503_RETRY_AT,0)
            self.assertEqual(retry,set())
            app.search_song('Song','Artist','',200,app.CandidateReview(), only_providers=['LRCLIB'])
            self.assertEqual(req.call_count,1,'Must skip during 503 temporary recovery')
        app.LRCLIB_503_RETRY_AT=0
        with mock.patch.object(app,'provider_lrclib',return_value=None) as req:
            app.search_song('Song','Artist','',200,app.CandidateReview(),only_providers=['LRCLIB'])
            self.assertEqual(req.call_count,1)
            self.assertEqual(app.LRCLIB_503_STREAK,0)
    def test_better_ttml_401_disables_only_unauthorized_source(self):
        with mock.patch.object(app,'provider_better',side_effect=app.ProviderFailure('HTTP 401: Unauthorized')) as req:
            app.search_song('Song','Artist','',200,app.CandidateReview(), only_providers=['BetterTTML'])
            self.assertIn('BetterTTML',app.blocked)
            app.search_song('Song','Artist','',200,app.CandidateReview(), only_providers=['BetterTTML'])
            self.assertEqual(req.call_count,1)
            self.assertEqual(len(app.HISTORY_CACHE),0)
    def test_429_still_persists_and_disables(self):
        with mock.patch.object(app,'record_rate_limit') as persist, mock.patch.object(app,'provider_lrclib',side_effect=app.ProviderFailure('429',rate_limit=True,retry_after='60')):
            rt=set()
            app.search_song('Song','Artist','',200,app.CandidateReview(),only_providers=['LRCLIB'],retry_targets=rt)
            self.assertIn('LRCLIB',app.blocked)
            persist.assert_called_once()
            self.assertEqual(rt,set())

if __name__=='__main__': unittest.main(verbosity=2)
