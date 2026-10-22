"""Adversarial tests for v2.5.0 manager: no unintended file removal/search."""
import csv
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import v250_manager as m

class ManagerSafety(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'music';self.root.mkdir()
        self.user=Path(self.temp.name)/'appdata';self.user.mkdir()
        self.audio=self.root/'One.mp3';self.audio.write_bytes(b'mp3 untouched')

    def _created(self,name='One.lrc',body=b'[00:01.00] a\n'):
        p=self.root/name;p.write_bytes(body)
        sid=m.start_session(self.root,appdata=self.user)
        self.assertTrue(m.record_created_file(p,session_id=sid,appdata=self.user))
        return sid,p

    def test_undo_recorded_verified_sidecar_only(self):
        sid,p=self._created()
        out=m.undo_session(sid,expected_root=self.root,appdata=self.user)
        self.assertEqual(out['removed'],[p]);self.assertFalse(p.exists())
        self.assertEqual(self.audio.read_bytes(),b'mp3 untouched')
        self.assertFalse(m.session_entries(sid,expected_root=self.root,appdata=self.user)[0]['eligible'])
        self.assertEqual(m.undo_session(sid,expected_root=self.root,appdata=self.user)['removed'],[])

    def test_undo_candidate_only_not_original_existing_lrc(self):
        self.root.joinpath('One.lrc').write_bytes(b'old original')
        sid,p=self._created('One.candidate.2.lrc')
        self.assertEqual(len(m.undo_session(sid,expected_root=self.root,appdata=self.user)['removed']),1)
        self.assertEqual(self.root.joinpath('One.lrc').read_bytes(),b'old original')

    def test_undo_refuses_modified_file(self):
        sid,p=self._created();p.write_bytes(b'user edits')
        self.assertEqual(m.undo_session(sid,expected_root=self.root,appdata=self.user)['removed'],[])
        self.assertEqual(p.read_bytes(),b'user edits')

    def test_undo_refuses_same_size_modified_content(self):
        sid,p=self._created();p.write_bytes(b'changed!!!!!')
        self.assertFalse(m.session_entries(sid,expected_root=self.root,appdata=self.user)[0]['eligible'])

    def test_undo_refuses_same_bytes_modified_timestamp(self):
        sid,p=self._created();os.utime(p,ns=(p.stat().st_atime_ns,p.stat().st_mtime_ns+1_000_000))
        self.assertEqual(m.undo_session(sid,expected_root=self.root,appdata=self.user)['removed'],[])

    def test_undo_refuses_cross_library(self):
        sid,p=self._created();other=Path(self.temp.name)/'other';other.mkdir()
        with self.assertRaises(ValueError):m.undo_session(sid,expected_root=other,appdata=self.user)
        self.assertTrue(p.exists())

    def test_undo_refuses_untracked_file_and_audio(self):
        sid,p=self._created();track=self.root/'stray.lrc';track.write_bytes(b'untouched')
        self.assertEqual(len(m.undo_session(sid,expected_root=self.root,appdata=self.user)['removed']),1)
        self.assertTrue(track.is_file());self.assertTrue(self.audio.is_file())

    def test_session_find_last_and_id_is_unguessable(self):
        sid,p=self._created();self.assertEqual(len(sid),32)
        self.assertEqual(m.latest_session(self.root,appdata=self.user),sid)
        with self.assertRaises(ValueError):m.session_entries('../../secret',appdata=self.user)

    def test_session_refuses_symlink_file(self):
        sid=m.start_session(self.root,appdata=self.user)
        p=self.root/'One.lrc'
        try:p.symlink_to(self.audio)
        except (OSError,NotImplementedError):self.skipTest('symlink unavailable')
        with self.assertRaises(ValueError):m.record_created_file(p,session_id=sid,appdata=self.user)

    def test_manifest_selects_exact_order_only(self):
        second=self.root/'Two.mp3';second.write_bytes(b'audio')
        path=m.make_selection_manifest(self.root,[second,self.audio])
        self.addCleanup(lambda:path.unlink(missing_ok=True))
        self.assertEqual(m.filter_selected_tracks(self.root,[self.audio,second],path),[second,self.audio])

    def test_manifest_invalid_folder_never_falls_back_full_search(self):
        path=m.make_selection_manifest(self.root,[self.audio])
        self.addCleanup(lambda:path.unlink(missing_ok=True))
        other=Path(self.temp.name)/'different';other.mkdir()
        with self.assertRaises(ValueError):m.filter_selected_tracks(other,[self.audio],path)

    def test_manifest_missing_track_never_falls_back(self):
        path=m.make_selection_manifest(self.root,[self.audio]);self.audio.unlink()
        self.addCleanup(lambda:path.unlink(missing_ok=True))
        with self.assertRaises(ValueError):m.filter_selected_tracks(self.root,[],path)

    def test_manifest_lrc_appears_after_selection_never_searches(self):
        path=m.make_selection_manifest(self.root,[self.audio]);self.root.joinpath('One.lrc').write_bytes(b'existing')
        self.addCleanup(lambda:path.unlink(missing_ok=True))
        with self.assertRaises(ValueError):m.filter_selected_tracks(self.root,[self.audio],path)

    def test_manifest_outside_path_rejected(self):
        outside=Path(self.temp.name)/'outside.mp3';outside.write_bytes(b'music')
        with self.assertRaises(ValueError):m.make_selection_manifest(self.root,[outside])

    def test_manifest_directory_escape_rejected(self):
        path=m.make_selection_manifest(self.root,[self.audio]);self.addCleanup(lambda:path.unlink(missing_ok=True))
        data=json.loads(path.read_text());data['tracks']=['../outside.mp3'];path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):m.filter_selected_tracks(self.root,[self.audio],path)

    def test_manifest_duplicate_refused(self):
        with self.assertRaises(ValueError):m.make_selection_manifest(self.root,[self.audio,self.audio])

    def test_report_rejection_reason_distinguishes_uncertainty(self):
        report=self.root/'LRC_Finder_Report_v2_1_15.csv'
        with report.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f);w.writerow(['MP3 path','round','status','reason','saved provider','provider outcomes']);w.writerow([str(self.audio),'1','NOT_FOUND_PARTIAL','one provider unavailable','','LRCLIB=NO_MATCH | SyncLRC=SKIPPED'])
        candidates=self.root/'LRC_Finder_Review_v2_1_15.csv'
        with candidates.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f);w.writerow(['MP3 path','round','provider','candidate title','candidate artist','rejected because','nearby candidate .lrc path']);w.writerow([str(self.audio),'1','SyncLRC','Different version','Artist','Duration mismatch',''])
        reasons=m.load_rejection_explanations(self.root,[self.audio])
        msg=m.reason_for_row({'path':str(self.audio),'status':'Missing LRC'},reasons)
        self.assertIn('Duration mismatch',msg);self.assertIn('may be stale',msg)
        self.assertIn('provider unavailable',msg)

    def test_unmatched_report_absent_is_not_invented(self):
        msg=m.reason_for_row({'path':str(self.audio),'status':'Missing LRC'}, {})
        self.assertIn('No current per-song reason',msg)

    def test_main_reports_never_altered(self):
        report=self.root/'LRC_Finder_Report_v2_1_15.csv';report.write_bytes(b'nonstandard')
        m.load_rejection_explanations(self.root)
        self.assertEqual(report.read_bytes(),b'nonstandard')

if __name__=='__main__':unittest.main(verbosity=2)
