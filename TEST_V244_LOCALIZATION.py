"""QA: approved Greek GUI localization must not change music/search machinery."""
from __future__ import annotations
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ui_translations import UI_EL
from ui_locale import GuiLocale,read_language,save_language,PATTERNS
import LRC_Control_Center as gui

class CatalogAndPreferences(unittest.TestCase):
    def test_266_approved_strings_have_two_nonblank_languages(self):
        self.assertEqual(len(UI_EL),265) # 266 reviewed rows; one source phrase occurs twice
        for en,el in UI_EL.items():
            self.assertTrue(en.strip())
            self.assertTrue(el.strip())

    def test_all_strings_are_translated_and_plain_english_restored(self):
        el=GuiLocale('el'); en=GuiLocale('en')
        for source,result in UI_EL.items():
            if '{' not in source:self.assertEqual(el.tr(source),result)
            self.assertEqual(en.tr(source),source)
        self.assertEqual(el.tr('NO_MATCH'),'NO_MATCH')
        self.assertEqual(el.tr('my-library.flac'),'my-library.flac')

    def test_dynamic_placeholder_and_file_safety(self):
        trans=GuiLocale('el')
        msg='Delete saved settings for MyProfile? No music files are affected.'
        self.assertEqual(trans.tr(msg), 'Να διαγραφούν οι αποθηκευμένες ρυθμίσεις του «MyProfile»; Κανένα αρχείο μουσικής δεν θα επηρεαστεί.')
        confirm='Resume saved profile Old?\n\nCompleted matching checkpoints will be reused; unfinished work retried.'
        self.assertIn('Old',trans.tr(confirm))
        self.assertNotEqual(trans.tr(confirm),confirm)

    def test_file_location_atomic_save_and_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'c'/'ui_settings.json'
            self.assertEqual(read_language(p),'en')
            save_language('el',p)
            self.assertEqual(read_language(p),'el')
            save_language('en',p)
            self.assertEqual(read_language(p),'en')
            p.write_text('{broken',encoding='utf-8')
            self.assertEqual(read_language(p),'en')
            self.assertRaises(ValueError,save_language,'fr',p)
            self.assertEqual(read_language(p),'en')

class WindowsGuiLocalization(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.settings=mock.patch.dict(os.environ,{'APPDATA':self.temp.name})
        self.settings.start()
        self.app=gui.ControlCenter()
        self.app.withdraw()

    def tearDown(self):
        self.app.destroy()
        self.settings.stop()
        self.temp.cleanup()

    def set_language(self,language):
        self.app.language_choice.set('Ελληνικά' if language=='el' else 'English')
        self.app._language_selected()
        self.app.update_idletasks()

    def test_initial_state_is_english(self):
        self.assertEqual(self.app.gui_locale.language,'en')
        self.assertIn('Control Center',self.app.title())
        self.assertEqual(self.app.notebook.tab(self.app.search_tab,'text').strip(),'Saved searches')

    def test_switch_tabs_button_headings_and_back_without_rebuild(self):
        before=self.app.search_tab
        self.set_language('el')
        self.assertIs(self.app.search_tab,before)
        self.assertEqual(self.app.notebook.tab(self.app.search_tab,'text').strip(),'Αποθηκευμένες αναζητήσεις')
        self.assertEqual(self.app.health_tree.heading('provider','text'),'Πηγή')
        buttons=[w for w in self.app._iter_ui_children(self.app) if hasattr(w,'cget') and w.winfo_class()=='TButton']
        self.assertIn('Αποθήκευση', [w.cget('text') for w in buttons])
        self.set_language('en')
        self.assertEqual(self.app.notebook.tab(self.app.search_tab,'text').strip(),'Saved searches')
        self.assertIn('Save',[w.cget('text') for w in buttons])
        self.assertEqual(self.app.health_tree.heading('provider','text'),'Provider')

    def test_saved_search_preferences_unchanged_on_switch(self):
        self.app.folder.set('D:/My Music/test')
        self.app.action.set('1')
        self.app.provider_mode.set('fast')
        self.app.boolvars['experimental_simpmusic'].set(True)
        before=self.app._values()
        self.set_language('el')
        self.assertEqual(self.app._values(),before)
        self.set_language('en')
        self.assertEqual(self.app._values(),before)

    def test_presets_are_localized_but_internal_keys_remain_english(self):
        english=list(gui.PRESET_TEMPLATES)[0]
        self.app.preset_name.set(english)
        self.set_language('el')
        translated=self.app.preset_name.get()
        self.assertNotEqual(translated,english)
        self.assertEqual(self.app._preset_key(translated),english)
        self.app._apply_preset()
        self.assertEqual(self.app.name.get(),english)
        self.set_language('en')
        self.assertEqual(self.app.preset_name.get(),english)

    def test_dialogs_translate_but_preserve_return_values(self):
        self.set_language('el')
        with mock.patch('tkinter.messagebox.askyesno',return_value=True) as dialog:
            self.assertTrue(self.app._dialog('askyesno','Delete profile',
                            'Delete saved settings for MyProfile? No music files are affected.'))
            self.assertIn('MyProfile',dialog.call_args.args[1])
            self.assertNotIn('Delete saved settings',dialog.call_args.args[1])

    def test_tooltips_and_status_variables_switch_live(self):
        self.set_language('el')
        self.app.sync_status.set('No timings generated. All results are unverified.')
        self.assertEqual(self.app.sync_status.get(),UI_EL['No timings generated. All results are unverified.'])
        for child in self.app._iter_ui_children(self.app):
            if hasattr(child,'_lrc_original_tooltip'):
                self.assertEqual(child._lrc_tooltip.message,self.app._tr(child._lrc_original_tooltip))
        self.set_language('en')
        self.assertEqual(self.app.sync_status.get(),'No timings generated. All results are unverified.')

    def test_restart_recalls_stored_language(self):
        self.set_language('el')
        self.app.destroy()
        self.app=gui.ControlCenter()
        self.app.withdraw()
        self.assertEqual(self.app.gui_locale.language,'el')
        self.assertEqual(self.app.notebook.tab(self.app.search_tab,'text').strip(),'Αποθηκευμένες αναζητήσεις')

if __name__=='__main__':unittest.main(verbosity=2)
