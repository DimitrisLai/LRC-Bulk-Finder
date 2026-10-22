"""v2.8 unit/adversarial karaoke playlist, pairing, session, and preview QA."""
from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from v260_studio import LyricLine
from v280_karaoke_core import KaraokeSession, find_lyrics, preview_export, regular_file

class KaraokeCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.env=mock.patch.dict(os.environ,{"APPDATA":self.tmp.name});self.env.start();self.addCleanup(self.env.stop)
        self.root=Path(self.tmp.name)
        self.audio=self.root/"Πρώτο - Track (Instrumental).mp3"
        self.audio.write_bytes(b"sample-source-should-never-change")
        self.original=self.root/"Πρώτο - Track.lrc"
        self.original.write_text("[00:00.10] αρχή\n[00:01.50] τέλος\n",encoding="utf-8")
        self.before=(self.audio.read_bytes(),self.original.read_bytes())
    def test_instrumental_auto_pair(self):
        self.assertEqual(find_lyrics(self.audio),self.original)
    def test_exact_priority_with_case_insensitive_match(self):
        preferred=self.audio.with_suffix(".lrc");preferred.write_text("[00:00.20] custom",encoding="utf-8")
        self.assertEqual(find_lyrics(self.audio),preferred)
    def test_ambiguous_instrumental_refuses_guess(self):
        second=self.root/"ΠΡΏΤΟ - TRACK.lrc"
        second.write_text("[00:00.20] duplicate",encoding="utf-8")
        if len(list(self.root.glob("*.lrc")))<2:
            self.skipTest("Case-insensitive filesystem cannot represent two same-name LRCs")
        self.assertIsNone(find_lyrics(self.audio))
    def test_candidate_ignored_as_automatic_lyric(self):
        self.original.unlink()
        self.audio.with_suffix(".candidate.lrc").write_text("[00:00.00] candidate")
        self.assertIsNone(find_lyrics(self.audio))
    def test_safe_playlist_add_move_remove_and_duplicate(self):
        s=KaraokeSession()
        a=s.add(self.audio)
        self.assertEqual(a,0)
        self.assertEqual(s.entries[0].lrc,str(self.original))
        self.assertEqual(s.add(self.audio),0)
        another=self.root/"Second.wav";another.write_bytes(b"x")
        self.assertEqual(s.add(another),1)
        self.assertEqual(s.move(0,1),1)
        self.assertEqual(s.entries[1].audio,str(self.audio))
        self.assertEqual(s.next_index(1),None)
        s.remove(0);self.assertEqual(len(s.entries),1)
        self.assertEqual(self.before,(self.audio.read_bytes(),self.original.read_bytes()))
    def test_save_and_restore_private_json(self):
        s=KaraokeSession();s.add(self.audio)
        s.theme="Ocean";s.font_size=52;s.countdown=5;s.offset=.7
        s.last_audio=str(self.audio);s.window_geometry="1200x650+10+10"
        s.save_loop(self.audio,3,8)
        path=s.save()
        self.assertNotIn(self.audio.name,path.name)
        after=KaraokeSession.load()
        self.assertEqual(after.theme,"Ocean")
        self.assertEqual(after.load_loop(self.audio),(3,8))
        self.assertEqual(after.offset,.7)
        self.assertEqual(after.last_audio,str(self.audio))
        self.assertEqual(self.before,(self.audio.read_bytes(),self.original.read_bytes()))
    def test_corrupt_settings_fallback_without_writes_to_audio(self):
        path=KaraokeSession().save()
        path.write_text('{"schema":1,"entries":"not a list"}',encoding="utf-8")
        s=KaraokeSession.load()
        self.assertEqual(s.entries,[])
        self.assertEqual(s.theme,"Midnight")
        self.assertEqual(self.before,(self.audio.read_bytes(),self.original.read_bytes()))
    def test_unavailable_songs_skipped_on_reload(self):
        s=KaraokeSession();s.add(self.audio);s.save()
        self.audio.unlink()
        loaded=KaraokeSession.load()
        self.assertEqual(loaded.entries,[])
        self.assertEqual(loaded.selected,-1)
    def test_symlink_audio_refused(self):
        path=self.root/"linked.mp3"
        try:path.symlink_to(self.audio)
        except (OSError,NotImplementedError):self.skipTest("symlink unavailable")
        with self.assertRaises(ValueError):
            regular_file(path,{".mp3"})
    def test_session_rejects_nan_offset_invalid_geometry_and_options(self):
        s=KaraokeSession();s.offset=float("nan")
        with self.assertRaises(ValueError):s.save()
        s.offset=0;s.window_geometry="not-a-geometry"
        with self.assertRaises(ValueError):s.save()
        s.window_geometry="1000x560";s.theme="unsafe"
        with self.assertRaises(ValueError):s.save()
    def test_loop_bounds(self):
        s=KaraokeSession()
        self.assertFalse(s.save_loop(self.audio,8,3))
        self.assertFalse(s.save_loop(self.audio,0,float("nan")))
        self.assertTrue(s.save_loop(self.audio,0,4))
    def test_preview_matches_export_without_creating_file(self):
        content=preview_export(self.audio,[LyricLine(.1,"Α"),LyricLine(1.5,"Β")],"Precise 3 decimals")
        self.assertIn("[00:01.500]",content)
        self.assertFalse(list(self.root.glob("*.candidate*.lrc")))
        self.assertEqual(self.before,(self.audio.read_bytes(),self.original.read_bytes()))
    def test_preview_rejects_duplicate_or_beyond_track_end(self):
        with self.assertRaises(ValueError):
            preview_export(self.audio,[LyricLine(.1,"A"),LyricLine(.1,"B")],"Standard 2 decimals")
    def test_attach_external_lrc_but_never_modify(self):
        other=self.root/"custom.lrc";other.write_text("[00:02.00] X",encoding="utf-8")
        s=KaraokeSession();idx=s.add(self.audio);s.attach(idx,other)
        self.assertEqual(s.entries[idx].lrc,str(other))
        self.assertEqual(other.read_text(encoding="utf-8"),"[00:02.00] X")
    def test_large_playlist_guard(self):
        s=KaraokeSession()
        with self.assertRaises(ValueError):s.entries=[None]*501;s.save()

if __name__=="__main__":unittest.main(verbosity=2)
