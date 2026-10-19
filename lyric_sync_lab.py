"""v2.4 experimental assistance for UNTIMED text lyrics.

Creates only explicitly marked, unverified .candidate.lrc sidecars.
This is NOT audio alignment, AI transcription or validated synchronization.
"""
from __future__ import annotations
import re
from pathlib import Path
from incremental_library import AUDIO_EXTENSIONS

MAX_TEXT_BYTES=150_000
MAX_LINES=500
TIMECODE=re.compile(r"^\[(\d{1,3}):(\d{2})(?:\.(\d{1,3}))?\]\s*")
ANNOTATION=re.compile(r"^\[(?:verse|chorus|bridge|intro|outro|hook|instrumental|refrain)(?:\s+\d+)?\]$",re.I)

def plain_lines(text):
    lines=[]
    for raw in text.splitlines():
        line=TIMECODE.sub("",raw).strip()
        if not line or ANNOTATION.fullmatch(line):continue
        if len(line)>500:raise ValueError("One lyric line is too long for safe preview")
        lines.append(line)
        if len(lines)>MAX_LINES:raise ValueError("Too many lyric lines")
    if len(lines)<2:raise ValueError("At least two non-empty lyric lines are required")
    return lines

def estimate_timestamps(lines,duration):
    """Simple distribution for editing, not verified beat/speech alignment."""
    if not 0<float(duration)<=24*3600:
        raise ValueError("Accurate track duration is required")
    count=len(lines)
    start=min(8.0,float(duration)*0.04)
    end=max(start+1.0,float(duration)*0.94)
    if end>=float(duration):
        end=max(start+.01,float(duration)-.2)
    if end<=start:
        raise ValueError("Track too short")
    gap=(end-start)/max(1,count-1)
    return [round(start+i*gap,2) for i in range(count)]

def stamp(seconds):
    seconds=max(0,round(float(seconds)*100))
    mins,centis=divmod(seconds,6000)
    return f"[{mins:02d}:{centis//100:02d}.{centis%100:02d}]"

def draft_lrc(lines,timestamps):
    if len(lines)!=len(timestamps) or not lines:
        raise ValueError("Lyric lines and timestamps must correspond")
    nums=[float(x) for x in timestamps]
    if any(not 0<=x<=36000 for x in nums) or any(b<=a for a,b in zip(nums,nums[1:])):
        raise ValueError("Timestamps must be strictly increasing")
    return "[00:00.00] candidate\n"+''.join(
        f"{stamp(t)} {line}\n" for t,line in zip(nums,lines))

def candidate_output_path(audio_file):
    p=Path(audio_file)
    if p.suffix.casefold() not in AUDIO_EXTENSIONS:
        raise ValueError("Unsupported audio format")
    others=[p.with_suffix(ext) for ext in AUDIO_EXTENSIONS
            if ext!=p.suffix.casefold() and p.with_suffix(ext).exists()]
    if others:
        raise FileExistsError("Several audio files share the same LRC stem; choose unique filenames")
    if p.with_suffix(".lrc").exists():
        raise FileExistsError("Existing .lrc is protected")
    base=p.with_suffix(".candidate.lrc")
    if not base.exists():return base
    for n in range(2,1000):
        dest=p.with_suffix(f".candidate.{n}.lrc")
        if not dest.exists():return dest
    raise FileExistsError("Too many candidates")

def save_unverified_draft(audio_file,text,lines,times):
    p=Path(audio_file)
    if not p.is_file():raise FileNotFoundError("Audio file is missing")
    expected=draft_lrc(lines,times)
    # Even edited drafts must preserve the candidate marker and contain
    # exactly as many valid, strictly increasing timestamped lines.
    parts=[row.strip() for row in text.splitlines() if row.strip()]
    if not parts or parts[0]!="[00:00.00] candidate":
        raise ValueError("Do not remove the unverified candidate marker")
    if len(parts)!=len(lines)+1:
        raise ValueError("Candidate draft must contain exactly one timestamp per lyric line")
    stamps=[]
    for row in parts[1:]:
        match=TIMECODE.match(row)
        if not match or not row[match.end():].strip():
            raise ValueError("Every lyric line needs a valid timestamp and text")
        minutes=int(match.group(1));seconds=int(match.group(2))
        if seconds>59:raise ValueError("Invalid seconds in timestamp")
        fraction=match.group(3) or "0"
        stamps.append(minutes*60+seconds+int(fraction)/(10**len(fraction)))
    if any(second<=first for first,second in zip(stamps,stamps[1:])):
        raise ValueError("Timestamps must be strictly increasing")
    target=candidate_output_path(p)
    with target.open("x",encoding="utf-8",newline="\n") as stream:
        stream.write(text.rstrip()+"\n")
    return target
