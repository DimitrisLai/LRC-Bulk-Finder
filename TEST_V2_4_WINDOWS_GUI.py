"""Windows Tk widget smoke tests for v2.4. No network, installer or real music changes."""
import os
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

@unittest.skipUnless(os.name=="nt","Requires a Windows desktop/Tk display")
class WindowsGuiV24Tests(unittest.TestCase):
    def test_presets_hover_setup_buttons_and_sync_lab_real_wav(self):
        from LRC_Control_Center import ControlCenter
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            wav=base/"Singer - Testing.wav"
            with wave.open(str(wav),"wb") as audio:
                audio.setnchannels(1);audio.setsampwidth(2)
                audio.setframerate(8000);audio.writeframes(b"\x00\x00"*16000)
            before=wav.read_bytes()
            with mock.patch.dict(os.environ,{"APPDATA":d}):
                gui=ControlCenter()
                gui.withdraw()
                try:
                    gui.folder.set(d)
                    gui.database.set(str(base/"existing.sqlite3"))
                    gui.preset_name.set("Greek Night Search — Maximum Coverage")
                    gui._apply_preset()
                    self.assertTrue(gui.boolvars["recovery_wait"].get())
                    self.assertTrue(gui.boolvars["incremental"].get())
                    self.assertEqual(gui.limit.get(),"a")
                    self.assertEqual(gui.action.get(),"5")
                    with mock.patch("tkinter.messagebox.showerror") as error_dialog:
                        self.assertTrue(gui._save())
                        error_dialog.assert_not_called()
                    gui._refresh_profiles()
                    self.assertIn("Greek Night Search — Maximum Coverage",gui.loaded_profiles)
                    gui.preset_name.set("Greek OFFLINE ONLY")
                    gui._apply_preset()
                    self.assertFalse(gui.boolvars["musicbrainz"].get())
                    self.assertEqual(gui.action.get(),"4")
                    with mock.patch("tkinter.messagebox.askyesno",return_value=True),\
                         mock.patch("subprocess.Popen") as launch:
                        gui._launch_setup("SETUP_LRCLIB_DATABASE.cmd")
                        launch.assert_called_once()
                    gui.sync_audio.set(str(wav))
                    gui.sync_source.insert("1.0","One line\nSecond line\nThird line\n")
                    with mock.patch("tkinter.messagebox.showerror") as err:
                        gui._sync_estimate()
                        err.assert_not_called()
                    self.assertIn("[00:00.00] candidate",gui.sync_draft.get("1.0","end"))
                    self.assertEqual(len(gui.sync_times),3)
                    with mock.patch("tkinter.messagebox.askyesno",return_value=True),\
                         mock.patch("tkinter.messagebox.showinfo"):
                        gui._sync_save()
                    self.assertTrue(wav.with_suffix(".candidate.lrc").is_file())
                    self.assertEqual(wav.read_bytes(),before)
                    gui._refresh_review()
                    self.assertEqual(len(gui.review_rows),1)
                finally:gui.destroy()

    def test_stop_button_creates_real_stop_marker_and_force_stop_is_explicit(self):
        from LRC_Control_Center import ControlCenter
        with tempfile.TemporaryDirectory() as td:
            gui=ControlCenter()
            gui.withdraw()
            try:
                child=mock.Mock()
                child.poll.return_value=None
                gui.process=child
                marker=Path(td)/"stop.request"
                gui.stop_directory=Path(td)
                gui.stop_path=marker
                with mock.patch("tkinter.messagebox.askyesno",return_value=True):
                    gui._stop()
                self.assertTrue(marker.is_file(), "Stop button must send an IPC marker")
                self.assertEqual(marker.read_text(encoding="utf-8"),"STOP\n")
                self.assertTrue(gui.stop_requested)
                self.assertEqual(str(gui.stop_button.cget("state")),"disabled")
                gui._enable_force_stop(child)
                self.assertEqual(str(gui.stop_button.cget("state")),"normal")
                self.assertIn("Force STOP",gui.stop_button.cget("text"))
                with mock.patch("tkinter.messagebox.askyesno",return_value=True):
                    gui._stop()
                child.kill.assert_called_once()
                gui._line("STAGE COUNTERS: stage=1 found=2 candidate=1 not_found=3 total_found=2 total_candidate=1")
                self.assertEqual([gui.counter_vars[k].get() for k in
                                 ("found","candidate","not_found","total_found","total_candidate")],
                                 ["2","1","3","2","1"])
                gui._line("STAGE COUNTERS: stage=2 found=0 candidate=0 not_found=0 total_found=2 total_candidate=1")
                self.assertEqual([gui.counter_vars[k].get() for k in
                                 ("found","candidate","not_found","total_found","total_candidate")],
                                 ["0","0","0","2","1"])
            finally:
                gui.process=None
                gui.stop_directory=None
                gui.stop_path=None
                gui.destroy()

if __name__=="__main__":
    unittest.main(verbosity=2)
