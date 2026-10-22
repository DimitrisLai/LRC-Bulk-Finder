"""v2.9 Smart Library safety, Unicode SQL, rollback and incremental QC tests."""
from __future__ import annotations
import csv
import os
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from v290_smart_library import (scan_index,ScanCancelled,read_page,counts,history,
    audit_lrc,export_issues,set_review_state,canonical_root,_open_db)

class SmartLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.env=mock.patch.dict(os.environ,{"APPDATA":self.temp.name});self.env.start();self.addCleanup(self.env.stop)
        self.root=Path(self.temp.name)/"music";self.root.mkdir()
        self.good=self.root/"Καλημέρα - Τραγούδι.mp3";self.good.write_bytes(b"audio-not-to-be-modified")
        self.lrc=self.good.with_suffix(".lrc")
        self.lrc.write_text("[ti:Τραγούδι]\n[00:01.00] Γεια\n[00:04.10] Ελλάδα\n",encoding="utf-8")
        self.missing=self.root/"Missing Song.mp3";self.missing.write_bytes(b"b")
        self.candidate=self.root/"Candidate.mp3";self.candidate.write_bytes(b"c")
        self.candidate.with_suffix(".candidate.lrc").write_text("[00:01.00] cand",encoding="utf-8")
        self.before={str(p):p.read_bytes() for p in self.root.iterdir() if p.is_file()}
    def test_initial_scan_and_incremental_cache_and_unicode_search(self):
        first=scan_index(self.root)
        self.assertEqual(first.total,3)
        self.assertEqual(first.cached,0)
        second=scan_index(self.root)
        self.assertEqual(second.audited,0)
        self.assertEqual(second.cached,3)
        n,items=read_page(self.root,status="All",query="ΚΑΛΗΜΈΡΑ")
        self.assertEqual(n,1)
        self.assertEqual(items[0]["name"],self.good.name)
        n,items=read_page(self.root,status="Missing LRC")
        self.assertEqual(n,1)
        self.assertEqual(items[0]["name"],self.missing.name)
        self.assertEqual(self.before,{str(p):p.read_bytes() for p in self.root.iterdir() if p.is_file()})
        self.assertEqual(len(history(self.root)),2)
    def test_cache_invalidated_on_mtime_or_size_changes(self):
        scan_index(self.root)
        self.lrc.write_text("[00:01.00] new lyric\n[00:02.00] changed\n",encoding="utf-8")
        nextscan=scan_index(self.root)
        self.assertEqual(nextscan.audited,1)
        self.assertEqual(nextscan.cached,2)
    def test_issues_and_qc(self):
        scan_index(self.root)
        count,issues=read_page(self.root,status="Issues only")
        self.assertGreaterEqual(count,2)
        self.assertEqual(counts(self.root)["total"],3)
        self.assertEqual(counts(self.root)["missing"],1)
    def test_duplicate_out_of_order_and_large_offset_detected(self):
        self.lrc.write_text("[offset:15000]\n[00:02.00] Γεια\n[00:02.00] Άλλο\n[00:01.00] Πίσω\n",encoding="utf-8")
        flags,detail=audit_lrc(self.good,self.lrc)
        self.assertIn("Large global offset",flags)
        self.assertIn("Duplicate timestamps",flags)
        self.assertIn("Out-of-order timestamps",flags)
    def test_invalid_lrc_syntax_and_encoding(self):
        self.lrc.write_bytes(b"[00:AB.00] Broken")
        flags,_=audit_lrc(self.good,self.lrc)
        self.assertIn("Invalid or untimed LRC",flags)
        self.assertIn("Malformed timestamp",flags)
        self.lrc.write_bytes("Τραγούδι".encode("cp1253")+b"\n[00:01.00] Greek\n")
        flags,_=audit_lrc(self.good,self.lrc)
        self.assertIn("Encoding: Greek CP1253",flags)
    def test_ambiguous_audio(self):
        self.good.with_suffix(".flac").write_bytes(b"otheraudio")
        scan_index(self.root)
        n,rows=read_page(self.root,status="Ambiguous audio")
        self.assertEqual(n,2)
        self.assertTrue(any("Ambiguous audio stem" in x["flags"] for x in rows))
    def test_safe_cancel_rolls_back_changes_and_history(self):
        scan_index(self.root)
        before=read_page(self.root,status="All")
        n_history=len(history(self.root))
        stop=threading.Event()
        extra=self.root/"A brand new.mp3";extra.write_bytes(b"new")
        def callback(*args):stop.set()
        # Progress occurs at multiples of 250. Add 250 synthetic tiny files.
        for i in range(251):
            (self.root/f"x_{i:04d}.mp3").write_bytes(b"")
        with self.assertRaises(ScanCancelled):
            scan_index(self.root,cancel=stop,progress=callback)
        self.assertEqual(read_page(self.root,status="All"),before)
        self.assertEqual(len(history(self.root)),n_history)
    def test_guard_invalid_query_and_sql_injection(self):
        scan_index(self.root)
        with self.assertRaises(ValueError):
            read_page(self.root,status="NOT_A_STATUS")
        count,_=read_page(self.root,query="%' OR 1=1 --")
        self.assertEqual(count,0)
        count,_=read_page(self.root,query="%")
        self.assertEqual(count,0)
    def test_csv_formula_injection_and_no_overwrite(self):
        danger=self.root/"=HYPERLINK(evil).mp3"
        danger.write_bytes(b"")
        scan_index(self.root)
        target=Path(self.temp.name)/"qc.csv"
        n=export_issues(self.root,target,status="All")
        self.assertEqual(n,4)
        with target.open(encoding="utf-8-sig",newline="") as handle:
            rows=list(csv.reader(handle))
        match=[r for r in rows[1:] if r[0].startswith("'=")]
        self.assertTrue(match)
        with self.assertRaises(FileExistsError):
            export_issues(self.root,target,status="All")
        self.assertEqual(self.before,{p:v for p,v in self.before.items()})
    def test_bookmark_review_and_clear_survive_refresh(self):
        scan_index(self.root)
        set_review_state(self.root,self.good,"bookmarked")
        n,rows=read_page(self.root,query="καλημέρα")
        self.assertEqual(rows[0]["review"],"bookmarked")
        scan_index(self.root)
        _,rows=read_page(self.root,query="καλημέρα")
        self.assertEqual(rows[0]["review"],"bookmarked")
        set_review_state(self.root,self.good,"reviewed")
        _,rows=read_page(self.root,query="καλημέρα")
        self.assertEqual(rows[0]["review"],"reviewed")
        set_review_state(self.root,self.good,"clear")
        _,rows=read_page(self.root,query="καλημέρα")
        self.assertEqual(rows[0]["review"],"")
    def test_symlink_and_directory_protection(self):
        with self.assertRaises(ValueError):
            canonical_root(Path(self.temp.name)/"not-real")
        proxy=self.root/"link.mp3"
        try:proxy.symlink_to(self.good)
        except (OSError,NotImplementedError):self.skipTest("No symlink permission")
        scan_index(self.root)
        self.assertEqual(counts(self.root)["total"],3)
    def test_stale_entries_pruned_but_no_music_deleted(self):
        scan_index(self.root)
        self.missing.unlink()
        scan_index(self.root)
        self.assertEqual(counts(self.root)["total"],2)
        self.assertTrue(self.good.is_file())
    def test_reject_future_db_schema_version(self):
        db=_open_db()
        db.execute("PRAGMA user_version=300")
        db.close()
        with self.assertRaises(ValueError):
            _open_db()

if __name__=="__main__":unittest.main(verbosity=2)
