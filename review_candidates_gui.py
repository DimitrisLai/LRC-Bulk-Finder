"""Read-only candidate discovery and explicit marked review promotion.

The review GUI never automatically labels a candidate "verified".
Promotion delegates to the existing conservative production implementation.
"""
from __future__ import annotations
import re
from pathlib import Path
from incremental_library import AUDIO_EXTENSIONS

_CANDIDATE_PATTERN=re.compile(r"^(?P<stem>.+)\.candidate(?:\.(?P<index>(?:[2-9]|[1-9]\d+)))?\.lrc$",re.IGNORECASE)


def candidate_index(path):
    matched=_CANDIDATE_PATTERN.match(Path(path).name)
    return int(matched.group("index") or 1) if matched else None


def list_review_candidates(folder,recursive=True):
    directory=Path(folder)
    if not directory.is_dir():
        raise ValueError("Choose an existing folder")
    iterator=directory.rglob("*") if recursive else directory.iterdir()
    found=[]
    for file in iterator:
        if not file.is_file():
            continue
        match=_CANDIDATE_PATTERN.match(file.name)
        if not match:
            continue
        stem=match.group("stem")
        matches=[file.with_name(stem+ext) for ext in AUDIO_EXTENSIONS
                 if file.with_name(stem+ext).is_file()]
        mp3=matches[0] if len(matches)==1 else file.with_name(stem+".mp3")
        installed=file.with_name(stem+".lrc")
        found.append({
            "path":file,
            "mp3":mp3,
            "installed":installed,
            "index":int(match.group("index") or 1),
            "has_mp3":len(matches)==1,
            "ambiguous":len(matches)>1,
            "has_lrc":installed.is_file()
        })
    return sorted(found,key=lambda d:(str(d["mp3"]).casefold(),d["index"]))


def preview_candidate(path,max_bytes=160_000):
    candidate=Path(path)
    if candidate_index(candidate) is None:
        raise ValueError("Not a review-candidate .lrc file")
    if candidate.stat().st_size>max_bytes:
        raise ValueError("Candidate too large to preview safely")
    return candidate.read_text(encoding="utf-8-sig",errors="replace")


def explicitly_promote(candidate,approved=False):
    """Conservative Option 2 behavior: LRC is MARKED [00:00.00] candidate."""
    if not approved:
        raise PermissionError("Explicit confirmation is required for every promotion")
    candidate=Path(candidate)
    if candidate_index(candidate)!=1:
        raise ValueError("Only primary .candidate.lrc can be promoted (not numbered alternatives)")
    from LRC_Bulk_Finder import promote_candidate_file
    return promote_candidate_file(candidate)
