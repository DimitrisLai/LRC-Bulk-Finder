"""Bounded-memory, cancellable waveform approximation for Lyrics Studio 2.7.

Reads audio *only*. WAV uses Python wave; MP3/FLAC/OGG can use optional
libsndfile via soundfile. At most width * chunk sampled frames, never full files.
"""
from __future__ import annotations
from pathlib import Path
import math
import threading
import wave
import struct

MAX_POINTS = 1400
MAX_READ_FRAMES = 220_000
MAX_AUDIO_SECONDS = 6 * 3600

def _peak_pcm(raw, width, channels, sampwidth):
    if sampwidth not in (1, 2, 3, 4):
        raise ValueError("Unsupported PCM depth")
    stride = channels * sampwidth
    count = len(raw) // stride
    if not count:
        return 0.0
    stride_frames = max(1, count // 64)
    maximum = 0.0
    for j in range(0, count, stride_frames):
        data = raw[j * stride: j * stride + sampwidth]
        if sampwidth == 1:
            value = (data[0] - 128) / 128
        else:
            value = int.from_bytes(data, "little", signed=True) / float(1 << (8 * sampwidth - 1))
        maximum = max(maximum, abs(value))
    return min(1.0, maximum)

def _compute_wav(path, width, stop):
    result = []
    with wave.open(str(path), "rb") as audio:
        if audio.getcomptype() != "NONE":
            raise ValueError("Compressed WAV cannot be decoded by the native waveform reader")
        rate = audio.getframerate()
        count = audio.getnframes()
        if rate <= 0 or count / rate > MAX_AUDIO_SECONDS:
            raise ValueError("Unreasonable audio duration")
        frames_per_bucket = max(1, count // width)
        read_per_bucket = max(1, min(frames_per_bucket, max(32, MAX_READ_FRAMES // width)))
        for i in range(width):
            if stop.is_set():
                return None
            audio.setpos(min(count, i * count // width))
            raw = audio.readframes(read_per_bucket)
            result.append(_peak_pcm(raw, read_per_bucket, audio.getnchannels(), audio.getsampwidth()))
    return result

def _compute_soundfile(path, width, stop):
    try:
        import soundfile as sf
    except ImportError as ex:
        raise ValueError("For compressed waveforms, install soundfile") from ex
    with sf.SoundFile(str(path), "r") as audio:
        count, rate = audio.frames, audio.samplerate
        if rate <= 0 or count / rate > MAX_AUDIO_SECONDS:
            raise ValueError("Unreasonable audio duration")
        result = []
        for i in range(width):
            if stop.is_set():
                return None
            audio.seek(min(count, i * count // width))
            n = max(1, min(max(32, MAX_READ_FRAMES // width), count - audio.tell()))
            data = audio.read(n, dtype="float32", always_2d=True)
            # Usually small, and bounded by the read count.
            result.append(float(max((abs(float(v)) for row in data for v in row), default=0.0)))
    return [min(1.0, x) for x in result]

def read_waveform(path, width=900, stop=None):
    file = Path(path)
    if not file.is_file() or file.is_symlink():
        raise ValueError("Select a regular local audio file")
    if not 1 <= width <= MAX_POINTS:
        raise ValueError("Waveform width must be 1–1400")
    event = stop if stop is not None else threading.Event()
    if file.suffix.lower() == ".wav":
        try:
            return _compute_wav(file, width, event)
        except wave.Error:
            pass  # Non-PCM WAV may still work through libsndfile
    return _compute_soundfile(file, width, event)

def window_peaks(peaks, duration, start, seconds):
    if not peaks or duration <= 0 or seconds <= 0:
        return []
    n = len(peaks)
    lo = max(0, min(n, int(start / duration * n)))
    hi = max(lo + 1, min(n, int((start + seconds) / duration * n)))
    return peaks[lo:hi]
