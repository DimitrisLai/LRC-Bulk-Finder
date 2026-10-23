"""Regression tests for v2.9.4 startup and honest version reporting."""
from __future__ import annotations
import contextlib
import io
import os
import sys
import unittest
from unittest import mock
import run_saved_profile
from v245_features import VERSION
import LRC_Bulk_Finder as engine

class WorkerStartupTests(unittest.TestCase):
    def test_version_single_truth_and_engine_match(self):
        self.assertEqual(VERSION,"2.9.4")
        self.assertEqual(VERSION,engine.VERSION)
    def test_worker_without_profile_helpfully_identifies_gui(self):
        output=io.StringIO()
        with contextlib.redirect_stderr(output):
            with self.assertRaises(SystemExit) as thrown:
                run_saved_profile.main([])
        self.assertEqual(thrown.exception.code,2)
        self.assertIn("LRC_Control_Center.exe",output.getvalue())
        self.assertIn("background search worker",output.getvalue())
    def test_worker_help_still_works(self):
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as thrown:
                run_saved_profile.main(["--help"])
        self.assertEqual(thrown.exception.code,0)
        self.assertIn("--setup-lrclib",output.getvalue())

def display_available():
    if sys.platform=="win32":return True
    try:
        import tkinter as tk
        r=tk.Tk();r.withdraw();r.destroy()
        return True
    except Exception:return False

@unittest.skipUnless(display_available(),"Tk display not available")
class GuiStartupTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.patch=mock.patch.dict(os.environ,{"APPDATA":self.temp.name})
        self.patch.start();self.addCleanup(self.patch.stop)
        from LRC_Control_Center import ControlCenter
        self.root=ControlCenter()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
    def test_initial_title_matches_installed_version(self):
        self.assertEqual(self.root.title(),"LRC Bulk Finder v2.9.4 — Control Center")
    def test_greek_english_changes_cannot_revert_title(self):
        self.root.language_choice.set("Ελληνικά")
        self.root._language_selected()
        self.assertEqual(self.root.title(),"LRC Bulk Finder v2.9.4 — Control Center")
        self.root.language_choice.set("English")
        self.root._language_selected()
        self.assertEqual(self.root.title(),"LRC Bulk Finder v2.9.4 — Control Center")
        self.assertEqual(len(self.root.notebook.tabs()),8)
        self.assertEqual(len(self.root.studio_tabs.tabs()),5)

if __name__=="__main__":
    unittest.main(verbosity=2)
