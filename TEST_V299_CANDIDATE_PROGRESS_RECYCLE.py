"""v2.9.9 Candidate Review progress bar and Recycle Bin safety tests.

All destructive effects simulated with a disposable-file recycler. Never sends
real user files to Trash and never needs OS Recycle Bin in CI.
"""
from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from v298_candidate_workbench import (bulk_recycle_alternatives,
                                      selected_alternative_paths)
from review_candidates_gui import list_review_candidates


class RecycleSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.audio=self.folder/"Artist - Song.wav"
        self.audio.write_bytes(b"IMMUTABLE AUDIO")
        self.primary=self.folder/"Artist - Song.candidate.lrc"
        self.primary.write_text("[00:01.00] primary\n")
        self.alts=[]
        for n in (2,3,4):
            alt=self.folder/f"Artist - Song.candidate.{n}.lrc"
            alt.write_text(f"[00:01.00] alternative {n}\n")
            self.alts.append(alt)

    def fake_recycle(self,path):
        Path(path).unlink()  # Simulates OS Trash only inside disposable temp dir

    def test_selection_includes_only_numbered_alternatives(self):
        items=list_review_candidates(self.folder)
        self.assertEqual(selected_alternative_paths(items),self.alts)
        self.assertEqual([x["index"] for x in items],[1,2,3,4])

    def test_explicit_confirmation_required(self):
        with self.assertRaises(PermissionError):
            bulk_recycle_alternatives([self.alts[0]],self.folder,
                                      recycler=self.fake_recycle)
        self.assertTrue(self.alts[0].exists())

    def test_primary_and_installed_lrc_cannot_be_recycled(self):
        lrc=self.folder/"Artist - Song.lrc"
        lrc.write_bytes(b"DO NOT DELETE")
        for forbidden in (self.primary,lrc,self.audio):
            with self.subTest(name=forbidden.name),self.assertRaises(ValueError):
                bulk_recycle_alternatives([forbidden],self.folder,
                                          approved=True,recycler=self.fake_recycle)
            self.assertTrue(forbidden.exists())
        self.assertEqual(self.audio.read_bytes(),b"IMMUTABLE AUDIO")
        self.assertEqual(lrc.read_bytes(),b"DO NOT DELETE")

    def test_outside_folder_and_nonrecursive_subfolders_blocked(self):
        sub=self.folder/"album";sub.mkdir()
        path=sub/"X.candidate.2.lrc";path.write_text("test")
        with self.assertRaises(ValueError):
            bulk_recycle_alternatives([path],self.folder,recursive=False,
                                      approved=True,recycler=self.fake_recycle)
        with self.assertRaises(ValueError):
            bulk_recycle_alternatives([self.alts[0],self.alts[0]],self.folder,
                                      approved=True,recycler=self.fake_recycle)
        outside=self.folder.parent/"X.candidate.2.lrc"
        with self.assertRaises(ValueError):
            bulk_recycle_alternatives([outside],self.folder,
                                      approved=True,recycler=self.fake_recycle)

    def test_symlink_guard(self):
        if not hasattr(os,"symlink"):self.skipTest("No symlink support")
        link=self.folder/"symlink.candidate.2.lrc"
        try:link.symlink_to(self.alts[0])
        except (OSError,NotImplementedError):self.skipTest("Symlinks need privileges")
        with self.assertRaises(ValueError):
            bulk_recycle_alternatives([link],self.folder,
                                      approved=True,recycler=self.fake_recycle)
        self.assertTrue(self.alts[0].exists())

    def test_multi_recycle_progress_and_no_primary_or_audio_change(self):
        events=[]
        counts,detail=bulk_recycle_alternatives(
            self.alts,self.folder,approved=True,recycler=self.fake_recycle,
            report=lambda done,total,path,status,message:events.append((done,total,status)))
        self.assertEqual(counts,{"RECYCLED":3})
        self.assertEqual(events,[(1,3,"RECYCLED"),(2,3,"RECYCLED"),(3,3,"RECYCLED")])
        self.assertEqual(len(detail),3)
        self.assertTrue(self.primary.exists())
        self.assertEqual(self.audio.read_bytes(),b"IMMUTABLE AUDIO")
        self.assertFalse(any(path.exists() for path in self.alts))

    def test_trash_failure_never_falls_back_to_permanent_unlink(self):
        def broken(path):
            raise OSError("Recycle Bin unavailable")
        counts,_=bulk_recycle_alternatives(
            [self.alts[0]],self.folder,approved=True,recycler=broken)
        self.assertEqual(counts,{"ERROR":1})
        self.assertTrue(self.alts[0].exists())

    def test_stop_between_candidates(self):
        events=[]
        counts,_=bulk_recycle_alternatives(self.alts,self.folder,
            approved=True,recycler=self.fake_recycle,
            report=lambda done,total,*args:events.append(done),
            stop=lambda:bool(events))
        self.assertEqual(counts["RECYCLED"],1)
        self.assertEqual(counts["STOPPED"],2)
        self.assertFalse(self.alts[0].exists())
        self.assertTrue(self.alts[1].exists())
        self.assertTrue(self.alts[2].exists())

    def test_missing_file_skipped(self):
        self.alts[0].unlink()
        counts,_=bulk_recycle_alternatives([self.alts[0]],self.folder,
                                            approved=True,recycler=self.fake_recycle)
        self.assertEqual(counts,{"SKIPPED":1})


