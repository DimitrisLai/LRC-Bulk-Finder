"""v2.9.6 cumulative provider packs — explicit opt-in, backwards compatible.

Existing FAST/FULL profiles stay on LEGACY, so no new provider is silently
enabled on upgrade. Higher tiers only add sources; their order is deliberate.
BetterQQ is new and review-only because the public endpoint does not return
a verifiable recording identity/duration for safe automatic LRC writing.
"""
from __future__ import annotations
import re
import xml.etree.ElementTree as ET

LEGACY = "legacy"
BASE = ("LRCLIB", "SyncLRC", "Unison")
PACKS = {
    "1": BASE,
    "2": BASE + ("LrcAPI",),
    "3": BASE + ("LrcAPI", "NetEase", "Musixmatch", "Megalobiz"),
    "4": BASE + ("LrcAPI", "NetEase", "Musixmatch", "Megalobiz",
                 "LiriQo", "BetterKuGou"),
    "5": BASE + ("LrcAPI", "NetEase", "Musixmatch", "Megalobiz",
                 "LiriQo", "BetterKuGou", "BetterQQ",
                 "YouLyTTML", "BetterTTML", "Tencent"),
    "6": BASE + ("LrcAPI", "NetEase", "Musixmatch", "Megalobiz",
                 "LiriQo", "BetterKuGou", "BetterQQ",
                 "YouLyTTML", "BetterTTML", "Tencent", "SimpMusic"),
}
DISPLAY = {
    LEGACY: "Legacy — existing FAST/FULL (unchanged)",
    "1": "Tier 1 — CORE (3 sources)",
    "2": "Tier 2 — CORE + LrcAPI (4)",
    "3": "Tier 3 — BROAD (7 sources)",
    "4": "Tier 4 — EXTENDED (9 sources)",
    "5": "Tier 5 — MAXIMUM (13 sources)",
    "6": "Tier 6 — EXPERIMENTAL ALL (14 sources)",
}
DESCRIPTION = {
    LEGACY: "Existing FAST/FULL behavior. No provider changes on upgrade.",
    "1": "LRCLIB + SyncLRC + Unison. Smallest online source set.",
    "2": "Tier 1 plus LrcAPI. Four source searches in priority order.",
    "3": "Tier 2 plus NetEase, Musixmatch and Megalobiz. Slower scrapers; review-only.",
    "4": "Tier 3 plus LiriQo and BetterKuGou. Broader community sources.",
    "5": "Tier 4 plus BetterQQ, YouLyTTML, BetterTTML and Tencent. Restricted/unavailable routes may be skipped.",
    "6": "Tier 5 plus optional SimpMusic. Slowest; explicitly experimental.",
}
assert set(PACKS)==set(DISPLAY)-{LEGACY}
for a,b in zip(PACKS.values(),list(PACKS.values())[1:]):
    assert b[:len(a)]==a, "Provider packs must remain cumulative"
assert len(PACKS["1"])==3 and len(PACKS["2"])==4
ALL_PACK_PROVIDERS = frozenset(PACKS["6"])


def validate_pack(value):
    if value not in DISPLAY:
        raise ValueError("Unknown provider pack")
    return value


def select_pack(value, legacy_fast, legacy_full):
    """Legacy stays unchanged. Tiers are exact cumulative ordered tuples."""
    validate_pack(value)
    if value == LEGACY:
        return tuple(legacy_full if legacy_full is not None else legacy_fast)
    return PACKS[value]


def display_for_pack(value):
    return DISPLAY[validate_pack(value)]


def pack_from_display(label):
    for key,display in DISPLAY.items():
        if display == label:return key
    raise ValueError("Select a known provider pack")


def qrc_to_lrc(raw):
    """Convert public QRC line start timestamps to *review-only* line LRC.

    QRC's LyricContent normally contains lines like
      [12340,3400]words(12340,400) next(12740,500)
    All QRC numeric timing values are milliseconds. Strip per-word timings.
    Never follow external references, accept huge XML or execute markup.
    """
    if not isinstance(raw,str) or len(raw)>2_000_000:return ""
    if not raw.lstrip().startswith("<"):return ""
    try:root=ET.fromstring(raw)
    except ET.ParseError:return ""
    if root.tag.rsplit("}",1)[-1].lower() not in ("qrcinfos","lyricinfo","lyric","qrc"):
        return ""
    blocks=[]
    for el in root.iter():
        for key,value in el.attrib.items():
            if key.rsplit("}",1)[-1].lower()=="lyriccontent":
                blocks.append(value)
    if not blocks:return ""
    # Only start-timestamp lines, not accidental embedded numbers, are used.
    stamp=re.compile(r"^\s*\[(\d{1,9}),(\d{1,8})\]\s*(.*)$")
    word_stamp=re.compile(r"\(\d{1,9},\d{1,8}\)")
    output=[];seen=set()
    for block in blocks:
        for line in block.splitlines():
            match=stamp.match(line)
            if not match:continue
            ms=int(match.group(1));duration=int(match.group(2))
            if ms>35_999_999 or duration<0:continue
            words=word_stamp.sub("",match.group(3))
            words=" ".join(words.split()).strip()
            if not words:continue
            sec,cent=divmod(round(ms/10),100)
            minute,seconds=divmod(sec,60)
            value=f"[{minute:02}:{seconds:02}.{cent:02}] {words}"
            if value not in seen:
                output.append((ms,value));seen.add(value)
            if len(output)>=500:break
        if len(output)>=500:break
    output.sort(key=lambda v:v[0])
    return "\n".join(line for _,line in output)+"\n" if output else ""


def better_qq_review_only(title,artist,album,duration,review,*,direct_json,query_variants,
                          synced_payload,plausible_lrc):
    """Official public Better Lyrics QQ route, no key, never auto-save.

    Identity/duration are not returned; even accurate QRC is only a candidate.
    Nothing bypasses the application's strict verified-LRC gate.
    """
    for t,a in query_variants(title,artist):
        row=direct_json("BetterQQ","https://api.betterlyrics.org/qq/getLyrics",
                        {"s":t,"a":a,"al":album or "",
                         "d":str(round(duration)) if duration else "0"})
        if not isinstance(row,dict):continue
        raw=row.get("lyrics") or ""
        lyric=qrc_to_lrc(raw)
        if not lyric and isinstance(raw,str):
            lyric=synced_payload(raw,"lrc")
        if not lyric or not plausible_lrc(lyric,duration):continue
        review.add("BetterQQ",t,a,
                   "QQ/QRC timing; source did not return verified title, artist or duration. "
                   "Manual candidate review only.",lyrics=lyric)
    return None
