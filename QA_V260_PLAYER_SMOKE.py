"""Offline SDL_mixer smoke: synthetic WAV, real playback APIs, no music modifications."""
from __future__ import annotations
import hashlib
import math
import os
import struct
import tempfile
import time
import wave
from pathlib import Path

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
from v260_player import StudioPlayer


def smoke():
    with tempfile.TemporaryDirectory() as root:
        p = Path(root) / "smoke.wav"
        with wave.open(str(p), "wb") as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(22050)
            raw = b"".join(struct.pack("<h", int(2000 * math.sin(2 * math.pi * 440 * i / 22050)))
                           for i in range(22050))
            wav.writeframes(raw)
        old = hashlib.sha256(p.read_bytes()).digest()
        player = StudioPlayer()
        try:
            player.load(p)
            player.play()
            time.sleep(.12)
            assert player.position() >= 0, "Position must be non-negative"
            player.pause()
            paused = player.position()
            time.sleep(.06)
            assert abs(player.position() - paused) < .08, "Pause clock is unstable"
            player.play()
            time.sleep(.08)
            player.stop()
            assert player.position() == 0.0
            assert old == hashlib.sha256(p.read_bytes()).digest(), "Audio bytes were changed"
        finally:
            player.close()
    print("PASS: real pygame mixer WAV load/play/pause/resume/stop, original WAV SHA256 unchanged")


if __name__ == "__main__":
    smoke()
