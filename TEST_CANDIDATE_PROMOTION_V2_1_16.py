"""Offline-only regression tests for marked bulk promotion and candidate rotation."""
import csv
import io
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock
import sys

sys.modules.setdefault('syncedlyrics', types.SimpleNamespace(search=lambda *a, **k: None))
import LRC_Bulk_Finder as app

LYRICS='[00:05.00] First line\n[00:30.00] Second line\n[02:59.00] Last line\n'


def song(root, stem='Song', alternatives=3):
    mp3=root/(stem+'.mp3')
    mp3.write_bytes(b'AUDIO UNCHANGED')
    primary=root/(stem+'.candidate.lrc')
    primary.write_text(LYRICS,encoding='utf-8')
    for number in range(2,alternatives+2):
        (root/(stem+f'.candidate.{number}.lrc')).write_text(
            LYRICS+f'[03:00.00] OPTION {number}\n',encoding='utf-8')
    return mp3,primary


class CandidatePromotionTests(unittest.TestCase):
    def test_bulk_promotion_marks_and_rotates_all_alternatives(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);mp3,first=song(root,alternatives=3)
            original=[(root/f'Song.candidate.{i}.lrc').read_bytes() for i in (2,3,4)]
            action,_=app.promote_candidate_file(first)
            self.assertEqual(action,'PROMOTED')
            self.assertFalse(first.exists() and first.read_bytes()==LYRICS.encode('utf-8'))
            self.assertEqual((root/'Song.lrc').read_text(encoding='utf-8').splitlines()[0],
                             '[00:00.00] candidate')
            self.assertTrue((root/'Song.lrc').read_text().endswith(LYRICS))
            self.assertEqual(first.read_bytes(),original[0])
            self.assertEqual((root/'Song.candidate.2.lrc').read_bytes(),original[1])
            self.assertEqual((root/'Song.candidate.3.lrc').read_bytes(),original[2])
            self.assertFalse((root/'Song.candidate.4.lrc').exists())
            self.assertEqual(mp3.read_bytes(),b'AUDIO UNCHANGED')

    def test_after_deleting_wrong_lrc_next_candidate_is_ready(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);_,primary=song(root,alternatives=2)
            self.assertEqual(app.promote_candidate_file(primary)[0],'PROMOTED')
            first=(root/'Song.lrc')
            first.unlink()
            self.assertEqual(app.promote_candidate_file(primary)[0],'PROMOTED')
            self.assertIn('OPTION 2',first.read_text())
            self.assertIn('OPTION 3',primary.read_text())
            self.assertFalse((root/'Song.candidate.2.lrc').exists())

    def test_existing_lrc_is_never_overwritten_or_reordered(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);_,primary=song(root,alternatives=2)
            final=root/'Song.lrc';final.write_text('GOOD ORIGINAL')
            before={p.name:p.read_bytes() for p in root.iterdir()}
            action,_=app.promote_candidate_file(primary)
            self.assertEqual(action,'SKIPPED')
            self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir()})

    def test_bad_untimed_candidate_and_missing_mp3_are_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);_,primary=song(root,alternatives=1)
            primary.write_text('not synchronized',encoding='utf-8')
            self.assertEqual(app.promote_candidate_file(primary)[0],'SKIPPED')
            self.assertFalse((root/'Song.lrc').exists())
            self.assertTrue((root/'Song.candidate.2.lrc').exists())
            primary.write_text(LYRICS,encoding='utf-8')
            (root/'Song.mp3').unlink()
            self.assertEqual(app.promote_candidate_file(primary)[0],'SKIPPED')
            self.assertTrue(primary.exists())

    def test_bom_crlf_preserved_and_existing_marker_not_duplicated(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);mp3,primary=song(root,alternatives=0)
            crlf=b'\xef\xbb\xbf'+LYRICS.replace('\n','\r\n').encode('utf-8')
            primary.write_bytes(crlf)
            self.assertEqual(app.promote_candidate_file(primary)[0],'PROMOTED')
            payload=(root/'Song.lrc').read_bytes()
            self.assertTrue(payload.startswith(b'\xef\xbb\xbf[00:00.00] candidate\r\n'))
            self.assertEqual(payload.split(b'candidate\r\n',1)[1],crlf[3:])
            (root/'Song.lrc').unlink()
            primary.write_bytes(b'[00:00.00] candidate\n'+LYRICS.encode())
            self.assertEqual(app.promote_candidate_file(primary)[0],'PROMOTED')
            self.assertEqual((root/'Song.lrc').read_text().count('[00:00.00] candidate'),1)

    def test_number_gaps_shift_by_one_without_touching_noncanonical_names(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);_,primary=song(root,alternatives=0)
            (root/'Song.candidate.2.lrc').write_text('two')
            (root/'Song.candidate.4.lrc').write_text('four')
            (root/'Song.candidate.04.lrc').write_text('special')
            self.assertEqual(app.promote_candidate_file(primary)[0],'PROMOTED')
            self.assertEqual(primary.read_text(),'two')
            self.assertEqual((root/'Song.candidate.3.lrc').read_text(),'four')
            self.assertEqual((root/'Song.candidate.04.lrc').read_text(),'special')

    def test_bulk_confirm_no_makes_no_changes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);song(root)
            before={p.name:p.read_bytes() for p in root.iterdir()}
            with mock.patch('builtins.input',return_value='n'),redirect_stdout(io.StringIO()):
                result=app.promote_candidates(root)
            self.assertFalse(result['PROMOTED'])
            self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir()})

    def test_recursive_bulk_generates_report_and_leaves_existing_unmodified(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);nested=root/'nested';nested.mkdir()
            song(root,'One',alternatives=1)
            song(nested,'Two',alternatives=1)
            song(nested,'Existing',alternatives=1)
            (nested/'Existing.lrc').write_text('correct')
            with mock.patch('builtins.input',return_value='y'),redirect_stdout(io.StringIO()):
                results=app.promote_candidates(root,recursive=True)
            self.assertEqual(results['PROMOTED'],2)
            self.assertEqual(results['SKIPPED'],1)
            self.assertEqual((nested/'Existing.lrc').read_text(),'correct')
            report=root/'LRC_Candidate_Promotion_Report_v2_1_16.csv'
            rows=list(csv.DictReader(report.open(encoding='utf-8-sig',newline='')))
            self.assertEqual(len(rows),3)
            self.assertEqual(sum(r['result']=='PROMOTED' for r in rows),2)

    def test_large_bulk_is_offline_and_does_not_touch_audio(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for i in range(110):song(root,f'Track{i:03}',alternatives=1)
            with mock.patch('builtins.input',return_value='y'), \
                 mock.patch.object(app,'direct_get',side_effect=AssertionError('NETWORK')), \
                 mock.patch.object(app,'direct_json',side_effect=AssertionError('NETWORK')), \
                 mock.patch.object(app,'search_song',side_effect=AssertionError('NETWORK')), \
                 redirect_stdout(io.StringIO()):
                results=app.promote_candidates(root,recursive=False)
            self.assertEqual(results['PROMOTED'],110)
            self.assertEqual(len(list(root.glob('*.lrc'))),220)
            self.assertEqual((root/'Track042.mp3').read_bytes(),b'AUDIO UNCHANGED')


if __name__=='__main__':
    unittest.main()
