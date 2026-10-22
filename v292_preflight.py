"""v2.9.2: bounded, interruptible search preflight (no network and no writes).

Older releases parsed metadata for ALL missing tracks before applying
the chosen 20-song limit. This causes minutes with a zero progress bar.
Here the limit is applied while streaming candidates, but the existing
filename/ID3 LIVE guards and approved selection order are preserved.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class PreflightSummary:
    inspected: int
    eligible: int
    live_skipped: int
    metadata_failures: int
    total_candidates: int
    reached_limit: bool

def prepare_missing_tracks(candidates, *, limit, metadata_reader, is_live,
                           check_cancel, on_progress=None):
    """Collect at most limit eligible songs and metadata; never alter files.

    candidates must already exclude tracks with .lrc and names marked LIVE.
    Metadata is read in original discovery order until enough eligible songs
    are found; tagged-LIVE items do not consume the user-selected limit.
    If limit is None, all candidates are evaluated for a full-library search.
    A failed metadata read remains eligible, as the existing search engine
    can still fall back to the Artist - Title filename or report NO_METADATA.
    """
    if limit is not None and (not isinstance(limit,int) or isinstance(limit,bool) or limit<=0):
        raise ValueError("Selected song limit must be positive or ALL")
    chosen=[]
    cache={}
    inspected=0
    live=0
    failures=0
    n=len(candidates)
    if on_progress:
        on_progress(0,n,0,limit)
    for audio in candidates:
        check_cancel()
        inspected+=1
        try:
            info=metadata_reader(audio)
        except Exception:
            failures+=1
            info=None
        if info is not None and is_live(info[0]):
            live+=1
        else:
            chosen.append(audio)
            if info is not None:
                cache[audio]=info
        if on_progress and (inspected==1 or inspected%10==0 or
                            inspected==n or (limit is not None and len(chosen)>=limit)):
            on_progress(inspected,n,len(chosen),limit)
        if limit is not None and len(chosen)>=limit:
            break
    check_cancel()
    return chosen,cache,PreflightSummary(inspected,len(chosen),live,failures,n,
                                         limit is not None and len(chosen)>=limit)

def parse_limit(raw):
    value=str(raw).strip().lower()
    if value=="a":
        return None
    try:
        result=int(value) if value else 20
    except ValueError:
        result=20
    return result if result>0 else 0

def safe_filename_artist_fallback(filename_stem,tag_title,tag_artist):
    """Conservative Artist - Title fallback, never manufacture an artist.

    If the audio has a title tag equal to the FIRST half of a title-artist
    filename, the second half is an artist hint, not a verified tag. For
    placeholders (unknown artist, various artist, etc.) do not claim an
    artist; prefer no metadata over confidently searching the wrong name.
    """
    if " - " not in filename_stem:
        return tag_title,tag_artist
    first,second=filename_stem.split(" - ",1)
    clean=lambda s:" ".join(s.casefold().strip(" ._-").split())
    missing={"unknown artist","unknown","various artists","various artist","n/a","no artist","unbekannt","αγνωστος καλλιτεχνης"}
    if not tag_artist and tag_title and clean(tag_title)==clean(first):
        # Song - Artist filename style, supported only when the ID3 title
        # independently verifies the first half of the filename.
        if clean(second) in missing:return tag_title,""
        return tag_title,second.strip()
    # Original Artist - Title filename fallback: never replace valid tags.
    return tag_title or second.strip(),tag_artist or first.strip()
