"""Optional variable-speed playback (VLC native library required on Windows).

pygame stays the default for full portability. VLC is activated only when a
user explicitly requests non-1x speed. Never edits the source audio.
"""
from __future__ import annotations
from pathlib import Path
import math
from v260_player import PlaybackError

SPEEDS = (0.75, 1.0, 1.25)

class VLCPlayer:
    def __init__(self, vlc_module=None):
        if vlc_module is None:
            try:
                import vlc as vlc_module
            except (ImportError, OSError) as exc:
                raise PlaybackError("Variable speed requires python-vlc AND an installed compatible VLC player.") from exc
        self.vlc = vlc_module
        try:
            self.instance = self.vlc.Instance("--no-video", "--quiet")
            if self.instance is None:
                raise RuntimeError("VLC native runtime not found")
            self.media_player = self.instance.media_player_new()
        except Exception as exc:
            raise PlaybackError("VLC backend unavailable: " + str(exc)) from exc
        self.path = None
        self.rate = 1.0
        self._paused = False
        self._position = 0.0

    def load(self, path):
        track = Path(path)
        if not track.is_file() or track.is_symlink():
            raise PlaybackError("Choose a regular local audio track")
        try:
            self.stop()
            media = self.instance.media_new_path(str(track))
            self.media_player.set_media(media)
        except Exception as exc:
            raise PlaybackError("Could not load audio in VLC: " + str(exc)) from exc
        self.path = track

    def set_speed(self, rate):
        if rate not in SPEEDS:
            raise PlaybackError("Supported playback speeds: 0.75x, 1.00x, 1.25x")
        try:
            result = self.media_player.set_rate(float(rate))
            if result == -1:
                raise RuntimeError("Codec does not support rate change")
        except Exception as exc:
            raise PlaybackError("VLC could not change speed: " + str(exc)) from exc
        self.rate = float(rate)

    def play(self):
        if self.path is None:
            raise PlaybackError("Choose a track first")
        try:
            if self.media_player.play() == -1:
                raise RuntimeError("VLC playback refused")
            self.media_player.set_rate(self.rate)
            if self._paused:
                self._paused = False
            elif self._position > 0:
                self.media_player.set_time(round(self._position * 1000))
        except Exception as exc:
            raise PlaybackError("VLC playback failed: " + str(exc)) from exc

    def pause(self):
        self._position = self.position()
        self.media_player.set_pause(1)
        self._paused = True

    def stop(self):
        self._position = 0.0
        self._paused = False
        self.media_player.stop()

    def seek(self, seconds):
        if not math.isfinite(float(seconds)) or not 0 <= float(seconds) <= 24 * 3600:
            raise PlaybackError("Invalid seek position")
        self._position = float(seconds)
        self.play()
        self.media_player.set_time(round(self._position * 1000))

    def position(self):
        if self._paused:
            return self._position
        ms = self.media_player.get_time()
        return max(0.0, ms / 1000.0) if ms is not None and ms >= 0 else self._position

    def is_playing(self):
        return bool(self.media_player.is_playing())

    def close(self):
        try:
            self.stop()
            self.media_player.release()
            self.instance.release()
        except Exception:
            pass
