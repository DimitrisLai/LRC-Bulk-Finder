"""v2.9.8 Candidate Review Workbench — safety, counters, sorting, batch GUI.

All file writes occur exclusively in disposable temporary directories.
Never contacts lyrics providers or touches user music.
"""
from __future__ import annotations
import tempfile
import unittest
import os
import time
from pathlib import Path
from unittest import mock

from review_candidates_gui import list_review_candidates
from v298_candidate_workbench import (STATUSES,can_promote,status_for,summarize,
    filtered,sort_items,primary_paths,bulk_promote)


class ReviewBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.audio=self.root/"My Track.wav"
        self.audio.write_bytes(b"IMMUTABLE AUDIO")
        self.primary=self.root/"My Track.candidate.lrc"
        self.primary.write_text("[00:01.00] Hello\n[00:04.00] World\n",encoding="utf-8")
        self.secondary=self.root/"My Track.candidate.2.lrc"
        self.secondary.write_text("[00:02.00] Other\n[00:05.00] Alternative\n",encoding="utf-8")

    def test_primary_alternative_counter_and_sort(self):
        rows=list_review_candidates(self.root)
        self.assertEqual(summarize(rows),dict(total=2,primary=1,alternative=1,
                         eligible=1,blocked_primary=0))
        self.assertEqual(len(filtered(rows,"Primary eligible")),1)
        self.assertEqual(len(filtered(rows,"Alternative")),1)
        self.assertEqual(len(filtered(rows,"All statuses","alternative")),1)
        self.assertEqual(sort_items(rows,"number")[0]["index"],1)
        self.assertEqual(sort_items(rows,"number",True)[0]["index"],2)
        self.assertEqual(primary_paths(rows),[self.primary])

    def test_batch_requires_explicit_approval(self):
        with self.assertRaises(PermissionError):
            bulk_promote([self.primary],self.root)
        self.assertFalse((self.root/"My Track.lrc").exists())
        self.assertTrue(self.primary.exists())

    def test_promote_primary_and_shift_alternative_no_audio_change(self):
        before=self.audio.read_bytes()
        counts,log=bulk_promote([self.primary],self.root,approved=True)
        self.assertEqual(counts,{"PROMOTED":1})
        created=self.root/"My Track.lrc"
        self.assertTrue(created.exists())
        self.assertTrue(created.read_text(encoding="utf-8").startswith("[00:00.00] candidate"))
        self.assertFalse(self.primary.with_name("My Track.candidate.2.lrc").exists())
        self.assertTrue(self.primary.exists())  # Former alternative becomes primary.
        self.assertIn("Alternative",self.primary.read_text(encoding="utf-8"))
        self.assertEqual(self.audio.read_bytes(),before)
        self.assertEqual(len(log),1)

    def test_existing_lrc_never_overwritten(self):
        target=self.root/"My Track.lrc"
        target.write_bytes(b"KEEP THIS ORIGINAL")
        rows=list_review_candidates(self.root)
        self.assertEqual(summarize(rows)["eligible"],0)
        counts,_=bulk_promote([self.primary],self.root,approved=True)
        self.assertEqual(counts,{"SKIPPED":1})
        self.assertEqual(target.read_bytes(),b"KEEP THIS ORIGINAL")
        self.assertTrue(self.primary.exists())

    def test_only_primary_and_within_folder(self):
        with self.assertRaises(ValueError):
            bulk_promote([self.secondary],self.root,approved=True)
        with self.assertRaises(ValueError):
            bulk_promote([self.primary,self.primary],self.root,approved=True)
        other=Path(self.temp.name).parent/"something.candidate.lrc"
        with self.assertRaises(ValueError):
            bulk_promote([other],self.root,approved=True)

    def test_stops_before_next_song(self):
        second=self.root/"Second.wav"
        second.write_bytes(b"immutable")
        c=self.root/"Second.candidate.lrc"
        c.write_text("[00:01.00] Second\n[00:02.00] Song\n")
        results=[]
        flag=[False]
        def on_done(done,total,path,status,detail):
            results.append((done,status))
            flag[0]=True
        counts,_=bulk_promote([self.primary,c],self.root,approved=True,
                               report=on_done,stop=lambda:flag[0])
        self.assertEqual(counts.get("STOPPED"),1)
        self.assertFalse((self.root/"Second.lrc").exists())

    def test_filtered_status_primary_blocked_and_multi_folder(self):
        nested=self.root/"Album"
        nested.mkdir()
        (nested/"X.candidate.lrc").write_text("[00:01.00] Candidate\n")
        rows=list_review_candidates(self.root)
        self.assertEqual(len(filtered(rows,"Missing / ambiguous audio")),1)
        self.assertEqual(len(filtered(rows,"Primary needs review")),2)
        self.assertEqual(len(filtered(rows,"Primary eligible")),1)
        self.assertEqual(len(filtered(rows,"All statuses","album")),1)
        self.assertEqual(len(sort_items(rows,"folder")),3)


