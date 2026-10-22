"""LRC Bulk Finder v2.4.5: adversarial tests, 100% offline and disposable."""
from __future__ import annotations
import csv
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import v245_features as f


class V245CoreTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.base=Path(self.t.name)
        self.audio=self.base/'example.mp3'
        self.audio.write_bytes(b'ORIGINAL MP3 NEVER CHANGE')

    def test_missing_folder_rejected(self):
        with self.assertRaises(ValueError):f.scan_library(self.base/'absent')

    def test_inventory_missing_audio(self):
        r=f.scan_library(self.base)
        self.assertEqual(len(r),1)
        self.assertEqual(r[0]['status'],'Missing LRC')

    def test_existing_lrc_is_not_called_verified(self):
        self.audio.with_suffix('.lrc').write_text('[00:02.00]wrong text')
        self.assertEqual(f.scan_library(self.base)[0]['status'],'Has LRC')

    def test_candidate_needs_review(self):
        self.audio.with_suffix('.candidate.lrc').write_text('[00:00.00] candidate')
        r=f.scan_library(self.base)
        self.assertEqual((r[0]['status'],r[0]['candidates']),('Needs review',1))

    def test_numbered_candidates(self):
        (self.base/'example.candidate.2.lrc').write_text('safe')
        (self.base/'example.candidate.3.lrc').write_text('safe')
        self.assertEqual(f.scan_library(self.base)[0]['candidates'],2)

    def test_reports_are_not_wrongly_counted_as_audio(self):
        (self.base/'report.txt').write_text('x')
        self.assertEqual(len(f.scan_library(self.base)),1)

    def test_cross_extension_ambiguity(self):
        (self.base/'example.flac').write_bytes(b'original')
        self.assertTrue(all(x['status']=='Ambiguous audio' for x in f.scan_library(self.base)))

    def test_subfolder_option(self):
        d=self.base/'folder';d.mkdir()
        (d/'song.flac').write_bytes(b'original')
        self.assertEqual(len(f.scan_library(self.base,True)),2)
        self.assertEqual(len(f.scan_library(self.base,False)),1)

    def test_folder_symlink_not_followed(self):
        d=self.base/'folder';d.mkdir()
        (d/'nested.mp3').write_bytes(b'file')
        try:(self.base/'link').symlink_to(d,target_is_directory=True)
        except (OSError,NotImplementedError):self.skipTest('symlink privilege unavailable')
        self.assertEqual(len(f.scan_library(self.base,True)),2)

    def test_max_limit(self):
        (self.base/'second.mp3').write_bytes(b'new')
        with self.assertRaises(ValueError):f.scan_library(self.base,limit=1)

    def test_inventory_counts(self):
        rows=f.scan_library(self.base)
        self.assertEqual(f.inventory_counts(rows)['Total'],1)
        self.assertEqual(f.inventory_counts(rows)['Missing LRC'],1)

    def test_inventory_export_utf8(self):
        a=self.base/'Γιώργος.mp3';a.write_bytes(b'audio')
        target=self.base/'report.csv'
        f.export_inventory(f.scan_library(self.base),target)
        with target.open(encoding='utf-8-sig',newline='') as stream:
            rows=list(csv.reader(stream))
        self.assertTrue(any('Γιώργος.mp3' in row for row in rows))

    def test_csv_export_escapes_spreadsheet_formulas(self):
        malicious = self.base/'=HYPERLINK(1).mp3'
        malicious.write_bytes(b'audio')
        dest = self.base/'safe.csv'
        f.export_inventory(f.scan_library(self.base),dest)
        with dest.open(encoding='utf-8-sig',newline='') as stream:
            rows=list(csv.reader(stream))
        formula_rows=[r for r in rows if 'HYPERLINK' in r[0]]
        self.assertEqual(len(formula_rows),1)
        self.assertTrue(formula_rows[0][0].startswith("'="))
        self.assertEqual(malicious.name,'=HYPERLINK(1).mp3')

    def test_export_refuses_overwrite(self):
        target=self.base/'report.csv';target.write_bytes(b'IMPORTANT')
        with self.assertRaises(FileExistsError):f.export_inventory([],target)
        self.assertEqual(target.read_bytes(),b'IMPORTANT')

    def test_version_comparison(self):
        self.assertEqual(f.parse_version('v2.4.10'),(2,4,10))
        self.assertIsNone(f.parse_version('v2.4.5-beta'))

    def test_github_check_mock_no_private_data(self):
        class R:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):return json.dumps({'tag_name':'v2.4.6',
               'html_url':'https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/tag/v2.4.6'}).encode()
        urls=[]
        def mock(req,timeout):
            urls.append((req.full_url,timeout));return R()
        r=f.check_github_update('2.4.5',opener=mock)
        self.assertTrue(r['newer'])
        self.assertEqual(urls,[('https://api.github.com/repos/DimitrisLai/LRC-Bulk-Finder/releases/latest',7)])

    def test_github_check_rejects_external_url(self):
        class R:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):return b'{"tag_name":"v2.4.6","html_url":"https://evil.example/app.exe"}'
        with self.assertRaises(ValueError):f.check_github_update(opener=lambda *a,**kw:R())

    def test_diagnostics_has_no_private_paths(self):
        text=f.diagnostic_text(frozen=True,worker_exists=False,profiles=4)
        self.assertIn(f.VERSION,text)
        self.assertNotIn(str(self.base),text)
        self.assertNotIn(os.environ.get('HOME','---UNLIKELY---'),text)

    def test_diagnostics_exclusive_create(self):
        report=self.base/'diagnostic.txt'
        f.save_diagnostics(report)
        with self.assertRaises(FileExistsError):f.save_diagnostics(report)

    def test_shift_positive_preserves_metadata(self):
        data='[ar:Στέλιος]\n[00:02.00] Hello\n[00:10.35] World\n'
        out,n=f.shift_lrc_timestamps(data,1.25)
        self.assertEqual(n,2)
        self.assertIn('[ar:Στέλιος]',out)
        self.assertIn('[00:03.25] Hello',out)
        self.assertIn('[00:11.60] World',out)
        self.assertTrue(out.startswith('[00:00.00] candidate\n'))

    def test_shift_negative(self):
        out,n=f.shift_lrc_timestamps('[00:05.00] Hi',-2.5)
        self.assertIn('[00:02.50] Hi',out)

    def test_shift_negative_timestamp_rejected(self):
        with self.assertRaises(ValueError):f.shift_lrc_timestamps('[00:01.00] Hi',-2.5)

    def test_shift_disallows_infinite_and_big_offset(self):
        for value in ('nan','inf',1000,'text'):
            with self.subTest(value=value),self.assertRaises(ValueError):
                f.shift_lrc_timestamps('[00:02.00] Hi',value)

    def test_shift_multistamp(self):
        out,n=f.shift_lrc_timestamps('[00:03.00][00:04.00] Hello',0.5)
        self.assertEqual(n,2)
        self.assertIn('[00:03.50][00:04.50] Hello',out)

    def test_shift_keeps_single_marker(self):
        out,n=f.shift_lrc_timestamps('[00:00.00] candidate\n[00:03.00] text',1)
        self.assertEqual(out.count('[00:00.00] candidate'),1)
        self.assertEqual(n,1)

    def test_no_timestamps_rejected(self):
        with self.assertRaises(ValueError):f.shift_lrc_timestamps('[ar:test]\nhi',1)

    def test_150kb_limit(self):
        with self.assertRaises(ValueError):f.shift_lrc_timestamps('[00:00.01]'+('x'*151_000),1)

    def test_save_new_candidate_never_overwrites_lrc(self):
        original=self.audio.with_suffix('.lrc');original.write_bytes(b'PRECIOUS ORIGINAL')
        data,_=f.shift_lrc_timestamps('[00:02.00] line',1)
        dest=f.save_shifted_candidate(self.audio,original,data)
        self.assertEqual(dest.name,'example.candidate.lrc')
        self.assertEqual(original.read_bytes(),b'PRECIOUS ORIGINAL')
        self.assertEqual(self.audio.read_bytes(),b'ORIGINAL MP3 NEVER CHANGE')
        self.assertIn('[00:03.00]',dest.read_text())
        second=f.save_shifted_candidate(self.audio,original,data)
        self.assertEqual(second.name,'example.candidate.2.lrc')
        self.assertEqual(dest.read_text(),second.read_text())

    def test_save_rejects_unrelated_lrc(self):
        unrelated=self.base/'other.lrc';unrelated.write_text('hi')
        text,_=f.shift_lrc_timestamps('[00:02.00] hi',1)
        with self.assertRaises(ValueError):f.save_shifted_candidate(self.audio,unrelated,text)

    def test_save_rejects_unmarked(self):
        src=self.audio.with_suffix('.lrc');src.write_text('[00:01.00] hi')
        with self.assertRaises(ValueError):f.save_shifted_candidate(self.audio,src,'[00:02.00] hi')

    def test_save_cross_format_reject(self):
        src=self.audio.with_suffix('.lrc');src.write_text('orig')
        self.audio.with_suffix('.flac').write_bytes(b'original')
        with self.assertRaises(FileExistsError):
            f.save_shifted_candidate(self.audio,src,'[00:00.00] candidate\n[00:01.00] hi')

    def test_timing_save_lrc_no_modification_on_bad_input(self):
        src=self.audio.with_suffix('.lrc');src.write_bytes(b'ORIGINAL')
        with self.assertRaises(ValueError):f.save_shifted_candidate(self.audio,src,'invalid')
        self.assertEqual(src.read_bytes(),b'ORIGINAL')


if __name__=='__main__':unittest.main(verbosity=2)