def gui_exists():
    try:
        import tkinter as tk
        root=tk.Tk();root.withdraw();root.destroy();return True
    except Exception:return False


@unittest.skipUnless(gui_exists(),"No graphical display")
class ReviewProgressGuiTests(unittest.TestCase):
    def setUp(self):
        from LRC_Control_Center import ControlCenter
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env=mock.patch.dict(os.environ,{"APPDATA":self.temp.name})
        self.env.start();self.addCleanup(self.env.stop)
        self.folder=Path(self.temp.name)/"music";self.folder.mkdir()
        self.wav=self.folder/"Testing.wav";self.wav.write_bytes(b"ORIGINAL AUDIO")
        self.primary=self.folder/"Testing.candidate.lrc"
        self.primary.write_text("[00:01.00] one\n[00:02.00] two\n[00:03.00] three\n")
        self.alt=self.folder/"Testing.candidate.2.lrc"
        self.alt.write_text("[00:01.00] alternative\n")
        self.app=ControlCenter();self.app.withdraw()
        self.addCleanup(self.app.destroy)
        self.app.folder.set(str(self.folder))
        self.app._refresh_review()

    def test_visible_alternative_selection_and_progress_widget(self):
        app=self.app
        app._review_select_alternatives()
        selected=[app.review_rows[k]["path"] for k in app.review_tree.selection()]
        self.assertEqual(selected,[self.alt])
        self.assertTrue(app.review_progress_bar.winfo_exists())
        self.assertEqual(app.review_progress.get(),0)

    def test_recycle_requires_consent(self):
        app=self.app
        app._review_select_alternatives()
        with mock.patch.object(app,"_dialog",return_value=False):
            app._recycle_selected_alternatives()
        self.assertTrue(self.alt.exists())
        self.assertFalse(app.review_bulk_running)

    def test_batch_recycle_has_determinate_progress_and_completes(self):
        app=self.app
        app._review_select_alternatives()
        def test_recycle(path):Path(path).unlink()
        with mock.patch.object(app,"_dialog",return_value=True),\
             mock.patch("v298_candidate_workbench.bulk_recycle_alternatives") as batch:
            # Mocked batch reports to GUI exactly as production thread does.
            def simulate(paths,folder,recursive,*,approved,report,stop):
                for index,path in enumerate(paths,1):
                    test_recycle(path)
                    report(index,len(paths),path,"RECYCLED","simulated")
                return {"RECYCLED":len(paths)},[(p,"RECYCLED","simulated") for p in paths]
            batch.side_effect=simulate
            # Patch the GUI module alias, not the helper import
            with mock.patch("LRC_Control_Center.bulk_recycle_alternatives",side_effect=simulate):
                app._recycle_selected_alternatives()
                deadline=time.monotonic()+10
                while app.review_bulk_running and time.monotonic()<deadline:
                    app.update();time.sleep(.02)
                app.update()
        self.assertFalse(app.review_bulk_running)
        self.assertEqual(app.review_progress.get(),100)
        self.assertEqual(app.review_progress_label.get(),"1 / 1 (100%)")
        self.assertFalse(self.alt.exists())
        self.assertTrue(self.primary.exists())
        self.assertEqual(self.wav.read_bytes(),b"ORIGINAL AUDIO")
        self.assertIn("RECYCLED",app.review_batch_status.get())


if __name__=="__main__":
    unittest.main()
