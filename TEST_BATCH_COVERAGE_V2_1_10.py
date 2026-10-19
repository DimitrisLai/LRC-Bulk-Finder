"""Integration test: 503 on one song cannot silently skip the next song."""
import csv, io, json, sys, tempfile, types, unittest, urllib.error
from pathlib import Path
from unittest import mock
from contextlib import redirect_stdout
sys.modules.setdefault('syncedlyrics',types.SimpleNamespace(search=lambda *a,**kw:None))
import LRC_Bulk_Finder as app

class Response:
    status=200
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,*args):return b'[]'

class TestFullBatch(unittest.TestCase):
    def setUp(self):
        app.blocked.clear(); app.errors.clear();app.PROVIDER_RECOVERY_AT.clear()
        app.PROVIDER_ERROR_STREAK.clear();app.LRCLIB_503_RETRY_AT=0
        app.LRCLIB_503_STREAK=0;app.HISTORY_ENABLED=False;app.HISTORY_CACHE.clear()
        app.LRCLIB_EXACT_FALLBACK=False;app.MB_ENABLED=False
    def test_thorough_first_attempt_and_503_queue(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);one=folder/'A.mp3';two=folder/'B.mp3'
            one.write_bytes(b'A-ORIGINAL');two.write_bytes(b'B-ORIGINAL')
            answers=iter(['1','n','n','fast','y','n','n','a','n'])
            requested=[]
            def fake_open(req,timeout=10):
                requested.append(req.full_url)
                if len(requested)==1:
                    raise urllib.error.HTTPError(req.full_url,503,'Service Unavailable',{},None)
                return Response()
            def pass_recovery(source,until,description):
                app.LRCLIB_503_RETRY_AT=0
            with mock.patch.object(app,'select_folder',return_value=folder),\
                 mock.patch.object(app,'song_info',side_effect=lambda p:(p.stem,'Demo Artist','',180.0)),\
                 mock.patch.object(app,'provider_synclrc',return_value=None),\
                 mock.patch.object(app,'provider_unison',return_value=None),\
                 mock.patch.object(app,'provider_lrcapi',return_value=None),\
                 mock.patch.object(app,'provider_syncedlyrics',return_value=None),\
                 mock.patch.object(app,'wait_for'),\
                 mock.patch.object(app,'wait_for_recovery',side_effect=pass_recovery) as waiting,\
                 mock.patch('urllib.request.urlopen',side_effect=fake_open),\
                 mock.patch('builtins.input',side_effect=lambda _:next(answers)),\
                 redirect_stdout(io.StringIO()):
                app.main()
            self.assertEqual(len(requested),2)
            waiting.assert_called_once()
            coverage=folder/f"LRC_First_Attempt_Coverage_v{app.VERSION.replace('.', '_')}.csv"
            with coverage.open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
            lc=[r for r in rows if r['provider']=='LRCLIB']
            self.assertEqual(len(lc),2)
            self.assertEqual([r['first-pass coverage'] for r in lc],['REQUEST_SENT','REQUEST_SENT'])
            catchup=folder/f"LRC_LRCLIB_Catchup_Queue_v{app.VERSION.replace('.', '_')}.csv"
            with catchup.open(encoding='utf-8-sig') as f:queued=list(csv.DictReader(f))
            self.assertEqual(len(queued),1)
            self.assertEqual(queued[0]['MP3 path'],str(one))
            self.assertEqual(one.read_bytes(),b'A-ORIGINAL')
            self.assertEqual(two.read_bytes(),b'B-ORIGINAL')

if __name__=='__main__':unittest.main(verbosity=2)
