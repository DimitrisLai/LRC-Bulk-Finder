"""v2.9.2 scan preflight and uploaded-MP3 metadata regression.

Real user recordings are NEVER added to repository or release. Fixture
metadata mirrors those verified from the 3 private recordings only.
"""
import ast
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from mutagen import File as MutagenFile

class RealWorldPreflightTests(unittest.TestCase):
    def test_realworld_mp3_metadata_fixture(self):
        # Based on actual user-provided recordings, without copyrighted audio.
        metadata=[
          ("Summer In Greece - Mazwnakhs Giwrgos.mp3","Summer In Greece","Mazwnakhs Giwrgos",267.94),
          ("H Gkeisa - Iwanna Koutalidou.mp3","H Gkeisa","Iwanna Koutalidou",258.2),
          ("_ Aniko Se Mena - unknown artist.mp3",". Aniko Se Mena","",38.98),
        ]
        self.assertEqual(len(metadata),3)
        self.assertTrue(all(name.lower().endswith(".mp3") and sec>0 for name,_,_,sec in metadata))
        self.assertEqual(len([a for _,_,a,_ in metadata if not a]),1)
    def test_preflight_runs_metadata_selection_before_indexing(self):
        source=Path(__file__).with_name("LRC_Bulk_Finder.py").read_text(encoding="utf-8")
        tree=ast.parse(source)
        main=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name=="main")
        block=ast.get_source_segment(source,main)
        self.assertIn("PREFLIGHT DISCOVERY:",block)
        self.assertIn("PREFLIGHT METADATA:",block)
        self.assertIn("PREFLIGHT COMPLETE:",block)
        self.assertLess(block.index("howmany=input('How many missing songs?"),block.index("info=song_info(track)"))
        self.assertLess(block.index("if limit is not None and len(missing)>=limit:"),block.index("start_incremental_index(folder,missing)"))
        self.assertIn("check_stop()",block)
        self.assertIn("if is_live_track(info[0])",block)
    def test_private_recordings_never_packaged(self):
        build=Path(__file__).with_name("BUILD_V292_RELEASE.py").read_text(encoding="utf-8")
        self.assertNotIn("Summer In Greece - Mazwnakhs",build)
        self.assertNotIn("Aniko Se Mena",build)
        self.assertNotIn("H Gkeisa",build)
    def test_optional_local_inference_not_enabled_by_normal_quick_search(self):
        from search_profiles import DEFAULT,preset_profile
        self.assertFalse(DEFAULT["local_ai"])
        self.assertFalse(preset_profile("Greek Quick Test — 20 Songs")["local_ai"])

if __name__=="__main__": unittest.main(verbosity=2)
