"""v2.9.2 regression: 3,200 audio files, bounded 20-song preflight and Greek ID3 edge cases.

Uses synthetic dummy music files. Private real user MP3s are never committed.
"""
from __future__ import annotations
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from incremental_library import safe_audio_files,IncrementalLibrary
from v292_preflight import (prepare_missing_tracks,parse_limit,
                            safe_filename_artist_fallback)

class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.paths=[]
        for i in range(3200):
            p=self.root/f"Στίχοι_{i:04d}.mp3"
            p.touch()
            self.paths.append(p)
    def test_limit_20_does_not_inspect_all_3200_id3_tags(self):
        reads=[]
        stages=[]
        def read(p):
            reads.append(p)
            return (p.stem,"artist","album",180.)
        tracks,meta,stats=prepare_missing_tracks(
            self.paths,limit=20,metadata_reader=read,is_live=lambda s:"LIVE" in s,
            check_cancel=lambda:None,on_progress=lambda *args:stages.append(args))
        self.assertEqual(len(tracks),20)
        self.assertEqual(len(reads),20)
        self.assertEqual(len(meta),20)
        self.assertEqual(stats.inspected,20)
        self.assertEqual(stats.total_candidates,3200)
        self.assertEqual(stages[0],(0,3200,0,20))
        self.assertEqual(stages[-1],(20,3200,20,20))
    def test_tagged_live_tracks_do_not_consume_limit(self):
        reads=[]
        def info(p):
            reads.append(p)
            return ("LIVE Concert" if p==self.paths[1] else "Song","artist","",180)
        tracks,meta,s=prepare_missing_tracks(self.paths,limit=3,metadata_reader=info,
                  is_live=lambda s:"LIVE" in s,check_cancel=lambda:None)
        self.assertEqual(len(tracks),3)
        self.assertEqual(s.inspected,4)
        self.assertEqual(s.live_skipped,1)
        self.assertNotIn(self.paths[1],tracks)
    def test_all_mode_reaches_all_and_progress_finishes(self):
        chunks=[]
        result,meta,s=prepare_missing_tracks(
            self.paths[:63],limit=None,metadata_reader=lambda p:(p.stem,"", "",1),
            is_live=lambda s:False,check_cancel=lambda:None,
            on_progress=lambda *x:chunks.append(x))
        self.assertEqual(len(result),63)
        self.assertEqual(s.inspected,63)
        self.assertEqual(chunks[-1],(63,63,63,None))
    def test_uncertain_metadata_is_still_eligible_not_crash(self):
        result,meta,s=prepare_missing_tracks(
            self.paths[:4],limit=2,metadata_reader=lambda p:(_ for _ in ()).throw(ValueError("bad MP3")),
            is_live=lambda s:False,check_cancel=lambda:None)
        self.assertEqual(len(result),2)
        self.assertEqual(s.metadata_failures,2)
        self.assertEqual(meta,{})
    def test_stop_during_metadata_does_not_search(self):
        signal=threading.Event()
        def info(p):
            signal.set()
            return (p.stem,"artist","",180)
        def stop():
            if signal.is_set():raise KeyboardInterrupt("STOP requested")
        with self.assertRaises(KeyboardInterrupt):
            prepare_missing_tracks(self.paths,limit=20,metadata_reader=info,
                    is_live=lambda s:False,check_cancel=stop)
    def test_missing_id3_artist_keeps_unknown_unconfirmed(self):
        title,artist=safe_filename_artist_fallback(
            "_ Aniko Se Mena - unknown artist",". Aniko Se Mena","")
        self.assertEqual(title,". Aniko Se Mena")
        self.assertEqual(artist,"")
    def test_preserve_existing_standard_artist_title_filename(self):
        title,artist=safe_filename_artist_fallback("Artist - Song","", "")
        self.assertEqual((title,artist),("Song","Artist"))
        self.assertEqual(safe_filename_artist_fallback("H Gkeisa - Iwanna Koutalidou",
                                 "H Gkeisa","Iwanna Koutalidou"),("H Gkeisa","Iwanna Koutalidou"))
    def test_limits_are_bounded_or_all(self):
        self.assertEqual(parse_limit("a"),None)
        self.assertEqual(parse_limit("20"),20)
        self.assertEqual(parse_limit(""),20)
        self.assertEqual(parse_limit("nonsense"),20)
        self.assertEqual(parse_limit("-3"),0)
        with self.assertRaises(ValueError):
            prepare_missing_tracks([],limit=-1,metadata_reader=lambda p:None,
                    is_live=lambda s:False,check_cancel=lambda:None)
    def test_discovery_callback_and_incremental_cache_for_3200(self):
        reports=[]
        songs,collisions=safe_audio_files(
            self.root,False,progress=lambda visited,found:reports.append((visited,found)))
        self.assertEqual(len(songs),3200)
        self.assertEqual(collisions,[])
        self.assertEqual(reports[-1],(3200,3200))
        db=IncrementalLibrary(self.root)
        try:
            index_progress=[]
            summary=db.inventory(songs,progress=lambda processed,total:index_progress.append((processed,total)))
            self.assertEqual(summary["new"],3200)
            self.assertEqual(index_progress[-1],(3200,3200))
        finally:db.close()
        for p in self.paths:self.assertEqual(p.stat().st_size,0)

if __name__=="__main__":unittest.main(verbosity=2)
