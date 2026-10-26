"""v3 Stage 1 hotfix: hard LRCLIB latency bound without touching music.

Synthetic responses only. Never contacts public providers or reads user files.
"""
from __future__ import annotations

import threading
import time
import unittest
import urllib.error
from unittest import mock

import LRC_Bulk_Finder as app


class SlowResponse:
    status = 200

    def __init__(self, delay=0.25, data=b'[]'):
        self.delay = delay
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, maxlen):
        time.sleep(self.delay)
        return self.data


class LRCLIBHardBudgetTests(unittest.TestCase):
    def setUp(self):
        self.saved = (app.blocked, app.errors, app.ACTIVE_PROVIDERS, app.LOCAL_LRCLIB,
                      app.LRCLIB_ACTIVE_DEADLINE, app.LRCLIB_LAST_FINISHED,
                      app.LRCLIB_503_STREAK, app.LRCLIB_503_RETRY_AT,
                      app.STAGED_ONLINE_MODE, app.MB_ENABLED,
                      app.HISTORY_ENABLED, app.LRCLIB_EXACT_FALLBACK,
                      app.COMPLETE_FIRST_PASS)
        app.blocked = {}
        app.errors.clear()
        app.ACTIVE_PROVIDERS = ('LRCLIB', 'SyncLRC')
        app.LOCAL_LRCLIB = None
        app.LRCLIB_ACTIVE_DEADLINE = None
        app.LRCLIB_LAST_FINISHED = 0
        app.LRCLIB_503_STREAK = 0
        app.LRCLIB_503_RETRY_AT = 0
        app.STAGED_ONLINE_MODE = False
        app.MB_ENABLED = False
        app.HISTORY_ENABLED = False
        app.LRCLIB_EXACT_FALLBACK = False
        app.COMPLETE_FIRST_PASS = False
        self.addCleanup(self.restore)

    def restore(self):
        (app.blocked, prev_errors, app.ACTIVE_PROVIDERS, app.LOCAL_LRCLIB,
         app.LRCLIB_ACTIVE_DEADLINE, app.LRCLIB_LAST_FINISHED,
         app.LRCLIB_503_STREAK, app.LRCLIB_503_RETRY_AT,
         app.STAGED_ONLINE_MODE, app.MB_ENABLED,
         app.HISTORY_ENABLED, app.LRCLIB_EXACT_FALLBACK,
         app.COMPLETE_FIRST_PASS) = self.saved
        app.errors.clear()
        app.errors.update(prev_errors)

    def test_slow_body_cannot_block_for_minutes(self):
        with mock.patch.object(app, 'LRCLIB_SONG_BUDGET_SECONDS', 0.035), \
             mock.patch.object(app, 'wait_for'), \
             mock.patch.object(app.urllib.request, 'urlopen', return_value=SlowResponse()):
            started = time.monotonic()
            with self.assertRaises(app.ProviderFailure) as caught:
                app.direct_get('LRCLIB', 'https://lrclib.net/api/search', {'q': 'dummy'})
            took = time.monotonic() - started
        self.assertTrue(caught.exception.stall)
        self.assertFalse(caught.exception.timeout)
        self.assertLess(took, 0.18, 'A slow streaming response must have an actual wall-clock cap')

    def test_stalled_lrclib_is_disabled_after_one_attempt_without_retrying(self):
        with mock.patch.object(app, 'LRCLIB_SONG_BUDGET_SECONDS', 0.04), \
             mock.patch.object(app, 'wait_for'), \
             mock.patch.object(app.urllib.request, 'urlopen', return_value=SlowResponse()), \
             mock.patch.object(app, 'provider_synclrc', return_value=None) as sync:
            retry = set()
            _, status, details, calls = app.search_song(
                'Song', 'Artist', '', 180, app.CandidateReview(),
                only_providers=('LRCLIB', 'SyncLRC'), retry_targets=retry)
            self.assertEqual(status, 'NOT_FOUND_PARTIAL')
            self.assertNotIn('LRCLIB', retry)
            self.assertIn('LRCLIB', app.blocked)
            self.assertIn('catch-up', app.blocked['LRCLIB'])
            self.assertIn('SyncLRC=NO_MATCH', calls)
            self.assertEqual(sync.call_count, 1)
            self.assertEqual(app.LRCLIB_503_STREAK, 0)

    def test_circuit_prevents_new_network_threads_on_later_songs(self):
        app.blocked['LRCLIB'] = 'previous network stall'
        with mock.patch.object(app.urllib.request, 'urlopen') as request, \
             mock.patch.object(app, 'provider_synclrc', return_value=None):
            _, status, _, calls = app.search_song('Song2','Artist','',180,
                app.CandidateReview(),only_providers=('LRCLIB','SyncLRC'))
            self.assertEqual(status,'NOT_FOUND_PARTIAL')
            self.assertTrue(any(c.startswith('LRCLIB=SKIPPED') for c in calls))
            request.assert_not_called()

    def test_fast_503_keeps_existing_cooldown_logic(self):
        error = urllib.error.HTTPError('https://lrclib.net/api/search', 503,
                                      'Service Unavailable', {}, None)
        with mock.patch.object(app, 'wait_for'), \
             mock.patch.object(app.urllib.request, 'urlopen', side_effect=error):
            _, status, _, calls=app.search_song('Song','Artist','',180,
                    app.CandidateReview(), only_providers=('LRCLIB',))
        self.assertIn('LRCLIB=ERROR', calls[0])
        self.assertGreater(app.LRCLIB_503_RETRY_AT, time.monotonic())
        self.assertNotIn('LRCLIB', app.blocked)
        self.assertEqual(app.LRCLIB_503_STREAK,1)

    def test_fast_response_still_matches_current_search_path(self):
        with mock.patch.object(app,'wait_for'), \
             mock.patch.object(app.urllib.request,'urlopen',return_value=SlowResponse(0, b'[]')) as rq:
            self.assertEqual(app.direct_json('LRCLIB','https://lrclib.net/api/search',{'q':'Artist Song'}),[])
            self.assertEqual(rq.call_count,1)


if __name__ == '__main__':
    unittest.main()
