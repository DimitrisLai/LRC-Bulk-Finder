"""v2.7 karaoke/precision adversarial tests on disposable local audio.

No provider calls. Never mutates user audio or existing primary lyric files.
"""
from __future__ import annotations
import os
import wave
import struct
import hashlib
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from v260_studio import LyricLine
from v270_precision import (validate_timing, render_export, export_candidate,
                             save_draft, load_draft, clear_draft, playback_report)
from v270_waveform import read_waveform, window_peaks, _peak_pcm, MAX_READ_FRAMES
from v270_vlc import VLCPlayer, PlaybackError

class TimingAndExport(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.audio=Path(self.tmp.name)/"Greek instrumental.mp3"
        self.audio.write_bytes(b"original audio bytes")
        self.lrc=self.audio.with_suffix(".lrc")
        self.lrc.write_text("[00:01.00] υπάρχον\n",encoding="utf-8")
        self.lines=[LyricLine(1.005,"Γειά"),LyricLine(2.123,"κόσμε")]
    def test_timing_warnings_duplicate_order_duration_and_gap(self):
        lines=[LyricLine(1,"a"),LyricLine(1,"b"),LyricLine(.5,"c"),
               LyricLine(30,"d"),LyricLine(40,"e")]
        found=validate_timing(lines, duration=36, gap_warning=15)
        codes=[x.code for x in found]
        self.assertIn("duplicate",codes)
        self.assertIn("order",codes)
        self.assertIn("gap",codes)
        self.assertIn("duration",codes)
    def test_export_profiles_utf8_bom_and_three_decimal(self):
        original=self.lrc.read_bytes(); audio=self.audio.read_bytes()
        a=export_candidate(self.audio,self.lines,"Precise 3 decimals")
        b=export_candidate(self.audio,self.lines,"Car radio UTF-8 BOM")
        self.assertIn(b"[00:01.005]",a.read_bytes())
        self.assertTrue(b.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertEqual(original,self.lrc.read_bytes())
        self.assertEqual(audio,self.audio.read_bytes())
        self.assertNotEqual(a,b)
    def test_existing_candidate_not_overwritten(self):
        p=self.audio.with_suffix(".candidate.lrc")
        p.write_bytes(b"manual lyrics")
        result=export_candidate(self.audio,self.lines,"Precise 3 decimals")
        self.assertEqual(result.name,"Greek instrumental.candidate.2.lrc")
        self.assertEqual(p.read_bytes(),b"manual lyrics")
    def test_invalid_precision_collision_blocks_disk_write(self):
        with self.assertRaises(ValueError):
            render_export([LyricLine(1.001,"x"),LyricLine(1.004,"y")],"Standard 2 decimals")
        with self.assertRaises(ValueError):
            export_candidate(self.audio,[LyricLine(1.001,"x"),LyricLine(1.004,"y")],"Standard 2 decimals")
        self.assertFalse(list(Path(self.tmp.name).glob("*.candidate*.lrc")))
    def test_same_stem_different_codec_refuses_ambiguous_save(self):
        (Path(self.tmp.name)/"Greek instrumental.FLAC").write_bytes(b"audio")
        with self.assertRaises(FileExistsError):
            export_candidate(self.audio,self.lines)
    def test_nonnumeric_invalid_and_unknown_profile(self):
        for v in (-1,float("inf"),float("nan")):
            with self.subTest(v=v),self.assertRaises(ValueError):
                render_export([LyricLine(v,"lyric")],"Precise 3 decimals")
        with self.assertRaises(ValueError):
            render_export(self.lines,"not a real profile")

class PrivateDraftRecovery(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.patch=mock.patch.dict(os.environ,{"APPDATA":self.tmp.name});self.patch.start();self.addCleanup(self.patch.stop)
        self.track=Path(self.tmp.name)/"Αρχείο.mp3";self.track.write_bytes(b"not decoded audio")
        self.source=self.track.with_suffix(".lrc");self.source.write_bytes(b"[00:01.00] original")
        self.lines=[LyricLine(1,"Αρχή"),LyricLine(2,"Τέλος")]
    def test_recover_matching_audio_and_source_no_original_changes(self):
        before=(self.track.read_bytes(),self.source.read_bytes())
        path=save_draft(self.track,self.lines,self.source)
        self.assertNotIn("Αρχείο.mp3",path.name)
        self.assertEqual(load_draft(self.track,self.source),self.lines)
        self.assertEqual(before,(self.track.read_bytes(),self.source.read_bytes()))
        clear_draft(self.track)
        self.assertIsNone(load_draft(self.track,self.source))
    def test_changed_source_rejects_stale_draft(self):
        save_draft(self.track,self.lines,self.source)
        self.source.write_bytes(b"edited elsewhere")
        self.assertIsNone(load_draft(self.track,self.source))
    def test_changed_audio_rejects_stale_draft(self):
        save_draft(self.track,self.lines,self.source)
        with self.track.open("ab") as f:f.write(b"new bytes")
        self.assertIsNone(load_draft(self.track,self.source))
    def test_symlink_audio_rejected(self):
        shadow=Path(self.tmp.name)/"proxy.mp3"
        try:shadow.symlink_to(self.track)
        except (OSError,NotImplementedError):self.skipTest("Cannot make symlink")
        with self.assertRaises(ValueError):
            save_draft(shadow,self.lines)
    def test_corrupted_draft_ignored_without_touching_audio(self):
        path=save_draft(self.track,self.lines,self.source)
        path.write_text("{corrupted",encoding="utf-8")
        self.assertIsNone(load_draft(self.track,self.source))

class WaveformTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.file=Path(self.tmp.name)/"wave.wav"
        with wave.open(str(self.file),"wb") as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(8000)
            f.writeframes(b"".join(struct.pack("<h",int(15000*((i%200)/200-0.5))) for i in range(16000)))
    def test_native_real_pcm_bounded_peak_result_and_read_only(self):
        before=hashlib.sha256(self.file.read_bytes()).digest()
        out=read_waveform(self.file,width=400)
        self.assertEqual(len(out),400)
        self.assertTrue(all(0<=v<=1 for v in out))
        self.assertEqual(hashlib.sha256(self.file.read_bytes()).digest(),before)
        self.assertGreater(len(window_peaks(out,2.0,.5,.7)),10)
    def test_cancelled_work_returns_none(self):
        cancel=threading.Event();cancel.set()
        self.assertIsNone(read_waveform(self.file,400,cancel))
    def test_invalid_width_and_missing_file(self):
        with self.assertRaises(ValueError):read_waveform(self.file,100000)
        with self.assertRaises(ValueError):read_waveform(self.file.with_suffix(".none"))
    def test_legacy_pcm_8bit(self):
        self.assertAlmostEqual(_peak_pcm(bytes([0,128,255]),3,1,1),1,places=2)

class FakeNativePlayer:
    def __init__(self):
        self.p=0; self.playing=False; self.rate=1.0
    def set_media(self,x):pass
    def play(self):self.playing=True;return 0
    def stop(self):self.playing=False
    def set_rate(self,x):self.rate=x;return 0
    def get_time(self):return self.p
    def set_time(self,x):self.p=x
    def set_pause(self,x):self.playing=not bool(x)
    def is_playing(self):return self.playing
    def release(self):pass
class FakeInstance:
    def __init__(self):self.p=FakeNativePlayer()
    def media_player_new(self):return self.p
    def media_new_path(self,x):return x
    def release(self):pass
class FakeVLC:
    def Instance(self,*args):return FakeInstance()
class VLCBackends(unittest.TestCase):
    def test_speed_and_seek_vlc_optional_backend(self):
        with tempfile.TemporaryDirectory() as t:
            file=Path(t)/"track.wav";file.write_bytes(b"audio")
            v=VLCPlayer(FakeVLC())
            v.load(file)
            v.set_speed(.75)
            self.assertEqual(v.rate,.75)
            v.seek(12)
            self.assertEqual(v.position(),12)
            v.pause();self.assertEqual(v.position(),12)
            v.set_speed(1.25)
            self.assertEqual(v.rate,1.25)
            v.close()
    def test_invalid_speed(self):
        v=VLCPlayer(FakeVLC())
        with self.assertRaises(PlaybackError):
            v.set_speed(8.0)
    def test_private_report_excludes_paths(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/"private_song.mp3"
            dummy=type("MockPlayer",(),{"path":p})()
            report=playback_report(dummy,".mp3")
            self.assertNotIn("private_song",str(report))
            self.assertNotIn(str(root),str(report))

if __name__=="__main__":unittest.main(verbosity=2)
