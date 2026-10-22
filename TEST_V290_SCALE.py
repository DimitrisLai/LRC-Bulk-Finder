"""Stress test 10,000 actual files with v2.9 incremental SQLite + pagination."""
from __future__ import annotations
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from v290_smart_library import scan_index,read_page,counts

class SmartScaleTests(unittest.TestCase):
    def test_10000_indexed_tracks_incremental_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch.dict(os.environ,{"APPDATA":temp}):
                root=Path(temp)/"collection";root.mkdir()
                for i in range(100):
                    directory=root/f"folder_{i:03d}";directory.mkdir()
                    for j in range(100):
                        (directory/f"track_{j:04d}.mp3").touch()
                first_start=time.monotonic()
                first=scan_index(root)
                first_elapsed=time.monotonic()-first_start
                self.assertEqual(first.total,10000)
                self.assertEqual(first.audited,10000)
                count,page=read_page(root,status="Missing LRC")
                self.assertEqual(count,10000)
                self.assertEqual(len(page),200)
                self.assertEqual(counts(root)["total"],10000)
                second_start=time.monotonic()
                second=scan_index(root)
                second_elapsed=time.monotonic()-second_start
                self.assertEqual(second.total,10000)
                self.assertEqual(second.audited,0)
                self.assertEqual(second.cached,10000)
                n,one=read_page(root,query="TRACK_0099",page_size=200)
                self.assertEqual(n,100)
                self.assertEqual(len(one),100)
                self.assertFalse(list(root.rglob("*.lrc")))
                for p in root.rglob("*.mp3"):
                    self.assertEqual(p.stat().st_size,0)
                print(f"10k Smart Library initial {first_elapsed:.2f}s; cached {second_elapsed:.2f}s; 200-row pagination verified")
if __name__=="__main__":unittest.main(verbosity=2)
