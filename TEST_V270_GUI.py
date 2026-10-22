"""v2.7 real Tk karaoke / precision journeys using disposable audio and lyrics."""
from __future__ import annotations
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import LRC_Control_Center as gui


def can_show():
    if sys.platform == "win32":
        return True
    import tkinter as tk
    try:
        root = tk.Tk(); root.withdraw(); root.destroy()
        return True
    except tk.TclError:
        return False

@unittest.skipUnless(can_show(), "Tk display required")
class PrecisionUI(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.env=mock.patch.dict(os.environ,{"APPDATA":self.tmp.name})
        self.env.start();self.addCleanup(self.env.stop)
        self.track=Path(self.tmp.name)/"instrumental.wav"
        import wave
        with wave.open(str(self.track),"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000)
            w.writeframes(b"\x00\x00"*16000)
        self.lrc=self.track.with_suffix(".lrc")
        self.lrc.write_text("[00:00.30] Πρώτος\n[00:00.70] Δεύτερος\n",encoding="utf-8")
        self.app=gui.ControlCenter()
        self.app.withdraw()
        self.addCleanup(self.app.destroy)
        self.app.folder.set(str(Path(self.tmp.name)))

    def test_main_and_nested_tabs(self):
        self.assertEqual(len(self.app.notebook.tabs()),8)
        self.assertEqual(len(self.app.studio_tabs.tabs()),4)
        self.assertEqual(self.app.studio_tabs.tab(self.app.precision_tab,"text"),"Precision & Karaoke")

    def test_dashboard_open_goes_to_studio(self):
        self.app.dashboard_visible_rows={"0":{"path":str(self.track),"name":self.track.name,"status":"Has LRC"}}
        self.app.dashboard_tree.insert("","end",iid="0",values=(self.track.name,"Has LRC",0,str(self.track.parent)))
        self.app.dashboard_tree.selection_set("0")
        with mock.patch.object(self.app.studio_player,"load"):
            self.app._v270_from_dashboard()
        self.assertEqual(self.app.studio_audio.get(),str(self.track))
        self.assertEqual(len(self.app.studio_doc.lines),2)
        self.assertEqual(self.app.studio_tabs.select(),str(self.app.studio_frame))

    def test_candidate_open_loads_chosen_candidate(self):
        candidate=self.track.with_suffix(".candidate.lrc")
        candidate.write_text("[00:00.00] candidate\n[00:00.20] Ξεχωριστό\n",encoding="utf-8")
        self.app.review_rows={"0":{"path":candidate,"mp3":self.track,"has_mp3":True}}
        self.app.review_tree.insert("","end",iid="0",values=(self.track.name,candidate.name,"Primary"))
        self.app.review_tree.selection_set("0")
        with mock.patch.object(self.app.studio_player,"load"):
            self.app._v270_from_review()
        self.assertEqual(self.app.studio_doc.lines[0].text,"Ξεχωριστό")

    def test_karaoke_live_lines_and_next_without_write(self):
        self.app.studio_audio.set(str(self.track))
        self.app._studio_load_lyrics(self.lrc)
        original=(self.track.read_bytes(),self.lrc.read_bytes())
        self.app._v270_show_karaoke()
        with mock.patch.object(self.app.studio_player,"position",return_value=.45):
            self.app._v270_karaoke_refresh()
        self.assertEqual(self.app.karaoke_current.get(),"Πρώτος")
        self.assertEqual(self.app.karaoke_next.get(),"Δεύτερος")
        self.app._v270_close_karaoke()
        self.assertEqual(original,(self.track.read_bytes(),self.lrc.read_bytes()))

    def test_nudge_autosave_recovery_and_cancel_save(self):
        self.app.studio_audio.set(str(self.track))
        self.app._studio_load_lyrics(self.lrc)
        self.app.studio_tree.selection_set("0")
        self.app._studio_shift(.05)
        self.assertAlmostEqual(self.app.studio_doc.lines[0].seconds,.35)
        from v270_precision import load_draft
        self.assertIsNotNone(load_draft(self.track,self.lrc))
        with mock.patch.object(self.app,"_dialog",return_value=False):
            self.app._studio_save()
        self.assertFalse(list(Path(self.tmp.name).glob("*.candidate*.lrc")))

    def test_export_new_candidate_no_original_changes(self):
        self.app.studio_audio.set(str(self.track))
        self.app._studio_load_lyrics(self.lrc)
        original=(self.track.read_bytes(),self.lrc.read_bytes())
        self.app._v270_profile.set("Car radio UTF-8 BOM")
        with mock.patch.object(self.app,"_dialog",return_value=True):
            self.app._studio_save()
        p=self.track.with_suffix(".candidate.lrc")
        self.assertTrue(p.is_file())
        self.assertTrue(p.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertEqual(original,(self.track.read_bytes(),self.lrc.read_bytes()))

    def test_invalid_timing_blocks_save(self):
        self.app.studio_audio.set(str(self.track))
        self.app._studio_load_lyrics(self.lrc)
        self.app.studio_doc.set_time(1,.3)
        with mock.patch.object(self.app,"_dialog") as dialog:
            self.app._studio_save()
            self.assertTrue(dialog.called)
        self.assertFalse(list(Path(self.tmp.name).glob("*.candidate*.lrc")))

    def test_loop_and_clear(self):
        with mock.patch.object(self.app.studio_player,"position",side_effect=[.25,.8]):
            self.app._v270_set_a();self.app._v270_set_b()
        self.assertEqual(self.app.loop_a,.25)
        self.assertEqual(self.app.loop_b,.8)
        self.app._v270_clear_loop()
        self.assertIsNone(self.app.loop_a)

    def test_shortcut_collision_rejected(self):
        self.app._v270_keys["stamp"].set("<F6>")
        self.app._v270_keys["back"].set("<F6>")
        with mock.patch.object(self.app,"_dialog") as dialog:
            self.app._v270_apply_keys()
        self.assertTrue(dialog.called)

    def test_greek_and_english_labels_stable(self):
        self.app.language_choice.set("Ελληνικά")
        self.app._language_selected()
        self.assertEqual(self.app.studio_tabs.tab(self.app.precision_tab,"text"),"Ακρίβεια και Καραόκε")
        self.app.language_choice.set("English")
        self.app._language_selected()
        self.assertEqual(self.app.studio_tabs.tab(self.app.precision_tab,"text"),"Precision & Karaoke")

if __name__=="__main__": unittest.main(verbosity=2)
