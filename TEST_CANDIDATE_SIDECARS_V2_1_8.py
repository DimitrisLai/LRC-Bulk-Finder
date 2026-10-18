"""No-network candidate sidecar and promotion regression tests."""
import io
import tempfile
import types
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock
sys.modules.setdefault('syncedlyrics',types.SimpleNamespace(search=lambda *a,**k: None))
import LRC_Bulk_Finder as app

GOOD='[00:01.20] One line\n[00:05.30] Another line\n[00:07.40] Third line\n'
ALT='[00:02.70] Different candidate\n[00:06.90] Different lyrics\n[00:08.10] Third lyric\n'

class CandidateTests(unittest.TestCase):
    def test_review_sidecar_in_same_folder(self):
        with tempfile.TemporaryDirectory() as d:
            audio=Path(d)/'TheProdigy.mp3';audio.write_bytes(b'ORIGINAL MP3')
            c=app.CandidateReview();c.add('Tencent','Song','Artist','uncertain',lyrics=GOOD)
            rows=app.export_review_candidates(audio,1,c)
            candidate=audio.with_name('TheProdigy.candidate.lrc')
            self.assertEqual(rows[0][-1],str(candidate))
            self.assertTrue(candidate.exists());self.assertFalse(audio.with_suffix('.lrc').exists())
            self.assertEqual(audio.read_bytes(),b'ORIGINAL MP3')

    def test_multiple_sources_get_safe_numbered_alternatives(self):
        with tempfile.TemporaryDirectory() as d:
            audio=Path(d)/'TheProdigy.mp3';audio.write_bytes(b'X')
            c=app.CandidateReview()
            c.add('Tencent','Song','Artist','one',lyrics=GOOD)
            c.add('NetEase','Song','Artist','two',lyrics=ALT)
            c.add('Other','Song','Artist','duplicate',lyrics=GOOD)
            rows=app.export_review_candidates(audio,1,c)
            self.assertEqual(Path(rows[0][-1]).name,'TheProdigy.candidate.lrc')
            self.assertEqual(Path(rows[1][-1]).name,'TheProdigy.candidate.2.lrc')
            self.assertEqual(Path(rows[2][-1]),Path(rows[0][-1]))
            self.assertEqual(len(list(Path(d).glob('*.candidate*.lrc'))),2)

    def test_repeat_search_never_overwrites_or_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            audio=Path(d)/'TheProdigy.mp3';audio.write_bytes(b'X')
            c=app.CandidateReview();c.add('A','Song','Artist','same',lyrics=GOOD)
            app.export_review_candidates(audio,1,c)
            app.export_review_candidates(audio,2,c)
            self.assertEqual(len(list(Path(d).glob('*.candidate*.lrc'))),1)
            c2=app.CandidateReview();c2.add('A','Song','Artist','different',lyrics=ALT)
            app.export_review_candidates(audio,3,c2)
            self.assertEqual(len(list(Path(d).glob('*.candidate*.lrc'))),2)
            self.assertEqual((Path(d)/'TheProdigy.candidate.lrc').read_text(),GOOD)

    def test_promotion_creates_lrc_and_removes_primary_not_alternative(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);mp3=folder/'TheProdigy.mp3';mp3.write_bytes(b'KEEP')
            (folder/'TheProdigy.candidate.lrc').write_text(GOOD)
            (folder/'TheProdigy.candidate.2.lrc').write_text(ALT)
            out=app.promote_candidates(folder,confirm=False)
            self.assertEqual(out['PROMOTED'],1)
            self.assertEqual((folder/'TheProdigy.lrc').read_text(),GOOD)
            self.assertFalse((folder/'TheProdigy.candidate.lrc').exists())
            self.assertTrue((folder/'TheProdigy.candidate.2.lrc').exists())
            self.assertEqual(mp3.read_bytes(),b'KEEP')
            self.assertTrue((folder/'LRC_Candidate_Promotion_Report_v2_1_8.csv').is_file())

    def test_existing_approved_lrc_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);(folder/'Song.mp3').write_bytes(b'X')
            (folder/'Song.lrc').write_text('MY APPROVED LYRICS')
            (folder/'Song.candidate.lrc').write_text(GOOD)
            out=app.promote_candidates(folder,confirm=False)
            self.assertEqual(out['SKIPPED'],1)
            self.assertEqual((folder/'Song.lrc').read_text(),'MY APPROVED LYRICS')
            self.assertTrue((folder/'Song.candidate.lrc').exists())

    def test_no_mp3_or_invalid_candidate_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            (folder/'Missing.candidate.lrc').write_text(GOOD)
            (folder/'Bad.mp3').write_bytes(b'X')
            (folder/'Bad.candidate.lrc').write_text('No timestamps')
            out=app.promote_candidates(folder,confirm=False)
            self.assertEqual(out['SKIPPED'],2)
            self.assertFalse((folder/'Bad.lrc').exists())

    def test_subfolders_recursive_and_nonrecursive(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);sub=folder/'Sub';sub.mkdir()
            (sub/'Tune.mp3').write_bytes(b'X');(sub/'Tune.candidate.lrc').write_text(GOOD)
            out=app.promote_candidates(folder,recursive=False,confirm=False)
            self.assertEqual(out['PROMOTED'],0)
            out=app.promote_candidates(folder,recursive=True,confirm=False)
            self.assertEqual(out['PROMOTED'],1)

    def test_promotion_is_explicitly_confirmed(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);(folder/'Song.mp3').write_bytes(b'X')
            (folder/'Song.candidate.lrc').write_text(GOOD)
            with mock.patch('builtins.input',return_value='n'):
                out=app.promote_candidates(folder)
            self.assertEqual(out['PROMOTED'],0)
            self.assertFalse((folder/'Song.lrc').exists())

    def test_unverified_candidates_not_exported_if_approved_lrc_exists(self):
        with tempfile.TemporaryDirectory() as d:
            audio=Path(d)/'Song.mp3';audio.write_bytes(b'X')
            audio.with_suffix('.lrc').write_text('Approved')
            review=app.CandidateReview();review.add('Tencent','Song','A','review',lyrics=GOOD)
            rows=app.export_review_candidates(audio,1,review)
            self.assertEqual(rows[0][-1],'')
            self.assertFalse((Path(d)/'Song.candidate.lrc').exists())

    def test_user_samples_are_valid_lrc_candidate_content(self):
        samples=list(Path('/mnt/data').glob('*.candidate.txt'))
        if not samples:self.skipTest('Uploaded samples unavailable')
        for path in samples:
            with self.subTest(path=path.name):
                self.assertTrue(app.plausible_lrc(path.read_text(encoding='utf-8'),0))

if __name__=='__main__':unittest.main(verbosity=2)
