"""v2.1.20 offline-first 3-stage pipeline, no live network or databases."""
import io
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock
import sys
sys.modules.setdefault('syncedlyrics',types.SimpleNamespace(search=lambda *a,**k:None))
import LRC_Bulk_Finder as app


class StagedPipelineTests(unittest.TestCase):
    def setUp(self):
        app.STAGED_ONLINE_MODE=False
        app.GREEK_MODE=False
        app.MB_ENABLED=False
        app.G2G_SONG_PLANS.clear()
        app.G2G_TOOL=None
        app.blocked.clear()

    def tearDown(self):
        app.STAGED_ONLINE_MODE=False
        app.G2G_TOOL=None

    def test_stages_are_global_offline_online_only_misses_and_timeout_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            for name in ('A','B','C'):
                (folder/(name+'.mp3')).write_bytes(b'DO NOT CHANGE')
            events=[]
            original=lambda path:(path.stem,'Artist','',180)
            def fake_offline(title,artist,duration,review):
                events.append(('offline',title))
                if title=='A':
                    return app.Hit('[00:05.00] test\\n[02:58.00] end\\n','LRCLIB','verified','LOCAL_SQLITE',True)
                return None
            def fake_online(title,artist,album,duration,review,*,only_providers=None,retry_targets=None,timings=None,request_traces=None):
                events.append(('online' if only_providers is None else 'retry',title,
                               tuple(sorted(only_providers)) if only_providers is not None else None))
                if only_providers is None and title=='B':
                    retry_targets.add('LiriQo')
                    if timings is not None: timings.append(('LiriQo',.1))
                    if request_traces is not None: request_traces.append([])
                    return None,'TIMEOUT','only LiriQo timed out',['LiriQo=TIMEOUT']
                if only_providers is not None:
                    return None,'NOT_FOUND','retry completed',['LiriQo=NO_MATCH']
                return None,'NOT_FOUND','no match',['SyncLRC=NO_MATCH']
            def save(track,hit):
                track.with_suffix('.lrc').write_text(hit.lyrics,encoding='utf-8')
            answers=iter(['5','n','n','full','n','n','n','a','y'])
            def answer(_prompt=''):
                return next(answers)
            with mock.patch('builtins.input',side_effect=answer),\
                 mock.patch.object(app,'select_folder',return_value=folder),\
                 mock.patch.object(app,'ensure_local_lrclib_config',return_value=True),\
                 mock.patch.object(app,'load_provider_cooldowns'),\
                 mock.patch.object(app,'configure_lrclib_contact',return_value=True),\
                 mock.patch.object(app,'show_provider_availability'),\
                 mock.patch.object(app,'song_info',side_effect=original),\
                 mock.patch.object(app,'local_lrclib_search',side_effect=fake_offline),\
                 mock.patch.object(app,'search_song',side_effect=fake_online),\
                 mock.patch.object(app,'save_hit',side_effect=save),\
                 redirect_stdout(io.StringIO()):
                 app.main()
            self.assertEqual(events[:3],[('offline','A'),('offline','B'),('offline','C')])
            self.assertEqual(events[3],[('online','B',None)])
            self.assertEqual(events[4],[('online','C',None)])
            self.assertEqual(events[5],[('retry','B',('LiriQo',))])
            self.assertEqual(len(events),6)
            self.assertEqual((folder/'A.mp3').read_bytes(),b'DO NOT CHANGE')
            self.assertTrue((folder/'A.lrc').is_file())
            self.assertFalse((folder/'B.lrc').exists())
            self.assertFalse(app.STAGED_ONLINE_MODE)
            self.assertTrue((folder/'LRC_First_Attempt_Coverage_v2_1_20.csv').exists())

    def test_missing_database_never_falls_back_to_online(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch('builtins.input',return_value='5'),\
                 mock.patch.object(app,'select_folder',return_value=Path(tmp)),\
                 mock.patch.object(app,'ensure_local_lrclib_config',return_value=False),\
                 mock.patch.object(app,'search_song',side_effect=AssertionError('NO NETWORK')),\
                 redirect_stdout(io.StringIO()):
                 app.main()
            self.assertFalse(app.STAGED_ONLINE_MODE)

    def test_original_online_lrclib_local_lookup_disabled_only_during_stage(self):
        with mock.patch.object(app,'LOCAL_LRCLIB',object()),\
             mock.patch.object(app,'local_lrclib_search',side_effect=AssertionError('LOCAL REPEATED')),\
             mock.patch.object(app,'direct_json',return_value=[]) as http:
            app.STAGED_ONLINE_MODE=True
            app.GREEK_MODE=False
            app.LRCLIB_EXACT_FALLBACK=False
            app.provider_lrclib('Title','Artist','',180,app.CandidateReview())
            self.assertTrue(http.called)

    def test_option4_still_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch('builtins.input',return_value='4'),\
                 mock.patch.object(app,'select_folder',return_value=Path(tmp)),\
                 mock.patch.object(app,'ensure_local_lrclib_config',return_value=True),\
                 mock.patch.object(app,'run_offline_lrclib_folder') as func,\
                 redirect_stdout(io.StringIO()):
                app.main()
            func.assert_called_once()

if __name__=='__main__':
    unittest.main(verbosity=2)
