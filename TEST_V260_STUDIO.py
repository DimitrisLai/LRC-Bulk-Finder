"""v2.6 Lyrics Studio adversarial offline tests. Files are disposable; no provider calls."""
from __future__ import annotations
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from v260_studio import (
    LyricLine, StudioDocument, format_time, parse_lrc, read_lyric_file,
    render_candidate, save_candidate
)
from v260_player import StudioPlayer, PlaybackError, PLAYER_EXTENSIONS


class ParserTests(unittest.TestCase):
    def test_standard_greek_and_three_digit_fraction(self):
        parsed = parse_lrc("[ar: Δοκιμή]\n[00:01.250] Καλημέρα\n[00:02.5] Γεια\n")
        self.assertEqual(parsed, [LyricLine(1.25, "Καλημέρα"), LyricLine(2.5, "Γεια")])

    def test_multiple_timestamps_and_offset(self):
        parsed = parse_lrc("[offset:+250]\n[00:01.00][00:04.00] Chorus\n")
        self.assertEqual(parsed, [LyricLine(1.25, "Chorus"), LyricLine(4.25, "Chorus")])

    def test_ignore_metadata_and_prior_unverified_marker(self):
        x = parse_lrc("[ar:A]\n[00:00.00] candidate\n[00:02.00] Κυρίως\n")
        self.assertEqual(x, [LyricLine(2.0, "Κυρίως")])

    def test_bad_seconds_rejected(self):
        with self.assertRaises(ValueError):
            parse_lrc("[00:78.00] impossible")

    def test_negative_global_offset_rejected(self):
        with self.assertRaises(ValueError):
            parse_lrc("[offset:-3000]\n[00:01.00] start")

    def test_untimed_only_not_valid(self):
        with self.assertRaises(ValueError):
            parse_lrc("hello\nworld\n")

    def test_invalid_offset_rejected(self):
        with self.assertRaises(ValueError):
            parse_lrc("[offset:abc]\n[00:03.00] text")

    def test_oversized_lrc_rejected(self):
        with self.assertRaises(ValueError):
            parse_lrc("X" * 600000)

    def test_legacy_greek_encoding(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "song.lrc"
            p.write_bytes("[00:12.30] Καλησπέρα\n".encode("cp1253"))
            self.assertEqual(read_lyric_file(p)[0].text, "Καλησπέρα")

    def test_nonfinite_and_duplicate_centiseconds_rejected(self):
        for value in (float("nan"), float("inf"), -0.01):
            with self.subTest(value=value), self.assertRaises(ValueError):
                render_candidate([LyricLine(value, "bad")])
        with self.assertRaises(ValueError):
            render_candidate([LyricLine(1.001, "A"), LyricLine(1.004, "B")])

    def test_format_round_trip_precision(self):
        self.assertEqual(format_time(125.239), "[02:05.24]")

    def test_many_lines_guard(self):
        text = "\n".join("[00:01.00] line" for _ in range(1001))
        with self.assertRaises(ValueError):
            parse_lrc(text)


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.doc = StudioDocument([LyricLine(1, "one"), LyricLine(2, "two"), LyricLine(3, "three")])

    def test_edit_and_undo_redo(self):
        self.doc.set_time(1, 2.5)
        self.assertEqual(self.doc.lines[1].seconds, 2.5)
        self.assertTrue(self.doc.undo())
        self.assertEqual(self.doc.lines[1].seconds, 2.0)
        self.assertTrue(self.doc.redo())
        self.assertEqual(self.doc.lines[1].seconds, 2.5)

    def test_bulk_nudge_is_atomic_on_invalid(self):
        old = list(self.doc.lines)
        with self.assertRaises(ValueError):
            self.doc.shift([0, 1], -3)
        self.assertEqual(self.doc.lines, old)
        self.assertFalse(self.doc.undo())

    def test_bulk_nudge_and_dedupe_selection(self):
        self.doc.shift([0, 1, 1], .1)
        self.assertEqual([r.seconds for r in self.doc.lines], [1.1, 2.1, 3.0])

    def test_timeline_selects_latest_started_line(self):
        self.assertIsNone(self.doc.active_line(.5))
        self.assertEqual(self.doc.active_line(2.5), 1)

    def test_unsorted_edit_cannot_export(self):
        self.doc.set_time(1, .5)
        with self.assertRaises(ValueError):
            render_candidate(self.doc.lines)
        self.assertTrue(self.doc.undo())
        self.assertIn("two", render_candidate(self.doc.lines))


class ProtectedWrites(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.mp3 = self.root / "Song.mp3"
        self.mp3.write_bytes(b"original audio never change")
        self.lrc = self.root / "Song.lrc"
        self.lrc.write_bytes(b"[00:01.00] ORIGINAL LYRIC")
        self.rows = [LyricLine(1, "alpha"), LyricLine(2, "beta")]

    def test_original_audio_and_lrc_never_overwritten(self):
        original_audio, original_lrc = self.mp3.read_bytes(), self.lrc.read_bytes()
        first = save_candidate(self.mp3, self.rows)
        second = save_candidate(self.mp3, self.rows)
        self.assertEqual(first.name, "Song.candidate.lrc")
        self.assertEqual(second.name, "Song.candidate.2.lrc")
        self.assertEqual(self.mp3.read_bytes(), original_audio)
        self.assertEqual(self.lrc.read_bytes(), original_lrc)
        self.assertIn("candidate", first.read_text(encoding="utf-8"))

    def test_invalid_timing_creates_nothing(self):
        with self.assertRaises(ValueError):
            save_candidate(self.mp3, [LyricLine(1, "x"), LyricLine(.2, "y")])
        self.assertEqual(set(p.name for p in self.root.iterdir()), {"Song.mp3", "Song.lrc"})

    def test_same_stem_other_audio_rejected(self):
        (self.root / "song.FLAC").write_bytes(b"other recording")
        with self.assertRaises(FileExistsError):
            save_candidate(self.mp3, self.rows)

    def test_missing_audio_rejected(self):
        with self.assertRaises(ValueError):
            save_candidate(self.root / "absent.mp3", self.rows)

    def test_existing_symlink_candidate_is_not_followed(self):
        link = self.root / "Song.candidate.lrc"
        try:
            link.symlink_to(self.lrc)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks not permitted on this system")
        original = self.lrc.read_bytes()
        path = save_candidate(self.mp3, self.rows)
        self.assertEqual(path.name, "Song.candidate.2.lrc")
        self.assertEqual(self.lrc.read_bytes(), original)

    def test_existing_candidate_not_touched_even_if_modified(self):
        (self.root / "Song.candidate.lrc").write_bytes(b"manual edits")
        save_candidate(self.mp3, self.rows)
        self.assertEqual((self.root / "Song.candidate.lrc").read_bytes(), b"manual edits")


class FakeMusic:
    def __init__(self):
        self.playing = False
        self.loaded = None
        self.starts = []
    def stop(self): self.playing = False
    def load(self, name): self.loaded = name
    def play(self, start=0): self.playing = True; self.starts.append(start)
    def pause(self): self.playing = False
    def unpause(self): self.playing = True
    def get_busy(self): return self.playing
    def unload(self): pass


class FakeMixer:
    def __init__(self):
        self.music = FakeMusic()
    def get_init(self): return True


class FakePygame:
    def __init__(self):
        self.mixer = FakeMixer()


class PlayerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.track = Path(self.tmp.name) / "Recording.mp3"
        self.track.write_bytes(b"fake decoder bytes")
        self.now = [0]
        self.fake = FakePygame()
        self.player = StudioPlayer(self.fake, clock=lambda: self.now[0])

    def test_play_pause_seek_resume_clock(self):
        self.player.load(self.track)
        self.player.play()
        self.now[0] = 3
        self.assertEqual(self.player.position(), 3)
        self.player.pause()
        self.now[0] = 10
        self.assertEqual(self.player.position(), 3)
        self.player.play()
        self.now[0] = 12
        self.assertEqual(self.player.position(), 5)
        self.player.seek(20)
        self.assertEqual(self.player.position(), 20)

    def test_stop_resets_and_closes(self):
        self.player.load(self.track)
        self.player.play()
        self.player.stop()
        self.assertEqual(self.player.position(), 0)
        self.player.close()

    def test_invalid_seek_rejected(self):
        self.player.load(self.track)
        with self.assertRaises(PlaybackError):
            self.player.seek(float("nan"))
        with self.assertRaises(PlaybackError):
            self.player.seek(-1)

    def test_unavailable_format_reports_not_supported(self):
        file = self.track.with_suffix(".opus")
        file.write_bytes(b"audio")
        with self.assertRaises(PlaybackError):
            self.player.load(file)

    def test_player_requires_explicit_audio(self):
        with self.assertRaises(PlaybackError):
            self.player.play()


if __name__ == "__main__":
    unittest.main(verbosity=2)
