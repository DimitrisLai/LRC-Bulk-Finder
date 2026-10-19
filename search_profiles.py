"""LRC Bulk Finder v2.3 saved search profiles.

Only JSON preferences, never audio, lyrics or personal track inventories.
Profiles are local to the Windows user (APPDATA) and are not uploaded.
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path

FIELDS=("folder","action","greek","local_ai","musicbrainz","provider_mode",
        "order","custom_order","recovery_wait","recursive","history","limit",
        "exact_fallback","auto_search","database")
DEFAULT={
    "folder":"","action":"5","greek":True,"local_ai":False,
    "musicbrainz":True,"provider_mode":"full","order":"d","custom_order":"",
    "recovery_wait":False,"recursive":True,"history":True,"limit":"20",
    "exact_fallback":True,"auto_search":True,"database":"",
}
NAMES_RE=re.compile(r"^[\w][\w ._-]{0,39}$",re.UNICODE)
PROVIDER_FAST=("LRCLIB","SyncLRC","NetEase","Unison","LrcAPI")
PROVIDER_FULL=("LRCLIB","SyncLRC","Unison","BetterKuGou","BetterTTML","YouLyTTML",
               "LrcAPI","LiriQo","NetEase","Musixmatch","Megalobiz","Tencent")
BOOL_FIELDS=("greek","local_ai","musicbrainz","recovery_wait","recursive",
             "history","exact_fallback","auto_search")


def profile_file(appdata=None):
    directory=appdata or os.environ.get("APPDATA")
    root=Path(directory) if directory else Path.home()/".config"
    return root/"LRCBulkFinder"/"profiles.json"


def validate_profile(values):
    if not isinstance(values,dict):
        raise ValueError("Profile settings must be a JSON object")
    data={**DEFAULT,**{k:v for k,v in values.items() if k in FIELDS}}
    for k in ("folder","database","custom_order"):
        if not isinstance(data[k],str):
            raise ValueError(f"{k} must be text")
    for k in BOOL_FIELDS:
        if not isinstance(data[k],bool):
            raise ValueError(f"{k} must be true or false")
    if str(data["action"]) not in ("1","4","5"):
        raise ValueError("Only SEARCH (1), OFFLINE (4), and OFFLINE FIRST (5) are profile actions")
    data["action"]=str(data["action"])
    if data["local_ai"] and not data["greek"]:
        raise ValueError("Local Greek AI requires Greek mode")
    if data["provider_mode"] not in ("fast","full"):
        raise ValueError("Provider mode must be fast or full")
    if data["order"] not in ("d","s","c"):
        raise ValueError("Order must be d, s or c")
    if data["order"]=="c" and data["action"]!="4":
        providers=PROVIDER_FULL if data["provider_mode"]=="full" else PROVIDER_FAST
        ordered=[v.strip() for v in data["custom_order"].split(",") if v.strip()]
        if len(ordered)!=len(providers) or {v.casefold() for v in ordered}!={v.casefold() for v in providers} or len({v.casefold() for v in ordered})!=len(providers):
            raise ValueError("CUSTOM requires every provider exactly once, comma separated")
    limit=data["limit"].strip().lower()
    if limit!="a" and (not limit.isdecimal() or int(limit)<1):
        raise ValueError("Limit must be A or a positive number")
    data["limit"]=limit
    if not data["folder"].strip():
        raise ValueError("Choose an MP3 folder")
    return data


def load_profiles(path=None):
    destination=Path(path) if path is not None else profile_file()
    if not destination.is_file():
        return {}
    try:
        content=json.loads(destination.read_text(encoding="utf-8-sig"))
        if not isinstance(content,dict) or content.get("schema")!=1:
            raise ValueError("Unsupported profile format")
        values={}
        for name,data in content.get("profiles",{}).items():
            if isinstance(name,str) and NAMES_RE.fullmatch(name):
                try:values[name]=validate_profile(data)
                except ValueError:continue
        return values
    except (OSError,UnicodeError,ValueError,TypeError,AttributeError) as error:
        raise ValueError(f"Cannot load search profiles safely: {error}") from error


def save_profiles(profiles,path=None):
    destination=Path(path) if path is not None else profile_file()
    if not isinstance(profiles,dict):
        raise ValueError("Profiles must be named objects")
    cleaned={}
    for name,data in profiles.items():
        if not isinstance(name,str) or not NAMES_RE.fullmatch(name):
            raise ValueError("Profile names must be 1–40 characters: letters, numbers, spaces, underscores, hyphens or dots")
        cleaned[name]=validate_profile(data)
    destination.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps({"schema":1,"profiles":cleaned},indent=2,ensure_ascii=False)
    temp=destination.with_name(destination.name+".tmp")
    with temp.open("w",encoding="utf-8",newline="\n") as handle:
        handle.write(payload+"\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp,destination)
    return destination


def answers_for_profile(profile):
    """Map actual CLI prompt fragments to explicit responses, no prompt guessing."""
    p=validate_profile(profile)
    answers=[
      ("Choose [1/2/3/4/5]",p["action"]),
    ]
    if p["action"] in ("1","5"):
        answers.extend([
          ("Greeklish / Greek folder?", "y" if p["greek"] else "n"),
        ])
        if p["greek"]:
            answers.append(("Use your installed LOCAL G2G AI model?", "y" if p["local_ai"] else "n"))
        answers.extend([
          ("MusicBrainz extra artist/title metadata", "y" if p["musicbrainz"] else "n"),
          ("Search mode: FAST",p["provider_mode"]),
          ("Provider order?",p["order"]),
        ])
        if p["order"]=="c":
            answers.append(("List ALL selected providers",p["custom_order"]))
        answers.extend([
          ("Wait for temporary provider recovery","y" if p["recovery_wait"] else "n"),
          ("Include subfolders?", "y" if p["recursive"] else "n"),
          ("Skip identical provider searches","y" if p["history"] else "n"),
          ("How many missing songs?",p["limit"]),
          ("Optional LRCLIB exact-signature fallback","y" if p["exact_fallback"] else "n"),
        ])
        if p["greek"]:
            answers.append(("After the Greek/AI preview","y" if p["auto_search"] else "n"))
    else:
        answers.extend([
          ("Greeklish / Greek folder?", "y" if p["greek"] else "n"),
        ])
        if p["greek"]:
            answers.append(("Use installed LOCAL G2G AI for Greek names?", "y" if p["local_ai"] else "n"))
        answers.extend([
          ("Include subfolders?","y" if p["recursive"] else "n"),
          ("How many eligible songs?",p["limit"]),
          ("Start offline-only scan?","y"),
        ])
    return answers


class ProfileAnswers:
    def __init__(self,settings):
        self.answers=answers_for_profile(settings)
        self.position=0
        self.database=settings.get("database","").strip()

    def __call__(self,prompt=""):
        if prompt.startswith("Path to existing .sqlite3 file"):
            if not self.database:
                raise RuntimeError("Local LRCLIB database not configured. Set its path in the profile.")
            print(prompt+"[configured local database]",flush=True)
            return self.database
        if self.position>=len(self.answers):
            raise RuntimeError(f"Unexpected prompt: {prompt!r}. Refusing unattended guess.")
        expected,answer=self.answers[self.position]
        if expected not in prompt:
            raise RuntimeError(f"Prompt mismatch at step {self.position+1}. Expected {expected!r}; got {prompt!r}. No guess.")
        self.position+=1
        print(f"{prompt}{answer}",flush=True)
        return answer
