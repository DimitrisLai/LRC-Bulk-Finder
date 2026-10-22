"""Offline 10,000-track inventory QA. Safe disposable files; no provider calls."""
from __future__ import annotations
import os
import tempfile
import time
import unittest
from pathlib import Path
from v245_features import scan_library, inventory_counts

class ScaleQA(unittest.TestCase):
    def test_10000_audio_files_read_only_and_unique(self):
        with tempfile.TemporaryDirectory() as root:
            base=Path(root)
            for folder_index in range(100):
                directory=base / f"music_{folder_index:03d}"
                directory.mkdir()
                for song_index in range(100):
                    (directory / f"track_{song_index:03d}.mp3").write_bytes(b"")
            marked=base / "music_000" / "track_000.lrc"
            marked.write_text("[00:01.00] first\n", encoding="utf-8")
            candidate=base / "music_001" / "track_001.candidate.lrc"
            candidate.write_text("[00:00.00] candidate\n[00:01.00] sample\n",encoding="utf-8")
            before={str(p):p.stat().st_size for p in base.rglob("*") if p.is_file()}
            begin=time.monotonic()
            rows=scan_library(base,recursive=True)
            elapsed=time.monotonic()-begin
            counts=inventory_counts(rows)
            self.assertEqual(counts["Total"],10000)
            self.assertEqual(counts["Has LRC"],1)
            self.assertEqual(counts["Needs review"],1)
            self.assertEqual(counts["Missing LRC"],9998)
            self.assertEqual(len({r["path"] for r in rows}),10000)
            after={str(p):p.stat().st_size for p in base.rglob("*") if p.is_file()}
            self.assertEqual(before,after)
            print(f"10k library read-only inventory completed in {elapsed:.2f}s")
if __name__=="__main__":unittest.main(verbosity=2)
