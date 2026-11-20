"""Regression fixtures for album scope, Greek previews and empty result pages."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from candidate_review_v3 import group_candidates, read_snapshot
from incremental_library import safe_audio_files
from review_candidates_gui import list_review_candidates, preview_candidate
from v300_candidate_compare_gui import CandidateCompareWindow


class CandidateReviewRegression(unittest.TestCase):
    def cached_inventory(self, folder):
        from LRC_Control_Center import ControlCenter
        app = ControlCenter.__new__(ControlCenter)
        app.tk = None
        app._candidate_compare_window = None
        app.review_bulk_running = False
        app._review_refresh_generation = 0
        app.folder = Mock()
        app.folder.get.return_value = str(folder)
        app.boolvars = {"recursive": Mock()}
        app.boolvars["recursive"].get.return_value = True
        app._render_review = Mock()
        app._refresh_review()
        app._refresh_review_background = Mock()
        return app

    def test_distinct_albums_with_equivalent_casefold_are_independent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            albums = [root / "Strasse", root / "Straße"]
            albums[0].mkdir()
            if albums[1].exists():
                self.skipTest("This filesystem treats the two album names as identical")
            albums[1].mkdir()
            for album in albums:
                (album / "Track.mp3").write_bytes(b"synthetic audio")
                (album / "Track.candidate.lrc").write_text("[00:01.00] Sample\n")
            # Two formats sharing one basename in one album still need review.
            for extension in ("mp3", "wav"):
                (albums[0] / ("Bonus." + extension)).write_bytes(b"fixture")

            safe, collisions = safe_audio_files(root)
            self.assertCountEqual(safe, [album / "Track.mp3" for album in albums])
            self.assertCountEqual(collisions, [albums[0] / "Bonus.mp3", albums[0] / "Bonus.wav"])
            groups = group_candidates(list_review_candidates(root))
            self.assertCountEqual([g.audio for g in groups], safe)
            self.assertEqual(len({g.key for g in groups}), 2)
            for group in groups:
                self.assertEqual([row["path"].parent for row in group.candidates], [group.audio.parent])

    def test_greek_preview_and_comparison_show_the_same_recording_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Track.candidate.lrc"
            row = {"path": path, "index": 1}
            text = "[00:01.00] Αθήνα\n[00:03.00] Μουσική\n"
            for encoding in ("cp1253", "utf-8", "utf-8-sig"):
                with self.subTest(encoding=encoding):
                    data = text.replace("\n", "\r\n").encode(encoding)
                    path.write_bytes(data)
                    self.assertEqual(preview_candidate(path), text)
                    snapshot = read_snapshot(row)
                    self.assertEqual([line.text for line in snapshot.lines], ["Αθήνα", "Μουσική"])
                    self.assertEqual(snapshot.digest, hashlib.sha256(data).hexdigest())
                    self.assertEqual(path.read_bytes(), data)

    def test_empty_filter_stays_on_the_first_page(self):
        ui = SimpleNamespace(page=0, groups=[], query=Mock(), _refresh=Mock())
        ui.query.get.return_value = "no such song"
        for _ in range(3):
            CandidateCompareWindow._move(ui, 1)
        self.assertEqual(ui.page, 0)

    def test_folder_change_requests_a_fresh_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"
            first.mkdir()
            second.mkdir()
            (first / "Track.candidate.lrc").write_text("[00:01.00] first\n")
            app = self.cached_inventory(first)
            existing = Mock()
            existing.winfo_exists.return_value = True
            existing.review_scope = (str(first), True)
            app._candidate_compare_window = existing
            app.folder.get.return_value = str(second)
            app._open_candidate_stage1()
            existing.lift.assert_not_called()
            existing.destroy.assert_called_once()
            app._refresh_review_background.assert_called_once()

    def test_changing_subfolders_invalidates_cached_comparison_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            album = root / "nested"
            album.mkdir()
            (album / "Nested.candidate.lrc").write_text("[00:01.00] nested\n")
            app = self.cached_inventory(root)
            self.assertEqual(len(app.review_all_rows), 1)
            app.boolvars["recursive"].get.return_value = False
            with patch("v300_candidate_compare_gui.CandidateCompareWindow") as window:
                app._open_candidate_stage1()
            window.assert_not_called()
            app._refresh_review_background.assert_called_once()
