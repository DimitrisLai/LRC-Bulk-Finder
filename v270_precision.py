"""v2.7 precision: warnings, safe profile exports, and crash-recovery drafts.

Nothing in this module modifies original audio, ID3, primary LRC, candidates or
search journal entries. Caller must make an explicit user-confirmed export.
"""
from __future__ import annotations
from pathlib import Path
from v260_studio import LyricLine, MAX_LRC_BYTES, MAX_SECONDS, _validate_audio
import hashlib
import json
import math
import os
import re
import tempfile
from dataclasses import dataclass

PROFILES = {"Standard 2 decimals": (2, False), "Precise 3 decimals": (3, False),
            "Car radio UTF-8 BOM": (2, True)}
MAX_DRAFT_BYTES = 640_000
MAX_DRAFTS = 50

@dataclass(frozen=True)
class TimingWarning:
    line: int
    code: str
    message: str

def validate_timing(lines, duration=0.0, gap_warning=16.0):
    warnings = []
    if not lines:
        return [TimingWarning(0, "empty", "No lyrics available")]
    previous = None
    for index, line in enumerate(lines):
        t = line.seconds
        if not isinstance(t, (float, int)) or not math.isfinite(t) or t < 0 or t > MAX_SECONDS:
            warnings.append(TimingWarning(index + 1, "range", "Invalid/out-of-range timestamp"))
            continue
        if duration > 0 and t > duration + 0.01:
            warnings.append(TimingWarning(index + 1, "duration", "Timestamp after audio ends"))
        if previous is not None:
            if round(t * 1000) == round(previous * 1000):
                warnings.append(TimingWarning(index + 1, "duplicate", "Duplicate timestamp"))
            elif t < previous:
                warnings.append(TimingWarning(index + 1, "order", "Timestamp is out of order"))
            elif t - previous >= gap_warning:
                warnings.append(TimingWarning(index + 1, "gap", "Large gap between lyric lines (review manually)"))
            elif t - previous < 0.25:
                warnings.append(TimingWarning(index + 1, "close", "Lines are very close together (review manually)"))
        previous = t
    return warnings

def format_mark(seconds, decimals):
    if decimals not in (2, 3) or not isinstance(seconds, (float, int)) or not math.isfinite(seconds):
        raise ValueError("Invalid time precision or timestamp")
    if not 0 <= seconds <= MAX_SECONDS:
        raise ValueError("Timestamp outside supported range")
    mul = 10 ** decimals
    count = round(seconds * mul)
    mm, rem = divmod(count, 60 * mul)
    ss, fract = divmod(rem, mul)
    return f"[{mm:02d}:{ss:02d}.{fract:0{decimals}d}]"

def render_export(lines, profile):
    if profile not in PROFILES:
        raise ValueError("Unknown export profile")
    decimals, bom = PROFILES[profile]
    if not 1 <= len(lines) <= 1000:
        raise ValueError("Need 1–1000 lines")
    rows = ["[00:00.00] candidate"]
    last = -1
    for item in lines:
        text = item.text
        if not isinstance(text, str) or not text.strip() or any(c in text for c in "\r\n") or len(text) > 1000:
            raise ValueError("Invalid lyric line")
        mark = format_mark(item.seconds, decimals)
        tick = round(item.seconds * 10 ** decimals)
        if tick <= last:
            raise ValueError("Timestamps must increase by at least one export tick")
        last = tick
        rows.append(mark + " " + text.strip())
    result = ("\n".join(rows) + "\n").encode("utf-8-sig" if bom else "utf-8")
    if len(result) > MAX_LRC_BYTES:
        raise ValueError("Candidate exceeds 512 KB")
    return result

def export_candidate(audio, lines, profile="Standard 2 decimals"):
    p = _validate_audio(audio)
    payload = render_export(lines, profile)  # all validation before filesystem writes
    for n in range(1, 1001):
        target = p.with_suffix(".candidate.lrc" if n == 1 else f".candidate.{n}.lrc")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(target, flags, 0o600)
        except FileExistsError:
            continue
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        return target
    raise FileExistsError("No free candidate filename")

