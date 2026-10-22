"""User-level Tk Library Manager actions, on disposable music only."""
from __future__ import annotations
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock
import LRC_Control_Center as gui
from v250_manager import start_session,record_created_file
from v245_features import scan_library

def _display():
    if sys.platform=='win32':return True
    import tkinter as tk
    try:
        x=tk.Tk();x.withdraw();x.destroy();return True
    except tk.TclError:return False

@unittest.skipUnless(_display(),'Windows desktop or Xvfb required')
class V250LibraryManagerUI(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        e=mock.patch.dict(os.environ,{'APPDATA':self.temp.name})
        e.start();self.addCleanup(e.stop)
        self.root=Path(self.temp.name)/'music';self.root.mkdir()
        self.a=self.root/'Alpha.mp3';self.a.write_bytes(b'NO AUDIO MODIFICATION')
        self.b=self.root/'Beta.mp3';self.b.write_bytes(b'NEVER CHANGED')
        self.app=gui.ControlCenter();self.app.withdraw()
        self.addCleanup(self.app.destroy)
        self.app.folder.set(str(self.root))
        self.app.dashboard_all_rows=scan_library(self.root)
        self.app._dashboard_filter()

    def select_one(self):
        self.app.dashboard_tree.selection_set('0')

    def test_new_buttons_are_present(self):
        labels=[w.cget('text') for w in self.app._iter_ui_children(self.app)
                if w.winfo_class()=='TButton']
        for b in ['Retry selected tracks','Why was this rejected?','Undo last search session...']:
            self.assertIn(b,labels)

    def test_no_selection_never_starts_search(self):
        with mock.patch.object(self.app,'_dialog') as msg,mock.patch.object(self.app,'_run_profile') as run:
            self.app._manager_retry_selected()
            msg.assert_called_once();run.assert_not_called()

    def test_selective_retry_sends_only_exact_selection(self):
        self.select_one()
        selected=[]
        def run():
            from v250_manager import filter_selected_tracks
            selected.extend(filter_selected_tracks(self.root,[self.a,self.b],self.app._manager_selection_manifest))
        with mock.patch.object(self.app,'_dialog',return_value=True),mock.patch.object(self.app,'_run_profile',side_effect=run):
            self.app._manager_retry_selected()
        self.assertEqual(selected,[self.a])
        self.assertEqual(self.app._values()['provider_mode'],'full')
        self.assertEqual(self.app._values()['action'],'1')
        self.assertFalse(self.app._values()['history'])
        self.assertFalse(self.app._manager_selection_manifest)

    def test_user_cancel_never_creates_selection(self):
        self.select_one()
        with mock.patch.object(self.app,'_dialog',return_value=False),mock.patch.object(self.app,'_run_profile') as run:
            self.app._manager_retry_selected()
            run.assert_not_called()
        self.assertIsNone(self.app._manager_selection_manifest)

    def test_ambiguous_audio_cannot_retry(self):
        self.select_one();self.app.dashboard_all_rows[0]['status']='Ambiguous audio'
        self.app._dashboard_filter();self.select_one()
        with mock.patch.object(self.app,'_dialog') as dialog,mock.patch.object(self.app,'_run_profile') as run:
            self.app._manager_retry_selected()
            dialog.assert_called_once();run.assert_not_called()

    def test_session_undo_confirm_removes_only_created(self):
        sid=start_session(self.root,appdata=self.temp.name)
        target=self.a.with_suffix('.candidate.lrc');target.write_bytes(b'[00:00.00] candidate\n')
        record_created_file(target,session_id=sid,appdata=self.temp.name)
        with mock.patch.object(self.app,'_dialog',return_value=True), mock.patch.object(self.app,'_dashboard_refresh'):
            self.app._manager_undo()
        self.assertFalse(target.exists())
        self.assertEqual(self.a.read_bytes(),b'NO AUDIO MODIFICATION')
        self.assertEqual(self.b.read_bytes(),b'NEVER CHANGED')

    def test_session_undo_decline_keeps_all(self):
        sid=start_session(self.root,appdata=self.temp.name)
        target=self.a.with_suffix('.lrc');target.write_bytes(b'some lyrics')
        record_created_file(target,session_id=sid,appdata=self.temp.name)
        with mock.patch.object(self.app,'_dialog',return_value=False):self.app._manager_undo()
        self.assertTrue(target.exists())

    def test_session_undo_modified_candidate_kept(self):
        sid=start_session(self.root,appdata=self.temp.name)
        target=self.a.with_suffix('.candidate.lrc');target.write_bytes(b'candidate')
        record_created_file(target,session_id=sid,appdata=self.temp.name)
        target.write_bytes(b'USER EDITS')
        with mock.patch.object(self.app,'_dialog'):
            self.app._manager_undo()
        self.assertEqual(target.read_bytes(),b'USER EDITS')

    def test_greek_controls_and_english_restore(self):
        self.app.language_choice.set('Ελληνικά');self.app._language_selected()
        labels=[w.cget('text') for w in self.app._iter_ui_children(self.app)
                if w.winfo_class()=='TButton']
        self.assertIn('Επανάληψη επιλεγμένων τραγουδιών',labels)
        self.app.language_choice.set('English');self.app._language_selected()
        labels=[w.cget('text') for w in self.app._iter_ui_children(self.app)
                if w.winfo_class()=='TButton']
        self.assertIn('Retry selected tracks',labels)

    def test_why_rejected_explains_old_report_not_live_provider(self):
        import csv
        report=self.root/'LRC_Finder_Report_v2_1_15.csv'
        with report.open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.writer(f);writer.writerow(['MP3 path','round','status','reason','saved provider','provider outcomes']);writer.writerow([str(self.a),1,'NOT_FOUND','recording version differs','','LRCLIB=NO_MATCH'])
        self.select_one();self.app._manager_explain()
        limit=time.monotonic()+4
        while time.monotonic()<limit:
            self.app.update()
            if 'recording version differs' in self.app.manager_reason.get('1.0','end'):break
            time.sleep(.03)
        self.assertIn('recording version differs',self.app.manager_reason.get('1.0','end'))

if __name__=='__main__':unittest.main(verbosity=2)
