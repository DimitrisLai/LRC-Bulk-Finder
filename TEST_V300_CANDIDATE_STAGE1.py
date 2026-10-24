"""v3.0 Stage 1: candidate grouping and read-only comparison safety.

All filesystem fixtures live inside disposable temporary directories.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from candidate_review_v3 import (MAX_PREVIEW_BYTES, PAGE_SIZE,
    comparison, group_candidates, page_groups, read_snapshot)
from review_candidates_gui import list_review_candidates


class ReadOnlyCandidateCore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.album = self.root / "Άλμπουμ — Greek"
        self.album.mkdir()
        self.audio = self.album / "Τραγούδι - Καλλιτέχνης.mp3"
        self.audio.write_bytes(b"IMMUTABLE MUSIC AND TAGS")
        self.files = []
        for number, data in (
            (1, "[00:01.00] Γεια σου\n[00:06.00] Κόσμε\n"),
            (2, "[00:01.20] Γεια σου\n[00:06.10] Αλλαγή\n"),
            (3, "[00:01.00] Γεια σου\n[00:06.00] Κόσμε\n"),
        ):
            suffix = ".candidate.lrc" if number == 1 else f".candidate.{number}.lrc"
            path = self.audio.with_suffix(suffix)
            path.write_text(data, encoding="utf-8")
            self.files.append(path)

    def rows(self):
        return list_review_candidates(self.root, recursive=True)

    def hashes(self):
        return {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (self.audio, *self.files)}

    def test_group_multiples_and_different_album(self):
        other = self.root / "Other Album"
        other.mkdir()
        (other / self.audio.name).write_bytes(b"OTHER MUSIC")
        (other / self.files[0].name).write_text("[00:01.00] New\n")
        groups = group_candidates(self.rows())
        self.assertEqual(len(groups), 2)
        self.assertEqual([len(g.candidates) for g in groups], [3, 1])
        self.assertTrue(all(g.audio is not None for g in groups))

    def test_compare_greek_text_and_timing_with_no_writes(self):
        initial = self.hashes()
        group = group_candidates(self.rows())[0]
        first = read_snapshot(group.candidates[0], duration=10.0)
        second = read_snapshot(group.candidates[1], duration=10.0)
        third = read_snapshot(group.candidates[2], duration=10.0)
        self.assertEqual(first.line_count, 2)
        self.assertEqual(first.error, "")
        diff = comparison(first, second)
        self.assertTrue(diff["ready"])
        self.assertEqual(diff["changed_text"], 1)
        self.assertEqual(diff["changed_timing"], 2)
        self.assertFalse(diff["exact_duplicate"])
        self.assertTrue(comparison(first, third)["exact_duplicate"])
        self.assertEqual(initial, self.hashes())

    def test_duration_warning_and_no_verification_claim(self):
        g = group_candidates(self.rows())[0]
        first = read_snapshot(g.candidates[0], duration=4.0)
        self.assertTrue(any("after audio" in w for w in first.warnings))
        self.assertFalse(hasattr(first, "verified"))
        self.assertFalse(hasattr(first, "provider"))

    def test_orphan_and_ambiguous_audio_blocked_for_pairing(self):
        orphan = self.root / "No Audio.candidate.lrc"
        orphan.write_text("[00:01.00] one\n")
        self.addCleanup(orphan.unlink, missing_ok=True)
        wav = self.album / (self.audio.stem + ".wav")
        wav.write_bytes(b"ANOTHER AUDIO")
        groups = group_candidates(self.rows())
        self.assertEqual(len(groups), 2)
        self.assertTrue(all(g.audio is None for g in groups))
        self.assertTrue(any(g.ambiguous for g in groups))

    def test_invalid_large_and_symlink_warning_without_crash(self):
        self.files[0].write_text("[00:99.00] Malformed timestamp\n")
        item = self.rows()[0]
        snapshot = read_snapshot(item)
        self.assertNotEqual(snapshot.error, "")
        self.assertFalse(comparison(snapshot, snapshot)["ready"])
        self.files[0].write_bytes(b"x" * (MAX_PREVIEW_BYTES + 1))
        self.assertIn("exceeds", read_snapshot(item).error)
        if hasattr(os, "symlink"):
            link = self.root / "Linked.candidate.lrc"
            try:
                link.symlink_to(self.files[1])
            except (OSError, NotImplementedError):
                return
            row = dict(item, path=link, index=1)
            self.assertIn("unsafe", read_snapshot(row).error)

    def test_legacy_greek_encoding_and_utf8_bom(self):
        path = self.files[1]
        path.write_bytes("[00:01.00] Αθήνα\n".encode("cp1253"))
        rows = self.rows()
        item = next(x for x in rows if x["path"] == path)
        self.assertEqual(read_snapshot(item).lines[0].text, "Αθήνα")
        path.write_bytes(b"\xef\xbb\xbf" + "[00:01.00] Ελληνικά\n".encode("utf8"))
        self.assertEqual(read_snapshot(item).lines[0].text, "Ελληνικά")

    def test_existing_lrc_is_not_modified_by_comparison(self):
        installed = self.audio.with_suffix(".lrc")
        installed.write_bytes(b"EXISTING LRC MUST STAY")
        before = self.hashes()
        rows = self.rows()
        self.assertTrue(group_candidates(rows)[0].has_lrc)
        snapshots = [read_snapshot(x) for x in rows]
        comparison(snapshots[0], snapshots[1])
        self.assertEqual(installed.read_bytes(), b"EXISTING LRC MUST STAY")
        self.assertEqual(before, self.hashes())

    def test_pagination_and_unicode_filter(self):
        g = group_candidates(self.rows())
        page, n = page_groups(g, 0, query="Άλμπουμ")
        self.assertEqual(n, 1)
        self.assertEqual(len(page), 1)
        self.assertEqual(page_groups(g, 1)[0], [])
        with self.assertRaises(ValueError):
            page_groups(g, -1)
        self.assertEqual(PAGE_SIZE, 200)


def available_tk():
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        return True
    except Exception:
        return False


@unittest.skipUnless(available_tk(), "Tk desktop unavailable")
class ReadOnlyCandidateGui(unittest.TestCase):
    def setUp(self):
        from LRC_Control_Center import ControlCenter
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.appdata = mock.patch.dict(os.environ, {"APPDATA": self.tmp.name})
        self.appdata.start()
        self.addCleanup(self.appdata.stop)
        self.root = Path(self.tmp.name) / "music"
        self.root.mkdir()
        self.audio = self.root / "Song.wav"
        self.audio.write_bytes(b"ORIGINAL AUDIO")
        self.primary = self.root / "Song.candidate.lrc"
        self.primary.write_text("[00:01.00] first\n")
        self.secondary = self.root / "Song.candidate.2.lrc"
        self.secondary.write_text("[00:01.20] second\n")
        self.app = ControlCenter()
        self.app.withdraw()
        self.addCleanup(self.app.destroy)
        self.app.folder.set(str(self.root))
        self.app._refresh_review()

    def test_comparison_has_two_panes_and_read_only(self):
        before = {p: p.read_bytes() for p in (self.audio, self.primary, self.secondary)}
        self.app._open_candidate_stage1()
        compare = self.app._candidate_compare_window
        compare.update_idletasks()
        self.assertEqual(len(compare.previews), 2)
        self.assertEqual(len(compare.groups), 1)
        self.assertTrue(compare.choice_a.get())
        self.assertTrue(compare.choice_b.get())
        self.assertIn("Different text", compare.diff_status.get())
        compare.query.set("not found")
        compare.update()
        self.assertEqual(compare.visible, [])
        compare.destroy()
        self.assertEqual({p: p.read_bytes() for p in before}, before)
        self.assertTrue(self.app.review_promote_button.winfo_exists())
        self.assertTrue(self.app.review_recycle_button.winfo_exists())

    def test_open_twice_does_not_make_duplicate(self):
        self.app._open_candidate_stage1()
        first = self.app._candidate_compare_window
        self.app._open_candidate_stage1()
        self.assertIs(self.app._candidate_compare_window, first)
        first.destroy()


if __name__ == "__main__":
    unittest.main()
