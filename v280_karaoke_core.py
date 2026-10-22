"""v2.8 Karaoke Edition: read-only audio/LRC pairing, safe playlists and settings.

Only JSON in the private application settings folder may be changed. No code path
here writes to media, ID3, source LRC, candidates or library search records.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import math
import os
import re
import tempfile

AUDIO_EXTS = frozenset({".mp3",".wav",".flac",".ogg",".opus",".m4a",".mp4"})
MAX_ITEMS = 500
MAX_JSON_BYTES = 512_000
MAX_LRC_BYTES = 512_000
THEMES = {
    "Midnight": ("#101b2d","#f8dc85","#b5c7e2"),
    "Black & Gold": ("#000000","#ffd34c","#e0e0e0"),
    "Ocean": ("#073848","#7df1e6","#d5f7ff"),
    "High Contrast": ("#000000","#ffffff","#e8e8e8"),
}
COUNTDOWNS = (0,3,5,10)
FONTS = (22,28,34,42,52,64)
DISPLAY_NEXT = (True,False)
OFFSETS = (-30.0,30.0)
CANDIDATES = re.compile(r"\.candidate(?:\.\d+)?\.lrc$",re.I)
INSTRUMENTAL = re.compile(r"(?i)(?:[\s_\-]*(?:\((?:instrumental|karaoke|backing track|minus one)\)|\[(?:instrumental|karaoke|backing track|minus one)\]|(?:instrumental|karaoke|backing track|minus one)))+$")

def settings_file():
    return Path(os.environ.get("APPDATA") or (Path.home()/".config"))/"LRCBulkFinder"/"karaoke_v280.json"

def regular_file(path, suffixes):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.suffix.lower() not in suffixes:
        raise ValueError("Select a regular supported local file")
    return path

def find_lyrics(audio, options=()):
    """Prefer an *exact* LRC; never choose a candidate or an ambiguous match.
    Instrumental normalization only applies to explicitly named instrumental tracks.
    """
    track = regular_file(audio,AUDIO_EXTS)
    stem = track.stem.casefold()
    lrcs = [p for p in track.parent.iterdir() if p.is_file() and not p.is_symlink()
            and p.suffix.casefold() == ".lrc" and p.stat().st_size <= MAX_LRC_BYTES
            and not CANDIDATES.search(p.name)]
    exact = [p for p in lrcs if p.stem.casefold() == stem]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return None
    normalized = INSTRUMENTAL.sub("",track.stem).strip(" -_.")
    if normalized == track.stem or not normalized:
        return None
    variants = [p for p in lrcs if p.stem.casefold()==normalized.casefold()]
    return variants[0] if len(variants)==1 else None

@dataclass
class PlaylistEntry:
    audio: str
    lrc: str = ""

    def validate(self):
        track = regular_file(self.audio,AUDIO_EXTS)
        lyr = regular_file(self.lrc,{".lrc"}) if self.lrc else None
        if lyr and lyr.stat().st_size > MAX_LRC_BYTES:
            raise ValueError("Lyric file too large")
        return track

class KaraokeSession:
    def __init__(self):
        self.entries = []
        self.selected = -1
        self.last_audio = ""
        self.theme = "Midnight"
        self.font_size = 34
        self.show_next = True
        self.countdown = 0
        self.offset = 0.0
        self.window_geometry = "1000x560"
        self.background_image = ""  # local file reference only; not copied or uploaded
        self.loops = {}             # path keys, private on this device
        self.auto_advance = False   # OFF by default, never surprising playback

    def add(self,audio,lrc=None):
        track = regular_file(audio,AUDIO_EXTS)
        lyric = regular_file(lrc,{".lrc"}) if lrc else find_lyrics(track)
        if lyric and lyric.stat().st_size > MAX_LRC_BYTES:
            raise ValueError("Lyric file too large")
        identity = str(track.resolve()).casefold()
        for i,row in enumerate(self.entries):
            if str(Path(row.audio).resolve()).casefold()==identity:
                if lyric:
                    row.lrc = str(lyric)
                return i
        if len(self.entries)>=MAX_ITEMS:
            raise ValueError("Playlist limit: 500")
        self.entries.append(PlaylistEntry(str(track),str(lyric) if lyric else ""))
        if self.selected < 0:
            self.selected = 0
        return len(self.entries)-1

    def attach(self,index,lyrics):
        regular_file(lyrics,{".lrc"})
        if Path(lyrics).stat().st_size>MAX_LRC_BYTES:
            raise ValueError("Lyric file too large")
        self.entries[index].lrc=str(Path(lyrics))

    def move(self,index,step):
        dest=index+step
        if not 0 <= index<len(self.entries) or not 0 <= dest<len(self.entries):
            return index
        self.entries[index],self.entries[dest]=self.entries[dest],self.entries[index]
        if self.selected==index:
            self.selected=dest
        elif self.selected==dest:
            self.selected=index
        return dest

    def remove(self,index):
        if not 0<=index<len(self.entries):
            return
        self.entries.pop(index)
        self.selected=min(self.selected,len(self.entries)-1)

    def next_index(self,step):
        i=self.selected+step
        return i if 0<=i<len(self.entries) else None

    def save_loop(self,audio,start,end):
        if audio and all(isinstance(t,(float,int)) and math.isfinite(t) for t in (start,end)) and 0<=start<end<=24*3600:
            self.loops[str(Path(audio).resolve()).casefold()]=[round(start,3),round(end,3)]
            # Keep state within bounded JSON file, oldest entries removed.
            if len(self.loops)>MAX_ITEMS:
                del self.loops[next(iter(self.loops))]
            return True
        return False

    def load_loop(self,audio):
        value=self.loops.get(str(Path(audio).resolve()).casefold())
        return tuple(value) if value else None

    def validated(self):
        if self.theme not in THEMES or self.font_size not in FONTS or self.countdown not in COUNTDOWNS:
            raise ValueError("Invalid karaoke theme, text size or countdown")
        if not isinstance(self.show_next,bool) or not isinstance(self.auto_advance,bool):
            raise ValueError("Invalid karaoke display options")
        if not isinstance(self.offset,(int,float)) or not math.isfinite(self.offset) or not OFFSETS[0]<=self.offset<=OFFSETS[1]:
            raise ValueError("Invalid karaoke offset")
        if not isinstance(self.window_geometry,str) or len(self.window_geometry)>80 or not re.fullmatch(r"\d{3,5}x\d{3,5}(?:[+-]\d{1,6}){0,2}",self.window_geometry):
            raise ValueError("Invalid window geometry")
        if not -1<=self.selected<len(self.entries) or len(self.entries)>MAX_ITEMS:
            raise ValueError("Invalid playlist selection")
        if len(self.loops)>MAX_ITEMS:
            raise ValueError("Too many saved loops")
        for pair in self.loops.values():
            if not isinstance(pair,(tuple,list)) or len(pair)!=2 or any(not isinstance(x,(int,float)) or not math.isfinite(x) for x in pair) or not 0<=pair[0]<pair[1]<=24*3600:
                raise ValueError("Invalid loop")
        return self

    def to_dict(self):
        self.validated()
        return {"schema":1,"entries":[asdict(e) for e in self.entries],"selected":self.selected,
                "last_audio":self.last_audio,"theme":self.theme,"font_size":self.font_size,
                "show_next":self.show_next,"countdown":self.countdown,"offset":self.offset,
                "window_geometry":self.window_geometry,"background_image":self.background_image,
                "loops":self.loops,"auto_advance":self.auto_advance}

    def save(self,path=None):
        dest=Path(path) if path else settings_file()
        text=json.dumps(self.to_dict(),ensure_ascii=False)
        if len(text.encode("utf-8"))>MAX_JSON_BYTES:
            raise ValueError("Session is too large")
        dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.parent.is_symlink() or (dest.exists() and dest.is_symlink()):
            raise ValueError("Unsafe settings location")
        tmp=None
        try:
            with tempfile.NamedTemporaryFile("w",encoding="utf-8",dir=dest.parent,prefix=".karaoke-",suffix=".tmp",delete=False) as f:
                tmp=Path(f.name)
                os.chmod(tmp,0o600)
                f.write(text);f.flush();os.fsync(f.fileno())
            os.replace(tmp,dest)
        finally:
            if tmp and tmp.exists():tmp.unlink()
        return dest

    @classmethod
    def load(cls,path=None):
        dest=Path(path) if path else settings_file()
        session=cls()
        try:
            if not dest.is_file() or dest.is_symlink() or dest.stat().st_size>MAX_JSON_BYTES:
                return session
            data=json.loads(dest.read_text(encoding="utf-8"))
            if data.get("schema")!=1 or not isinstance(data.get("entries"),list):
                return session
            session.entries=[]
            for row in data["entries"][:MAX_ITEMS]:
                try:
                    entry=PlaylistEntry(str(row["audio"]),str(row.get("lrc") or ""))
                    entry.validate()
                    session.entries.append(entry)
                except (ValueError,OSError,KeyError,TypeError):
                    continue  # missing songs never auto-play; preserve surviving rows
            session.selected=int(data.get("selected",-1))
            if not -1<=session.selected<len(session.entries):
                session.selected=0 if session.entries else -1
            session.last_audio=str(data.get("last_audio",""))[:4096]
            session.theme=data.get("theme","Midnight")
            session.font_size=data.get("font_size",34)
            session.show_next=data.get("show_next",True)
            session.countdown=data.get("countdown",0)
            session.offset=data.get("offset",0.0)
            session.window_geometry=data.get("window_geometry","1000x560")
            session.background_image=str(data.get("background_image",""))[:4096]
            session.loops=data.get("loops",{})
            session.auto_advance=data.get("auto_advance",False)
            session.validated()
            return session
        except (OSError,ValueError,TypeError,KeyError,AttributeError):
            return cls()

def preview_export(audio,lines,profile):
    from v270_precision import render_export,validate_timing
    from v260_player import duration_seconds
    invalid=[w for w in validate_timing(lines,duration_seconds(audio))
             if w.code in ("range","order","duplicate","duration")]
    if invalid:
        raise ValueError("Fix invalid timing before previewing this candidate")
    content=render_export(lines,profile)
    if len(content)>MAX_LRC_BYTES:
        raise ValueError("Candidate too large")
    return content.decode("utf-8-sig")
