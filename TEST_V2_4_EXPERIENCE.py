"""v2.4 built-in presets, incremental tracking, extra audio and draft-only sync.

Only temporary fixture audio / data. No HTTP or installation actions.
"""
from __future__ import annotations
import os
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

import LRC_Bulk_Finder as app
from incremental_library import IncrementalLibrary,audio_files,safe_audio_files
from search_profiles import (DEFAULT,PRESET_TEMPLATES,PRESET_DESCRIPTIONS,
                             preset_profile,validate_profile)
from lyric_sync_lab import (plain_lines,estimate_timestamps,draft_lrc,
                            save_unverified_draft,candidate_output_path)
from review_candidates_gui import list_review_candidates,explicitly_promote

class ExperienceTests(unittest.TestCase):
    def tearDown(self):
        if app.LIBRARY_INDEX is not None:
            app.LIBRARY_INDEX.close()
            app.LIBRARY_INDEX=None

    def test_presets_cover_greek_normal_night_offline_ai_and_fast(self):
        self.assertGreaterEqual(len(PRESET_TEMPLATES),15)
        self.assertTrue({
            "Greek FULL — Offline First", "Greek Night Search — Maximum Coverage",
            "Greek Quick Test — 20 Songs", "Greek OFFLINE ONLY",
            "Greek Local AI — FULL", "International FAST — 20 Songs",
        }.issubset(PRESET_TEMPLATES))
        with tempfile.TemporaryDirectory() as folder:
            for name in PRESET_TEMPLATES:
                p=preset_profile(name,folder)
                self.assertTrue(p["folder"])
                self.assertTrue(p["incremental"])
                self.assertIn(name,PRESET_DESCRIPTIONS)
            night=preset_profile("Greek Night Search — Maximum Coverage",folder)
            self.assertEqual(night["action"],"5")
            self.assertTrue(night["recovery_wait"])
            self.assertEqual(night["limit"],"a")
            self.assertFalse(night["history"])
            offline=preset_profile("Greek OFFLINE ONLY",folder)
            self.assertEqual(offline["action"],"4")
            self.assertFalse(offline["musicbrainz"])
            ai=preset_profile("Greek Local AI — FULL",folder)
            self.assertTrue(ai["local_ai"])
            normal=preset_profile("Greek FULL — Offline First",folder)
            self.assertFalse(normal["local_ai"])
            self.assertFalse(normal["recovery_wait"])

    def test_incremental_profile_is_boolean_and_legacy_defaults_true(self):
        with tempfile.TemporaryDirectory() as folder:
            config=validate_profile({"folder":folder})
            self.assertTrue(config["incremental"])
            with self.assertRaises(ValueError):
                validate_profile({"folder":folder,"incremental":"True"})
            self.assertFalse(validate_profile({"folder":folder,"incremental":False})["incremental"])

    def test_audio_extensions_and_conflicting_sidecar_names_are_safe(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            for suffix in (".mp3",".flac",".m4a",".ogg",".opus",".wav",".mp4"):
                (base/("Unique"+suffix[1:]+suffix)).write_bytes(b"NO REAL AUDIO NEEDED")
            names=audio_files(base)
            self.assertEqual(len(names),7)
            (base/"Overlap.mp3").write_bytes(b"X")
            (base/"Overlap.flac").write_bytes(b"Y")
            safe,conflicts=safe_audio_files(base)
            self.assertEqual(len(safe),7)
            self.assertEqual(len(conflicts),2)

    def test_incremental_index_caches_metadata_and_detects_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            wav=base/"Test.wav"
            with wave.open(str(wav),"wb") as wave_writer:
                wave_writer.setnchannels(1)
                wave_writer.setsampwidth(2)
                wave_writer.setframerate(8000)
                wave_writer.writeframes(b"\x00\x00"*8000)
            calls=[]
            def parser(_):
                calls.append(1)
                return "Song","Artist","Album",1.0
            idx=IncrementalLibrary(base)
            try:
                first=idx.inventory([wav])
                self.assertEqual(first["new"],1)
                self.assertEqual(idx.metadata(wav,parser)[0],"Song")
                self.assertEqual(idx.metadata(wav,parser)[0],"Song")
                self.assertEqual(len(calls),1)
                (base/"Test.lrc").write_text("[00:00.01] Existing",encoding="utf-8")
                again=idx.inventory([wav])
                self.assertEqual(again["changed"],1)
                idx.metadata(wav,parser)
                self.assertEqual(len(calls),1,"Sidecar change should not invalidate audio metadata")
                wav.write_bytes(wav.read_bytes()+b"changed")
                idx.inventory([wav])
                idx.metadata(wav,parser)
                self.assertEqual(len(calls),2)
                self.assertGreaterEqual(idx.stats["metadata_hits"],2)
            finally:idx.close()
            idx2=IncrementalLibrary(base)
            try:
                self.assertEqual(idx2.inventory([wav])["unchanged"],1)
                idx2.metadata(wav,parser)
                self.assertEqual(len(calls),2)
            finally:idx2.close()

    def test_real_wav_metadata_read_only_support(self):
        with tempfile.TemporaryDirectory() as folder:
            audio=Path(folder)/"Singer - WAV Track.wav"
            with wave.open(str(audio),"wb") as output:
                output.setnchannels(1);output.setsampwidth(2);output.setframerate(8000)
                output.writeframes(b"\x00\x00"*16000)
            before=audio.read_bytes()
            title,artist,album,length=app.song_info(audio)
            self.assertEqual((title,artist),("WAV Track","Singer"))
            self.assertAlmostEqual(length,2,places=1)
            self.assertEqual(audio.read_bytes(),before)

    def test_sync_estimates_marked_only_and_never_overwrite_existing(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            audio=root/"Singer - Untimed.mp3";audio.write_bytes(b"AUDIO UNCHANGED")
            lines=plain_lines("[Verse 1]\nThe first lyric\n\nNext lyric\nOne more lyric")
            self.assertEqual(len(lines),3)
            times=estimate_timestamps(lines,180)
            draft=draft_lrc(lines,times)
            self.assertTrue(draft.startswith("[00:00.00] candidate\n"))
            before=audio.read_bytes()
            candidate=save_unverified_draft(audio,draft,lines,times)
            self.assertEqual(candidate.name,"Singer - Untimed.candidate.lrc")
            self.assertEqual(audio.read_bytes(),before)
            second=save_unverified_draft(audio,draft,lines,times)
            self.assertEqual(second.name,"Singer - Untimed.candidate.2.lrc")
            self.assertEqual(len(list_review_candidates(folder)),2)
            audio.with_suffix(".lrc").write_text("APPROVED",encoding="utf-8")
            with self.assertRaises(FileExistsError):
                save_unverified_draft(audio,draft,lines,times)
            self.assertEqual(audio.with_suffix(".lrc").read_text(encoding="utf-8"),"APPROVED")

    def test_sync_manual_edited_times_reject_bad_lines_and_marker_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            audio=Path(folder)/"Song.opus";audio.write_bytes(b"TEST")
            lines=["One","Two"]
            times=[2.0,4.0]
            lrc=draft_lrc(lines,times)
            for edited in (lrc.replace("[00:00.00] candidate\n",""),
                           lrc.replace("[00:04.00]","[00:01.00]"),
                           lrc.replace("[00:04.00]","[00:80.00]"),
                           lrc.replace("[00:04.00] Two","no timestamp")):
                with self.subTest(edited=edited):
                    with self.assertRaises(ValueError):
                        save_unverified_draft(audio,edited,lines,times)
            candidate=save_unverified_draft(audio,lrc,lines,times)
            self.assertTrue(candidate.is_file())

    def test_sync_rejects_shared_stem_with_other_audio_format(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            mp3=base/"Song.mp3";mp3.write_bytes(b"A")
            (base/"Song.flac").write_bytes(b"B")
            lines=["One","Two"];times=[1,2]
            with self.assertRaises(FileExistsError):
                save_unverified_draft(mp3,draft_lrc(lines,times),lines,times)

    def test_review_candidate_flac_and_opus_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            audio=base/"Singer - Song.flac";audio.write_bytes(b"SAFE FLAC")
            candidate=base/"Singer - Song.candidate.lrc"
            candidate.write_text("[00:03.00] First\n[00:06.00] Second\n")
            items=list_review_candidates(base)
            self.assertTrue(items[0]["has_mp3"])
            self.assertEqual(items[0]["mp3"].suffix,".flac")
            self.assertEqual(len(items),1)

    def test_gui_module_import_and_tooltip_available(self):
        from LRC_Control_Center import ControlCenter
        from tooltip_help import ToolTip
        self.assertTrue(callable(ControlCenter._build_sync_lab))
        self.assertTrue(callable(ControlCenter._launch_setup))
        self.assertTrue(callable(ToolTip))

if __name__=="__main__":
    unittest.main(verbosity=2)
