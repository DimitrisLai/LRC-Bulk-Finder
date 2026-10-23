"""Provider Intelligence: pure selection, privacy and mocked GUI/worker tests.

No external HTTP, no downloaded lyrics, no user audio. Actual network behavior
is outside CI and requires explicit end-user consent.
"""
from __future__ import annotations
import csv
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from v297_provider_intelligence import (ALL_SOURCES,benchmark,classification,
    report_csv,validate_exclusions,effective_sources)
from v296_provider_tiers import PACKS
from search_profiles import DEFAULT,validate_profile,save_profiles,load_profiles,PROVIDER_FULL


class ExclusionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder=self.temp.name

    def test_legacy_profile_unchanged(self):
        old=validate_profile({"folder":self.folder,"provider_pack":"legacy"})
        self.assertEqual(old["provider_exclusions"],[])
        self.assertEqual(old["provider_mode"],"full")

    def test_tier2_minus_lrcapi_is_exact_tier1(self):
        selected=effective_sources("2",(),["lrcapi"])
        self.assertEqual(selected,PACKS["1"])
        self.assertEqual(PACKS["2"][-1],"LrcAPI")

    def test_exclusions_reject_wrong_tier_and_duplicates_and_disabling_everything(self):
        for excluded in (["Tencent"],["LRCLIB","SyncLRC","Unison"],
                         ["Unison","unison"],"LRCLIB",["Bad Source"]):
            with self.subTest(excluded=excluded):
                with self.assertRaises(ValueError):
                    validate_profile({"folder":self.folder,"provider_pack":"1",
                                      "provider_exclusions":excluded})

    def test_custom_order_can_keep_disabled_provider_for_reenable(self):
        profile=validate_profile({"folder":self.folder,"provider_pack":"2",
           "provider_exclusions":["LrcAPI"],"order":"c",
           "custom_order":",".join(reversed(PACKS["2"]))})
        self.assertEqual(profile["provider_exclusions"],["LrcAPI"])

    def test_round_trip_keeps_exclusion_list(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"profiles.json"
            p=validate_profile({"folder":self.folder,"provider_pack":"5",
                                "provider_exclusions":["BetterQQ","YouLyTTML"]})
            save_profiles({"Trial":p},path)
            restored=load_profiles(path)["Trial"]
            self.assertEqual(restored["provider_exclusions"],["BetterQQ","YouLyTTML"])
            self.assertEqual(restored["provider_pack"],"5")
            self.assertEqual(restored["limit"],"20")

    def test_legacy_full_with_experimental_source_can_be_excluded(self):
        result=validate_profile({"folder":self.folder,"provider_pack":"legacy",
             "provider_mode":"full","experimental_simpmusic":True,
             "provider_exclusions":["SimpMusic"]})
        self.assertEqual(result["provider_exclusions"],["SimpMusic"])


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.audio=self.root/"Original & untouched.mp3"
        self.audio.write_bytes(b"this is just a dummy test fixture")
        self.info=lambda path:("Test Song","Test Artist","Test Album",185.0)

    def test_benchmark_reports_unique_contributions_without_writing_lyrics(self):
        import LRC_Bulk_Finder as engine
        called=[]
        class Found:
            verified=True
        def search(t,a,album,duration,review,**kwargs):
            source=kwargs["only_providers"][0]
            called.append(source)
            if source in ("LRCLIB","SyncLRC"):
                return Found(),"SAVED","mocked verified", [source+"=SAVED"]
            if source=="Unison":
                review.add("Unison",t,a,"needs review",lyrics="[00:01.00] Test line")
                return None,"REVIEW_AVAILABLE","mocked candidate",["Unison=REVIEW_AVAILABLE"]
            return None,"NOT_FOUND","mocked no match",[source+"=NO_MATCH"]
        previous={key:getattr(engine,key) for key in
                  ("HISTORY_ENABLED","MB_ENABLED","GREEK_MODE","G2G_ENABLED",
                   "LOCAL_LRCLIB","STAGED_ONLINE_MODE","COMPLETE_FIRST_PASS",
                   "ACTIVE_PROVIDERS")}
        prior_blocked=dict(engine.blocked)
        try:
            with mock.patch.object(engine,"save_hit",side_effect=AssertionError("Must NEVER save")),\
                 mock.patch.object(engine,"export_review_candidates",side_effect=AssertionError("Must NEVER save candidates")):
                stats,report,stopped=benchmark(
                   self.root,"1","fast",[],5,True,runner=search,
                   source_files=[self.audio],read_info=self.info,report_folder=self.root/"reports")
        finally:
            for key,value in previous.items():setattr(engine,key,value)
            engine.blocked.clear();engine.blocked.update(prior_blocked)
        self.assertEqual(called,list(PACKS["1"]))
        self.assertFalse(stopped)
        self.assertEqual(stats["LRCLIB"]["verified"],1)
        self.assertEqual(stats["LRCLIB"]["unique"],1)
        self.assertEqual(stats["SyncLRC"]["verified"],1)
        self.assertEqual(stats["SyncLRC"]["unique"],0)
        self.assertEqual(stats["Unison"]["review"],1)
        self.assertTrue(report.exists())
        self.assertEqual(self.audio.read_bytes(),b"this is just a dummy test fixture")
        self.assertFalse(self.audio.with_suffix(".lrc").exists())
        self.assertFalse(self.audio.with_suffix(".candidate.lrc").exists())
        csv_text=report.read_text(encoding="utf-8-sig")
        self.assertNotIn("Test Song",csv_text)
        self.assertNotIn("Test Artist",csv_text)
        self.assertNotIn("Original & untouched",csv_text)
        with report.open(encoding="utf-8-sig",newline="") as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]["unique_verified_matches"],"1")

    def test_benchmark_cannot_run_all_excluded_or_bad_sample(self):
        with self.assertRaises(ValueError):
            benchmark(self.root,"1","fast",list(PACKS["1"]),5,True,
                     source_files=[self.audio],read_info=self.info,
                     report_folder=self.root/"reports")
        with self.assertRaises(ValueError):
            benchmark(self.root,"1","fast",[],500,True,
                     source_files=[self.audio],read_info=self.info,
                     report_folder=self.root/"reports")

    def test_classification_discriminates_review_timeout_and_skipped(self):
        self.assertEqual(classification(None,"REVIEW_AVAILABLE",[],1),"review")
        self.assertEqual(classification(None,"TIMEOUT",["LRCLIB=ERROR (timed out)"],0),"timeout")
        self.assertEqual(classification(None,"SERVER_ERROR",["LRCLIB=ERROR (HTTP 401)"],0),"error")
        self.assertEqual(classification(None,"NOT_FOUND",["LRCLIB=SKIPPED (cooldown)"],0),"skipped")

    def test_report_uses_collision_free_name(self):
        values={"LRCLIB":{"attempts":1,"verified":1,"unique":1,"review":0,
                "no_match":0,"timeout":0,"error":0,"skipped":0,"seconds":2}}
        p1=report_csv(values,1,1,2,folder=self.root)
        p2=report_csv(values,1,1,2,folder=self.root)
        self.assertNotEqual(p1,p2)
        self.assertTrue(p1.is_file() and p2.is_file())


