"""Lyrics Studio real-Tk user journey tests on disposable local music files."""
from __future__ import annotations
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from v260_studio import LyricLine
import LRC_Control_Center as gui


def _has_display():
    if sys.platform == "win32":
        return True
    import tkinter as tk
    try:
        app = tk.Tk()
        app.withdraw()
        app.destroy()
        return True
    except tk.TclError:
        return False


@unittest.skipUnless(_has_display(), "Tkinter display required")
class StudioGuiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.patch_env = mock.patch.dict(os.environ, {"APPDATA": self.tmp.name})
        self.patch_env.start()
        self.addCleanup(self.patch_env.stop)
        self.music = Path(self.tmp.name)
        self.track = self.music / "Greek Track.mp3"
        self.track.write_bytes(b"audio unchanged")
        self.original = self.music / "Greek Track.lrc"
        self.original.write_text("[00:01.00] Καλημέρα\n[00:03.00] κόσμε\n", encoding="utf-8")
        self.app = gui.ControlCenter()
        self.app.withdraw()
        self.addCleanup(self.app.destroy)
        self.app.studio_audio.set(str(self.track))

    def test_main_tabs_and_nested_studio(self):
        self.assertEqual(len(self.app.notebook.tabs()), 8)
        self.assertEqual(len(self.app.studio_tabs.tabs()), 5)
        self.assertEqual(self.app.studio_tabs.tab(self.app.precision_tab, 'text'), 'Precision & Karaoke')
        self.assertEqual(self.app.studio_tabs.tab(self.app.studio_frame, "text"), "Lyrics Studio")
        self.assertIsNotNone(self.app.sync_source)

    def test_read_only_import_and_preview(self):
        self.app._studio_load_lyrics(self.original)
        self.assertEqual(self.app.studio_tree.get_children(), ("0", "1"))
        self.assertEqual(self.app.studio_doc.active_line(1.2), 0)
        self.assertEqual(self.original.read_text(encoding="utf-8"),
                         "[00:01.00] Καλημέρα\n[00:03.00] κόσμε\n")

    def test_nudge_and_model_undo_redo(self):
        self.app._studio_load_lyrics(self.original)
        self.app.studio_tree.selection_set("1")
        self.app._studio_shift(0.1)
        self.assertEqual(self.app.studio_doc.lines[1].seconds, 3.1)
        self.app._studio_undo()
        self.assertEqual(self.app.studio_doc.lines[1].seconds, 3.0)
        self.app._studio_redo()
        self.assertEqual(self.app.studio_doc.lines[1].seconds, 3.1)

    def test_invalid_entry_keeps_audio_and_sidecar(self):
        self.app._studio_load_lyrics(self.original)
        self.app.studio_tree.selection_set("0")
        self.app.studio_exact.set("not a number")
        with mock.patch.object(self.app, "_dialog"):
            self.app._studio_exact()
        self.assertEqual(self.app.studio_doc.lines[0].seconds, 1)
        self.assertFalse(list(self.music.glob("*.candidate*.lrc")))

    def test_save_copies_only_to_new_candidate(self):
        self.app._studio_load_lyrics(self.original)
        self.app.studio_tree.selection_set("1")
        self.app._studio_shift(.2)
        before_mp3, before_lrc = self.track.read_bytes(), self.original.read_bytes()
        with mock.patch.object(self.app, "_dialog", return_value=True):
            self.app._studio_save()
        candidates = list(self.music.glob("*.candidate*.lrc"))
        self.assertEqual(len(candidates), 1)
        self.assertEqual(self.track.read_bytes(), before_mp3)
        self.assertEqual(self.original.read_bytes(), before_lrc)
        self.assertIn("UNVERIFIED", self.app.studio_status.get())

    def test_cancel_save_changes_nothing(self):
        self.app._studio_load_lyrics(self.original)
        with mock.patch.object(self.app, "_dialog", return_value=False):
            self.app._studio_save()
        self.assertFalse(list(self.music.glob("*.candidate*.lrc")))

    def test_does_not_save_bad_order(self):
        self.app._studio_load_lyrics(self.original)
        self.app.studio_doc.set_time(1, 0.5)
        with mock.patch.object(self.app, "_dialog") as dialog:
            self.app._studio_save()
        self.assertTrue(dialog.called)
        self.assertFalse(list(self.music.glob("*.candidate*.lrc")))

    def test_import_from_classic_lab(self):
        self.app.sync_source.insert("1.0", "Καλό\nΒράδυ\n")
        self.app._studio_from_classic()
        self.assertEqual(len(self.app.studio_doc.lines), 2)
        self.assertFalse(self.app._studio_saved)
        self.assertFalse(list(self.music.glob("*.candidate*.lrc")))

    def test_discard_unsaved_changes_requires_confirmation(self):
        self.app._studio_load_lyrics(self.original)
        self.app.studio_tree.selection_set("0")
        self.app._studio_shift(.1)
        with mock.patch.object(self.app, "_dialog", return_value=False):
            self.assertFalse(self.app._studio_can_close())

    def test_greek_labels_and_restore(self):
        self.app.language_choice.set("Ελληνικά")
        self.app._language_selected()
        self.assertEqual(self.app.studio_tabs.tab(self.app.studio_frame, "text"), "Στούντιο στίχων")
        self.assertEqual(self.app.studio_tree.heading("text", "text"), "Γραμμή στίχων")
        self.app.language_choice.set("English")
        self.app._language_selected()
        self.assertEqual(self.app.studio_tabs.tab(self.app.studio_frame, "text"), "Lyrics Studio")
        self.assertEqual(self.app.studio_tree.heading("text", "text"), "Lyric line")


if __name__ == "__main__":
    unittest.main(verbosity=2)
