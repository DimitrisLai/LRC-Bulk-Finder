"""v2.4.5 GUI user journeys on disposable music files. Never contact providers."""
import os
import sys
import time
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import LRC_Control_Center as gui


def display():
    if sys.platform=='win32':return True
    import tkinter as tk
    try:
        t=tk.Tk();t.withdraw();t.destroy();return True
    except tk.TclError:return False


@unittest.skipUnless(display(),'Windows desktop or virtual X display required')
class V245GuiJourneys(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env=mock.patch.dict(os.environ,{'APPDATA':self.tmp.name})
        self.env.start();self.addCleanup(self.env.stop)
        self.music=Path(self.tmp.name)/'music';self.music.mkdir()
        self.track=self.music/'Test.mp3';self.track.write_bytes(b'ORIGINAL AUDIO')
        self.lrc=self.music/'Test.lrc';self.lrc.write_text('[00:02.00] Hello\n[00:04.00] World\n',encoding='utf-8')
        self.app=gui.ControlCenter();self.app.withdraw()
        self.addCleanup(self.app.destroy)
        self.app.folder.set(str(self.music))

    def test_eight_tabs_open(self):
        tabs=self.app.notebook.tabs()
        self.assertEqual(len(tabs),8)
        for tab in tabs:
            self.app.notebook.select(tab)
            self.assertEqual(self.app.notebook.select(),tab)

    def test_quick_button_saves_expected_safe_settings(self):
        self.app.quick_scope.set('20')
        self.app.quick_greek.set(True)
        self.app.quick_include_subfolders.set(False)
        with mock.patch.object(self.app,'_run_profile') as run:
            self.app._quick_start()
            run.assert_called_once()
        self.assertEqual(self.app.name.get(),'Quick Search v2.4.5')
        v=self.app._values()
        self.assertEqual(v['action'],'1')
        self.assertEqual(v['provider_mode'],'fast')
        self.assertEqual(v['limit'],'20')
        self.assertTrue(v['greek'])
        self.assertFalse(v['recursive'])
        self.assertFalse(v['local_ai'])
        self.assertFalse(v['experimental_simpmusic'])

    def test_quick_all_songs_no_db(self):
        self.app.quick_scope.set('a')
        with mock.patch.object(self.app,'_run_profile'):
            self.app._quick_start()
        self.assertEqual(self.app._values()['limit'],'a')
        self.assertFalse(self.app.database.get())

    def test_quick_invalid_folder_does_not_start(self):
        self.app.folder.set(str(self.music/'absent'))
        with mock.patch.object(self.app,'_dialog',return_value=None) as dialog,\
             mock.patch.object(self.app,'_run_profile') as run:
            self.app._quick_start()
            dialog.assert_called_once()
            run.assert_not_called()

    def test_dashboard_scan_does_not_write_to_music(self):
        initial={p.name:p.read_bytes() for p in self.music.iterdir()}
        self.app._dashboard_refresh()
        deadline=time.monotonic()+5
        while self.app._dashboard_scanning and time.monotonic()<deadline:
            self.app.update();time.sleep(.02)
        self.assertFalse(self.app._dashboard_scanning)
        self.assertEqual(len(self.app.dashboard_all_rows),1)
        self.assertEqual(self.app.dashboard_all_rows[0]['status'],'Has LRC')
        self.assertEqual(initial,{p.name:p.read_bytes() for p in self.music.iterdir()})

    def test_dashboard_filter_status_and_name(self):
        self.app.dashboard_all_rows=[
            {'path':'C:/music/A.mp3','name':'A.mp3','folder':'C:/music','status':'Missing LRC','candidates':0},
            {'path':'C:/music/B.mp3','name':'B.mp3','folder':'C:/music','status':'Has LRC','candidates':0}]
        self.app.dashboard_state.set('Missing LRC')
        self.app._dashboard_filter()
        self.assertEqual(len(self.app.dashboard_visible_rows),1)
        self.app.dashboard_query.set('unmatched')
        self.assertEqual(len(self.app.dashboard_visible_rows),0)
        self.app.dashboard_query.set('A.mp3')
        self.assertEqual(len(self.app.dashboard_visible_rows),1)

    def test_dashboard_fully_translated_and_filter_works(self):
        self.app.language_choice.set('Ελληνικά');self.app._language_selected()
        self.assertIn('Πίνακας',self.app.notebook.tab(self.app.dashboard_tab,'text'))
        self.assertEqual(self.app.dashboard_state.get(),'Όλες οι καταστάσεις')
        self.app.dashboard_state.set('Δεν υπάρχει LRC')
        self.app.dashboard_all_rows=[{'path':'C:/m/A.mp3','name':'A.mp3','folder':'C:/m','status':'Missing LRC','candidates':0}]
        self.app._dashboard_filter()
        self.assertEqual(len(self.app.dashboard_visible_rows),1)
        self.app.language_choice.set('English');self.app._language_selected()
        self.assertEqual(self.app.dashboard_state.get(),'Missing LRC')

    def test_diagnostics_refuse_overwrite(self):
        target=self.music/'d.txt';target.write_text('do not overwrite')
        with mock.patch.object(self.app,'_file_dialog',return_value=str(target)),\
             mock.patch.object(self.app,'_dialog',return_value=True) as dialog:
            self.app._diagnostics()
            self.assertEqual(target.read_text(),'do not overwrite')
            self.assertTrue(any(x.args[0]=='showerror' for x in dialog.call_args_list))

    def test_update_check_explicit_only(self):
        self.assertIsNone(self.app.update_page)
        with mock.patch('v245_gui.check_github_update',return_value={'newer':True,'latest':'v2.4.6',
             'url':'https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/tag/v2.4.6'}):
            self.app._check_update()
            deadline=time.monotonic()+2
            while self.app._v245_queue.empty() and time.monotonic()<deadline:time.sleep(.02)
            self.app._poll_v245()
        self.assertIn('v2.4.6',self.app.update_notice.get())
        self.assertEqual(str(self.app.update_open_button.cget('state')),'normal')

    def test_timing_preview_and_save_safe_separate_candidate(self):
        self.app.repair_audio.set(str(self.track))
        self.app.repair_lrc.set(str(self.lrc))
        self.app.repair_offset.set('1.50')
        self.app._repair_preview()
        self.assertIn('[00:03.50] Hello',self.app.repair_preview_value)
        with mock.patch.object(self.app,'_dialog',return_value=True):self.app._repair_save()
        candidate=self.music/'Test.candidate.lrc'
        self.assertTrue(candidate.is_file())
        self.assertEqual(self.lrc.read_text(),'[00:02.00] Hello\n[00:04.00] World\n')
        self.assertEqual(self.track.read_bytes(),b'ORIGINAL AUDIO')
        self.assertTrue(candidate.read_text().startswith('[00:00.00] candidate'))

    def test_timing_change_after_preview_requires_new_preview(self):
        self.app.repair_audio.set(str(self.track));self.app.repair_lrc.set(str(self.lrc))
        self.app.repair_offset.set('1')
        self.app._repair_preview()
        self.app.repair_offset.set('2')
        with mock.patch.object(self.app,'_dialog',return_value=True) as dialog:
            self.app._repair_save()
            self.assertTrue(any(x.args[0]=='showerror' for x in dialog.call_args_list))
        self.assertFalse((self.music/'Test.candidate.lrc').exists())

    def test_save_does_not_replace_existing_lrc(self):
        self.app.repair_audio.set(str(self.track));self.app.repair_lrc.set(str(self.lrc))
        self.app.repair_offset.set('1')
        self.app._repair_preview()
        (self.music/'Test.candidate.lrc').write_text('PRESERVE ME')
        with mock.patch.object(self.app,'_dialog',return_value=True):self.app._repair_save()
        self.assertEqual((self.music/'Test.candidate.lrc').read_text(),'PRESERVE ME')
        self.assertTrue((self.music/'Test.candidate.2.lrc').is_file())


if __name__=='__main__':unittest.main(verbosity=2)
