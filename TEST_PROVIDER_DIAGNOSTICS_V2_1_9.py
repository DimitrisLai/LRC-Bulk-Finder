"""v2.1.7 HTTP diagnostic regression tests. No network traffic or MP3 writes."""
import csv
import io
import json
import socket
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock
import sys,types
sys.modules.setdefault('syncedlyrics',types.SimpleNamespace(search=lambda *a,**k: None))
import LRC_Bulk_Finder as app

class FakeResponse:
    def __init__(self,body=b'{}',status=200):self.body=body;self.status=status
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,*args):return self.body

class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        app.blocked.clear();app.errors.clear();app.next_available.clear()
        app.HISTORY_ENABLED=False;app.HISTORY_CACHE.clear();app.HISTORY_PATH=None
        app.GREEK_MODE=False;app.MB_ENABLED=False;app.MB_DISABLED_REASON=None
        app.ACTIVE_PROVIDERS=None;app.ACTIVE_HTTP_TRACE=None
        app.COOLDOWN_PATH=None;app.COOLDOWN_UNTIL={}
        app.PROVIDER_RECOVERY_AT.clear();app.PROVIDER_ERROR_STREAK.clear();app.COMPLETE_FIRST_PASS=False
        app.LRCLIB_503_STREAK=0;app.LRCLIB_503_RETRY_AT=0.0

    def request(self,code=200,provider='LRCLIB'):
        trace=[]
        with mock.patch.object(app,'wait_for'),mock.patch('urllib.request.urlopen',return_value=FakeResponse(b'[]',code)):
            app.ACTIVE_HTTP_TRACE=trace
            result=app.direct_get(provider,'https://example.org/lyrics',{'q':'Personal Song Title'})
        app.ACTIVE_HTTP_TRACE=None
        return result,trace

    def test_http_200_exact_status_and_no_query_leak(self):
        result,events=self.request()
        self.assertEqual(result,'[]')
        self.assertEqual(events[0]['status'],'200')
        self.assertEqual(events[0]['endpoint'],'example.org/lyrics')
        self.assertNotIn('Personal Song',str(events))
        self.assertIn('HTTP 200',app.http_summary('LRCLIB',events))

    def test_http_404_is_visible_even_when_no_result(self):
        ex=urllib.error.HTTPError('https://example.org/x',404,'Not Found',{},None)
        trace=[]
        with mock.patch.object(app,'wait_for'),mock.patch('urllib.request.urlopen',side_effect=ex):
            app.ACTIVE_HTTP_TRACE=trace
            self.assertIsNone(app.direct_get('LRCLIB','https://example.org/x',{'q':'X'}))
        app.ACTIVE_HTTP_TRACE=None
        self.assertEqual(trace[0]['status'],'404')

    def test_better_ttml_401_is_visible(self):
        ex=urllib.error.HTTPError('https://example.org/x',401,'Unauthorized',{},None)
        trace=[]
        with mock.patch.object(app,'wait_for'),mock.patch('urllib.request.urlopen',side_effect=ex):
            app.ACTIVE_HTTP_TRACE=trace
            with self.assertRaises(app.ProviderFailure) as cm:
                app.direct_get('BetterTTML','https://example.org/x',{'q':'X'})
            self.assertIn('HTTP 401',str(cm.exception))
        app.ACTIVE_HTTP_TRACE=None
        self.assertEqual(trace[0]['status'],'401')
        self.assertIn('uncached',trace[0]['detail'])

    def test_http_403_and_503_exceptions_with_codes(self):
        for code in [403,503]:
            with self.subTest(code=code):
                ex=urllib.error.HTTPError('https://example.org/x',code,'Failure',{},None)
                trace=[]
                with mock.patch.object(app,'wait_for'),mock.patch('urllib.request.urlopen',side_effect=ex):
                    app.ACTIVE_HTTP_TRACE=trace
                    with self.assertRaises(app.ProviderFailure) as ctx:
                        app.direct_get('LRCLIB','https://example.org/x',{'q':'X'})
                app.ACTIVE_HTTP_TRACE=None
                self.assertEqual(trace[0]['status'],str(code))
                self.assertFalse(ctx.exception.timeout)

    def test_http_429_records_retry_after_without_retrying(self):
        ex=urllib.error.HTTPError('https://example.org/x',429,'Limit',{'Retry-After':'60'},None)
        trace=[]
        with mock.patch.object(app,'wait_for'),mock.patch('urllib.request.urlopen',side_effect=ex):
            app.ACTIVE_HTTP_TRACE=trace
            with self.assertRaises(app.ProviderFailure) as ctx:
                app.direct_get('LRCLIB','https://example.org/x',{'q':'X'})
        app.ACTIVE_HTTP_TRACE=None
        self.assertTrue(ctx.exception.rate_limit)
        self.assertEqual(ctx.exception.retry_after,'60')
        self.assertEqual(trace[0]['status'],'429')

    def test_network_timeout_has_no_fake_http_code(self):
        trace=[]
        with mock.patch.object(app,'wait_for'),mock.patch('urllib.request.urlopen',side_effect=urllib.error.URLError(socket.timeout('timed out'))):
            app.ACTIVE_HTTP_TRACE=trace
            with self.assertRaises(app.ProviderFailure) as ctx:
                app.direct_get('LRCLIB','https://example.org/x',{'q':'X'})
        app.ACTIVE_HTTP_TRACE=None
        self.assertTrue(ctx.exception.timeout)
        self.assertEqual(trace[0]['status'],'NETWORK_TIMEOUT')

    def test_skipped_provider_prints_reason_with_no_request(self):
        app.blocked['LRCLIB']='429 cooldown until tomorrow'
        log=io.StringIO();traces=[]
        with redirect_stdout(log):
            _,status,_,calls=app.search_song('Song','Artist','',200,app.CandidateReview(),only_providers=['LRCLIB'],request_traces=traces)
        self.assertIn('SKIPPED',log.getvalue())
        self.assertIn('cooldown until tomorrow',log.getvalue())
        self.assertEqual(traces,[[]])
        self.assertEqual(status,'SERVER_ERROR')
        self.assertIn('SKIPPED',calls[0])

    def test_timeout_retries_only_affected_provider(self):
        retry=set();traces=[]
        with mock.patch.object(app,'provider_unison',side_effect=app.ProviderFailure('socket timeout',timeout=True)),\
             mock.patch.object(app,'provider_lrclib',return_value=None):
            _,status,_,calls=app.search_song('Song','Artist','',200,app.CandidateReview(),only_providers=['Unison','LRCLIB'],retry_targets=retry,request_traces=traces)
        self.assertEqual(status,'TIMEOUT')
        self.assertEqual(retry,{'Unison'})
        self.assertEqual(len(traces),2)
        self.assertEqual(len(calls),2)

    def test_provider_error_threshold_is_printed_and_later_skipped(self):
        buffer=io.StringIO()
        with mock.patch.object(app,'provider_unison',side_effect=app.ProviderFailure('HTTP 503: Service Unavailable')),redirect_stdout(buffer):
            for _ in range(3):
                app.search_song('Song','Artist','',200,app.CandidateReview(),only_providers=['Unison'])
        log=buffer.getvalue()
        self.assertIn('HTTP 503',log)
        self.assertIn('TEMPORARY recovery',log)
        self.assertIn('Unison: SKIPPED',log)

    def test_library_status_explicitly_unknown(self):
        self.assertIn('UNKNOWN',app.http_summary('NetEase',[]))
        self.assertIn('NO HTTP request',app.http_summary('LRCLIB',[]))

    def test_main_emits_new_diagnostic_csv_without_modifying_mp3(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            original=b'MP3-DO-NOT-CHANGE'
            (folder/'A.mp3').write_bytes(original)
            answers=iter(['1','n','n','fast','n','n','n','a','n'])
            out=io.StringIO()
            def simulated_request(req,timeout=10):
                if 'lrclib.net' in req.full_url:
                    return FakeResponse(b'[]',200)
                return FakeResponse(b'{}',200)
            with mock.patch.object(app,'select_folder',return_value=folder),\
                 mock.patch.object(app,'song_info',return_value=('Song','Artist','',190.0)),\
                 mock.patch.object(app,'provider_syncedlyrics',return_value=None),\
                 mock.patch('urllib.request.urlopen',side_effect=simulated_request),\
                 mock.patch.object(app,'wait_for'),\
                 mock.patch('builtins.input',side_effect=lambda _:next(answers)),\
                 redirect_stdout(out):
                app.main()
            self.assertEqual((folder/'A.mp3').read_bytes(),original)
            with (folder/'LRC_HTTP_Diagnostics_v2_1_15.csv').open(encoding='utf-8-sig') as f:
                rows=list(csv.DictReader(f))
            self.assertTrue(rows)
            self.assertTrue(any(row['HTTP status / transport outcome']=='200' for row in rows))
            self.assertTrue(any(row['HTTP status / transport outcome']=='NOT_OBSERVED' and 'third-party' in row['reason'] for row in rows))
            self.assertTrue((folder/'LRC_Finder_Provider_Details_v2_1_15.csv').exists())
            self.assertIn('HTTP status',out.getvalue())
            self.assertTrue(any((folder/'LRC_Run_Reports').iterdir()))

if __name__=='__main__':unittest.main(verbosity=2)
