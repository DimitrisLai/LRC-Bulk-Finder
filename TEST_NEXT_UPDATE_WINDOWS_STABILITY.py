"""Regressions for real Windows unicode-hyphen crash and unavailable local AI.

All audio fixtures are synthetic / no network calls. Original music untouched.
"""
from __future__ import annotations
import io
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.modules.setdefault("syncedlyrics",types.SimpleNamespace(search=lambda *a,**kw:None))
import run_saved_profile
import search_profiles


class WorkerUnicodeTests(unittest.TestCase):
    def test_utf8_stdout_survives_windows_cp1252_hyphen_greek_paths(self):
        output = io.BytesIO()
        narrow = io.TextIOWrapper(output,encoding="cp1252",errors="strict",
                                  write_through=True)
        example = "16‐ 2 Brothers ‐ Ελλάδα ‐ σοφία.mp3"  # U+2010, Greek text
        with mock.patch.object(sys,"stdout",narrow):
            with self.assertRaises(UnicodeEncodeError):
                print(example)
            run_saved_profile.configure_console_output()
            print(example,flush=True)
            self.assertEqual(sys.stdout.encoding.lower().replace("-",""),"utf8")
        self.assertIn(example.encode("utf-8"),output.getvalue())

    def test_unconfigurable_stdout_does_not_crash_worker_boot(self):
        sink=io.StringIO()
        with mock.patch.object(sys,"stdout",sink):
            run_saved_profile.configure_console_output()
            print("Unicode ‐ Καλημέρα",flush=True)
        self.assertIn("Καλημέρα",sink.getvalue())

    def test_frozen_old_ai_profile_falls_back_without_changing_saved_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            music=base/"Αρχεία ‐ Music"
            music.mkdir()
            profiles=base/"profiles.json"
            data=search_profiles.preset_profile("Greek Local AI — FULL",folder=str(music))
            search_profiles.save_profiles({"old AI":data},profiles)
            before=profiles.read_bytes()
            with mock.patch.object(sys,"frozen",True,create=True),\
                 mock.patch("LRC_Bulk_Finder.main") as search,\
                 mock.patch("run_saved_profile.check_stop"):
                run_saved_profile.run_profile("old AI",profiles)
                search.assert_called_once()
            self.assertEqual(before,profiles.read_bytes())
            self.assertTrue(search_profiles.load_profiles(profiles)["old AI"]["local_ai"])

    def test_readonly_profile_baseline_does_not_enable_ai_when_frozen(self):
        from LRC_Control_Center import ControlCenter
        with mock.patch.object(sys,"frozen",True,create=True),\
             mock.patch("g2g_auto.installed",return_value=None):
            instance=object.__new__(ControlCenter)
            names=ControlCenter._available_preset_names(instance)
            self.assertNotIn("Greek Local AI — FULL",names)
            self.assertIn("Greek FULL — Offline First",names)
        with mock.patch.object(sys,"frozen",False,create=True):
            names=ControlCenter._available_preset_names(instance)
            self.assertIn("Greek Local AI — FULL",names)


def display_available():
    if sys.platform=="win32":return True
    try:
        import tkinter as tk
        window=tk.Tk()
        window.withdraw()
        window.destroy()
        return True
    except Exception:return False


@unittest.skipUnless(display_available(),"No graphical display available")
class GuiNoSurpriseTests(unittest.TestCase):
    def setUp(self):
        from LRC_Control_Center import ControlCenter
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env=mock.patch.dict(os.environ,{"APPDATA":self.temp.name})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.app=ControlCenter()
        self.app.withdraw()
        self.addCleanup(self.app.destroy)
        folder=Path(self.temp.name)/"music"
        folder.mkdir()
        self.app.folder.set(str(folder))

    def test_builtin_name_with_incorrect_settings_cannot_silently_run_all(self):
        app=self.app
        app.name.set("International FAST — 20 Songs")
        app.action.set("5")
        app.limit.set("a")
        app.boolvars["greek"].set(False)
        app.provider_mode.set("fast")
        with mock.patch.object(app,"_dialog",return_value=False) as dialog,\
             mock.patch.object(app,"_save") as save:
            app._run_profile()
            save.assert_not_called()
            self.assertTrue(any(call.args[0]=="askyesno" and
                call.args[1]=="Preset settings differ" for call in dialog.call_args_list))
        self.assertEqual(app.action.get(),"5")
        self.assertEqual(app.limit.get(),"a")

    def test_user_can_restore_named_20_song_fast_scope(self):
        app=self.app
        app.name.set("International FAST — 20 Songs")
        app.action.set("5")
        app.limit.set("a")
        app.boolvars["greek"].set(False)
        app.provider_mode.set("fast")
        with mock.patch.object(app,"_dialog",return_value=True),\
             mock.patch.object(app,"_save",return_value=False):
            app._run_profile()
        self.assertEqual(app.action.get(),"1")
        self.assertEqual(app.limit.get(),"20")
        self.assertFalse(app.boolvars["greek"].get())

    def test_old_local_ai_config_is_sanitized_if_frozen(self):
        app=self.app
        candidate={**search_profiles.DEFAULT,
                   **search_profiles.PRESET_TEMPLATES["Greek Local AI — FULL"],
                   "folder":app.folder.get()}
        with mock.patch.object(sys,"frozen",True,create=True):
            app._set_values(candidate)
        self.assertFalse(app.boolvars["local_ai"].get())

    def test_gui_notifies_nonzero_worker_exit_instead_of_success(self):
        # The completion label must never report success after a code-2 worker.
        from LRC_Control_Center import ControlCenter
        self.app.messages.put(("ended",2))
        with mock.patch.object(self.app,"_refresh_review"):
            self.app._poll()
        self.assertIn("stopped unexpectedly",self.app.phase.get())


if __name__=="__main__":
    unittest.main()
