"""v2.9 native Tk integration, scan cancellation, read-only Studio open, Greek UI."""
from __future__ import annotations
import os
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock
import LRC_Control_Center as gui

def has_display():
    if sys.platform=="win32":return True
    import tkinter as tk
    try:
        root=tk.Tk();root.withdraw();root.destroy()
        return True
    except tk.TclError:return False

@unittest.skipUnless(has_display(),"Native Tk display required")
class SmartUITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.env=mock.patch.dict(os.environ,{"APPDATA":self.tmp.name});self.env.start();self.addCleanup(self.env.stop)
        self.root=Path(self.tmp.name)/"music";self.root.mkdir()
        self.track=self.root/"Μουσική.wav"
        with wave.open(str(self.track),"wb") as out:
            out.setnchannels(1);out.setsampwidth(2);out.setframerate(8000)
            out.writeframes(b"\0\0"*16000)
        self.lrc=self.track.with_suffix(".lrc");self.lrc.write_text("[00:00.30] Ελλάς\n[00:01.10] Μουσική\n",encoding="utf-8")
        self.bad=self.root/"Missing.mp3";self.bad.write_bytes(b"audio")
        self.app=gui.ControlCenter();self.app.withdraw();self.addCleanup(self.app.destroy)
        self.app.folder.set(str(self.root))
    def _scan(self):
        from v290_smart_library import scan_index
        scan_index(self.root)
        self.app._v290_root=str(self.root)
        self.app._v290_reset_page()
    def test_five_nested_eight_top_and_greek_title(self):
        self.assertEqual(len(self.app.notebook.tabs()),8)
        self.assertEqual(len(self.app.studio_tabs.tabs()),5)
        self.assertEqual(self.app.studio_tabs.tab(self.app.smart_library_tab,"text"),"Smart Library")
        self.app.language_choice.set("Ελληνικά");self.app._language_selected()
        self.assertEqual(self.app.studio_tabs.tab(self.app.smart_library_tab,"text"),"Έξυπνη Βιβλιοθήκη")
    def test_missing_review_queue_filter(self):
        self._scan()
        self.assertGreaterEqual(len(self.app._v290_records),1)
        self.assertTrue(any(row["name"]==self.bad.name for row in self.app._v290_records.values()))
        self.app._v290_filter.set("All")
        self.app._v290_reset_page()
        self.assertEqual(len(self.app._v290_records),2)
    def test_open_selected_track_without_writing_any_source(self):
        self._scan()
        self.app._v290_filter.set("All");self.app._v290_reset_page()
        idx=next(key for key,row in self.app._v290_records.items() if Path(row["path"]).resolve()==self.track.resolve())
        self.app._v290_tree.selection_set(idx)
        before=(self.track.read_bytes(),self.lrc.read_bytes())
        self.app._v290_open()
        self.assertEqual(Path(self.app.studio_audio.get()).resolve(),self.track.resolve())
        self.assertEqual(self.app.studio_doc.lines[0].text,"Ελλάς")
        self.assertEqual(before,(self.track.read_bytes(),self.lrc.read_bytes()))
    def test_mark_bookmark_and_history(self):
        self._scan()
        selected=next(iter(self.app._v290_records))
        self.app._v290_tree.selection_set(selected)
        self.app._v290_mark("bookmarked")
        self.assertEqual(next(iter(self.app._v290_records.values()))["review"],"bookmarked")
        with mock.patch.object(self.app,"_dialog") as dialog:
            self.app._v290_history()
        self.assertTrue(dialog.called)
    def test_no_scan_close_inprogress(self):
        self.app._v290_running=True
        with mock.patch.object(self.app,"_dialog",return_value=True):
            self.assertFalse(self.app._studio_can_close())
        self.assertTrue(self.app._v290_stop.is_set())
        self.app._v290_running=False
    def test_completed_queue_update_on_tk_thread(self):
        from v290_smart_library import scan_index
        result=scan_index(self.root)
        self.app._v290_token=4
        self.app._v290_root=str(self.root)
        self.app._v290_running=True
        self.app._v290_progress.put((4,"result",result))
        self.app._v290_poll()
        self.assertFalse(self.app._v290_running)
        self.assertTrue(self.app._v290_records)
    def test_switch_track_after_optional_vlc_recreates_safe_player(self):
        from v270_vlc import VLCPlayer
        from v260_player import StudioPlayer
        from TEST_V270_FEATURES import FakeVLC
        old=VLCPlayer(FakeVLC())
        old.load(self.track)
        self.app.studio_player=old
        self.app._v270_rate.set("1.25x")
        before=(self.track.read_bytes(),self.lrc.read_bytes())
        self.assertTrue(self.app._v270_open(self.track))
        self.assertIsInstance(self.app.studio_player,StudioPlayer)
        self.assertEqual(self.app._v270_rate.get(),"1.00x")
        self.assertEqual(before,(self.track.read_bytes(),self.lrc.read_bytes()))

    def test_export_rejected_when_user_declines(self):
        self._scan()
        chosen=Path(self.tmp.name)/"export.csv"
        with mock.patch.object(self.app,"_file_dialog",return_value=str(chosen)),mock.patch.object(self.app,"_dialog",return_value=False):
            self.app._v290_export()
        self.assertFalse(chosen.exists())
if __name__=="__main__":unittest.main(verbosity=2)