def can_tk():
    try:
        import tkinter as tk
        w=tk.Tk();w.withdraw();w.destroy();return True
    except Exception:return False


@unittest.skipUnless(can_tk(),"Tk graphical desktop not available")
class CandidateWorkbenchGuiTests(unittest.TestCase):
    def setUp(self):
        from LRC_Control_Center import ControlCenter
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env=mock.patch.dict(os.environ,{"APPDATA":self.temp.name})
        self.env.start();self.addCleanup(self.env.stop)
        self.music=Path(self.temp.name)/"music";self.music.mkdir()
        for name in ("One","Two"):
            (self.music/(name+".wav")).write_bytes(b"ORIGINAL "+name.encode())
            (self.music/(name+".candidate.lrc")).write_text(
                "[00:01.00] First\n[00:04.00] Second\n",encoding="utf-8")
            (self.music/(name+".candidate.2.lrc")).write_text(
                "[00:01.00] Alt\n[00:03.00] Alt2\n",encoding="utf-8")
        self.app=ControlCenter();self.app.withdraw()
        self.addCleanup(self.app.destroy)
        self.app.folder.set(str(self.music))
        self.app._refresh_review()

    def test_filter_sort_counter_selection(self):
        app=self.app
        self.assertIn("Primary: 2",app.review_counter.get())
        self.assertIn("Alternatives: 2",app.review_counter.get())
        app.review_filter.set("Primary eligible")
        app._render_review()
        self.assertEqual(len(app.review_rows),2)
        app._review_select_eligible()
        self.assertEqual(len(app.review_tree.selection()),2)
        app._sort_review("candidate")
        self.assertEqual(len(app.review_tree.selection()),2)
        app.review_filter.set("Alternative")
        app._render_review()
        self.assertEqual(len(app.review_rows),2)
        app._review_select_visible()
        self.assertEqual(len(app.review_tree.selection()),2)
        app.review_query.set("One")
        self.assertEqual(len(app.review_rows),1)

    def test_all_primary_cancel_then_confirm(self):
        app=self.app
        with mock.patch.object(app,"_dialog",return_value=False):
            app._promote_all_primary()
        self.assertFalse((self.music/"One.lrc").exists())
        with mock.patch.object(app,"_dialog",return_value=True):
            app._promote_all_primary()
        end=time.monotonic()+10
        while app.review_bulk_running and time.monotonic()<end:
            app.update()
            time.sleep(.025)
        app.update()
        self.assertFalse(app.review_bulk_running)
        self.assertTrue((self.music/"One.lrc").exists())
        self.assertTrue((self.music/"Two.lrc").exists())
        self.assertEqual((self.music/"One.lrc").read_text(encoding="utf-8").splitlines()[0],
                         "[00:00.00] candidate")
        self.assertEqual((self.music/"One.wav").read_bytes(),b"ORIGINAL One")
        self.assertIn("Batch complete",app.review_batch_status.get())

    def test_cannot_close_during_batch(self):
        app=self.app
        app.review_bulk_running=True
        with mock.patch.object(app,"_dialog") as dialog:
            app._close()
            dialog.assert_called()
        app.review_bulk_running=False


if __name__=="__main__":
    unittest.main()
