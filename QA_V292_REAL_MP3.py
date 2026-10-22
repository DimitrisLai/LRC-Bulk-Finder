"""Optional LOCAL, read-only MP3 QA using files supplied by a tester.

Usage (Python/source ZIP):
  python QA_V292_REAL_MP3.py "C:\\music\\track1.mp3" "C:\\music\\track2.mp3" ...

The files and contents are NEVER uploaded, copied, recorded in CI or
included in public release assets. Use this script with your own tracks.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import sys
from mutagen import File as AudioFile
from v292_preflight import prepare_missing_tracks
from LRC_Bulk_Finder import _read_audio_info,is_live_track

def sha256(path):
    sha=hashlib.sha256()
    with open(path,"rb") as file:
        for block in iter(lambda:file.read(1024*1024),b""):
            sha.update(block)
    return sha.hexdigest()

def run(paths):
    selected=[Path(p) for p in paths]
    if not selected or any(not p.is_file() or p.is_symlink() or p.suffix.lower()!=".mp3" for p in selected):
        raise ValueError("Specify existing, ordinary local .mp3 files")
    before={p:sha256(p) for p in selected}
    try:
        for p in selected:
            audio=AudioFile(p,easy=True)
            if audio is None or getattr(audio,"info",None) is None:
                raise ValueError("Unreadable MP3: "+p.name)
            title,artist,album,duration=_read_audio_info(p)
            if not title or duration<=0:
                raise AssertionError("Invalid or missing song title/duration: "+p.name)
            print(f"PASS MP3: {p.name} | title={title!r}, artist={artist or '(missing)'!r}, "
                  f"album={album!r}, duration={duration:.1f}s",flush=True)
        callback=[]
        chosen,cache,summary=prepare_missing_tracks(
            selected,limit=len(selected),metadata_reader=_read_audio_info,
            is_live=is_live_track,check_cancel=lambda:None,
            on_progress=lambda *state:callback.append(state))
        if len(chosen)!=len(selected) or len(cache)!=len(selected):
            raise AssertionError("Selected MP3 preflight dropped a valid track")
        if not callback or callback[-1][0]!=len(selected):
            raise AssertionError("No terminal preflight progress update")
        print(f"PASS real audio preflight: {summary.inspected} titles, "
              f"{summary.metadata_failures} metadata failures, no network requests")
    finally:
        after={p:sha256(p) for p in selected}
        if before!=after:
            raise AssertionError("One or more original MP3s were unexpectedly changed")
        print("PASS source MP3 SHA-256 preserved",flush=True)

if __name__=="__main__":
    if len(sys.argv)<2:
        sys.exit("Specify at least one MP3 path. No MP3 data is uploaded or copied.")
    run(sys.argv[1:])
