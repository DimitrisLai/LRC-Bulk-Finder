"""Lyrics Studio 2.6: conservative, offline standard-LRC editing.

All edits remain in memory until an explicit, uniquely named .candidate.lrc
export. The source audio, existing .lrc, metadata and search records are never
opened for writing. No online lookup or automatic lyric verification occurs.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import os
import re

AUDIO_EXTENSIONS = frozenset({".mp3", ".flac", ".wav", ".ogg", ".opus", ".m4a", ".mp4"})
TIMED = re.compile(r"^((?:\[\d{1,3}:\d{2}(?:\.\d{1,3})?\])+)(.*)$")
TIMESTAMP = re.compile(r"\[(\d{1,3}):(\d{2})(?:\.(\d{1,3}))?\]")
META = re.compile(r"^\[([a-z][a-z0-9_-]*):([^\]]*)\]$", re.I)
MAX_LRC_BYTES = 512_000
MAX_LINES = 1000
MAX_LINE_CHARS = 1000
MAX_SECONDS = 24 * 3600


@dataclass(frozen=True)
class LyricLine:
    seconds: float
    text: str


def format_time(seconds: float) -> str:
    if not math.isfinite(seconds) or seconds < 0 or seconds > MAX_SECONDS:
        raise ValueError("Timestamp is outside the supported range")
    centis = round(seconds * 100)
    mm, rem = divmod(centis, 6000)
    ss, cs = divmod(rem, 100)
    return f"[{mm:02d}:{ss:02d}.{cs:02d}]"


def _time(match) -> float:
    mins, secs = int(match.group(1)), int(match.group(2))
    if secs > 59:
        raise ValueError("Invalid seconds field in timestamp")
    frac = match.group(3) or "0"
    value = mins * 60 + secs + int(frac) / 10 ** len(frac)
    if value > MAX_SECONDS:
        raise ValueError("Timestamp exceeds 24 hours")
    return value


def parse_lrc(text: str) -> list[LyricLine]:
    if len(text.encode("utf-8")) > MAX_LRC_BYTES:
        raise ValueError("Lyrics exceed the 512 KB limit")
    raw_lines: list[LyricLine] = []
    offset_ms = 0
    for row in text.lstrip("\ufeff").splitlines():
        row = row.strip()
        if not row:
            continue
        meta = META.fullmatch(row)
        if meta:
            if meta.group(1).lower() == "offset":
                try:
                    offset_ms = int(meta.group(2).strip())
                except ValueError as ex:
                    raise ValueError("Invalid LRC offset metadata") from ex
                if abs(offset_ms) > 3_600_000:
                    raise ValueError("LRC offset is unreasonably large")
            continue
        matched = TIMED.fullmatch(row)
        if not matched:
            # Preserve no untimed or proprietary content: line-level editor only.
            # Instead of silently treating an invalid timestamp as lyric text,
            # report timestamp-like malformed lines explicitly.
            if row.startswith("[") and len(row) > 2 and row[1].isdigit():
                raise ValueError("Malformed LRC timestamp: " + row[:60])
            continue
        lyric = matched.group(2).strip()
        if lyric.lower() == "candidate" and not raw_lines:
            continue
        if not lyric:
            continue
        if len(lyric) > MAX_LINE_CHARS:
            raise ValueError("Lyric line exceeds 1000 characters")
        for token in TIMESTAMP.finditer(matched.group(1)):
            raw_lines.append(LyricLine(_time(token), lyric))
            if len(raw_lines) > MAX_LINES:
                raise ValueError("More than 1000 lyric lines")
    if not raw_lines:
        raise ValueError("No timestamped lyric lines found")
    results = [LyricLine(round(line.seconds + offset_ms / 1000, 3), line.text)
               for line in raw_lines]
    if any(line.seconds < 0 or line.seconds > MAX_SECONDS for line in results):
        raise ValueError("LRC offset puts a line outside the supported range")
    return results


def read_lyric_file(path: str | Path) -> list[LyricLine]:
    file = Path(path)
    if not file.is_file() or file.is_symlink():
        raise ValueError("Choose a regular local lyric file")
    if file.stat().st_size > MAX_LRC_BYTES:
        raise ValueError("Lyrics exceed the 512 KB limit")
    data = file.read_bytes()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Legacy Greek sidecars are sometimes saved in Windows-1253.
        text = data.decode("cp1253")
    return parse_lrc(text)


def render_candidate(lines: list[LyricLine]) -> str:
    if not lines or len(lines) > MAX_LINES:
        raise ValueError("A candidate requires 1–1000 lyric lines")
    rows = ["[00:00.00] candidate"]
    previous = -1.0
    for line in lines:
        if not isinstance(line.text, str) or not line.text.strip():
            raise ValueError("Every lyric line must contain text")
        if len(line.text) > MAX_LINE_CHARS or "\n" in line.text or "\r" in line.text:
            raise ValueError("Lyric line contains unsupported text")
        value = line.seconds
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("Non-finite timestamp")
        rounded = round(value * 100)
        if rounded <= previous or value < 0 or value > MAX_SECONDS:
            raise ValueError("Timestamps must be strictly increasing to 0.01 seconds")
        previous = rounded
        rows.append(format_time(value) + " " + line.text.strip())
    encoded = "\n".join(rows) + "\n"
    if len(encoded.encode("utf-8")) > MAX_LRC_BYTES:
        raise ValueError("Candidate exceeds 512 KB")
    return encoded


class StudioDocument:
    """Model-level undo/redo; preview and edits never write to disk."""

    def __init__(self, lines: list[LyricLine]):
        if not lines:
            raise ValueError("The document is empty")
        self.lines = list(lines)
        self._undo: list[list[LyricLine]] = []
        self._redo: list[list[LyricLine]] = []

    @property
    def dirty(self) -> bool:
        return bool(self._undo)

    def _record(self) -> None:
        self._undo.append(list(self.lines))
        self._undo = self._undo[-100:]
        self._redo.clear()

    def set_time(self, index: int, seconds: float) -> None:
        if not 0 <= index < len(self.lines):
            raise IndexError(index)
        if not math.isfinite(seconds) or not 0 <= seconds <= MAX_SECONDS:
            raise ValueError("Invalid playback position")
        self._record()
        old = self.lines[index]
        self.lines[index] = LyricLine(round(seconds, 2), old.text)

    def shift(self, indices: list[int], seconds: float) -> None:
        unique = sorted(set(indices))
        if not unique or any(not 0 <= i < len(self.lines) for i in unique):
            raise ValueError("Select valid lyric lines")
        if not math.isfinite(seconds):
            raise ValueError("Invalid timing offset")
        new = list(self.lines)
        for i in unique:
            result = round(new[i].seconds + seconds, 2)
            if result < 0 or result > MAX_SECONDS:
                raise ValueError("Shift exceeds supported range")
            new[i] = LyricLine(result, new[i].text)
        self._record()
        self.lines = new

    def undo(self) -> bool:
        if not self._undo:
            return False
        self._redo.append(list(self.lines))
        self.lines = self._undo.pop()
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._undo.append(list(self.lines))
        self.lines = self._redo.pop()
        return True

    def active_line(self, seconds: float) -> int | None:
        latest = None
        for i, line in enumerate(self.lines):
            if line.seconds <= seconds and (latest is None or line.seconds >= self.lines[latest].seconds):
                latest = i
        return latest


def _validate_audio(audio_file: str | Path) -> Path:
    p = Path(audio_file)
    if not p.is_file() or p.is_symlink() or p.suffix.lower() not in AUDIO_EXTENSIONS:
        raise ValueError("Choose a supported, regular local audio track")
    # Same-stem audio makes the .lrc pairing ambiguous even when case differs.
    stem = p.stem.casefold()
    choices = [f for f in p.parent.iterdir()
               if f.is_file() and f.stem.casefold() == stem
               and f.suffix.lower() in AUDIO_EXTENSIONS]
    if len(choices) != 1:
        raise FileExistsError("Ambiguous same-stem audio: candidate save refused")
    return p


def save_candidate(audio_file: str | Path, lines: list[LyricLine]) -> Path:
    """Exclusive creation only, even when the original audio.lrc already exists."""
    p = _validate_audio(audio_file)
    data = render_candidate(lines).encode("utf-8")
    for n in range(1, 1001):
        label = ".candidate.lrc" if n == 1 else f".candidate.{n}.lrc"
        target = p.with_suffix(label)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(target, flags, 0o600)
        except FileExistsError:
            continue
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        return target
    raise FileExistsError("All candidate suffixes are in use")
