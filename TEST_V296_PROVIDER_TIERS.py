"""v2.9.6 source-pack regression, offline/no-network/no-user-MP3 tests."""
from __future__ import annotations
import csv
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import search_profiles
import v296_provider_tiers as tiers


class TierTests(unittest.TestCase):
    def test_first_two_exact(self):
        self.assertEqual(tiers.PACKS["1"],("LRCLIB","SyncLRC","Unison"))
        self.assertEqual(tiers.PACKS["2"],("LRCLIB","SyncLRC","Unison","LrcAPI"))

    def test_all_six_strictly_cumulative_without_duplicates(self):
        prev=()
        for key in "123456":
            names=tiers.PACKS[key]
            self.assertEqual(names[:len(prev)],prev)
            self.assertEqual(len(names),len(set(names)))
            prev=names
        self.assertEqual([len(tiers.PACKS[p]) for p in "123456"],[3,4,7,9,13,14])
        self.assertIn("BetterQQ",tiers.PACKS["5"])
        self.assertIn("SimpMusic",tiers.PACKS["6"])
        self.assertNotIn("BetterQQ",tiers.PACKS["1"])

    def test_existing_saved_profiles_preserve_fast_full_modes(self):
        with tempfile.TemporaryDirectory() as temp:
            base={"folder":temp,"action":"1","greek":False}
            for mode in ("fast","full"):
                data=search_profiles.validate_profile({**base,"provider_mode":mode})
                self.assertEqual(data["provider_pack"],tiers.LEGACY)
                self.assertEqual(tiers.select_pack(
                    data["provider_pack"],search_profiles.PROVIDER_FAST,
                    search_profiles.PROVIDER_FULL if mode=="full" else search_profiles.PROVIDER_FAST),
                    search_profiles.PROVIDER_FULL if mode=="full" else search_profiles.PROVIDER_FAST)

    def test_custom_order_validated_for_exact_selected_tier(self):
        with tempfile.TemporaryDirectory() as temp:
            all_4=",".join(reversed(tiers.PACKS["2"]))
            good=search_profiles.validate_profile({
                "folder":temp,"action":"1","provider_mode":"fast",
                "provider_pack":"2","order":"c","custom_order":all_4,
            })
            self.assertEqual(good["provider_pack"],"2")
            with self.assertRaisesRegex(ValueError,"CUSTOM"):
                search_profiles.validate_profile({
                    **good,"provider_pack":"1",
                })
            with self.assertRaises(ValueError):
                search_profiles.validate_profile({**good,"provider_pack":"unknown"})

    def test_profile_json_roundtrip_keeps_pack_and_local_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"profiles.json"
            data=search_profiles.validate_profile({"folder":temp,"provider_pack":"5"})
            search_profiles.save_profiles({"Tier MAX test":data},path)
            loaded=search_profiles.load_profiles(path)
            self.assertEqual(loaded["Tier MAX test"]["provider_pack"],"5")
            self.assertTrue(loaded["Tier MAX test"]["recursive"])

    def test_every_existing_preset_defaults_to_legacy(self):
        for name,fields in search_profiles.PRESET_TEMPLATES.items():
            with self.subTest(name=name):
                self.assertEqual(fields.get("provider_pack",tiers.LEGACY),tiers.LEGACY)


class QrcTests(unittest.TestCase):
    XML='<QrcInfos><LyricInfo><Lyric_1 LyricType="1" LyricContent="[0,900]Hi(0,300) all(300,400)&#10;[1000,1400]Hello(1000,700) again(1700,300)&#10;[2800,1200]Third(2800,1200)"/></LyricInfo></QrcInfos>'
    def test_qrc_words_to_plain_line_lrc(self):
        text=tiers.qrc_to_lrc(self.XML)
        self.assertIn("[00:00.00] Hi all",text)
        self.assertIn("[00:01.00] Hello again",text)
        self.assertIn("[00:02.80] Third",text)
        self.assertNotIn("(1700,300)",text)

    def test_reject_invalid_or_non_qrc(self):
        for raw in ("", "<unknown/>","<QrcInfos><Lyric","X"*2000001):
            self.assertEqual(tiers.qrc_to_lrc(raw),"")

    def test_qq_never_returns_autosave_even_with_plausible_text(self):
        result=[]
        class Review:
            def add(self,*args,**kwargs): result.append((args,kwargs))
        provider_reply={"provider":"qq","lyrics":self.XML}
        found=tiers.better_qq_review_only(
            "Song","Artist","",4.0,Review(),
            direct_json=lambda *args:provider_reply,
            query_variants=lambda title,artist:[(title,artist)],
            synced_payload=lambda raw,fmt:raw,
            plausible_lrc=lambda raw,duration:len(raw.splitlines())>=3
        )
        self.assertIsNone(found)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0][0][0],"BetterQQ")
        self.assertIn("Manual",result[0][0][3])


def can_tk():
    try:
        import tkinter as tk
        w=tk.Tk()
        w.withdraw()
        w.destroy()
        return True
    except Exception:return False


@unittest.skipUnless(can_tk(),"No graphical desktop in this test environment")
class TierGuiTests(unittest.TestCase):
    def setUp(self):
        from LRC_Control_Center import ControlCenter
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        env=mock.patch.dict(os.environ,{"APPDATA":self.temp.name})
        env.start()
        self.addCleanup(env.stop)
        self.root=ControlCenter()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)

    def test_all_tiers_selectable_and_save_roundtrip(self):
        app=self.root
        app.folder.set(self.temp.name)
        for key,text in tiers.DISPLAY.items():
            with self.subTest(tier=key):
                app.provider_pack.set(app._tr(text))
                self.assertEqual(app._values()["provider_pack"],key)
        app.provider_pack.set(tiers.DISPLAY["2"])
        profile=app._values()
        app._set_values(profile)
        self.assertEqual(app._values()["provider_pack"],"2")

    def test_greek_english_label_still_same_tier(self):
        app=self.root
        app.folder.set(self.temp.name)
        app.provider_pack.set(tiers.DISPLAY["5"])
        app.language_choice.set("Ελληνικά")
        app._language_selected()
        self.assertEqual(app._values()["provider_pack"],"5")
        app.language_choice.set("English")
        app._language_selected()
        self.assertEqual(app._values()["provider_pack"],"5")

    def test_switch_tier_does_not_start_search_or_change_limit(self):
        app=self.root
        app.folder.set(self.temp.name)
        app.limit.set("20")
        app.action.set("1")
        with mock.patch.object(app,"_run_profile") as start:
            app.provider_pack.set(tiers.DISPLAY["6"])
            app._pack_changed()
            start.assert_not_called()
        self.assertEqual(app.limit.get(),"20")
        self.assertEqual(app.action.get(),"1")


if __name__=="__main__":
    unittest.main()
