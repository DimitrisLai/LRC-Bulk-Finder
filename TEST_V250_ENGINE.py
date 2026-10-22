"""Verify the *actual* finder save paths connect to the creation-only journal.
No external lyrics network calls and no changes to real user music.
"""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import LRC_Bulk_Finder as finder
from v250_manager import start_session, session_entries, undo_session

class FinderJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'songs';self.root.mkdir()
        self.audio=self.root/'One.mp3';self.audio.write_bytes(b'ORIGINAL AUDIO NEVER CHANGE')
        self.expected_audio=self.audio.read_bytes()
        self.sid=start_session(self.root,appdata=self.temp.name)
        env=mock.patch.dict(os.environ,{'APPDATA':self.temp.name,'LRC_SESSION_ID':self.sid})
        env.start();self.addCleanup(env.stop)

    def test_installed_lrc_gets_journaled_and_undo_is_safe(self):
        hit=SimpleNamespace(lyrics='[00:01.00] line one\n[00:02.00] line two\n')
        with mock.patch.object(finder,'sanitize_lrc',side_effect=lambda v:v),mock.patch.object(finder,'plausible_lrc',return_value=True):
            finder.save_hit(self.audio,hit)
        dest=self.audio.with_suffix('.lrc')
        self.assertTrue(dest.is_file())
        items=session_entries(self.sid,expected_root=self.root,appdata=self.temp.name)
        self.assertEqual([p['path'] for p in items if p['eligible']],[dest])
        self.assertEqual(undo_session(self.sid,expected_root=self.root,appdata=self.temp.name)['removed'],[dest])
        self.assertEqual(self.audio.read_bytes(),self.expected_audio)

    def test_candidate_export_gets_journaled_not_confused_with_existing_lrc(self):
        review=SimpleNamespace(items=[('Provider','title','artist','identity uncertain','[00:01.00] line one\n[00:02.00] line two\n')])
        records=finder.export_review_candidates(self.audio,1,review)
        self.assertTrue(records[0][-1].endswith('.candidate.lrc'))
        candidate=self.audio.with_suffix('.candidate.lrc')
        self.assertEqual(session_entries(self.sid,expected_root=self.root,appdata=self.temp.name)[0]['path'],candidate)
        self.assertEqual(len(undo_session(self.sid,expected_root=self.root,appdata=self.temp.name)['removed']),1)
        self.assertEqual(self.audio.read_bytes(),self.expected_audio)

    def test_preexisting_lrc_not_written_or_journaled(self):
        old=self.audio.with_suffix('.lrc');old.write_bytes(b'PREEXISTING')
        hit=SimpleNamespace(lyrics='[00:01.00] line one\n[00:02.00] line two\n')
        with mock.patch.object(finder,'sanitize_lrc',side_effect=lambda v:v),mock.patch.object(finder,'plausible_lrc',return_value=True):
            with self.assertRaises(FileExistsError):finder.save_hit(self.audio,hit)
        self.assertEqual(session_entries(self.sid,expected_root=self.root,appdata=self.temp.name),[])
        self.assertEqual(old.read_bytes(),b'PREEXISTING')

if __name__=='__main__':unittest.main(verbosity=2)
