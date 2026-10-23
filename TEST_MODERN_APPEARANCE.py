"""Regression coverage for the v2.9.5 appearance-only refresh.

No internet, filesystem music modifications, or provider requests. Tests validate
theme persistence, bilingual switches, accessibility contrast, profile integrity
and the visibility of the advanced form's Start Search button.
"""
from __future__ import annotations
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ui_appearance import PALETTES,read_mode,save_mode
from ui_locale import read_language,save_language


def luminance(hex_color):
    parts=[int(hex_color[i:i+2],16)/255 for i in (1,3,5)]
    rgb=[p/12.92 if p<=0.04045 else ((p+0.055)/1.055)**2.4 for p in parts]
    return 0.2126*rgb[0]+0.7152*rgb[1]+0.0722*rgb[2]


def contrast(a,b):
    values=sorted([luminance(a),luminance(b)],reverse=True)
    return (values[0]+0.05)/(values[1]+0.05)


class AppearanceSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="ui-theme-test")
        self.addCleanup(self.temp.cleanup)
        self.file=Path(self.temp.name)/"settings.json"

    def test_default_and_bad_settings(self):
        self.assertEqual(read_mode(self.file),"light")
        self.file.write_text("not JSON",encoding="utf-8")
        self.assertEqual(read_mode(self.file),"light")
        self.file.write_text('{"appearance":"nonexistent"}',encoding="utf-8")
        self.assertEqual(read_mode(self.file),"light")

    def test_save_mode_does_not_remove_language(self):
        save_language("el",self.file)
        save_mode("dark",self.file)
        self.assertEqual(read_language(self.file),"el")
        self.assertEqual(read_mode(self.file),"dark")
        save_language("en",self.file)
        self.assertEqual(read_mode(self.file),"dark")
        self.assertEqual(read_language(self.file),"en")

    def test_change_theme_keeps_future_settings(self):
        self.file.write_text(json.dumps({"schema":1,"appearance":"light",
                                        "extra_setting":"keep me"}),encoding="utf-8")
        save_mode("dark",self.file)
        self.assertEqual(json.loads(self.file.read_text(encoding="utf-8"))["extra_setting"],"keep me")
        save_language("el",self.file)
        self.assertEqual(json.loads(self.file.read_text(encoding="utf-8"))["extra_setting"],"keep me")

    def test_invalid_theme_never_modifies_config(self):
        self.file.write_text('{"interface_language":"el"}',encoding="utf-8")
        original=self.file.read_bytes()
        with self.assertRaises(ValueError):
            save_mode("invalid",self.file)
        self.assertEqual(self.file.read_bytes(),original)

    def test_text_contrast_on_surfaces_and_logs(self):
        for name,p in PALETTES.items():
            with self.subTest(theme=name):
                self.assertGreaterEqual(contrast(p["text"],p["surface"]),4.5)
                self.assertGreaterEqual(contrast(p["subtext"],p["surface"]),4.5)
                self.assertGreaterEqual(contrast(p["log_fg"],p["log_bg"]),4.5)
                self.assertGreaterEqual(contrast(p["accent_text"],p["accent"]),4.5)


def has_display():
    if os.name=="nt":return True
    try:
        import tkinter as tk
        app=tk.Tk()
        app.withdraw()
        app.destroy()
        return True
    except Exception:
        return False


@unittest.skipUnless(has_display(),"Graphical display unavailable")
class AppearanceGuiTests(unittest.TestCase):
    def setUp(self):
        from LRC_Control_Center import ControlCenter
        self.temp=tempfile.TemporaryDirectory(prefix="lrc-ui-display")
        self.addCleanup(self.temp.cleanup)
        self.config=mock.patch.dict(os.environ,{"APPDATA":self.temp.name})
        self.config.start()
        self.addCleanup(self.config.stop)
        self.root=ControlCenter()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)

    def test_all_original_tabs_and_callbacks_remain(self):
        app=self.root
        self.assertEqual(len(app.notebook.tabs()),8)
        self.assertEqual(len(app.studio_tabs.tabs()),5)
        self.assertTrue(callable(app._run_profile))
        self.assertTrue(callable(app._install_g2g))
        self.assertTrue(callable(app._stop))
        self.assertEqual(str(app.search_start_button.cget("style")),"Primary.TButton")
        self.assertEqual(str(app.stop_button.cget("style")),"Danger.TButton")
        self.assertTrue(hasattr(app,"profiles_canvas"))

    def test_light_dark_switch_does_not_modify_search_fields_or_selected_tab(self):
        app=self.root
        app.name.set("My private profile")
        app.limit.set("20")
        app.folder.set("C:/music/Αθήνα ‐ demo")
        app.notebook.select(app.run_tab)
        original_tab=app.notebook.select()
        app.appearance_choice.set("Dark")
        app._appearance_selected()
        self.assertEqual(app.appearance_mode,"dark")
        self.assertEqual(app.name.get(),"My private profile")
        self.assertEqual(app.folder.get(),"C:/music/Αθήνα ‐ demo")
        self.assertEqual(app.limit.get(),"20")
        self.assertEqual(app.notebook.select(),original_tab)
        self.assertEqual(read_mode(),"dark")
        app.appearance_choice.set("Light")
        app._appearance_selected()
        self.assertEqual(read_mode(),"light")

    def test_greek_english_theme_switch_is_reversible(self):
        app=self.root
        app.appearance_choice.set("Dark")
        app._appearance_selected()
        app.language_choice.set("Ελληνικά")
        app._language_selected()
        self.assertEqual(app.appearance_choice.get(),"Σκοτεινό")
        self.assertEqual(read_mode(),"dark")
        self.assertEqual(read_language(),"el")
        app.appearance_choice.set("Φωτεινό")
        app._appearance_selected()
        self.assertEqual(read_mode(),"light")
        app.language_choice.set("English")
        app._language_selected()
        self.assertEqual(app.appearance_choice.get(),"Light")
        self.assertEqual(read_mode(),"light")

    def test_theme_change_does_not_clear_logs_or_start_search(self):
        app=self.root
        app.log.configure(state="normal")
        app.log.insert("end","Found: Αθήνα ‐ 20 matches")
        app.log.configure(state="disabled")
        with mock.patch.object(app,"_run_profile") as run:
            app.appearance_choice.set("Dark")
            app._appearance_selected()
            app.appearance_choice.set("Light")
            app._appearance_selected()
            run.assert_not_called()
        self.assertIn("Αθήνα",app.log.get("1.0","end"))
        self.assertEqual(str(app.log.cget("state")),"disabled")

    def test_advanced_page_scrollregion_and_start_button_still_exist(self):
        app=self.root
        app.notebook.select(app.search_tab)
        app.update_idletasks()
        region=str(app.profiles_canvas.cget("scrollregion"))
        self.assertTrue(region)
        self.assertTrue(app.search_start_button.winfo_exists())
        self.assertEqual(len(app.preset_choice.cget("values")),15)

    def test_restart_restores_theme_and_language_without_rebuild(self):
        from LRC_Control_Center import ControlCenter
        app=self.root
        app.appearance_choice.set("Dark")
        app._appearance_selected()
        app.language_choice.set("Ελληνικά")
        app._language_selected()
        reopened=ControlCenter()
        reopened.withdraw()
        self.addCleanup(reopened.destroy)
        self.assertEqual(reopened.appearance_mode,"dark")
        self.assertEqual(reopened.gui_locale.language,"el")
        self.assertEqual(len(reopened.notebook.tabs()),8)


if __name__=="__main__":
    unittest.main()
