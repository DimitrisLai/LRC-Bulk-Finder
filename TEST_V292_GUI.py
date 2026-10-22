"""v2.9.2 Tk UI checks: progress during indexing and metadata preflight."""
from __future__ import annotations
import os
import sys
import tempfile
import unittest
from unittest import mock

def has_display():
    if sys.platform=="win32":return True
    try:
        import tkinter as tk
        w=tk.Tk();w.withdraw();w.destroy();return True
    except Exception:return False

@unittest.skipUnless(has_display(),"Native GUI display required")
class PreflightProgressGUI(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patch=mock.patch.dict(os.environ,{"APPDATA":self.tmp.name})
        patch.start();self.addCleanup(patch.stop)
        from LRC_Control_Center import ControlCenter
        self.gui=ControlCenter()
        self.gui.withdraw()
        self.addCleanup(self.gui.destroy)
    def test_discovery_does_not_claim_elapsed_song_progress(self):
        self.gui._line("DISCOVERY: inspected=2250 audio=2200")
        self.assertIn("2,200 audio",self.gui.progress_text.get())
        self.assertEqual(float(self.gui.bar["value"]),0.)
        self.assertEqual(self.gui.counter_vars["found"].get(),"0")
    def test_index_progress_independent_from_lyrics_progress(self):
        self.gui._line("INDEXING: inspected=1500 total=3000")
        self.assertIn("1,500 / 3,000",self.gui.progress_text.get())
        self.assertAlmostEqual(float(self.gui.bar["value"]),50.)
        self.assertEqual(self.gui.counter_vars["found"].get(),"0")
    def test_preflight_limit_20_shows_real_selected_count(self):
        self.gui._line("PREFLIGHT: inspected=20 candidates=3183 selected=20 target=20")
        self.assertIn("20/20",self.gui.phase.get())
        self.assertIn("3,183 candidates",self.gui.progress_text.get())
        self.assertAlmostEqual(float(self.gui.bar["value"]),100.)
        self.assertEqual(self.gui.counter_vars["total_found"].get(),"0")
    def test_all_mode_preflight_progress(self):
        self.gui._line("PREFLIGHT: inspected=500 candidates=1000 selected=480 target=ALL")
        self.assertAlmostEqual(float(self.gui.bar["value"]),50.)
        self.assertIn("480/1000",self.gui.phase.get())
    def test_real_search_stage_replaces_preflight(self):
        self.gui._line("PREFLIGHT: inspected=20 candidates=3000 selected=20 target=20")
        self.gui._line("===== ROUND 1/3 | 20 songs | OFFLINE SQLITE ONLY; NO INTERNET =====")
        self.assertIn("ROUND 1/3",self.gui.phase.get())

if __name__=="__main__":
    unittest.main(verbosity=2)