def has_display():
    try:
        import tkinter as tk
        app=tk.Tk();app.withdraw();app.destroy();return True
    except Exception:return False


@unittest.skipUnless(has_display(),"No Tk display")
class GuiExclusionsAndBenchmark(unittest.TestCase):
    def setUp(self):
        from LRC_Control_Center import ControlCenter
        self.home=tempfile.TemporaryDirectory()
        self.addCleanup(self.home.cleanup)
        self.env=mock.patch.dict(os.environ,{"APPDATA":self.home.name})
        self.env.start();self.addCleanup(self.env.stop)
        self.app=ControlCenter();self.app.withdraw()
        self.addCleanup(self.app.destroy)
        self.app.folder.set(self.home.name)

    def test_benchmark_panel_and_checkboxes_exist(self):
        self.assertTrue(self.app.benchmark_start_button.winfo_exists())
        self.assertTrue(self.app.benchmark_tree.winfo_exists())
        self.assertEqual(len(self.app.source_enabled),14)

    def test_switch_tier_preserves_other_settings_and_saved_checkboxes(self):
        from v296_provider_tiers import DISPLAY
        app=self.app
        app.limit.set("20")
        app.provider_pack.set(DISPLAY["2"])
        app._pack_changed()
        app.source_enabled["LrcAPI"].set(False)
        profile=app._values()
        self.assertEqual(profile["provider_exclusions"],["LrcAPI"])
        app._set_values(profile)
        self.assertFalse(app.source_enabled["LrcAPI"].get())
        app.provider_pack.set(DISPLAY["1"])
        app._pack_changed()
        self.assertTrue(app.source_enabled["LrcAPI"].get())
        self.assertEqual(app.limit.get(),"20")

    def test_benchmark_spawns_only_with_consent_without_search(self):
        from v296_provider_tiers import DISPLAY
        app=self.app
        app.provider_pack.set(DISPLAY["1"])
        app._pack_changed()
        app.source_enabled["Unison"].set(False)
        app.benchmark_sample.set("5")
        class Fake:
            poll=lambda self:None
            stdout=iter([])
        with mock.patch.object(app,"_dialog",return_value=True),\
             mock.patch("subprocess.Popen",return_value=Fake()) as popen,\
             mock.patch("threading.Thread") as thread:
            app._start_provider_benchmark()
        arguments=popen.call_args.args[0]
        self.assertIn("--benchmark",arguments)
        self.assertEqual(arguments[arguments.index("--benchmark-excluded")+1],"Unison")
        self.assertEqual(arguments[arguments.index("--benchmark-sample")+1],"5")
        self.assertIsNone(app.process)
        self.assertTrue(thread.called)

    def test_no_consent_never_calls_worker(self):
        app=self.app
        with mock.patch.object(app,"_dialog",return_value=False),\
             mock.patch("subprocess.Popen") as popen:
            app._start_provider_benchmark()
        popen.assert_not_called()


if __name__=="__main__":
    unittest.main()
