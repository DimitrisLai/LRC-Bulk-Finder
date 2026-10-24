"""v3.0 Stage 1: bounded, read-only grouping and comparison of LRC candidates.

Never writes music, LRC, candidates, tags or configuration. Playback and
installation are deliberately left to later stages.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Optional

from v260_studio import read_lyric_file, LyricLine
from v270_precision import validate_timing

MAX_PREVIEW_BYTES = 160_000
PAGE_SIZE = 200


@dataclass(frozen=True)
class SongGroup:
    key: str
    title: str
    audio: Optional[Path]
    candidates: tuple
    has_lrc: bool
    ambiguous: bool


@dataclass(frozen=True)
class CandidateSnapshot:
    path: Path
    index: int
    lines: tuple[LyricLine, ...]
    digest: str
    warnings: tuple[str, ...]
    error: str = ""

    @property
    def line_count(self):
        return len(self.lines)


def _name_and_index(item):
    path = Path(item["path"])
    index = int(item["index"])
    suffix = ".candidate.lrc" if index == 1 else f".candidate.{index}.lrc"
    if index < 1 or not path.name.casefold().endswith(suffix):
        raise ValueError("Not a canonical candidate filename")
    return path.name[:-len(suffix)], index


def group_candidates(items):
    """Group by folder + literal audio stem, not just title across albums.

    The returned group never implies that ambiguous/missing audio is valid.
    No LRC content is read; sorting and grouping are bounded by row count.
    """
    mapping = {}
    for item in items:
        stem, _ = _name_and_index(item)
        path = Path(item["path"])
        key = str(path.parent.absolute()).casefold() + "\0" + stem.casefold()
        mapping.setdefault(key, []).append(item)
    groups = []
    for key, rows in mapping.items():
        rows = sorted(rows, key=lambda r: (int(r["index"]), str(r["path"]).casefold()))
        unique = not any(r["ambiguous"] or not r["has_mp3"] for r in rows)
        audio_paths = {str(Path(r["mp3"]).absolute()).casefold() for r in rows}
        audio = Path(rows[0]["mp3"]) if unique and len(audio_paths) == 1 else None
        if audio is not None and (not audio.is_file() or audio.is_symlink()):
            audio = None
        groups.append(SongGroup(
            key=key, title=audio.name if audio is not None else _name_and_index(rows[0])[0],
            audio=audio, candidates=tuple(rows),
            has_lrc=any(bool(r["has_lrc"]) for r in rows),
            ambiguous=bool(any(r["ambiguous"] for r in rows) or len(audio_paths) > 1)))
    return sorted(groups, key=lambda g: (g.title.casefold(), g.key))


def read_snapshot(item, duration=0.0):
    """Safely parse a *selected* candidate only; never bulk-read the library."""
    path = Path(item["path"])
    try:
        _name_and_index(item)
        if path.is_symlink() or not path.is_file():
            raise ValueError("Missing or unsafe candidate file")
        st = path.stat()
        if st.st_size > MAX_PREVIEW_BYTES:
            raise ValueError("Candidate exceeds 160 KB preview limit")
        raw = path.read_bytes()
        if len(raw) > MAX_PREVIEW_BYTES:
            raise ValueError("Candidate changed or exceeds preview limit")
        lines = tuple(read_lyric_file(path))
        warnings = tuple(f"Line {w.line}: {w.message}" for w in
                         validate_timing(lines, float(duration) if duration and duration > 0 else 0))
        return CandidateSnapshot(path, int(item["index"]), lines,
                                 sha256(raw).hexdigest(), warnings)
    except (OSError, ValueError, UnicodeError) as exc:
        return CandidateSnapshot(path, int(item.get("index", 0)), (), "", (), str(exc))


def comparison(left, right):
    """Index-aligned structural comparison; not an automatic correctness score."""
    if left.error or right.error:
        return {"ready": False, "reason": left.error or right.error,
                "same_file": False, "exact_duplicate": False,
                "changed_text": 0, "changed_timing": 0, "extra_lines": 0}
    common = min(len(left.lines), len(right.lines))
    changed_text = sum(" ".join(a.text.casefold().split()) != " ".join(b.text.casefold().split())
                       for a, b in zip(left.lines[:common], right.lines[:common]))
    changed_timing = sum(abs(a.seconds - b.seconds) > .005
                         for a, b in zip(left.lines[:common], right.lines[:common]))
    return {"ready": True, "reason": "",
            "same_file": left.path == right.path,
            "exact_duplicate": bool(left.digest and left.digest == right.digest),
            "changed_text": changed_text, "changed_timing": changed_timing,
            "extra_lines": abs(len(left.lines) - len(right.lines))}


def page_groups(groups, page=0, query=""):
    if not isinstance(page, int) or page < 0:
        raise ValueError("Invalid page")
    q = str(query or "").strip().casefold()
    matched = [g for g in groups if q in g.title.casefold() or
               q in str(g.candidates[0]["path"].parent).casefold()] if q else groups
    start = page * PAGE_SIZE
    return matched[start:start+PAGE_SIZE], len(matched)
