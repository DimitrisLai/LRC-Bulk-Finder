"""v2.3 saved-profile, GUI helper, progress and candidate safety tests.

Offline-only: no network, no real audio files, no user profile writes.
"""
from __future__ import annotations
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from search_profiles import (DEFAULT,PROVIDER_FAST,PROVIDER_FULL,
    ProfileAnswers,answers_for_profile,load_profiles,save_profiles,
    validate_profile,profile_file)
from review_candidates_gui import (
    list_review_candidates,preview_candidate,explicitly_promote,candidate_index)
from progress_eta import RoundProgress,format_seconds
from run_saved_profile import run_profile

LRC="[00:06.00] One\n[00:34.10] Two\n[01:25.00] Chorus\n[02:44.20] Ending\n"


def sample(folder,**changes):
    return {**DEFAULT,"folder":str(folder),**changes}


class UXV23Tests(unittest.TestCase):

    def test_01_save_load_unicode_profiles_and_atomic_write(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"users"/"profiles.json"
            examples={"Greek FULL":sample(d,action="5",limit="a"),
                      "Δοκιμή 20":sample(d,action="4",musicbrainz=False,limit="20")}
            self.assertEqual(save_profiles(examples,path),path)
            self.assertEqual(load_profiles(path),examples)
            self.assertFalse(path.with_name(path.name+".tmp").exists())
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["schema"],1)

    def test_02_reject_corrupt_profile_without_overwriting_original(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"profiles.json"
            path.write_text("{invalid json",encoding="utf-8")
            with self.assertRaises(ValueError):
                load_profiles(path)
            self.assertEqual(path.read_text(encoding="utf-8"),"{invalid json")

    def test_03_reject_nonstandard_or_extra_settings(self):
        with tempfile.TemporaryDirectory() as d:
            for change in [{"action":"2"},{"limit":"0"},{"limit":"bad"},
                           {"greek":False,"local_ai":True},
                           {"order":"shell"}, {"provider_mode":"UNSAFE"},
                           {"recursive":"yes"}]:
                with self.subTest(change=change):
                    with self.assertRaises(ValueError):
                        validate_profile(sample(d,**change))
            clean=validate_profile({**sample(d),"dangerous_extra":"ignored"})
            self.assertNotIn("dangerous_extra",clean)

    def test_04_custom_provider_order_never_silently_drops_routes(self):
        with tempfile.TemporaryDirectory() as d:
            ordered=",".join(reversed(PROVIDER_FULL))
            config=validate_profile(sample(d,order="c",custom_order=ordered,limit="a"))
            self.assertEqual(config["custom_order"],ordered)
            with self.assertRaises(ValueError):
                validate_profile(sample(d,order="c",custom_order="LRCLIB,Unison"))
            for provider_mode,providers in (("fast",PROVIDER_FAST),("full",PROVIDER_FULL)):
                self.assertEqual(len(providers),5 if provider_mode=="fast" else 12)

    def test_05_profile_prompt_order_full_greek(self):
        with tempfile.TemporaryDirectory() as d:
            p=sample(d,action="5",limit="a",greek=True,local_ai=True)
            items=answers_for_profile(p)
            expected=["Choose [1/2/3/4/5]","Greeklish / Greek folder?",
                     "Use your installed LOCAL G2G AI model?",
                     "MusicBrainz extra artist/title metadata",
                     "Search mode: FAST","Provider order?",
                     "Wait for temporary provider recovery","Include subfolders?",
                     "Skip identical provider searches",
                     "How many missing songs?","Optional LRCLIB exact-signature fallback",
                     "After the Greek/AI preview"]
            self.assertEqual([a for a,b in items],expected)
            obj=ProfileAnswers(p)
            self.assertEqual([obj(x+" : ") for x in expected],
                             [answer for x,answer in items])
            self.assertEqual(obj.position,len(expected))

    def test_06_profile_prompt_order_english_and_offline(self):
        with tempfile.TemporaryDirectory() as d:
            english=answers_for_profile(sample(d,greek=False,action="1"))
            self.assertFalse(any("local G2G" in x or "Greek/AI preview" in x for x,_ in english))
            offline=answers_for_profile(sample(d,action="4",greek=True,local_ai=False))
            self.assertEqual(offline[-1],("Start offline-only scan?","y"))
            self.assertFalse(any("MusicBrainz" in x or "Provider order?" in x for x,_ in offline))

    def test_07_unknown_prompts_fail_closed_instead_of_hanging(self):
        with tempfile.TemporaryDirectory() as d:
            prompt=ProfileAnswers(sample(d))
            with self.assertRaises(RuntimeError):
                prompt("Delete all songs? ")
            self.assertEqual(prompt.position,0)
            with self.assertRaises(RuntimeError):
                prompt("Path to existing .sqlite3 file (Enter to cancel): ")

    def test_08_database_prompt_uses_saved_database_path(self):
        with tempfile.TemporaryDirectory() as d:
            p=ProfileAnswers(sample(d,database=str(Path(d)/"large.sqlite3")))
            self.assertEqual(p("Path to existing .sqlite3 file (Enter to cancel): "),
                             str(Path(d)/"large.sqlite3"))

    def test_09_runner_restores_cli_functions_even_if_program_errors(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"profiles.json"
            save_profiles({"Demo":sample(d)},path)
            import LRC_Bulk_Finder as app
            original=app.select_folder
            with mock.patch.object(app,"main",side_effect=ValueError("test aborted")):
                with self.assertRaisesRegex(ValueError,"test aborted"):
                    run_profile("Demo",path)
            self.assertIs(app.select_folder,original)

    def test_10_candidate_discovery_primary_and_numbered(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            nested=folder/"sub";nested.mkdir()
            (nested/"Track.mp3").write_bytes(b"DO NOT MODIFY")
            (nested/"Track.candidate.lrc").write_text(LRC,encoding="utf-8")
            (nested/"Track.candidate.2.lrc").write_text(LRC,encoding="utf-8")
            (nested/"Track.candidate.3.lrc").write_text(LRC,encoding="utf-8")
            self.assertEqual(list_review_candidates(folder,recursive=False),[])
            results=list_review_candidates(folder,recursive=True)
            self.assertEqual([r["index"] for r in results],[1,2,3])
            self.assertTrue(all(x["has_mp3"] for x in results))
            self.assertTrue(all(not x["has_lrc"] for x in results))
            self.assertEqual(candidate_index(nested/"Track.candidate.2.lrc"),2)

    def test_11_candidate_preview_is_read_only_and_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"A.candidate.lrc";f.write_text(LRC,encoding="utf-8")
            before=f.read_bytes()
            self.assertEqual(preview_candidate(f),LRC)
            self.assertEqual(f.read_bytes(),before)
            with self.assertRaises(ValueError):
                preview_candidate(f,max_bytes=2)
            with self.assertRaises(ValueError):
                preview_candidate(Path(d)/"A.lrc")

    def test_12_promoting_without_explicit_confirmation_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"A.candidate.lrc";f.write_text(LRC,encoding="utf-8")
            with self.assertRaises(PermissionError):
                explicitly_promote(f,approved=False)
            with self.assertRaises(ValueError):
                explicitly_promote(Path(d)/"A.candidate.2.lrc",approved=True)
            self.assertTrue(f.exists())

    def test_13_confirmed_promotion_creates_marked_lrc_without_touching_mp3(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            mp3=folder/"Song.mp3";mp3.write_bytes(b"PROTECTED_MP3")
            primary=folder/"Song.candidate.lrc";primary.write_text(LRC,encoding="utf-8")
            alt=folder/"Song.candidate.2.lrc";alt.write_text(LRC,encoding="utf-8")
            status,reason=explicitly_promote(primary,approved=True)
            self.assertEqual(status,"PROMOTED",reason)
            self.assertEqual(mp3.read_bytes(),b"PROTECTED_MP3")
            self.assertTrue((folder/"Song.lrc").read_text(encoding="utf-8").startswith(
                "[00:00.00] candidate"))
            self.assertTrue(primary.exists(),"Alternative must be shifted to primary")
            self.assertFalse(alt.exists())

    def test_14_promotion_refuses_existing_approved_lrc(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            (folder/"Song.mp3").write_bytes(b"MP3")
            (folder/"Song.candidate.lrc").write_text(LRC,encoding="utf-8")
            verified=folder/"Song.lrc"
            verified.write_text("[00:02.00] Existing lyrics",encoding="utf-8")
            status,_=explicitly_promote(folder/"Song.candidate.lrc",approved=True)
            self.assertEqual(status,"SKIPPED")
            self.assertEqual(verified.read_text(encoding="utf-8"),
                             "[00:02.00] Existing lyrics")

    def test_15_progress_eta_respects_unfinished_and_replayed_tracks(self):
        ticks=[0]
        def fake_clock():
            ticks[0]+=1
            return ticks[0]
        progress=RoundProgress(6,2,clock=fake_clock)
        self.assertIsNone(progress.status()["remaining"])
        progress.complete(10)
        progress.complete(20)
        self.assertIsNone(progress.status()["remaining"])
        progress.complete(30)
        self.assertEqual(progress.status()["remaining"],60.0)
        progress.complete(0,checkpoint=True)
        self.assertEqual(progress.status()["remaining"],40.0)
        self.assertEqual(progress.status()["samples"],3)
        self.assertIn("THIS ROUND ETA:",progress.line())
        self.assertEqual(format_seconds(3665),"1h 01m")

    def test_16_progress_zero_total_and_clamp(self):
        p=RoundProgress(0,"OFFLINE",clock=lambda:0)
        self.assertEqual(p.status()["percent"],100.0)
        p2=RoundProgress(1,1,clock=lambda:0)
        p2.complete(1)
        p2.complete(1)
        self.assertEqual(p2.status()["percent"],100.0)

    def test_17_tkinter_control_center_module_import_only(self):
        # Creating a window requires GUI display; import is safe on headless CI.
        import LRC_Control_Center as ui
        self.assertTrue(callable(ui.main))
        self.assertTrue(hasattr(ui.ControlCenter,"_promote_selected"))


if __name__=="__main__":
    unittest.main(verbosity=2)
