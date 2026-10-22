"""v2.8 real Windows Tk karaoke UI smoke and safety checks (disposable fixtures)."""
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
    try:
        import tkinter as tk
        root=tk.Tk();root.withdraw();root.destroy();return True
    except tk.TclError:return False

@unittest.skipUnless(has_display(),"Native Tk display required")
class KaraokeUITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.env=mock.patch.dict(os.environ,{"APPDATA":self.tmp.name});self.env.start();self.addCleanup(self.env.stop)
        self.track=Path(self.tmp.name)/"Track (Instrumental).wav"
        with wave.open(str(self.track),"wb") as out:
            out.setnchannels(1);out.setsampwidth(2);out.setframerate(8000)
            out.writeframes(b"\0\0"*16000)
        self.lyrics=Path(self.tmp.name)/"Track.lrc"
        self.lyrics.write_text("[00:00.30] Καλημέρα\n[00:01.00] Ελλάδα\n",encoding="utf-8")
        self.app=gui.ControlCenter();self.app.withdraw();self.addCleanup(self.app.destroy)
    def test_nested_tabs_and_greek(self):
        self.assertEqual(len(self.app.notebook.tabs()),8)
        self.assertEqual(len(self.app.studio_tabs.tabs()),5)
        self.assertEqual(self.app.studio_tabs.tab(self.app.karaoke_edition_tab,"text"),"Karaoke Edition")
        self.app.language_choice.set("Ελληνικά");self.app._language_selected()
        self.assertEqual(self.app.studio_tabs.tab(self.app.karaoke_edition_tab,"text"),"Έκδοση Καραόκε")
    def test_automatic_instrumental_matching_and_playlist(self):
        self.app._v280_add_files([str(self.track)])
        self.assertEqual(len(self.app._v280_session.entries),1)
        self.assertEqual(self.app._v280_session.entries[0].lrc,str(self.lyrics))
        self.app._v280_open_selected()
        self.assertEqual(self.app.studio_audio.get(),str(self.track))
        self.assertEqual(self.app.studio_doc.lines[0].text,"Καλημέρα")
    def test_projector_current_next_with_offset_and_theme(self):
        self.app._v280_add_files([str(self.track)])
        self.app._v280_open_selected()
        self.app._v270_show_karaoke()
        self.assertIsNotNone(self.app._v280_canvas)
        with mock.patch.object(self.app.studio_player,"position",return_value=.85):
            self.app._v270_karaoke_refresh()
            self.assertEqual(self.app.karaoke_current.get(),"Καλημέρα")
            self.assertEqual(self.app.karaoke_next.get(),"Ελλάδα")
            self.app._v280_change_offset(1)
            self.assertEqual(self.app.karaoke_current.get(),"♪")
            self.app._v280_change_offset(-1)
        self.app._v280_theme.set("Ocean")
        self.app._v280_font.set(52)
        self.app._v280_next.set(False)
        self.app._v280_update_settings()
        self.assertEqual(self.app.karaoke_next.get(),"")
        self.assertEqual(self.app._v280_session.theme,"Ocean")
        self.app._v270_close_karaoke()
    def test_preview_no_write_and_apply_offset_only_memory(self):
        self.app._v280_add_files([str(self.track)])
        self.app._v280_open_selected()
        audio_before=self.track.read_bytes();lrc_before=self.lyrics.read_bytes()
        self.app._v280_preview_export()
        self.app._v280_change_offset(.1)
        with mock.patch.object(self.app,"_dialog",return_value=True):
            self.app._v280_apply_offset()
        self.assertAlmostEqual(self.app.studio_doc.lines[0].seconds,.4)
        self.assertEqual(self.app._v280_session.offset,0)
        self.assertEqual(self.track.read_bytes(),audio_before)
        self.assertEqual(self.lyrics.read_bytes(),lrc_before)
        self.assertFalse(list(Path(self.tmp.name).glob("*.candidate*.lrc")))
    def test_countdown_cancelled_on_track_change(self):
        self.app._v280_add_files([str(self.track)])
        self.app._v280_open_selected()
        self.app._v280_count.set(3);self.app._v280_update_settings()
        with mock.patch.object(self.app,"_studio_play") as play:
            self.app._v280_play_countdown()
            self.assertGreater(self.app._v280_count_remaining,0)
            token=self.app._v280_count_id
            self.app._v270_close_karaoke()
            self.app._v280_advance_count(token,str(self.track))
            play.assert_not_called()
    def test_remember_playlist_and_restore_last(self):
        self.app._v280_add_files([str(self.track)])
        self.app._v280_open_selected()
        self.assertEqual(self.app._v280_session.last_audio,str(self.track))
        from v280_karaoke_core import KaraokeSession
        self.assertEqual(KaraokeSession.load().entries[0].audio,str(self.track))
        self.app._v280_restore_last()
    def test_save_saved_ab_loop_and_restore(self):
        self.app._v280_add_files([str(self.track)])
        self.app._v280_open_selected()
        with mock.patch.object(self.app.studio_player,"position",side_effect=[.25,1.3]):
            self.app._v270_set_a();self.app._v270_set_b()
        self.assertEqual(self.app._v280_session.load_loop(self.track),(.25,1.3))
        self.app._v280_loop_restore()
        self.assertEqual((self.app.loop_a,self.app.loop_b),(.25,1.3))
    def test_shortcut_and_playlist_next_previous_no_audio_change(self):
        self.app._v280_add_files([str(self.track)])
        song=Path(self.tmp.name)/"second.wav";song.write_bytes(self.track.read_bytes())
        self.app._v280_add_files([str(song)])
        self.app._v280_tree.selection_set("0")
        self.app._v280_step(1)
        self.assertEqual(self.app.studio_audio.get(),str(song))
        self.app._v280_step(-1)
        self.assertEqual(self.app.studio_audio.get(),str(self.track))
    def test_optional_native_windows_drag_and_drop(self):
        if sys.platform!="win32":self.skipTest("Native Windows TkDnD acceptance")
        try:
            import tkinterdnd2
        except ImportError:
            self.skipTest("Optional tkinterdnd2 not installed (available in release build)")
        self.assertTrue(self.app._v280_drop_ready,
            "When tkinterdnd2 is packaged on Windows the real Treeview must register as native drop target.")

    def test_unsupported_drop_filename_preserves_session(self):
        self.app._v280_add_files([str(Path(self.tmp.name)/"suspicious.exe")])
        self.assertEqual(len(self.app._v280_session.entries),0)
if __name__=="__main__":unittest.main(verbosity=2)
