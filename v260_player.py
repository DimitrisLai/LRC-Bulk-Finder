"""Optional embedded player for v2.6 Lyrics Studio.

Uses pygame/SDL_mixer, imported lazily so all other search features and CI
work without it. Only audio is opened; no network and no metadata changes.
"""
from __future__ import annotations
import math
from pathlib import Path
import time

from v260_studio import _validate_audio

PLAYER_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac"}


class PlaybackError(RuntimeError):
    pass


class StudioPlayer:
    def __init__(self, pygame_module=None, clock=None):
        self._pg = pygame_module
        self._clock = clock or time.monotonic
        self.path: Path | None = None
        self._anchor = 0.0
        self._start = 0.0
        self._paused_at: float | None = None
        self._playing = False

    def _mixer(self):
        if self._pg is None:
            try:
                import pygame
            except ImportError as exc:
                raise PlaybackError("Embedded playback needs pygame. Install with: pip install pygame") from exc
            self._pg = pygame
        try:
            if not self._pg.mixer.get_init():
                self._pg.mixer.init()
            return self._pg.mixer.music
        except Exception as exc:
            raise PlaybackError("Cannot initialize the audio device: " + str(exc)) from exc

    def load(self, audio_file):
        path = _validate_audio(audio_file)
        if path.suffix.lower() not in PLAYER_EXTENSIONS:
            raise PlaybackError("This format is not supported by the embedded player; use Open audio player.")
        music = self._mixer()
        try:
            music.stop()
            music.load(str(path))
        except Exception as exc:
            raise PlaybackError("Audio decoder could not open this track: " + str(exc)) from exc
        self.path = path
        self._playing = False
        self._start = self._anchor = 0.0
        self._paused_at = None

    def play(self):
        if self.path is None:
            raise PlaybackError("Choose and load a track first")
        music = self._mixer()
        if self._paused_at is not None:
            try:
                music.unpause()
            except Exception as exc:
                raise PlaybackError("Could not resume playback: " + str(exc)) from exc
            self._anchor = self._clock()
            self._paused_at = None
            return
        self.seek(self.position() if self._playing else 0.0)

    def pause(self):
        if self._playing and self._paused_at is None:
            music = self._mixer()
            self._paused_at = self.position()
            music.pause()

    def stop(self):
        if self._pg is not None and self._pg.mixer.get_init():
            self._pg.mixer.music.stop()
        self._start = self._anchor = 0.0
        self._playing = False
        self._paused_at = None

    def seek(self, seconds):
        if self.path is None:
            raise PlaybackError("Choose and load a track first")
        seconds = float(seconds)
        if not math.isfinite(seconds) or seconds < 0 or seconds > 24 * 3600:
            raise PlaybackError("Invalid seek position")
        music = self._mixer()
        try:
            music.play(start=seconds)
        except Exception:
            try:
                music.play()
                music.set_pos(seconds)
            except Exception as exc:
                music.stop()
                self._playing = False
                raise PlaybackError("Precise seek is not supported for this audio codec: " + str(exc)) from exc
        self._playing = True
        self._start = seconds
        self._anchor = self._clock()
        self._paused_at = None

    def position(self):
        if self._paused_at is not None:
            return self._paused_at
        if not self._playing:
            return 0.0
        return max(0.0, self._start + self._clock() - self._anchor)

    def is_playing(self):
        if not self._playing or self._paused_at is not None:
            return False
        try:
            if not self._mixer().get_busy():
                self._playing = False
                return False
        except PlaybackError:
            self._playing = False
            return False
        return True

    def close(self):
        try:
            self.stop()
            if self._pg is not None and self._pg.mixer.get_init():
                self._pg.mixer.music.unload()
        except Exception:
            pass


def duration_seconds(audio_file):
    """Read-only metadata, returning 0 when unavailable."""
    try:
        from mutagen import File as MutagenFile
        audio = MutagenFile(str(audio_file))
        length = float(audio.info.length)
        return length if math.isfinite(length) and length > 0 else 0.0
    except (ImportError, AttributeError, TypeError, ValueError, OSError):
        return 0.0