def _base():
    folder = os.environ.get("APPDATA")
    root = Path(folder) if folder else Path.home() / ".config"
    return root / "LRCBulkFinder" / "studio_drafts"

def identity(audio):
    p = Path(audio)
    if not p.is_file() or p.is_symlink():
        raise ValueError("Missing or unsafe audio for draft")
    s = p.stat()
    stable = str(p.resolve()).casefold().encode("utf-8", "surrogatepass")
    ident = hashlib.sha256(stable).hexdigest()
    return ident, {"file_size": s.st_size, "mtime_ns": s.st_mtime_ns}

def draft_file(audio):
    ident, _ = identity(audio)
    return _base() / (ident + ".json")

def _validate_draft_lines(lines):
    # Temporary edits can be out of order; recovery must retain them so they
    # can be fixed. This is NOT a validation for candidate export.
    if not 1 <= len(lines) <= 1000:
        raise ValueError("Draft needs 1–1000 lines")
    for line in lines:
        if not isinstance(line.seconds, (float, int)) or not math.isfinite(line.seconds) or not 0 <= line.seconds <= MAX_SECONDS:
            raise ValueError("Invalid draft timestamp")
        if not isinstance(line.text, str) or not line.text.strip() or len(line.text) > 1000 or "\n" in line.text or "\r" in line.text:
            raise ValueError("Invalid draft lyric text")

def save_draft(audio, lines, source=None):
    ident, fingerprint = identity(audio)
    _validate_draft_lines(lines)
    root = _base()
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink():
        raise ValueError("Unsafe draft directory")
    src_hash = None
    if source and Path(source).is_file() and Path(source).stat().st_size <= MAX_LRC_BYTES:
        src_hash = hashlib.sha256(Path(source).read_bytes()).hexdigest()
    payload = {"schema": 1, "audio": ident, "fingerprint": fingerprint,
               "source_hash": src_hash, "lines": [[x.seconds, x.text] for x in lines]}
    text = json.dumps(payload, ensure_ascii=False)
    if len(text.encode("utf-8")) > MAX_DRAFT_BYTES:
        raise ValueError("Draft too large")
    target = root / (ident + ".json")
    temp = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=root, prefix=".studio-",
                                        suffix=".tmp", delete=False) as f:
            temp = Path(f.name)
            os.chmod(temp, 0o600)
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, target)
    finally:
        if temp and temp.exists():
            temp.unlink()
    # Draft housekeeping limited to this private folder, no deleting lyric sidecars.
    candidates = sorted(root.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    for old in candidates[MAX_DRAFTS:]:
        if old.is_file() and not old.is_symlink():
            old.unlink(missing_ok=True)
    return target

def load_draft(audio, source=None):
    ident, fingerprint = identity(audio)
    target = _base() / (ident + ".json")
    if not target.is_file() or target.is_symlink() or target.stat().st_size > MAX_DRAFT_BYTES:
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if data.get("schema") != 1 or data.get("audio") != ident or data.get("fingerprint") != fingerprint:
            return None
        if data.get("source_hash") is not None:
            if not source or not Path(source).is_file():
                return None
            if hashlib.sha256(Path(source).read_bytes()).hexdigest() != data["source_hash"]:
                return None
        lines = [LyricLine(float(t), str(value)) for t, value in data["lines"]]
        _validate_draft_lines(lines)
        return lines
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        return None

def clear_draft(audio):
    try:
        target = draft_file(audio)
        if target.is_file() and not target.is_symlink():
            target.unlink()
    except (OSError, ValueError):
        pass

def playback_report(player, codec=None):
    """Privacy-preserving report: never reveal paths, titles, text or lyrics."""
    supported = bool(player and getattr(player, "path", None))
    return {"engine": type(player).__name__ if player else "none",
            "loaded": supported,
            "format": codec if codec in (".wav", ".mp3", ".ogg", ".flac") else "other",
            "speed_backend": "VLC optional",
            "status": "ready" if supported else "not loaded"}
