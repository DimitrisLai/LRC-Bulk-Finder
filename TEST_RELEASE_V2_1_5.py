"""v2.1.5 offline regression tests. No network, no real MP3 changes."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import sys,types
sys.modules.setdefault('syncedlyrics',types.SimpleNamespace(search=lambda *a,**k: None))
import LRC_Bulk_Finder as app

class Version215Tests(unittest.TestCase):
    def setUp(self):
        app.MB_CACHE.clear()
        app.MB_ENABLED=True
        app.MB_DISABLED_REASON=None
        app.GREEK_MODE=False
        app.blocked.clear()

    def test_project_url_enables_lrclib_by_default(self):
        self.assertTrue(app.configure_lrclib_contact(Path(__file__).parent))
        self.assertIn('github.com/DimitrisLai/LRC-Bulk-Finder', app.LRCLIB_USER_AGENT)

    def test_international_musicbrainz_variant_supported(self):
        example={'recordings':[{'title':'Blinding Lights','length':200000,'artist-credit':[{'name':'The Weeknd'}]}]}
        with patch.object(app,'direct_json',return_value=example) as request:
            result=app.musicbrainz_variant('Blinding Lites','The Weeknd',200.0)
        self.assertEqual(result,('Blinding Lights','The Weeknd'))
        self.assertEqual(app.query_variants('Blinding Lites','The Weeknd')[1],result)
        request.assert_called_once()

    def test_wrong_remix_never_added(self):
        example={'recordings':[{'title':'Blinding Lights (Extended Remix)','length':200000,
                                 'artist-credit':[{'name':'The Weeknd'}]}]}
        with patch.object(app,'direct_json',return_value=example):
            self.assertIsNone(app.musicbrainz_variant('Blinding Lites','The Weeknd',200.0))
        self.assertEqual(len(app.query_variants('Blinding Lites','The Weeknd')),1)

    def test_wrong_duration_never_added(self):
        example={'recordings':[{'title':'Blinding Lights','length':220000,
                                 'artist-credit':[{'name':'The Weeknd'}]}]}
        with patch.object(app,'direct_json',return_value=example):
            self.assertIsNone(app.musicbrainz_variant('Blinding Lites','The Weeknd',200.0))

    def test_identical_result_does_not_waste_search_variation(self):
        example={'recordings':[{'title':'Blinding Lites','length':200000,
                                 'artist-credit':[{'name':'The Weeknd'}]}]}
        with patch.object(app,'direct_json',return_value=example):
            self.assertIsNone(app.musicbrainz_variant('Blinding Lites','The Weeknd',200.0))
        self.assertEqual(len(app.query_variants('Blinding Lites','The Weeknd')),1)

    def test_international_startup_asks_musicbrainz(self):
        prompts=[]
        answers=iter(['1','n','n','fast','d','n','n','n','0'])
        def fake_input(prompt):
            prompts.append(prompt)
            return next(answers)
        with tempfile.TemporaryDirectory() as temp:
            Path(temp,'Test.mp3').write_bytes(b'')
            with patch.object(app,'select_folder',return_value=Path(temp)),\
                 patch.object(app,'song_info',return_value=('Test','Test Artist','','180')) ,\
                 patch('builtins.input',side_effect=fake_input):
                app.main()
        self.assertTrue(any('MusicBrainz' in x for x in prompts))
        self.assertFalse(app.MB_ENABLED)

if __name__=='__main__':unittest.main(verbosity=2)
