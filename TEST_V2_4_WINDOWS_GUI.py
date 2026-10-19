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
                    self.assertTrue(gui._save())
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

if __name__=="__main__":
    unittest.main(verbosity=2)
