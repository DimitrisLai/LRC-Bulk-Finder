#!/usr/bin/env python3
"""LRC Bulk Finder v2.1.15. See README for provider/API limitations.
Reads audio ID3 metadata; writes ONLY sidecar .lrc and reports, never audio tags.
Created by Dimitris L. (project credit; third-party services credited separately).
"""
from __future__ import annotations
import csv
from lrclib_local import LocalLRCLIB, load_local_config
import hashlib
import shutil
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import asyncio
import threading
import difflib
import json
import socket
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from g2g_integration import G2GManager, GREEK as G2G_GREEK, english_skip as g2g_english_skip

try:
    from mutagen import File as AudioFile
    from unidecode import unidecode
    import syncedlyrics
except ImportError as ex:
    print(f'Missing required Python package: {ex}. Run Start_LRC_Finder.bat.')
    raise SystemExit(2)

VERSION = '2.1.15'
HEADERS = {'User-Agent': 'LRCBulkFinder/2.1.15',
           'Accept': 'application/json, text/plain'}
LRCLIB_IDENTIFIED = False
LRCLIB_USER_AGENT = ''
COOLDOWN_PATH = None
COOLDOWN_UNTIL = {}
# Older libraries use these identifiers exactly.
PROVIDERS = ('LRCLIB', 'SyncLRC', 'Unison', 'BetterKuGou', 'BetterTTML', 'YouLyTTML', 'LrcAPI', 'LiriQo', 'NetEase', 'Musixmatch', 'Megalobiz', 'Tencent')
BASE_GAP = {'LRCLIB': 2.4, 'SyncLRC': 2.2, 'Unison': 1.5, 'BetterKuGou': 1.8, 'BetterTTML': 1.8, 'YouLyTTML': 2.5, 'LrcAPI': 1.5, 'LiriQo': 1.5,
            'NetEase': 1.5, 'Musixmatch': 1.5, 'Megalobiz': 1.5, 'Tencent': 2.0, 'MusicBrainz': 1.2}
NETWORK_TIMEOUT = 10
OPTIONAL_TENCENT_AVAILABLE = False
try:
    import syncedlyrics_aio
    OPTIONAL_TENCENT_AVAILABLE = True
except ImportError:
    pass
blocked = {}
errors = Counter()
# HTTP 503 is transient, not a permanent provider ban. For LRCLIB, use a
# bounded provider-wide recovery period and probe again on a future song.
# It never adds a song to the network-timeout retry rounds.
LRCLIB_503_STREAK = 0
LRCLIB_503_RETRY_AT = 0.0
# Enabled by default in the Windows SEARCH workflow. Wait *before a first
# provider attempt* when a temporary recovery timer is active, rather than
# silently skipping hundreds of later songs. No HTTP 5xx is automatically retried.
COMPLETE_FIRST_PASS = False  # activated by interactive [Y/n] prompt
PROVIDER_RECOVERY_AT = {}
PROVIDER_ERROR_STREAK = Counter()
LOCAL_LRCLIB = None
LRCLIB_ONLINE_FALLBACK = True
LRCLIB_503_CIRCUIT_LIMIT = 3  # consecutive overload responses in one run
LRCLIB_EXACT_FALLBACK = False  # Opt-in: existing searches stay unchanged by default.
LRCLIB_LAST_FINISHED = 0.0  # minimum gap after completion (not just between start times)
next_available = {}
seen_rejections = {}
ROUND = 1
HISTORY_ENABLED = False
HISTORY_PATH = None
HISTORY_CACHE = {}
HISTORY_DAYS = 7

# Request-level diagnostics; stored only in local reports. URL query strings
# (which can contain song metadata or tokens) are deliberately not recorded.
ACTIVE_HTTP_TRACE = None
LIBRARY_MANAGED_SOURCES = {'NetEase','Musixmatch','Megalobiz','Tencent'}


def add_http_event(provider,url,status,started,detail=''):
    """Capture actual HTTP outcomes without claiming to see third-party internals."""
    if ACTIVE_HTTP_TRACE is None:return
    parts=urllib.parse.urlsplit(url)
    target=parts.netloc+parts.path  # never include URL query params
    ACTIVE_HTTP_TRACE.append({
        'provider':provider, 'endpoint':target, 'status':str(status),
        'detail':str(detail or '')[:180],
        'elapsed_seconds':round(max(0.0,time.monotonic()-started),3),
    })


def http_summary(provider,events):
    """Distinguish a successful HTTP lookup from an accepted lyric match."""
    if not events:
        if provider in LIBRARY_MANAGED_SOURCES:
            return 'HTTP status UNKNOWN (third-party library does not expose it)'
        return 'NO HTTP request recorded'
    codes=[event['status'] for event in events]
    labels=[]
    for code in dict.fromkeys(codes):
        count=codes.count(code)
        labels.append(('HTTP ' if code.isdigit() else '')+code+(f' x{count}' if count>1 else ''))
    return ', '.join(labels)


def print_provider_state(source,status,elapsed=0,events=None,reason=''):
    """Always print the source's outcome, even if no request was made."""
    events=events if events is not None else []
    explanation=reason or http_summary(source,events)
    print(f'      {source}: {status} | {explanation} | {elapsed:.1f}s',flush=True)


def show_provider_availability():
    print('\nProvider availability at startup (a selected provider may be skipped):',flush=True)
    for name in (ACTIVE_PROVIDERS if ACTIVE_PROVIDERS is not None else PROVIDERS):
        if name in blocked:
            print(f'  {name}: DISABLED — {blocked[name]}',flush=True)
        elif name=='Tencent' and not OPTIONAL_TENCENT_AVAILABLE:
            print(f'  {name}: UNAVAILABLE — optional syncedlyrics_aio package not installed',flush=True)
        else:
            print(f'  {name}: READY (not yet contacted)',flush=True)
    print('HTTP codes will be reported when exposed; READY is not proof the service is reachable.\n',flush=True)


def search_history_key(provider,title,artist,album,duration):
    # Include the exact variants: changed AI/model/alias results get a new key.
    # Include code version: old matching criteria never poison a safer release.
    request=[VERSION,provider,str(title),str(artist),str(album),round(float(duration or 0),2),
             query_variants(title,artist)]
    data=json.dumps(request,ensure_ascii=False,sort_keys=True)
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def load_search_history(path):
    global HISTORY_PATH,HISTORY_CACHE
    HISTORY_PATH=path
    HISTORY_CACHE.clear()
    if not path.is_file():return
    cutoff=time.time()-HISTORY_DAYS*86400
    try:
        with path.open(encoding='utf-8') as source:
            for line in source:
                try:
                    row=json.loads(line)
                    key=str(row['key'])
                    if row.get('state')=='NO_MATCH' and float(row.get('at',0))>=cutoff:
                        HISTORY_CACHE[key]=float(row['at'])
                    else:
                        # Later REVIEW_AVAILABLE / other statuses invalidate an
                        # earlier no-match event for the same exact query.
                        HISTORY_CACHE.pop(key,None)
                except (ValueError,KeyError,TypeError):continue
    except OSError as ex:print('Search history could not be read:',ex)


def store_search_event(key,state):
    if not HISTORY_ENABLED or not HISTORY_PATH:return
    if state not in {'NO_MATCH','REVIEW_AVAILABLE','VERIFIED_MATCH'}:return
    now=time.time()
    if state=='NO_MATCH':HISTORY_CACHE[key]=now
    else:HISTORY_CACHE.pop(key,None)
    try:
        with HISTORY_PATH.open('a',encoding='utf-8',newline='\n') as f:
            f.write(json.dumps({'key':key,'state':state,'at':now})+'\n')
    except OSError as ex:
        print('    Warning: search history write failed:',ex)


def store_completed_no_match(key):
    # Compatibility wrapper for previous test scripts.
    store_search_event(key,'NO_MATCH')


def contact_value(value):
    """Accept a real public HTTPS project URL or email, not a placeholder."""
    value=str(value or '').strip()
    if len(value)>180 or not value or any(c in value for c in '\r\n\t'):return ''
    if value.startswith('https://'):
        u=urllib.parse.urlsplit(value)
        if u.hostname and '.' in u.hostname and not u.username and not u.password:return value
    if re.fullmatch(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}',value):return value
    return ''


def configure_lrclib_contact(script_dir):
    """No invented homepage/email: LRCLIB is unavailable until configured."""
    global LRCLIB_IDENTIFIED,LRCLIB_USER_AGENT
    path=Path(script_dir)/'LRCLIB_CONTACT.txt'
    try:
        lines=path.read_text(encoding='utf-8-sig').splitlines() if path.exists() else []
        candidate=next((line.strip() for line in lines if line.strip() and not line.lstrip().startswith('#')), '')
        value=contact_value(candidate)
    except OSError:value=''
    LRCLIB_IDENTIFIED=bool(value)
    if value:
        LRCLIB_USER_AGENT=f'LRCBulkFinder/{VERSION} ({value})'
    else:
        LRCLIB_USER_AGENT=''
        blocked['LRCLIB']='LRCLIB needs project HTTPS URL or contact email in LRCLIB_CONTACT.txt'
        print('LRCLIB disabled: set your real project HTTPS URL or email in LRCLIB_CONTACT.txt before a run.')
    return LRCLIB_IDENTIFIED


def retry_after_seconds(header,now=None):
    now=time.time() if now is None else now
    if header is None:return 900  # cautious cooldown when header absent
    try:
        value=float(str(header).strip())
        if not 0 <= value <= 604800:return 900
        return max(value,1)
    except (TypeError,ValueError):
        try:
            when=parsedate_to_datetime(str(header))
            if when.tzinfo is None:when=when.replace(tzinfo=timezone.utc)
            return max(1,min(604800,when.timestamp()-now))
        except (ValueError,TypeError,OverflowError):return 900


def lrclib_503_delay(retry_after, streak):
    """Prefer the explicit server hint, with a short safety floor for overload.

    Without Retry-After, keep the proven bounded 60/120/240/... backoff.
    429 is handled separately and retains its persisted cooldown.
    """
    if retry_after is not None:
        return max(5.0, float(retry_after_seconds(retry_after)))
    return min(600.0, 60.0 * (2 ** min(max(0, streak - 1), 4)))


def wait_for_recovery(source, until, description):
    """Wait until a temporary server recovery ends, with visible progress.

    This is a *first attempt on a new song*, not a repeat of HTTP 503.
    Persistent 401/403/429 blocks always take precedence over this wait.
    Ctrl+C can interrupt normally; no busy loop or spurious traffic.
    """
    remaining=max(0.0,until-time.monotonic())
    if remaining <= 0:return
    print(f'    {source}: waiting ~{int(remaining + .999)}s for {description} '
          '(first-attempt coverage; Ctrl+C stops safely)', flush=True)
    while True:
        remaining=until-time.monotonic()
        if remaining<=0:break
        time.sleep(min(30.0,remaining))


def transient_recovery_delay(source, streak, hint=None):
    """Conservative short provider backoff; never bypass Retry-After."""
    if hint is not None:return max(5.0, float(retry_after_seconds(hint)))
    return min(180.0, 30.0 * (2 ** min(max(0,streak-1),3)))


def is_access_denied(ex):
    return str(ex).startswith(('HTTP 401:', 'HTTP 403:'))


def legacy_lrclib_queue_paths(folder):
    return (Path(folder)/'LRC_LRCLIB_Catchup_Queue_v2_1_13.csv',
            Path(folder)/'LRC_LRCLIB_Catchup_Queue_v2_1_12.csv',
            Path(folder)/'LRC_LRCLIB_Catchup_Queue_v2_1_11.csv',
            Path(folder)/'LRC_LRCLIB_Catchup_Queue_v2_1_10.csv',
            Path(folder)/'LRC_LRCLIB_Catchup_Queue_v2_1_9.csv')


def merge_previous_lrclib_queue(folder, current):
    """Bring forward v2.1.9-v2.1.13 incomplete LRCLIB entries."""
    gathered=[]
    for path in (current, *legacy_lrclib_queue_paths(folder)):
        if not path.is_file():continue
        try:
            with path.open(encoding='utf-8-sig',newline='') as f:
                gathered.extend(csv.DictReader(f))
        except (OSError,csv.Error) as ex:
            print('Warning: unable to read LRCLIB queue:',path,ex)
    unique={}
    for row in gathered:
        raw=row.get('MP3 path','')
        if raw and raw not in unique:unique[raw]=row
    return list(unique.values())


def load_provider_cooldowns(path):
    global COOLDOWN_PATH,COOLDOWN_UNTIL
    COOLDOWN_PATH=Path(path)
    COOLDOWN_UNTIL={}
    if not COOLDOWN_PATH.exists():return
    try:
        raw=json.loads(COOLDOWN_PATH.read_text(encoding='utf-8'))
        for name,until in raw.items():
            if name in PROVIDERS and time.time()<float(until)<time.time()+604801:
                COOLDOWN_UNTIL[name]=float(until)
                blocked[name]=f'429 cooldown active until {datetime.fromtimestamp(float(until)).isoformat(timespec="seconds")}'
    except (OSError,ValueError,TypeError,AttributeError):
        print('Warning: could not read provider cooldown file. Use provider rate limits responsibly.')


def record_rate_limit(provider,header):
    # Not a network retry. Records the required cooldown across restarts.
    if provider not in PROVIDERS:return
    expiry=time.time()+retry_after_seconds(header)
    COOLDOWN_UNTIL[provider]=max(COOLDOWN_UNTIL.get(provider,0),expiry)
    if not COOLDOWN_PATH:return
    try:
        data={k:v for k,v in COOLDOWN_UNTIL.items() if v>time.time()}
        temp=COOLDOWN_PATH.with_suffix('.tmp')
        temp.write_text(json.dumps(data,indent=2),encoding='utf-8')
        temp.replace(COOLDOWN_PATH)
    except OSError as ex:print('    Warning: cannot persist provider cooldown:',ex)


FAST_PROVIDERS = ('LRCLIB', 'SyncLRC', 'NetEase', 'Unison', 'LrcAPI')
ACTIVE_PROVIDERS = None


def normalize(s):
    s = unicodedata.normalize('NFKD', str(s or '')).casefold()
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = ''.join(c if c.isalnum() else ' ' for c in s)
    return ' '.join(s.split())

VERSION_WORDS = {'official','audio','video','remastered','remaster','version',
                 'edit','original','mix','radio','single','hd','hq','feat','ft','featuring',
                 'lyrics','lyric'}
GREEK_ARTIST_ALIASES = {}
G2G_ENABLED = False
G2G_TOOL = None
G2G_SONG_PLANS = {}
G2G_REPORT_ROWS = []
AI_PREVIEW_FIELDS = ['original title','original artist','Greek title alternative',
   'Greek artist alternative','title origin','artist origin','AI title output',
   'AI artist output','AI title flag','AI artist flag','search variations','review flag']
GREEK_TITLE_ALIASES = {}
# Custom Greek spellings can be edited without changing this script.
# File columns: type,greeklish,greek ; title AND artist aliases are supported.
# Empty by default in public release; every user may add their own aliases.
def load_aliases():
    f=Path(__file__).with_name('Greek_Aliases.csv')
    if not f.exists():return
    try:
        with f.open(encoding='utf-8-sig',newline='') as stream:
            for row in csv.DictReader(stream):
                key=normalize(row.get('greeklish'))
                val=(row.get('greek') or '').strip()
                kind=(row.get('type') or '').strip().casefold()
                if key and val:
                    if kind=='title':GREEK_TITLE_ALIASES[key]=val
                    elif kind=='artist':GREEK_ARTIST_ALIASES[key]=val
    except (OSError,UnicodeError,csv.Error) as ex:
        print('Could not load Greek_Aliases.csv:',ex)

# Greeklish spelling is ambiguous; 'nt' can be ντ or δ, 'i' can be ι/η/ει/οι.
# A letter-by-letter conversion produced errors like 'αν ισουνα εντο'.
# We now use curated FULL TITLE aliases, then a word-level Greek lexicon.
# If a title contains unknown words, do NOT invent a fake Greek translation.
GREEK_WORDS = {}

def load_greek_words():
    filename=Path(__file__).with_name('Greek_Words.csv')
    if not filename.exists():return
    try:
        with filename.open(encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                key=normalize(row.get('greeklish',''))
                value=(row.get('greek') or '').strip()
                if key and value and not any('a'<=c<='z' for c in value.casefold()):
                    GREEK_WORDS[key]=value
    except (OSError, UnicodeError, csv.Error) as ex:
        print('Cannot load Greek_Words.csv:',ex)

def dictionary_greek_title(title):
    """Return accented Greek title ONLY when every word is recognized.

    This does not pretend to be a full Greeklish translator. The user can
    add accurate spellings to Greek_Words.csv, or full phrases to Greek_Aliases.csv.
    """
    words=re.findall(r"[a-zA-Z]+",str(title or ''))
    if not words:return None
    result=[]
    for w in words:
        translated=GREEK_WORDS.get(normalize(w))
        if not translated:
            return None
        result.append(translated)
    text=' '.join(result)
    return text[:1].upper()+text[1:] if text else None

# Basic phonetic conversion. This is a *search guess*, not a Greek dictionary.
# Curated aliases and MusicBrainz verified names take precedence.
GREEKLISH_TO_GREEK = (
    ('th','θ'),('ps','ψ'),('ks','ξ'),('ch','χ'),('sh','σ'),('ou','ου'),
    ('tz','τζ'),('ts','τσ'),('mp','μπ'),('nt','ντ'),('gk','γκ'),
    ('ai','αι'),('ei','ει'),('oi','οι'),('ui','υι'),('au','αυ'),('eu','ευ'),
    ('a','α'),('b','μπ'),('c','κ'),('d','ντ'),('e','ε'),('f','φ'),
    ('g','γ'),('h','η'),('i','ι'),('j','τζ'),('k','κ'),('l','λ'),('m','μ'),
    ('n','ν'),('o','ο'),('p','π'),('q','κ'),('r','ρ'),('s','σ'),('t','τ'),
    ('u','ου'),('v','β'),('w','ω'),('x','χ'),('y','υ'),('z','ζ'),
)

def greeklish_to_greek(s):
    if any('\u0370'<=c<='\u03ff' for c in s):return s
    text=normalize(s)
    result=[];i=0
    while i<len(text):
        for latin,greek in GREEKLISH_TO_GREEK:
            if text.startswith(latin,i):
                result.append(greek);i+=len(latin);break
        else:
            result.append(text[i]);i+=1
    greek=''.join(result)
    return re.sub(r'σ(?=\s|$)', 'ς', greek)

# MusicBrainz metadata: ONE request per unique song, paced <=1 request/sec.
# It is NOT a lyrics database; it can suggest alternative artist/title spellings
# for Greek OR international files. Returned names are only search variants.
# Strict provider metadata verification still controls automatic LRC saving.
MB_ENABLED=False
GREEK_MODE=True
MB_CACHE={}
MB_CALLS=0
MB_DISABLED_REASON=None

def musicbrainz_variant(title,artist,duration):
    """Optional one-query metadata lookup for Greek and international tracks.

    International results must closely match identity, duration, and remix
    version. Greek-script variants retain the older Greeklish search thresholds.
    No result is accepted as proof that lyrics match a recording.
    """
    global MB_CALLS,MB_DISABLED_REASON
    key=(normalize(title),normalize(artist))
    if key in MB_CACHE:return MB_CACHE[key]
    MB_CACHE[key]=None
    if not MB_ENABLED or MB_DISABLED_REASON or not title or not artist:return None
    if GREEK_MODE and any('\u0370'<=c<='\u03ff' for c in title):return None
    try:
        query='"'+title.replace('"','')+'" '+artist.replace('"','')
        data=direct_json('MusicBrainz','https://musicbrainz.org/ws/2/recording',
            {'query':query,'fmt':'json','limit':10})
        MB_CALLS+=1
        rows=data.get('recordings',[]) if isinstance(data,dict) else []
        for r in rows:
            rt=r.get('title','')
            credits=r.get('artist-credit',[])
            ra=''.join(c.get('name','') for c in credits if isinstance(c,dict)) or artist
            length=r.get('length')
            if not rt or not ra:continue
            if GREEK_MODE:
                # Only seek a Greek-script alternative for likely Greeklish input.
                if not any('\u0370'<=ch<='\u03ff' for ch in rt):continue
                gap=abs(length/1000-duration) if length and duration else 0
                if similarity(title,rt)<.75 or similarity(artist,ra)<.7 or gap>12:continue
            else:
                # For international music, alternative spellings must be
                # independently plausible; never switch to a different remix.
                if not length or duration<=0:continue
                gap=abs(length/1000-duration)
                if gap>3 or not same_recording_version(title,rt):continue
                if similarity(title,rt)<.88 or similarity(artist,ra)<.85:continue
                if normalize(rt)==normalize(title) and normalize(ra)==normalize(artist):continue
            MB_CACHE[key]=(rt,ra)
            break
    except ProviderFailure as ex:
        # Optional metadata lookup never stops a lyrics search.
        if any(code in str(ex) for code in ('HTTP 503','HTTP 429','HTTP 502','HTTP 500')):
            MB_DISABLED_REASON=str(ex)
            print(f'    MusicBrainz unavailable ({ex}); disabling optional lookups for this run.')
        else:
            print(f'    MusicBrainz metadata unavailable ({ex}); use existing spellings.')
    return MB_CACHE[key]


def greeklish_phonetics(s):
    x = normalize(unidecode(str(s or '')))
    for old, new in [('th','8'),('ch','h'),('ph','f'),('ps','ps'),('ou','u'),
                     ('ei','i'),('oi','i'),('ai','e'),('mp','b'),('nt','d'),
                     ('gk','g'),('y','i')]:
        x = x.replace(old,new)
    return x


def forms(s):
    return {v for v in (normalize(s),normalize(unidecode(str(s or ''))),greeklish_phonetics(s)) if v}


def stripped(s):
    return ' '.join(x for x in normalize(s).split() if x not in VERSION_WORDS)


def similarity(a,b):
    if not a or not b:
        return 0.0
    scores=[]
    for x in forms(a):
        for y in forms(b):
            scores.append(difflib.SequenceMatcher(None,x,y).ratio())
            xx,yy=stripped(x),stripped(y)
            if xx and yy:
                scores.append(difflib.SequenceMatcher(None,xx,yy).ratio()*.985)
                scores.append(len(set(xx.split()) & set(yy.split())) / max(len(set(xx.split())),len(set(yy.split())))*.98)
    return max(scores or [0])


# Title-only Greek search aliases: NEVER replace the MP3 artist, and never
# infer an artist from the directory name or a previously searched track.
# The original tagged song title is always searched first.
GREEK_NONSONG_SUFFIX = re.compile(
    r"(?:\s*\((?:intro|outro|official\s+(?:video|audio)|lyrics?\s+video)\)"
    r"|\s*[-–]\s*(?:intro|outro|o\.?s\.?t\.?|soundtrack))\s*$", re.IGNORECASE
)

def clean_title_for_greek(title):
    cleaned=str(title or '').strip()
    while True:
        new=GREEK_NONSONG_SUFFIX.sub('',cleaned).strip()
        if new==cleaned:return cleaned
        cleaned=new

def protect_recording_suffix(title):
    """Keep recording/version labels in their original spelling during AI G2G.

    'Title - DJ Name Remix' becomes ('Title', ' - DJ Name Remix').
    Changing that suffix into phonetic Greek would erase useful identity data.
    """
    title=str(title or '')
    match=re.search(r'(\s*\([^)]{2,100}\)\s*)$',title)
    if match and VERSION_RE.search(match.group(1)) and title[:match.start()].strip():
        return title[:match.start()].strip(),match.group(1)
    match=re.search(r'(\s[-–]\s.{2,100})$',title)
    if match and VERSION_RE.search(match.group(1)) and title[:match.start()].strip():
        return title[:match.start()].strip(),match.group(1)
    return title,''

def is_live_track(text):
    # Match LIVE as a word. Do not skip 'Olive' or 'Deliver'.
    return bool(re.search(r'(?<![a-zA-Z])live(?![a-zA-Z])',str(text or ''),flags=re.IGNORECASE))

def query_variants(title,artist):
    """Preserve original tags, then at most two sensible Greek combinations.

    All plans and local model inferences are created in preflight. The lyrics
    search never calls the AI model, even in the second/third timeout rounds.
    Manual title/artist aliases always override AI candidates.
    """
    title=str(title or '').strip();artist=str(artist or '').strip()
    if not title or not artist:return []
    out=[(title,artist)]
    if not GREEK_MODE:
        # MusicBrainz is optional but now useful outside Greek mode as well.
        # The candidate is only a search spelling, NEVER trusted lyric identity.
        mb=MB_CACHE.get((normalize(title),normalize(artist))) if MB_ENABLED else None
        if mb and (normalize(mb[0]),normalize(mb[1])) != (normalize(title),normalize(artist)):
            out.append((mb[0],mb[1]))
        return out
    key=(normalize(title),normalize(artist))
    if key in G2G_SONG_PLANS:
        plan=list(G2G_SONG_PLANS[key])
        # MusicBrainz remains an optional source of verified Greek metadata;
        # preserve title/artist aliases as highest priority over its guesses.
        mb=MB_CACHE.get(key)
        if mb and not GREEK_TITLE_ALIASES.get(normalize(clean_title_for_greek(title))):
            mbtitle,mbartist=mb
            if mbtitle and (normalize(mbtitle),normalize(mbartist)) != (normalize(title),normalize(artist)):
                mbartist=GREEK_ARTIST_ALIASES.get(normalize(artist)) or mbartist or artist
                alternative=(mbtitle,mbartist,'MUSICBRAINZ_METADATA')
                if not any((t,a)==alternative[:2] for t,a,_ in plan):
                    plan.insert(1,alternative)
        return [(t,a) for t,a,_ in plan[:3]]
    base=clean_title_for_greek(title)
    alt_t=GREEK_TITLE_ALIASES.get(normalize(base))
    mb=MB_CACHE.get(key)
    if not alt_t and mb:alt_t=mb[0]
    if not alt_t and not any('\u0370'<=ch<='\u03ff' for ch in base):
        alt_t=dictionary_greek_title(base)
    if not alt_t and base!=title:alt_t=base
    if alt_t and normalize(alt_t)!=normalize(title):out.append((alt_t.strip(),artist))
    return out[:2]


def label_for_query(title,artist,query_title,query_artist):
    key=(normalize(title),normalize(artist))
    for t,a,source in G2G_SONG_PLANS.get(key,[]):
        if (t,a)==(query_title,query_artist):return source
    mb=MB_CACHE.get(key)
    if mb and (query_title,query_artist)==mb:return 'MUSICBRAINZ_METADATA'
    if (title,artist)==(query_title,query_artist):return 'ORIGINAL'
    return 'MANUAL_OR_DICTIONARY_TITLE'


def precompute_greek_plan(title,artist,manager=None):
    """Run once per song before network searches, never in provider functions.

    Return a detailed row for report/preview; all displayed alternatives are
    potential queries ONLY and do not alter original MP3 tags.
    """
    original_title=str(title or '').strip()
    original_artist=str(artist or '').strip()
    base=clean_title_for_greek(original_title)
    key=(normalize(original_title),normalize(original_artist))
    title_alias=GREEK_TITLE_ALIASES.get(normalize(base),'')
    ai_base,version_suffix=protect_recording_suffix(base)
    artist_alias=GREEK_ARTIST_ALIASES.get(normalize(original_artist),'')
    title_kind='MANUAL_TITLE' if title_alias else ''
    artist_kind='MANUAL_ARTIST' if artist_alias else ''
    ai_title='';ai_artist='';title_flag='';artist_flag=''
    if not title_alias:
        if manager:
            ai_title,title_flag=manager.convert(ai_base,'title')
            if ai_title:
                title_alias=ai_title+version_suffix;title_kind='AI_TITLE'
        if not title_alias:
            from_dict=dictionary_greek_title(ai_base) if not G2G_GREEK.search(ai_base) else ''
            if from_dict:
                title_alias=from_dict+version_suffix;title_kind='DICTIONARY_TITLE'
    if not artist_alias and manager and not g2g_english_skip(base,'title'):
        ai_artist,artist_flag=manager.convert(original_artist,'artist')
        if ai_artist:
            artist_alias=ai_artist;artist_kind='AI_ARTIST'
    if not title_alias and base!=original_title:
        title_alias=base;title_kind='CLEANED_TITLE'
    # Only include genuine changes, not alternate capitalization/accent variants
    # that normalize identically. Greek-script alternatives are different.
    if title_alias and normalize(title_alias)==normalize(original_title):
        title_alias='';title_kind=''
    if artist_alias and normalize(artist_alias)==normalize(original_artist):
        artist_alias='';artist_kind=''
    plan=[(original_title,original_artist,'ORIGINAL')]
    if title_alias and artist_alias:
        plan.append((title_alias,artist_alias,title_kind+'+'+artist_kind))
    if title_alias:
        plan.append((title_alias,original_artist,title_kind))
    elif artist_alias:
        plan.append((original_title,artist_alias,artist_kind))
    unique=[]
    for t,a,provenance in plan:
        if not any((x,y)==(t,a) for x,y,_ in unique):unique.append((t,a,provenance))
    # LRCLIB caps itself at 2 requests; other providers may search 3.
    G2G_SONG_PLANS[key]=unique[:3]
    return {
        'original title':original_title,'original artist':original_artist,
        'Greek title alternative':title_alias,'Greek artist alternative':artist_alias,
        'title origin':title_kind or 'NONE','artist origin':artist_kind or 'NONE',
        'AI title output':ai_title,'AI artist output':ai_artist,
        'AI title flag':title_flag,'AI artist flag':artist_flag,
        'search variations':' | '.join(f'{src}: {a} - {t}' for t,a,src in unique),
        'review flag': 'REVIEW_AI_SPELLING' if any(x.startswith('AI_') for x in (title_kind,artist_kind)) else '',
    }


# Safe to call more than once; dictionary keys are stable.
load_greek_words()

def tag_string(tags,key):
    try:
        val=tags.get(key)
        if isinstance(val,list): val=val[0] if val else ''
        return str(val or '').strip()
    except Exception: return ''


def song_info(path):
    audio=AudioFile(path,easy=True)
    tags=audio.tags if audio and audio.tags else {}
    title=tag_string(tags,'title')
    artist=tag_string(tags,'artist')
    album=tag_string(tags,'album')
    duration=float(audio.info.length) if audio and audio.info else 0
    if ' - ' in path.stem and (not title or not artist):
        guess_artist,guess_title=path.stem.split(' - ',1)
        title=title or guess_title.strip()
        artist=artist or guess_artist.strip()
    return title,artist,album,duration


class ProviderFailure(Exception):
    def __init__(self, message, *, rate_limit=False, retry_after=None, timeout=False):
        super().__init__(message)
        self.rate_limit=rate_limit
        self.retry_after=retry_after
        self.timeout=timeout or rate_limit


def wait_for(provider):
    gap=BASE_GAP.get(provider,1.0)*ROUND
    until=next_available.get(provider,0)
    # LRCLIB documents a gap *between* sequential requests. The older
    # start-to-start delay could send two long requests back-to-back.
    if provider=='LRCLIB':until=max(until,LRCLIB_LAST_FINISHED+0.5)
    if until>time.monotonic():time.sleep(until-time.monotonic())
    next_available[provider]=time.monotonic()+gap


def direct_get(provider,url,params):
    """Single bounded HTTP request; record actual status or transport error.

    Never expose the full URL with query parameters in diagnostic reports.
    """
    global LRCLIB_LAST_FINISHED
    wait_for(provider)
    full=url+'?'+urllib.parse.urlencode(params)
    started=time.monotonic()
    try:
        request_headers=dict(HEADERS)
        if provider=='MusicBrainz':
            # MusicBrainz requires a project-identifying User-Agent.
            request_headers['User-Agent']=f'LRCBulkFinder/{VERSION} (https://github.com/DimitrisLai/LRC-Bulk-Finder)'
        if provider=='LRCLIB' and LRCLIB_USER_AGENT:
            request_headers['User-Agent']=LRCLIB_USER_AGENT
            request_headers['Lrclib-Client']=LRCLIB_USER_AGENT
        req=urllib.request.Request(full,headers=request_headers)
        with urllib.request.urlopen(req,timeout=NETWORK_TIMEOUT) as response:
            code=getattr(response,'status',None)
            if code is None:
                code=response.getcode() if hasattr(response,'getcode') else None
            payload=response.read(2_000_000)
            add_http_event(provider,url,str(code) if code is not None else 'HTTP_2XX_UNSPECIFIED',started)
            return payload.decode('utf-8-sig','replace')
    except urllib.error.HTTPError as ex:
        ra=ex.headers.get('Retry-After') if ex.headers else None
        detail=''
        if ex.code==401 and provider=='BetterTTML':
            detail='uncached or unauthorized TTML response; no lyrics returned'
        elif ex.code==404:
            detail='resource not found'
        elif ex.code==429:
            detail=f'rate-limited; Retry-After={ra or "not supplied"}'
        else:
            detail=str(ex.reason or 'HTTP error')[:120]
        add_http_event(provider,url,str(ex.code),started,detail)
        if ex.code==404:return None
        # HTTP 401 means the endpoint refused this request; it is NOT proof
        # that synced lyrics do not exist. Do not poison NO_MATCH history.
        # This public endpoint may require access credentials or an upstream
        # cache; avoid thousands of repeated unauthorized attempts.
        if ex.code==429:
            raise ProviderFailure(f'HTTP 429: {detail}',rate_limit=True,retry_after=ra) from ex
        raise ProviderFailure(f'HTTP {ex.code}: {detail}',retry_after=ra if ex.code==503 else None) from ex
    except (TimeoutError,urllib.error.URLError,OSError) as ex:
        cause=ex.reason if isinstance(ex,urllib.error.URLError) else ex
        is_timeout=isinstance(cause,(TimeoutError,socket.timeout)) or 'timed out' in str(cause).lower()
        code='NETWORK_TIMEOUT' if is_timeout else 'NETWORK_ERROR'
        add_http_event(provider,url,code,started,f'{type(ex).__name__}: {str(cause)[:120]}')
        raise ProviderFailure(f'{type(ex).__name__}: {str(ex)[:150]}',timeout=is_timeout) from ex
    finally:
        if provider=='LRCLIB':LRCLIB_LAST_FINISHED=time.monotonic()


def direct_json(provider,url,params):
    raw=direct_get(provider,url,params)
    if raw is None:return None
    try:return json.loads(raw)
    except (ValueError,TypeError) as ex:raise ProviderFailure('Invalid JSON returned') from ex


def lrc_lines(text):
    """Parse conventional LRC timestamps, applying an optional millisecond offset.

    Duplicated time/text pairs are discarded; simultaneous distinct lines are
    preserved for human review. Original lyrics are never modified on disk.
    """
    if not isinstance(text,str) or len(text)>2_000_000:return []
    match=re.search(r'^\s*\[offset:\s*([+-]?\d+)\s*\]\s*$',text,re.I|re.M)
    offset_ms=int(match.group(1)) if match else 0
    if abs(offset_ms)>120000:return []
    result=[];seen=set()
    for line in text.splitlines():
        m=re.match(r'^\s*\[(\d{1,3}):(\d{2})(?:\.(\d{1,3}))?\]\s*(.*)$',line)
        if not m or int(m.group(2))>=60:continue
        fraction=(m.group(3) or '')
        stamp=int(m.group(1))*60+int(m.group(2))+(int(fraction)/(10**len(fraction)) if fraction else 0)+offset_ms/1000
        if not 0<=stamp<=36000:continue
        content=re.sub(r'<\d{1,3}:\d{2}(?:\.\d+)?>','',m.group(4))
        content=re.sub(r'\{agent:[^}]*\}','',content).strip()
        key=(round(stamp*100),content)
        if key not in seen:
            seen.add(key);result.append((stamp,content))
    return sorted(result,key=lambda item:item[0])


def sanitize_lrc(text):
    lines=lrc_lines(text)
    return ('\n'.join(f'[{round(s*100)//6000:02d}:{(round(s*100)//100)%60:02d}.{round(s*100)%100:02d}] {v}' for s,v in lines).strip()+'\n') if lines else ''


def plausible_lrc(text,duration):
    rows=lrc_lines(text)
    if len(rows)<3 or sum(bool(t) for _,t in rows)<2:return False
    end=max(t for t,_ in rows)
    if duration and not (duration*.45<=end<=duration+8):return False
    return True


# Strict recording-version verification: a regular studio recording cannot
# silently accept an extended mix, radio edit, instrumental, or named remix.
VERSION_RE = re.compile(r'\b(remix|re\s*mix|mix|extended|radio\s*edit|radio|edit|instrumental|acoustic|karaoke|live|demo|club|sped\s*up|slowed|remaster(?:ed)?)\b',re.I)

def version_signature(title):
    title=str(title or '')
    norm=normalize(title)
    markers=set()
    if re.search(r'\b(remix|re\s*mix|mix|club)\b',norm):markers.add('mix')
    if re.search(r'\b(extended|long version)\b',norm):markers.add('extended')
    if re.search(r'\b(radio edit|radio mix|radio version)\b',norm):markers.add('radio')
    if re.search(r'\b(edit)\b',norm) and 'radio' not in markers:markers.add('edit')
    for token in ('instrumental','acoustic','karaoke','live','demo','remaster','sped up','slowed'):
        if re.search(r'\b'+re.escape(token)+r'(?:ed)?\b',norm):markers.add(token)
    # Capture descriptive version names in parentheses or after a dash.
    descriptors=[]
    for value in re.findall(r'\(([^)]{2,100})\)',title):
        if VERSION_RE.search(value):descriptors.append(normalize(value))
    dash=re.search(r'\s[-–]\s(.{2,100})$',title)
    if dash and VERSION_RE.search(dash.group(1)):descriptors.append(normalize(dash.group(1)))
    return frozenset(markers),frozenset(descriptors)


def same_recording_version(title,candidate):
    tags_a,descriptions_a=version_signature(title)
    tags_b,descriptions_b=version_signature(candidate)
    if tags_a!=tags_b:return False
    # Named remixes must refer to the same named mix, not a different remix.
    if descriptions_a or descriptions_b:
        return bool(descriptions_a and descriptions_b and descriptions_a==descriptions_b)
    return True


def metadata_score(title,artist,duration,result_title,result_artist,result_duration=0):
    ts=similarity(title,result_title)
    ars=similarity(artist,result_artist)
    try:
        rd=float(result_duration or 0)
        gap=abs(rd-duration) if rd>0 and duration>0 else None
    except (TypeError,ValueError):gap=None
    return ts,ars,gap


def acceptable(title,artist,duration,candidate_title,candidate_artist,candidate_duration,text,*,require_duration=True):
    """Automatic sidecar writing requires verified identity, version AND length.

    Timed text alone cannot verify the track; unverified provider results must
    only enter candidate review, even if the title in the query looks right.
    """
    if not plausible_lrc(text,duration):return False,'LRC timestamps incompatible with MP3 duration'
    if not candidate_title or not candidate_artist:return False,'Provider did not resolve title AND artist'
    if not same_recording_version(title,candidate_title):return False,'Recording version/remix/edit mismatch'
    ts,ars,gap=metadata_score(title,artist,duration,candidate_title,candidate_artist,candidate_duration)
    if ts<.77 or ars<.73:return False,f'artist/title uncertain ({ts:.2f}/{ars:.2f})'
    if gap is None or duration<=0:
        return False,'Provider has no verified recording duration'
    if gap>3.0:return False,f'duration difference {gap:.2f}s exceeds 3s limit'
    return True, f'verified artist/title {ars:.2f}/{ts:.2f}, duration difference {gap:.2f}s'


@dataclass
class Hit:
    lyrics:str
    provider:str
    note:str
    search_variation:str="ORIGINAL"
    verified:bool=False


class CandidateReview:
    """Collect timed review candidates without treating them as verified lyrics."""
    def __init__(self):
        self.items=[]
        self.count=Counter()
    def add(self,provider,title,artist,note,lyrics=None):
        self.count[provider]+=1
        if len(self.items)<15:
            body=sanitize_lrc(lyrics) if lyrics and plausible_lrc(lyrics,0) else ''
            # Bound memory and saved review content for large collections.
            if body and len(body)>100000:body=''
            # Keep each eligible candidate (up to the existing 15-item cap).
            self.items.append((provider,title,artist,note,body))


def candidate_path(track,position=1):
    """Keep candidate(s) beside the MP3 without masquerading as approved LRC.

    Multiple potential matches get .candidate.2.lrc, .candidate.3.lrc, etc.
    Only the primary .candidate.lrc is eligible for bulk promotion.
    """
    suffix='.candidate.lrc' if position==1 else f'.candidate.{position}.lrc'
    return track.with_name(track.stem+suffix)


def export_review_candidates(track,rnd,review,review_folder=None):
    """Store candidates beside MP3, never replacing existing lyrics or candidates.

    review_folder is an unused compatibility parameter for older test callers.
    Every nonempty candidate has a destination path in the review CSV.
    """
    output=[]
    # No reason to leave an unverified sidecar if verified lyrics were installed.
    if track.with_suffix('.lrc').exists():
        return [[str(track),rnd,p,t,a,n,''] for p,t,a,n,_ in review.items]
    body_to_path={}
    position=1
    for provider,title,artist,note,body in review.items:
        saved_path=''
        if body:
            # Reuse the first matching candidate path instead of writing duplicates.
            if body in body_to_path:
                saved_path=body_to_path[body]
                output.append([str(track),rnd,provider,title,artist,note,saved_path])
                continue
            while position<=100:
                target=candidate_path(track,position)
                if target.exists():
                    try:
                        old=target.read_text(encoding='utf-8-sig')
                        if old==body:
                            saved_path=str(target)
                            body_to_path[body]=saved_path
                            break
                    except (OSError,UnicodeError):
                        pass
                    position+=1
                    continue
                try:
                    with target.open('x',encoding='utf-8',newline='\n') as out:
                        out.write(body)
                    saved_path=str(target)
                    body_to_path[body]=saved_path
                    print('      Review candidate saved:',target.name,flush=True)
                    position+=1
                    break
                except FileExistsError:
                    position+=1
                except OSError as ex:
                    print(f'      Warning: candidate not saved ({target.name}): {ex}',flush=True)
                    break
            else:
                print('      Warning: 100 candidate sidecars already exist; no additional candidate saved.',flush=True)
        output.append([str(track),rnd,provider,title,artist,note,saved_path])
    return output


def promote_candidate_file(candidate):
    """Safely copy then remove an explicitly chosen .candidate.lrc.

    Preconditions: same-named MP3 exists; candidate is valid timestamped LRC;
    final .lrc does not exist. Destination is opened exclusively, NEVER replaced.
    Returns (action, reason).
    """
    suffix='.candidate.lrc'
    if not candidate.name.lower().endswith(suffix):
        return 'SKIPPED','not a primary .candidate.lrc file'
    original_stem=candidate.name[:-len(suffix)]
    mp3=candidate.with_name(original_stem+'.mp3')
    target=candidate.with_name(original_stem+'.lrc')
    if not mp3.is_file():return 'SKIPPED','matching MP3 not found'
    if target.exists():return 'SKIPPED','approved .lrc already exists (never overwrite)'
    try:
        text=candidate.read_text(encoding='utf-8-sig')
    except (OSError,UnicodeError) as ex:
        return 'ERROR',f'cannot read candidate: {ex}'
    if not plausible_lrc(text,0):return 'SKIPPED','candidate is not a valid timed LRC'
    try:
        # Exclusive mode prevents accidental overwriting and works on Windows.
        raw=candidate.read_bytes()
        with target.open('xb') as out:
            out.write(raw)
            out.flush()
            import os
            os.fsync(out.fileno())
        candidate.unlink()
    except FileExistsError:
        return 'SKIPPED','approved .lrc appeared during promotion'
    except OSError as ex:
        # If the copy was written but removal failed, leave both intact.
        return 'ERROR',str(ex)
    return 'PROMOTED',str(target)


def promote_candidates(folder,recursive=True,confirm=True):
    """Promote primary review sidecars, with preflight and one confirmation."""
    if not folder.is_dir():
        print('Folder does not exist:',folder)
        return {'PROMOTED':0,'SKIPPED':0,'ERROR':1}
    candidates=sorted((p for p in (folder.rglob('*') if recursive else folder.iterdir())
                       if p.is_file() and p.name.lower().endswith('.candidate.lrc')),
                      key=lambda p:str(p).casefold())
    counts=Counter()
    print(f'\nFound {len(candidates)} primary .candidate.lrc files.',flush=True)
    if not candidates:return counts
    print('Only exact .candidate.lrc files will be promoted. .candidate.2.lrc alternatives stay untouched.')
    print('Original MP3 files will not be edited. Existing approved .lrc files are NEVER overwritten.')
    for path in candidates[:5]:
        print('  '+path.name+'  ->  '+path.name[:-len('.candidate.lrc')]+'.lrc')
    if len(candidates)>5:print(f'  ... and {len(candidates)-5} more')
    if confirm and input('Promote all eligible candidates to approved .lrc? [y/N]: ').strip().lower() not in {'y','yes'}:
        print('Cancelled; no files changed.')
        return counts
    report=[]
    for index,path in enumerate(candidates,1):
        action,reason=promote_candidate_file(path)
        counts[action]+=1
        report.append([str(path),action,reason])
        if action!='PROMOTED' or index<=10 or index%100==0:
            print(f'  [{index}/{len(candidates)}] {action}: {path.name} — {reason}',flush=True)
    report_path=folder/'LRC_Candidate_Promotion_Report_v2_1_8.csv'
    try:
        with report_path.open('w',encoding='utf-8-sig',newline='') as out:
            writer=csv.writer(out)
            writer.writerow(['candidate path','result','reason / approved LRC path'])
            writer.writerows(report)
        print('Promotion report:',report_path)
    except OSError as ex:
        print('Warning: could not save promotion report:',ex)
    print('PROMOTED:',counts['PROMOTED'],'| SKIPPED:',counts['SKIPPED'],'| ERRORS:',counts['ERROR'])
    return counts


# ---- Verified public sources added for v2.0 (2026-10) ----------------------
# Unicode/TTML -> simple, line-timed sidecar LRC for older car stereos.
def parse_timestamp(value):
    x=str(value or '').strip()
    if not x:return None
    if re.fullmatch(r'\d+(?:\.\d+)?ms',x):return float(x[:-2])/1000
    if re.fullmatch(r'\d+(?:\.\d+)?s',x):return float(x[:-1])
    if re.fullmatch(r'\d+(?:\.\d+)?',x):return float(x)
    parts=x.split(':')
    try:
        if len(parts)==2: return int(parts[0])*60+float(parts[1])
        if len(parts)==3: return int(parts[0])*3600+int(parts[1])*60+float(parts[2])
    except ValueError: pass
    return None


def ttml_to_lrc(source):
    """Convert TTML p@begin lines to plain LRC; no karaoke word tags required."""
    if not isinstance(source,str) or len(source)>2_000_000:return ''
    try:root=ET.fromstring(source)
    except ET.ParseError:return ''
    out=[]
    for elem in root.iter():
        if elem.tag.rsplit('}',1)[-1] != 'p':continue
        stamp=parse_timestamp(elem.attrib.get('begin') or elem.attrib.get('start'))
        if stamp is None or not (0<=stamp<36000):continue
        words=''.join(elem.itertext())
        words=' '.join(words.split()).strip()
        if words:
            out.append((stamp,words))
    out.sort(key=lambda a:a[0])
    return '\n'.join(f'[{cs//6000:02d}:{(cs//100)%60:02d}.{cs%100:02d}] {line}' for cs,line in ((round(sec*100),line) for sec,line in out))+'\n' if out else ''


def synced_payload(data,fmt=''):
    """Read provider payload, converting TTML only when necessary."""
    if isinstance(data,dict):
        fmt=str(data.get('format',fmt)).lower()
        data=data.get('lyrics') or data.get('ttml') or data.get('synced') or ''
    if not isinstance(data,str):return ''
    if fmt=='plain':return ''
    if fmt=='ttml' or re.search(r'<(?:tt|\w+:tt)(?:\s|>)',data[:500]):
        return ttml_to_lrc(data)
    return data if lrc_lines(data) else ''


def provider_unison(title,artist,album,duration,review):
    """Unison: metadata-rich exact lookup + bounded ranked discovery fallback."""
    seen_ids=set()
    for t,a in query_variants(title,artist):
        body=direct_json('Unison','https://unison.boidu.dev/lyrics',
                         {'song':t,'artist':a})
        if isinstance(body,dict) and body.get('success') and isinstance(body.get('data'),dict):
            row=body['data']
            lyr=synced_payload(row.get('lyrics',''),row.get('format',''))
            if lyr:
                ok,note=acceptable(title,artist,duration,row.get('song',''),row.get('artist',''),row.get('duration'),lyr)
                if ok:return Hit(lyr,'Unison',note,label_for_query(title,artist,t,a),True)
                review.add('Unison',row.get('song',''),row.get('artist',''),note,lyrics=lyr)
        # Broader search can surface other transliterations; metadata must match
        # before downloading potentially large community-submitted lyric bodies.
        candidates=direct_json('Unison','https://unison.boidu.dev/lyrics/search',
                               {'q':t+' '+a,'limit':8})
        rows=candidates.get('data',[]) if isinstance(candidates,dict) and candidates.get('success') else []
        if not isinstance(rows,list):rows=[]
        ranked=[]
        for row in rows:
            if not isinstance(row,dict):continue
            ts=similarity(title,row.get('song',''))
            ars=similarity(artist,row.get('artist',''))
            if ts>=.77 and ars>=.73 and row.get('format')!='plain':
                ranked.append((ts+ars,row))
        for _,candidate in sorted(ranked,reverse=True,key=lambda pair:pair[0])[:2]:
            vid=candidate.get('videoId'); rid=candidate.get('id')
            key=str(vid or rid or '')
            if not key or key in seen_ids:continue
            seen_ids.add(key)
            if vid:
                match=direct_json('Unison','https://unison.boidu.dev/lyrics',{'v':vid})
            elif rid:
                match=direct_json('Unison',f'https://unison.boidu.dev/lyrics/{int(rid)}',{})
            else:continue
            if not isinstance(match,dict) or not match.get('success'):continue
            row=match.get('data',{})
            if not isinstance(row,dict):continue
            lyr=synced_payload(row.get('lyrics',''),row.get('format',''))
            if not lyr:continue
            ok,note=acceptable(title,artist,duration,row.get('song',''),row.get('artist',''),row.get('duration'),lyr)
            if ok:return Hit(lyr,'Unison',note,label_for_query(title,artist,t,a),True)
            review.add('Unison',row.get('song',''),row.get('artist',''),note,lyrics=lyr)
    return None


def provider_better(provider,title,artist,album,duration,review):
    """Better Lyrics: independent endpoint routes, often cached-only."""
    endpoint='/kugou/getLyrics' if provider=='BetterKuGou' else '/ttml/getLyrics'
    for t,a in query_variants(title,artist):
        params={'s':t,'a':a,'al':album or '', 'd':str(round(duration)) if duration else '0'}
        body=direct_json(provider,'https://api.betterlyrics.org'+endpoint,params)
        if not isinstance(body,dict):continue
        lyr=synced_payload(body.get('lyrics',''), 'lrc' if provider=='BetterKuGou' else 'ttml')
        if not lyr:continue
        # Response does not include resolved song metadata. We cannot prove
        # it is the requested remix/version; do not auto-save remixes without it.
        if re.search(r'\b(remix|live|edit|extended|instrumental|club|radio)\b',normalize(title)):
            review.add(provider,t,a,'Result has no verified recording metadata; remix/version needs manual review',lyrics=lyr)
            continue
        if plausible_lrc(lyr,duration):
            review.add(provider,t,a,'Unverified identity; candidate only, never automatically saved',lyrics=lyr)
            continue
        review.add(provider,t,a,'timing incompatible with MP3 duration')
    return None


def provider_youly(title,artist,album,duration,review):
    """Experimental hosted YouLy+ Apple/other-provider TTML endpoint.

    The API may be intermittently inaccessible; errors do not force retries.
    """
    for t,a in query_variants(title,artist):
        raw=direct_get('YouLyTTML','https://lyricsplus.prjktla.my.id/v1/ttml/get',
                       {'title':t,'artist':a,'album':album or '',
                        'duration':str(round(duration)) if duration else '0'})
        if not raw:continue
        lyr=synced_payload(raw,'ttml')
        if not lyr and raw.lstrip().startswith('{'):
            try:lyr=synced_payload(json.loads(raw),'ttml')
            except ValueError:pass
        if not lyr:continue
        if re.search(r'\b(remix|live|edit|extended|instrumental|club|radio)\b',normalize(title)):
            review.add('YouLyTTML',t,a,'No verified recording metadata; manual review for remix/version',lyrics=lyr)
            continue
        if plausible_lrc(lyr,duration):
            review.add('YouLyTTML',t,a,'Unverified identity; candidate only',lyrics=lyr)
            continue
        review.add('YouLyTTML',t,a,'TTML timing incompatible with audio duration')
    return None

def configure_local_lrclib(script_dir):
    """Load an optional independently downloaded SQLite snapshot, never network."""
    global LOCAL_LRCLIB
    LOCAL_LRCLIB = None
    try:
        local_path = load_local_config(Path(script_dir) / 'LRCLIB_LOCAL_DB.txt')
        if local_path:
            LOCAL_LRCLIB = LocalLRCLIB(local_path)
            print('LOCAL LRCLIB: READY —', local_path, flush=True)
            print('  Searches the snapshot first; original artist/version/duration safeguards remain.', flush=True)
        else:
            print('LOCAL LRCLIB: Not configured (optional). Run SETUP_LRCLIB_DATABASE.cmd.',flush=True)
    except (OSError, ValueError, RuntimeError) as ex:
        print('LOCAL LRCLIB: unavailable:',ex,flush=True)
        print('  Check LRCLIB_LOCAL_DB.txt or rerun SETUP_LRCLIB_DATABASE.cmd.',flush=True)


def local_lrclib_search(title, artist, duration, review):
    """Look up locally and evaluate exactly like normal LRCLIB results."""
    if LOCAL_LRCLIB is None:
        return None
    started=time.monotonic()
    try:
        candidates=LOCAL_LRCLIB.search(query_variants(title,artist)[:2],duration)
        if ACTIVE_HTTP_TRACE is not None:
            ACTIVE_HTTP_TRACE.append({'provider':'LRCLIB','endpoint':'local LRCLIB SQLite (no network)',
                'status':'LOCAL_DB_LOOKUP','detail':f'{len(candidates)} candidates (no HTTP request)',
                'elapsed_seconds':round(time.monotonic()-started,3)})
    except (OSError,RuntimeError,ValueError) as ex:
        if ACTIVE_HTTP_TRACE is not None:
            ACTIVE_HTTP_TRACE.append({'provider':'LRCLIB','endpoint':'local LRCLIB SQLite (no network)',
                'status':'LOCAL_DB_ERROR','detail':str(ex)[:170],
                'elapsed_seconds':round(time.monotonic()-started,3)})
        print('      Local LRCLIB lookup failed:',ex,flush=True)
        return None
    best=[]
    for row in candidates:
        lyr=row.get('syncedLyrics')
        if not lyr:continue
        ot=row.get('trackName','');oa=row.get('artistName','')
        ok,note=acceptable(title,artist,duration,ot,oa,row.get('duration'),lyr)
        if ok:best.append((similarity(title,ot)+similarity(artist,oa),lyr,note))
        else:review.add('LRCLIB local',ot,oa,note,lyrics=lyr)
    if best:
        _,lyrics,note=max(best,key=lambda item:item[0])
        return Hit(lyrics,'LRCLIB',note,'LOCAL_SQLITE',True)
    return None


def provider_lrclib(title,artist,album,duration,review):
    """Manual-style full-text search, maximum two requests per track.

    Old implementation could issue 4+ calls/song and trigger 429 immediately.
    A Greek spelling alternative counts as search inside the FIRST round.
    """
    if LOCAL_LRCLIB is not None:
        local_hit=local_lrclib_search(title,artist,duration,review)
        if local_hit:
            print('      LRCLIB: verified OFFLINE SQLite match (no HTTP request)',flush=True)
            return local_hit
        if not LRCLIB_ONLINE_FALLBACK:
            print('      LRCLIB: offline snapshot checked; online fallback disabled for this catch-up run.',flush=True)
            return None
    candidates=[]
    seen=set()
    for qt,qa in query_variants(title,artist)[:2]:
        res=direct_json('LRCLIB','https://lrclib.net/api/search',
            {'q':(qa+' '+qt).strip()})
        ranked=[]
        for row in (res if isinstance(res,list) else []):
            if not isinstance(row,dict):continue
            rid=row.get('id') or (row.get('trackName'),row.get('artistName'))
            if str(rid) in seen:continue
            seen.add(str(rid))
            lyr=row.get('syncedLyrics')
            if not lyr:continue
            ot=row.get('trackName','');oa=row.get('artistName','')
            ok,note=acceptable(title,artist,duration,ot,oa,row.get('duration'),lyr)
            if ok:ranked.append((similarity(title,ot)+similarity(artist,oa),lyr,note,label_for_query(title,artist,qt,qa)))
            else:review.add('LRCLIB',ot,oa,note,lyrics=lyr)
        if ranked:
            _,lyr,note,variation=max(ranked,key=lambda v:v[0])
            return Hit(lyr,'LRCLIB',note,variation,True)
    # Optional, strictly guarded fallback: keep the two original keyword
    # searches UNCHANGED. Only after they produce no verified lyrics can
    # /api/get receive a single original title+artist+duration signature.
    # Disabled by default to avoid extra LRCLIB load during bulk searches.
    if LRCLIB_EXACT_FALLBACK and title and artist and 1 <= duration <= 3600:
        args={'track_name':title,'artist_name':artist,'duration':round(duration,2)}
        if album:args['album_name']=album
        row=direct_json('LRCLIB','https://lrclib.net/api/get',args)
        if isinstance(row,dict):
            lyr=row.get('syncedLyrics')
            if lyr:
                ot=row.get('trackName','');oa=row.get('artistName','')
                ok,note=acceptable(title,artist,duration,ot,oa,row.get('duration'),lyr)
                if ok:return Hit(lyr,'LRCLIB',note,'LRCLIB_EXACT_SIGNATURE',True)
                review.add('LRCLIB',ot,oa,note,lyrics=lyr)
    return None


def provider_synclrc(title,artist,album,duration,review):
    for t,a in query_variants(title,artist):
        data=direct_json('SyncLRC','https://api.synclrc.dev/search',{'q':f'{t} {a}', 'limit':10})
        rows=data.get('results',[]) if isinstance(data,dict) else []
        for row in rows:
            if not isinstance(row,dict):continue
            lyrics=row.get('lyrics',{})
            lyr=lyrics.get('synced') if isinstance(lyrics,dict) else row.get('synced')
            if not lyr:continue
            ot=row.get('track','');oa=row.get('artist','')
            ok,note=acceptable(title,artist,duration,ot,oa,row.get('duration'),lyr)
            if ok:return Hit(lyr,'SyncLRC',note,label_for_query(title,artist,t,a),True)
            review.add('SyncLRC',ot,oa,note,lyrics=lyr)
    return None


def provider_lrcapi(title,artist,album,duration,review):
    for t,a in query_variants(title,artist):
        params={'title':t,'artist':a}
        # Album is often incompatible with online catalogs: omit by default.
        rows=direct_json('LrcAPI','https://api.lrc.cx/api/v1/lyrics/advance',params)
        if isinstance(rows,dict): rows=rows.get('results',rows.get('data',[]))
        if not isinstance(rows,list):continue
        for row in rows[:15]:
            if not isinstance(row,dict):continue
            lyr=row.get('lyrics',''); ot=row.get('title','');oa=row.get('artist','')
            if not lyr:continue
            ok,note=acceptable(title,artist,duration,ot,oa,row.get('duration'),lyr)
            if ok:return Hit(lyr,'LrcAPI',note,label_for_query(title,artist,t,a),True)
            review.add('LrcAPI',ot,oa,note,lyrics=lyr)
    return None


def timed_to_lrc(timed):
    out=[]
    for ln in timed:
        if not isinstance(ln,dict):continue
        try:seconds=float(ln.get('start'))
        except (TypeError,ValueError):continue
        if seconds<0 or seconds>20000:continue
        content=ln.get('text') or ''
        if not isinstance(content,str):continue
        mins=int(seconds//60);secs=int(seconds%60);cent=int(round((seconds%1)*100))
        if cent==100:secs+=1;cent=0
        if secs>=60:mins+=1;secs=0
        out.append(f'[{mins:02}:{secs:02}.{cent:02}] {content.strip()}')
    return '\n'.join(out)+'\n'


def provider_liriqo(title,artist,album,duration,review):
    for t,a in query_variants(title,artist):
        data=direct_json('LiriQo','https://api.liriqo-alfarrizi.my.id/v1/lyrics',
                         {'title':t,'artist':a,'duration':int(duration)} if duration else {'title':t,'artist':a})
        if not isinstance(data,dict):continue
        result=data.get('data') if isinstance(data.get('data'),dict) else data
        meta=result.get('metadata',{})
        if not isinstance(meta,dict):meta={}
        ot=meta.get('title') or t; oa=meta.get('artist') or a
        ol=meta.get('duration') or None
        tracks=result.get('tracks') or []
        if isinstance(result.get('primary'),dict):tracks=[result['primary']]+list(tracks)
        for track in tracks:
            if not isinstance(track,dict):continue
            timed=track.get('timed')
            if not isinstance(timed,list):continue
            lyr=timed_to_lrc(timed)
            if not lyr:continue
            # The service can resolve a different song than the query; check resolved metadata.
            if not meta or not meta.get('title') or not meta.get('artist'):
                review.add('LiriQo',ot,oa,'API did not include verifiable resolved metadata',lyrics=lyr)
                continue
            ok,note=acceptable(title,artist,duration,ot,oa,ol,lyr)
            if ok:return Hit(lyr,'LiriQo ('+str(track.get('provider','aggregated'))+')',note,label_for_query(title,artist,t,a),True)
            review.add('LiriQo',ot,oa,note,lyrics=lyr)
    return None


def provider_syncedlyrics(provider,title,artist,album,duration,review):
    for t,a in query_variants(title,artist):
        wait_for(provider)
        # This third-party library may swallow HTTP errors internally, so a None
        # result is a completed search from our viewpoint, not a proven database miss.
        query=f'{t} {a}'
        try:
            lyr=bounded_blocking_search(provider,lambda: syncedlyrics.search(query,providers=[provider],plain_only=False),13)
        except ProviderFailure:
            raise
        except Exception as ex:
            raise ProviderFailure(f'{type(ex).__name__}: {str(ex)[:120]}',timeout=('timed out' in str(ex).lower() or 'timeout' in type(ex).__name__.lower())) from ex
        if isinstance(lyr,str) and plausible_lrc(lyr,duration):
            # Provider does not return resolved recording ID or duration; weaker check.
            review.add(provider,t,a,'Unverified search-only response; candidate only',lyrics=lyr)
            continue
    return None


def bounded_blocking_search(provider, callback, seconds=13):
    """Daemon worker: avoid the whole folder freezing on a blocked scraper.

    If a provider times out, disable it to avoid accumulating worker threads.
    """
    result={}
    def run():
        try:result['value']=callback()
        except BaseException as ex:result['error']=ex
    worker=threading.Thread(target=run,daemon=True)
    worker.start();worker.join(seconds)
    if worker.is_alive():
        blocked[provider]=f'client-side {seconds}s timeout; skip for rest of run'
        raise ProviderFailure(f'client-side timeout after {seconds}s',timeout=True)
    if 'error' in result:
        raise result['error']
    return result.get('value')


def provider_tencent(title,artist,album,duration,review):
    if not OPTIONAL_TENCENT_AVAILABLE:
        raise ProviderFailure('Optional syncedlyrics_aio not installed (see README)')
    for t,a in query_variants(title,artist):
        wait_for('Tencent')
        query=f'{t} {a}'
        try:
            async def one():
                return await asyncio.wait_for(
                    syncedlyrics_aio.search(query,providers=['Tencent'],plain_only=False),
                    timeout=12)
            lyrics=bounded_blocking_search('Tencent',lambda: asyncio.run(one()),14)
        except (TimeoutError,asyncio.TimeoutError) as ex:
            raise ProviderFailure('Tencent request timed out',timeout=True) from ex
        except ProviderFailure:
            raise
        except Exception as ex:
            raise ProviderFailure(f'Tencent {type(ex).__name__}: {str(ex)[:120]}',
                timeout='timeout' in type(ex).__name__.lower()) from ex
        if isinstance(lyrics,str) and plausible_lrc(lyrics,duration):
            review.add('Tencent',t,a,'Unverified identity; candidate only',lyrics=lyrics)
            continue
    return None

def search_song(title,artist,album,duration,review,*,only_providers=None,retry_targets=None,timings=None,request_traces=None):
    """Return (hit, status, detail, calls).

    Completed NO_MATCH providers are NEVER queried again in later rounds.
    Only the exact provider(s) that had a genuine network timeout may be
    retried for the SAME song. HTTP 429 is deferred when
    its provider has been disabled for the rest of the run. HTTP 5xx,
    invalid responses and other errors NEVER trigger another round.
    """
    global ACTIVE_HTTP_TRACE
    calls=[];completed=0;failures=0;real_timeouts=0
    if timings is None:timings=[]
    if request_traces is None:request_traces=[]
    if retry_targets is None:retry_targets=set()
    if MB_ENABLED and title and artist:
        musicbrainz_variant(title,artist,duration)
    functions={'LRCLIB':provider_lrclib,'SyncLRC':provider_synclrc,'Unison':provider_unison,
               'BetterKuGou':lambda t,a,al,d,r:provider_better('BetterKuGou',t,a,al,d,r),
               'BetterTTML':lambda t,a,al,d,r:provider_better('BetterTTML',t,a,al,d,r),
               'YouLyTTML':provider_youly,'LrcAPI':provider_lrcapi,
               'LiriQo':provider_liriqo, 'Tencent':provider_tencent}
    sources=tuple(only_providers) if only_providers is not None else (ACTIVE_PROVIDERS if ACTIVE_PROVIDERS is not None else PROVIDERS)
    global LRCLIB_503_STREAK, LRCLIB_503_RETRY_AT
    for source in sources:
        history_key=search_history_key(source,title,artist,album,duration) if HISTORY_ENABLED else None
        if history_key and history_key in HISTORY_CACHE:
            completed+=1
            calls.append(f'{source}=CACHED_NO_MATCH')
            timings.append((source,0.0))
            request_traces.append([])
            print_provider_state(source,'CACHED_NO_MATCH',reason='7-day history; request not sent')
            continue
        if source=='Tencent' and not OPTIONAL_TENCENT_AVAILABLE:
            calls.append('Tencent=UNAVAILABLE (optional dependency not installed)')
            timings.append((source,0.0))
            request_traces.append([])
            print_provider_state(source,'UNAVAILABLE',reason='optional dependency not installed; request not sent')
            continue
        if source=='LRCLIB' and source in blocked and LOCAL_LRCLIB is not None:
            # A remote 503/429/access restriction does not prevent genuine
            # read-only offline lookups. Never make a network request here.
            started=time.monotonic();trace=[];request_traces.append(trace)
            ACTIVE_HTTP_TRACE=trace
            before=review.count.get('LRCLIB local',0)
            hit=local_lrclib_search(title,artist,duration,review)
            ACTIVE_HTTP_TRACE=None
            elapsed=time.monotonic()-started;timings.append((source,elapsed))
            if hit:
                calls.append('LRCLIB=SAVED')
                print_provider_state(source,'LRC_FOUND_OFFLINE',elapsed,trace,'online blocked; local SQLite verified')
                return hit,'SAVED','LRCLIB local SQLite verified match',calls
            calls.append(f'LRCLIB=SKIPPED (online blocked: {blocked[source]}; offline checked)')
            failures+=1
            print_provider_state(source,'ONLINE_BLOCKED_OFFLINE_CHECKED',elapsed,trace,blocked[source])
            continue
        if source in blocked:
            calls.append(f'{source}=SKIPPED ({blocked[source]})')
            failures+=1
            timings.append((source,0.0))
            request_traces.append([])
            print_provider_state(source,'SKIPPED',reason=blocked[source]+'; request not sent')
            continue
        # Even after repeated HTTP 503s, LRCLIB is re-probed when its temporary
        # server-recovery cooldown expires. Never convert a 503 into a
        # permanent per-run block, and never bypass a genuine HTTP 429.
        if source == 'LRCLIB' and time.monotonic() < LRCLIB_503_RETRY_AT:
            if COMPLETE_FIRST_PASS and source not in blocked:
                wait_for_recovery(source, LRCLIB_503_RETRY_AT, 'HTTP 503 recovery')
            else:
                remaining=max(1,int(LRCLIB_503_RETRY_AT-time.monotonic()))
                calls.append(f'LRCLIB=SKIPPED (temporary HTTP 503 recovery; {remaining}s remaining)')
                failures+=1
                timings.append((source,0.0))
                request_traces.append([])
                print_provider_state(source,'SKIPPED',reason=f'HTTP 503 recovery, next attempt after ~{remaining}s; request not sent')
                continue
        if source in PROVIDER_RECOVERY_AT and time.monotonic() < PROVIDER_RECOVERY_AT[source]:
            if COMPLETE_FIRST_PASS and source not in blocked:
                wait_for_recovery(source, PROVIDER_RECOVERY_AT[source], 'temporary provider recovery')
            else:
                remaining=max(1,int(PROVIDER_RECOVERY_AT[source]-time.monotonic()))
                calls.append(f'{source}=SKIPPED (temporary provider recovery; {remaining}s remaining)')
                failures+=1
                timings.append((source,0.0))
                request_traces.append([])
                print_provider_state(source,'SKIPPED',reason=f'temporary recovery ~{remaining}s; request not sent')
                continue
        print(f'    {source}...',flush=True)
        started=time.monotonic()
        trace=[]
        request_traces.append(trace)
        ACTIVE_HTTP_TRACE=trace
        review_before=review.count.get(source,0)
        try:
            if source in functions:
                hit=functions[source](title,artist,album,duration,review)
            else:
                hit=provider_syncedlyrics(source,title,artist,album,duration,review)
            completed+=1
            had_review=review.count.get(source,0)>review_before
            calls.append(f'{source}='+('SAVED' if hit else 'REVIEW_AVAILABLE' if had_review else 'NO_MATCH'))
            print_provider_state(source,('LRC_FOUND' if hit and hit.verified else 'REVIEW_AVAILABLE' if (had_review or hit) else 'NO_MATCH'),time.monotonic()-started,trace)
            errors[source]=0
            PROVIDER_ERROR_STREAK[source]=0
            PROVIDER_RECOVERY_AT.pop(source,None)
            if source=='LRCLIB':
                LRCLIB_503_STREAK=0
                LRCLIB_503_RETRY_AT=0.0
            if hit and not hit.verified:
                review.add(source,title,artist,'Candidate identity unverified; automatic saving forbidden',lyrics=hit.lyrics)
                calls[-1]=f'{source}=REVIEW_AVAILABLE'
                if history_key:store_search_event(history_key,'REVIEW_AVAILABLE')
                continue
            if hit:
                # A search-only service has no resolved artist/title/duration. An
                # AI-only spelling must NOT silently authorize an uncertain LRC.
                if 'AI_' in hit.search_variation and any(token in hit.note.lower() for token in
                    ('unverified', 'does not return recording metadata', 'query match')):
                    review.add(source,title,artist,
                        'AI-derived query returned lyrics without resolved song identity; manual review required')
                    calls[-1]=f'{source}=REVIEW_AVAILABLE'
                    if history_key:store_search_event(history_key,'REVIEW_AVAILABLE')
                    continue
                if history_key:store_search_event(history_key,'VERIFIED_MATCH')
                timings.append((source,time.monotonic()-started))
                ACTIVE_HTTP_TRACE=None
                return hit,'SAVED',f'{source}: {hit.note}',calls
            if history_key:
                store_search_event(history_key,'REVIEW_AVAILABLE' if had_review else 'NO_MATCH')
        except ProviderFailure as ex:
            failures+=1;errors[source]+=1
            calls.append(f'{source}=ERROR ({ex})')
            if ex.timeout and not ex.rate_limit:real_timeouts+=1
            if ex.rate_limit:
                record_rate_limit(source,ex.retry_after)
                blocked[source]='429 for this run; cooldown recorded'+(f' (Retry-After {ex.retry_after})' if ex.retry_after else '')
                print_provider_state(source,'HTTP_429_DISABLED',time.monotonic()-started,trace,str(ex)+'; cooldown persisted')
            else:
                if source=='LRCLIB' and str(ex).startswith('HTTP 503:'):
                    LRCLIB_503_STREAK+=1
                    # Honor a server-specified Retry-After (+5s safety floor);
                    # otherwise exponential 60s/120s/... capped at 10m.
                    recovery=lrclib_503_delay(ex.retry_after, LRCLIB_503_STREAK)
                    LRCLIB_503_RETRY_AT=time.monotonic()+recovery
                    if LRCLIB_503_STREAK >= LRCLIB_503_CIRCUIT_LIMIT:
                        blocked[source]=(f'HTTP 503 circuit open after {LRCLIB_503_STREAK} consecutive '
                                         'overload responses; unanswered songs remain queued for a later run')
                        print('      LRCLIB: CIRCUIT OPEN — stopping online requests for this run; '
                              'do not hammer an overloaded server.',flush=True)
                    print_provider_state(source,'TEMPORARY_HTTP_503',time.monotonic()-started,trace,
                        f'{ex}; LRCLIB remains enabled, next probe after ~{int(recovery)}s')
                else:
                    if is_access_denied(ex):
                        # Authentication/access failures cannot be repaired by
                        # resending the same unauthenticated request to all songs.
                        blocked[source]=str(ex).split(':',1)[0]+': access denied; no further requests this run'
                    else:
                        # Temporary failures must NEVER permanently disable
                        # the provider across the rest of a large collection.
                        PROVIDER_ERROR_STREAK[source]+=1
                        if PROVIDER_ERROR_STREAK[source]>=2 or str(ex).startswith('HTTP 503:'):
                            delay=transient_recovery_delay(source,PROVIDER_ERROR_STREAK[source],ex.retry_after)
                            PROVIDER_RECOVERY_AT[source]=time.monotonic()+delay
                    reason=str(ex)
                    if source in blocked:reason+='; DISABLED for remainder of run: '+blocked[source]
                    elif source in PROVIDER_RECOVERY_AT:
                        reason+='; TEMPORARY recovery, not a permanent provider ban'
                    print_provider_state(source,'TIMEOUT' if ex.timeout else 'ERROR',
                                         time.monotonic()-started,trace,reason)
            # A 429 is a provider-wide cooldown, NEVER retry it in this run.
            # Ordinary socket timeouts can retry this provider for this song only.
            if ex.timeout and not ex.rate_limit and source not in blocked:
                retry_targets.add(source)
        except Exception as ex:
            failures+=1;errors[source]+=1
            calls.append(f'{source}=ERROR ({type(ex).__name__}: {str(ex)[:120]})')
            PROVIDER_ERROR_STREAK[source]+=1
            if PROVIDER_ERROR_STREAK[source]>=2:
                delay=transient_recovery_delay(source,PROVIDER_ERROR_STREAK[source])
                PROVIDER_RECOVERY_AT[source]=time.monotonic()+delay
            reason=f'{type(ex).__name__}: {str(ex)[:120]}'
            if source in blocked:reason+='; DISABLED for remainder of run: '+blocked[source]
            print_provider_state(source,'UNEXPECTED_ERROR',time.monotonic()-started,trace,reason)
        timings.append((source,time.monotonic()-started))
        ACTIVE_HTTP_TRACE=None
    if retry_targets:
        # Retry ONLY timed-out sources on THIS song; never successful NO_MATCH
        # providers and never the other tracks in the folder.
        return None,'TIMEOUT',(
            f'{completed} provider(s) completed NO_MATCH; '
            f'retry ONLY timed-out: {", ".join(sorted(retry_targets))}'),calls
    review_count=sum(review.count.values())
    if review_count:
        return None,('REVIEW_PARTIAL' if failures else 'REVIEW_AVAILABLE'),(
            f'{review_count} candidate(s) require review; {completed} provider(s) completed; '
            f'{failures} unavailable/skipped'),calls
    if completed:
        # A disabled provider is not a fresh timeout on every later song.
        suffix=f'{completed} provider(s) finished NO_MATCH; {failures} unavailable/skipped'
        return None,'NOT_FOUND_PARTIAL' if failures else 'NOT_FOUND',suffix,calls
    if real_timeouts or any(c.startswith(x+'=ERROR (429') for x in (ACTIVE_PROVIDERS if ACTIVE_PROVIDERS is not None else PROVIDERS) for c in calls):
        return None,'DEFERRED_RATE_LIMIT','All checked providers were rate-limited or timed out; no automatic retry without an actual pending timeout',calls
    return None,'SERVER_ERROR',f'No provider completed; {failures} non-timeout failures/skips; no automatic retry',calls


def select_folder():
    if len(sys.argv)>1:return Path(sys.argv[1].strip('"'))
    try:
        import tkinter as tk
        from tkinter import filedialog
        root=tk.Tk();root.withdraw()
        result=filedialog.askdirectory(title='Select MP3 folder')
        root.destroy()
        if result:return Path(result)
    except Exception:pass
    entry=input('Paste full MP3 folder path (Enter to cancel): ').strip().strip('"')
    return Path(entry) if entry else None


def save_hit(track,hit):
    target=track.with_suffix('.lrc')
    clean=sanitize_lrc(hit.lyrics)
    if not plausible_lrc(clean,0):raise ValueError('Malformed LRC after sanitization')
    with target.open('x',encoding='utf-8',newline='\n') as output:
        output.write(clean)


def write_summary(folder,selected,states):
    lists=[('LRC_Not_Found.txt',{'NOT_FOUND','NOT_FOUND_PARTIAL'},
            'NO SYNCED LYRICS OR CANDIDATES FROM COMPLETED SEARCHES (some providers may be unavailable)'),
           ('LRC_Review_Needed.txt',{'REVIEW_AVAILABLE','REVIEW_PARTIAL'},
            'TIMED LYRICS CANDIDATES FOUND - REVIEW REQUIRED, NOTHING AUTO-INSTALLED'),
           ('LRC_Timeouts.txt',{'TIMEOUT','DEFERRED_RATE_LIMIT','SERVER_ERROR','INTERRUPTED'},
            'UNFINISHED SEARCHES / REAL TIMEOUTS / 429 / SERVER ERRORS (only actual TIMEOUT is auto-retried)')]
    for filename,statuses,head in lists:
        f=folder/filename
        rows=[(p,states[p][1]) for p in selected if states[p][0] in statuses and not p.with_suffix('.lrc').exists()]
        with f.open('w',encoding='utf-8-sig') as out:
            out.write(head+'\n')
            out.write('Selected folder: '+str(folder)+'\nCount: '+str(len(rows))+'\n\n')
            for p,msg in rows:out.write(f'{p} | {msg}\n')
    return (sum(states[p][0] in {'NOT_FOUND','NOT_FOUND_PARTIAL'} and not p.with_suffix('.lrc').exists() for p in selected),
            sum(states[p][0] in {'TIMEOUT','DEFERRED_RATE_LIMIT','SERVER_ERROR','INTERRUPTED'} and not p.with_suffix('.lrc').exists() for p in selected))



def lrclib_catchup_queue_path(folder):
    return Path(folder) / f'LRC_LRCLIB_Catchup_Queue_v{VERSION.replace(".", "_")}.csv'


def write_lrclib_catchup_queue(folder, missing, provider_outcomes):
    """Persist *unsearched* LRCLIB coverage for an explicit later first attempt.

    Automatic rounds NEVER retry skipped/503/429 outcomes. This file is an
    invitation for a separate user-initiated LRCLIB-only run, not a retry queue.
    """
    queue={}
    completed=set()
    for path, outcomes in provider_outcomes:
        for item in outcomes:
            if item.startswith(('LRCLIB=NO_MATCH', 'LRCLIB=REVIEW_AVAILABLE',
                                'LRCLIB=SAVED', 'LRCLIB=CACHED_NO_MATCH')):
                completed.add(path)
            elif item.startswith(('LRCLIB=SKIPPED', 'LRCLIB=UNAVAILABLE',
                                  'LRCLIB=ERROR (HTTP 503',
                                  'LRCLIB=ERROR (HTTP 429')):
                queue.setdefault(path, item.split('=',1)[1])
    output=lrclib_catchup_queue_path(folder)
    # Preserve earlier missed coverage if a later run searches only a subset.
    # Completed LRCLIB outcomes and approved sidecars remove stale entries.
    for row in merge_previous_lrclib_queue(folder,output):
        path=Path(row.get('MP3 path',''))
        if path.is_file():
            queue.setdefault(path,row.get('why LRCLIB was incomplete','from previous run'))
    pending=sorted(((path,reason) for path,reason in queue.items()
                    if path not in completed and path.is_file() and not path.with_suffix('.lrc').exists()),
                   key=lambda pair:str(pair[0]).casefold())
    with output.open('w',encoding='utf-8-sig',newline='') as out:
        writer=csv.writer(out)
        writer.writerow(['MP3 path','why LRCLIB was incomplete'])
        writer.writerows((str(path),reason) for path,reason in pending)
    return output,len(pending)


def run_lrclib_catchup(folder):
    """Explicit user-selected action: ONLY LRCLIB, never other providers.

    This is distinct from rounds 2/3; no other provider is searched again.
    Respects 429 and 503, doesn't erase existing LRCs, candidates or queue on
    interruption, and writes an independent report (normal run files untouched).
    """
    global GREEK_MODE, MB_ENABLED, ACTIVE_PROVIDERS, HISTORY_ENABLED
    global LRCLIB_EXACT_FALLBACK, COMPLETE_FIRST_PASS
    COMPLETE_FIRST_PASS=True  # in option 3, wait before each still-pending first attempt
    folder=Path(folder)
    queued=lrclib_catchup_queue_path(folder)
    if not queued.is_file():
        previous=next((p for p in legacy_lrclib_queue_paths(folder) if p.is_file()),None)
        if previous is not None:
            shutil.copy2(previous,queued)
            print('Imported earlier LRCLIB catch-up queue into v2.1.15 (original preserved).')
        else:
            print('No LRCLIB catch-up queue yet. Run SEARCH first to create it.')
            return
    configure_local_lrclib(Path(__file__).resolve().parent)
    global LRCLIB_ONLINE_FALLBACK
    if LOCAL_LRCLIB is not None:
        LRCLIB_ONLINE_FALLBACK=(input('After OFFLINE misses, contact the online LRCLIB API? [y/N]: ').strip().lower()=='y')
        print('LRCLIB catch-up mode:', 'LOCAL + ONLINE' if LRCLIB_ONLINE_FALLBACK else 'OFFLINE ONLY (no HTTP)',flush=True)
    else:
        LRCLIB_ONLINE_FALLBACK=True
    if LRCLIB_ONLINE_FALLBACK and not configure_lrclib_contact(Path(__file__).resolve().parent):return
    if LRCLIB_ONLINE_FALLBACK:
        load_provider_cooldowns(folder/'LRC_Provider_Cooldowns.json')
    if LRCLIB_ONLINE_FALLBACK and 'LRCLIB' in blocked:
        print('LRCLIB is currently unavailable:',blocked['LRCLIB'])
        print('The queue is unchanged. Try again after the official cooldown.')
        return
    GREEK_MODE=input('Greeklish / Greek filenames for catch-up? [y/N]: ').strip().lower()=='y'
    MB_ENABLED=False
    HISTORY_ENABLED=False  # These are missing first-attempt coverage, not cached NO_MATCH.
    LRCLIB_EXACT_FALLBACK=input('Also try optional LRCLIB exact lookup? [y/N]: ').strip().lower()=='y'
    ACTIVE_PROVIDERS=('LRCLIB',)
    try:
        with queued.open(encoding='utf-8-sig',newline='') as f:
            entries=list(csv.DictReader(f))
    except (OSError,csv.Error) as ex:
        print('Cannot read catch-up queue:',ex);return
    if not entries:
        print('Catch-up list is empty.');return
    print(f'LRCLIB ONLY: {len(entries)} queued songs; no other lyrics sources will be contacted.')
    print('Existing .lrc files are always skipped; version matching is unchanged.')
    if input('Start LRCLIB-only catch-up now? [y/N]: ').strip().lower()!='y':
        print('Canceled; catch-up queue unchanged.');return
    results=[];remaining=[];saved=0;reviewed=0
    previous=[];seen=set()
    for entry in entries:
        path_string=entry.get('MP3 path','')
        if not path_string or path_string in seen:continue
        seen.add(path_string)
        previous.append((Path(path_string),entry.get('why LRCLIB was incomplete','')))
    interrupted=False
    for i,(path,old_reason) in enumerate(previous,1):
        print(f'[{i}/{len(previous)}] {path.name}',flush=True)
        if not path.is_file():
            results.append([str(path),'FILE_MISSING',old_reason,''])
            remaining.append((path,old_reason))
            continue
        if path.with_suffix('.lrc').exists():
            results.append([str(path),'ALREADY_HAS_LRC','skipped',''])
            continue
        if is_live_track(path.stem):
            results.append([str(path),'LIVE_SKIPPED','no search',''])
            continue
        try:
            title,artist,album,duration=song_info(path)
            if is_live_track(title):
                results.append([str(path),'LIVE_SKIPPED','no search',''])
                continue
            if not title or not artist:
                results.append([str(path),'NO_METADATA','missing artist/title',''])
                remaining.append((path,'Missing metadata'))
                continue
            review=CandidateReview(); timing=[]; traces=[]
            hit,status,detail,calls=search_song(title,artist,album,duration,review,
                only_providers=('LRCLIB',),timings=timing,request_traces=traces)
            if hit:
                try:
                    save_hit(path,hit);saved+=1;status='SAVED'
                except FileExistsError:status='ALREADY_HAS_LRC'
            exported=export_review_candidates(path,'CATCHUP',review)
            if exported:reviewed+=1
            if LOCAL_LRCLIB is not None and not LRCLIB_ONLINE_FALLBACK and status not in {'SAVED','ALREADY_HAS_LRC'}:
                remaining.append((path,'Offline snapshot checked; online LRCLIB not yet searched'))
                if status in {'NOT_FOUND','REVIEW_AVAILABLE'}:
                    detail+='; offline only: retained for possible future online catch-up'
            elif status not in {'SAVED','ALREADY_HAS_LRC','NOT_FOUND','REVIEW_AVAILABLE'}:
                remaining.append((path,detail))
            results.append([str(path),status,detail,http_summary('LRCLIB',traces[0] if traces else [])])
            if 'LRCLIB' in blocked:
                print('LRCLIB online unavailable (access restriction or 503 circuit); '
                      'preserving the remaining catch-up queue.',flush=True)
                remaining.extend(previous[i:])
                break
            if time.monotonic()<LRCLIB_503_RETRY_AT:
                print('LRCLIB returned HTTP 503: this song stays queued; the NEXT song will wait for recovery before its first attempt.',flush=True)
        except KeyboardInterrupt:
            print('Interrupted; saving remaining paths.',flush=True)
            remaining.append((path,old_reason))
            remaining.extend(previous[i:])
            interrupted=True
            break
        except Exception as ex:
            results.append([str(path),'ERROR',f'{type(ex).__name__}: {ex}',''])
            remaining.append((path,old_reason))
    report=folder/f'LRC_LRCLIB_Catchup_Report_v{VERSION.replace(".", "_")}.csv'
    with report.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['MP3 path','outcome','reason','HTTP status summary'])
        writer.writerows(results)
    with queued.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['MP3 path','why LRCLIB was incomplete'])
        writer.writerows((str(p),r) for p,r in remaining)
    print('Catch-up complete:',len(results),'processed,',saved,'saved,',reviewed,'with review candidates,',len(remaining),'still pending')
    print('Report:',report)
    print('Remaining catch-up queue:',queued)



def ensure_local_lrclib_config(script_dir, *, input_fn=None):
    """Verify configured huge SQLite DB; optionally point to an existing installation.

    Only writes LRCLIB_LOCAL_DB.txt in the application folder. Never downloads,
    copies, extracts, alters or deletes the database itself.
    """
    global LOCAL_LRCLIB
    config=Path(script_dir)/'LRCLIB_LOCAL_DB.txt'
    configure_local_lrclib(script_dir)
    if LOCAL_LRCLIB is not None:
        return True
    print('OFFLINE MODE requires an existing extracted LRCLIB .sqlite3 database.',flush=True)
    print('If upgrading from an older program folder, copy LRCLIB_LOCAL_DB.txt into this folder,',flush=True)
    print('OR enter the existing SQLite file path once (no download or copying needed).',flush=True)
    print('Example: D:\\DataBase\\lrclib-db-dump-20261012T090639Z.sqlite3',flush=True)
    if input_fn is None: input_fn=input
    entry=input_fn('Path to existing .sqlite3 file (Enter to cancel): ').strip().strip('"')
    if not entry:
        print('No offline database selected; no scan started.',flush=True)
        return False
    try:
        path=Path(entry).expanduser().resolve()
        obj=LocalLRCLIB(path)
        config.write_text(str(path)+'\n',encoding='utf-8')
        LOCAL_LRCLIB=obj
        print('Saved location to:',config,flush=True)
        print('LOCAL LRCLIB: READY —',path,flush=True)
        return True
    except (OSError,ValueError,RuntimeError) as ex:
        print('Invalid offline database:',ex,flush=True)
        print('Your configuration was not changed.',flush=True)
        return False


def run_offline_lrclib_folder(folder):
    """Scan any folder using only an existing read-only SQLite dump; NO network calls.

    Uses the normal safe matcher/candidate exporter, and writes independent
    versioned offline reports so normal SEARCH reports/queues are untouched.
    """
    global GREEK_MODE, MB_ENABLED, G2G_ENABLED, G2G_TOOL, HISTORY_ENABLED, ACTIVE_PROVIDERS, ACTIVE_HTTP_TRACE
    GREEK_MODE=input('Greeklish / Greek folder? [y/N]: ').strip().lower()=='y'
    G2G_ENABLED=GREEK_MODE and input('Use installed LOCAL G2G AI for Greek names? [y/N]: ').strip().lower()=='y'
    G2G_TOOL=G2GManager() if G2G_ENABLED else None
    MB_ENABLED=False       # IMPORTANT: NO remote metadata calls
    HISTORY_ENABLED=False  # always check each eligible song against local SQLite
    ACTIVE_PROVIDERS=('LRCLIB',)
    recursive=input('Include subfolders? [Y/n]: ').strip().lower()!='n'
    # Case-insensitive MP3 extensions without touching non-MP3 files.
    files=folder.rglob('*') if recursive else folder.iterdir()
    mp3s=sorted((p for p in files if p.is_file() and p.suffix.lower()=='.mp3'),key=lambda p:str(p).casefold())
    eligible=[];existing=0;live=0
    for track in mp3s:
        if is_live_track(track.stem):live+=1;continue
        if track.with_suffix('.lrc').exists():existing+=1;continue
        eligible.append(track)
    print(f'Found {len(mp3s)} MP3s; {existing} already had .lrc; {live} filename-LIVE skipped; {len(eligible)} potentially eligible.',flush=True)
    if not eligible:return
    howmany=input('How many eligible songs? [20 for test, A for all]: ').strip().lower()
    if howmany!='a':
        try:n=int(howmany) if howmany else 20
        except ValueError:n=20
        if n<=0:print('No songs selected.');return
        eligible=eligible[:n]
    print(f'OFFLINE LRCLIB ONLY: {len(eligible)} songs. No HTTP, no MusicBrainz requests, no other providers.',flush=True)
    print('Database:',LOCAL_LRCLIB.path,flush=True)
    print('Only verified matches create .lrc; uncertain results become .candidate.lrc.',flush=True)
    if input('Start offline-only scan? [y/N]: ').strip().lower()!='y':
        print('Canceled; nothing scanned.',flush=True);return
    report=folder/'LRC_Offline_Only_Report_v2_1_15.csv'
    review_path=folder/'LRC_Offline_Only_Review_v2_1_15.csv'
    counts=Counter();started=time.monotonic()
    processed=0;interrupted=False
    try:
        with report.open('w',encoding='utf-8-sig',newline='') as outf, review_path.open('w',encoding='utf-8-sig',newline='') as reviewf:
            writer=csv.writer(outf)
            writer.writerow(['MP3 path','outcome','reason','seconds','review candidates'])
            rw=csv.writer(reviewf)
            rw.writerow(['MP3 path','mode','provider','candidate title','candidate artist','rejected because','candidate .lrc path'])
            for i,track in enumerate(eligible,1):
                print(f'[{i}/{len(eligible)}] {track.name}',flush=True)
                start=time.monotonic(); review=CandidateReview();outcome='NOT_FOUND';detail='';hit=None
                try:
                    if track.with_suffix('.lrc').exists():
                        outcome='EXISTS';detail='Already has .lrc (skipped)'
                    elif is_live_track(track.stem):
                        outcome='LIVE_SKIPPED';detail='Filename LIVE'
                    else:
                        title,artist,album,duration=song_info(track)
                        if is_live_track(title):
                            outcome='LIVE_SKIPPED';detail='ID3 title LIVE'
                        elif not title or not artist:
                            outcome='NO_METADATA';detail='Missing usable title/artist'
                        else:
                            if GREEK_MODE:
                                precompute_greek_plan(title,artist,G2G_TOOL)
                            # Never use provider_lrclib/search_song here: they may call HTTP.
                            traces=[]
                            ACTIVE_HTTP_TRACE=traces
                            try:
                                hit=local_lrclib_search(title,artist,duration,review)
                            finally:
                                ACTIVE_HTTP_TRACE=None
                            local_error=next((e['detail'] for e in traces if e['status']=='LOCAL_DB_ERROR'),None)
                            if local_error:
                                outcome='ERROR';detail='Offline database lookup failure: '+str(local_error)
                            elif hit:
                                try:save_hit(track,hit);outcome='SAVED';detail='Verified offline SQLite match'
                                except FileExistsError:outcome='EXISTS';detail='Already created .lrc during scan'
                            elif review.items:
                                outcome='REVIEW';detail=f'{len(review.items)} unverified candidate(s)'
                            else:
                                outcome='NO_MATCH';detail='No verified synchronized lyrics in offline snapshot'
                            # distinguish SQLite errors from actual NOT FOUND
                            # when local_lrclib_search records a failed database operation
                            # (errors also print visibly in local_lrclib_search)
                    rows=export_review_candidates(track,'OFFLINE',review)
                    rw.writerows(rows)
                except KeyboardInterrupt:
                    interrupted=True
                    print('Interrupted; reports retained for completed songs.',flush=True)
                    break
                except Exception as ex:
                    outcome='ERROR';detail=f'{type(ex).__name__}: {ex}'
                elapsed=round(time.monotonic()-start,3)
                writer.writerow([str(track),outcome,detail,elapsed,len(review.items)])
                outf.flush();reviewf.flush()
                counts[outcome]+=1;processed+=1
                print('  '+outcome+': '+detail+f' | {elapsed:.1f}s',flush=True)
    finally:
        if G2G_TOOL:
            G2G_TOOL.flush();G2G_TOOL.release_model()
        print('OFFLINE SCAN SUMMARY (no internet access):',flush=True)
        print('  Processed:',processed,'of',len(eligible),flush=True)
        for key in ('SAVED','REVIEW','NO_MATCH','NO_METADATA','LIVE_SKIPPED','EXISTS','ERROR'):
            if counts[key]:print(' ',key,':',counts[key],flush=True)
        print(f'  Elapsed: {time.monotonic()-started:.1f}s',flush=True)
        print('  Report:',report,flush=True)
        print('  Review:',review_path,flush=True)
        if interrupted:print('  Rerun option 4 to continue; songs already having .lrc are skipped.',flush=True)

def main():
    global ROUND
    print(f'\n=== LRC Bulk Finder v{VERSION} | 12 lyrics routes (some aggregate others) ===')
    print('Created by Dimitris L.')
    print('Writes verified .lrc files, nearby .candidate.lrc review files and reports; audio never changed.')
    print('Safety: resolved artist/title, matching version, and duration gap <= 3s required for auto-save.')
    if not OPTIONAL_TENCENT_AVAILABLE:print('Tencent/QQ Music is optional and not installed; it will be skipped.')
    print('Round 2/3: ONLY verified network timeouts for the affected song AND provider.')
    print('NOT_FOUND, SKIPPED, NO_CHECK, HTTP 429, and HTTP 5xx NEVER create a retry.')
    print('429 and unauthorized 401/403 disable the provider for this run; skipped source != new timeout.')
    print('Repeated LRCLIB 503 (3 in a row) opens a safety circuit: remaining songs are queued.')
    print('Optional local LRCLIB SQLite snapshot is searched before online LRCLIB requests.')
    print('First-attempt coverage can WAIT for temporary 503/network recovery on later songs.')
    print('A server returning 503 or 401 is not a successful lyrics search; gaps are reported.')
    print('Original artist/title tags remain untouched; AI provides extra search variants only.')
    print('LIVE tracks are completely excluded (filename or title tag).')
    print('Greek alternatives prioritize user-defined aliases; optional LOCAL G2G AI can suggest more.')
    print('All original ID3 artist/title searches are still performed.')
    print('AI conversion is precomputed and cached BEFORE any lyrics requests.')
    print('Optional 7-day history skips ONLY true NO_MATCH queries; review candidates remain searchable.')
    print('OVERNIGHT: all questions are asked BEFORE conversion/search; none during the run.')
    print('Preflight CSV lists which songs have a suggested Greek alternative BEFORE any network searches.')
    print('New: Unison, Better Lyrics KuGou/TTML and experimental YouLy+ TTML.\n')
    print('\nChoose what you want to do:')
    print('  1 — SEARCH for synchronized lyrics')
    print('  2 — PROMOTE .candidate.lrc files to .lrc (no network)')
    print('  3 — LRCLIB-only catch-up (only sources skipped or unavailable earlier)')
    print('  4 — OFFLINE LRCLIB ONLY (scan ANY folder; no internet)')
    action=input('Choose [1/2/3/4] (default 1): ').strip()
    if action not in {'','1','2','3','4'}:
        print('Invalid choice; no changes made.')
        return
    if action!='2':
        load_aliases()
        load_greek_words()
    folder=select_folder()
    if not folder:return
    if not folder.is_dir():print('Folder does not exist:',folder);return
    if action=='3':
        run_lrclib_catchup(folder)
        return
    if action=='4':
        if not ensure_local_lrclib_config(Path(__file__).resolve().parent):
            return
        run_offline_lrclib_folder(folder)
        return
    if action=='2':
        recursive=input('Include subfolders? [Y/n]: ').strip().lower()!='n'
        promote_candidates(folder,recursive=recursive)
        return
    configure_local_lrclib(Path(__file__).resolve().parent)
    load_provider_cooldowns(folder/'LRC_Provider_Cooldowns.json')
    configure_lrclib_contact(Path(__file__).resolve().parent)
    global MB_ENABLED,GREEK_MODE,ACTIVE_PROVIDERS,G2G_ENABLED,G2G_TOOL,HISTORY_ENABLED,COMPLETE_FIRST_PASS
    GREEK_MODE=input('Greeklish / Greek folder? [y/N]: ').strip().lower()=='y'
    G2G_ENABLED=GREEK_MODE and input('Use your installed LOCAL G2G AI model? [y/N]: ').strip().lower()=='y'
    G2G_TOOL=G2GManager() if G2G_ENABLED else None
    MB_ENABLED=input('MusicBrainz extra artist/title metadata for this folder? [Y/n] (optional; slower): ').strip().lower() not in {'n','no'}
    mode=input('Search mode: FAST (5 useful providers) or FULL (all 12)? [F/full]: ').strip().lower()
    ACTIVE_PROVIDERS=PROVIDERS if mode in {'full','all','12','a'} else FAST_PROVIDERS
    print('Selected providers:',', '.join(ACTIVE_PROVIDERS))
    show_provider_availability()
    COMPLETE_FIRST_PASS=input('Wait for temporary provider recovery before EACH first attempt? [Y/n] (slower, better coverage): ').strip().lower()!='n'
    print('First-attempt coverage:', 'WAIT for temporary recovery (may take hours if a server stays down)' if COMPLETE_FIRST_PASS else 'SKIP during recovery and record incomplete coverage')
    recursive=input('Include subfolders? [Y/n]: ').strip().lower()!='n'
    HISTORY_ENABLED=input('Skip identical provider searches completed NO_MATCH in the last 7 days? [Y/n]: ').strip().lower()!='n'
    if HISTORY_ENABLED:
        load_search_history(folder/'LRC_Completed_Search_History.jsonl')
    it=folder.rglob('*') if recursive else folder.iterdir()
    all_mp3=sorted((p for p in it if p.is_file() and p.suffix.lower()=='.mp3'),key=lambda p:str(p).casefold())
    # LIVE is excluded BEFORE limiting the test size and BEFORE any provider request.
    # Tag-only LIVE also counts, even if the file is named without the word.
    missing=[]; live_skipped=[]; already_have=0; metadata_cache={}
    for track in all_mp3:
        if is_live_track(track.stem):
            live_skipped.append(track)
            continue
        if track.with_suffix('.lrc').exists():
            already_have+=1
            continue
        try:
            info=song_info(track)
            metadata_cache[track]=info
            if is_live_track(info[0]):
                live_skipped.append(track)
                continue
        except Exception:
            # A malformed MP3 will be reported in the normal error path.
            pass
        missing.append(track)
    print(f'Found {len(all_mp3)} MP3; skipped {len(live_skipped)} LIVE songs; '
          f'{already_have} already had LRC; {len(missing)} eligible songs without .lrc.')
    if not missing:return
    howmany=input('How many missing songs? [20 for test, A for all]: ').strip().lower()
    if howmany!='a':
        try: limit=int(howmany) if howmany else 20
        except ValueError:limit=20
        if limit<=0:return
        missing=missing[:limit]
    global LRCLIB_EXACT_FALLBACK
    LRCLIB_EXACT_FALLBACK = input('Optional LRCLIB exact-signature fallback after existing searches? [y/N] (extra HTTP request): ').strip().lower()=='y'
    # All user choices are collected here, BEFORE local AI inference or network calls.
    # This prevents a late prompt from blocking unattended overnight runs.
    run_after_preview = True
    if GREEK_MODE:
        answer=input('After the Greek/AI preview, automatically SEARCH lyrics without any more questions? [Y/n]: ').strip().lower()
        run_after_preview = answer not in {'n','no','p','preview'}
        print('Selected: '+('UNATTENDED PREVIEW + SEARCH' if run_after_preview else 'PREVIEW ONLY')+'; there will be NO more setup questions.',flush=True)
    # PRE-FLIGHT: AI inference is exclusively here. The model is lazy and
    # instantiated once only if an uncached/unaliasable title or artist needs it.
    greek_plan_path=folder/'LRC_Greek_Search_Preview_v2_1_15.csv'
    ai_plan_path=folder/'LRC_G2G_AI_Review_v2_1_15.csv'
    preview=[];ai_preview=[];greek_ready=0
    if GREEK_MODE:
        print('\nPreparing Greek search variants BEFORE contacting lyrics providers...',flush=True)
        try:
            for index,path in enumerate(missing,1):
                try:
                    title,artist,album,duration=metadata_cache.get(path) or song_info(path)
                    detail=precompute_greek_plan(title,artist,G2G_TOOL)
                    variants=query_variants(title,artist)
                    greek_t=detail['Greek title alternative']
                    greek_a=detail['Greek artist alternative']
                    if greek_t:greek_ready+=1
                    preview.append([str(path),title,artist,greek_t,
                                    'ORIGINAL_AND_GREEK' if greek_t else 'ORIGINAL_ONLY'])
                    ai_preview.append([str(path)]+[detail.get(x,'') for x in AI_PREVIEW_FIELDS])
                    if G2G_ENABLED and (index <= 30 or index%50==0):
                        print(f'  [{index}/{len(missing)}] {artist} - {title} => '
                              f'{greek_a or artist} - {greek_t or title}',flush=True)
                except Exception as ex:
                    preview.append([str(path),'','','','METADATA_ERROR: '+str(ex)[:100]])
                    ai_preview.append([str(path)]+['']*len(AI_PREVIEW_FIELDS))
            if G2G_TOOL:
                G2G_TOOL.flush()
                G2G_TOOL.release_model()
        except (KeyboardInterrupt,Exception) as ex:
            if G2G_TOOL:G2G_TOOL.flush()
            if isinstance(ex,KeyboardInterrupt):
                print('AI preview interrupted safely; no lyrics downloaded.');return
            raise
        with greek_plan_path.open('w',encoding='utf-8-sig',newline='') as output:
            writer=csv.writer(output)
            writer.writerow(['MP3 path','ID3 title','ID3 artist','Greek title alternative','search plan'])
            writer.writerows(preview)
        with ai_plan_path.open('w',encoding='utf-8-sig',newline='') as output:
            writer=csv.writer(output)
            writer.writerow(['MP3 path']+AI_PREVIEW_FIELDS)
            writer.writerows(ai_preview)
        print(f'\nGREEK SEARCH CHECK: {greek_ready}/{len(missing)} selected titles have Greek alternatives.')
        print('Full original/AI artist+title comparison:',ai_plan_path)
        print('Compatible original search preview:',greek_plan_path)
        if G2G_TOOL:
            print(f'G2G model inference: {G2G_TOOL.inferences}; cache hits: {G2G_TOOL.hits}; '
                  f'model error: {G2G_TOOL.load_error or "none"}')
        if greek_ready<len(missing):
            print(f'{len(missing)-greek_ready} titles have no Greek alternative; originals remain searchable.')
        if G2G_ENABLED:
            print('IMPORTANT: AI Greek text may contain mistakes and missing accents. Review the CSV later.')
        if len(missing)>=50 and greek_ready/len(missing)<0.25:
            print('WARNING: Under 25% Greek title coverage; see preview CSV after the run.')
        if not run_after_preview:
            print('PREVIEW ONLY selected at startup. No lyrics services contacted.')
            return
        print('Starting lyrics searches automatically as selected BEFORE preview. No further questions.',flush=True)
    # New versioned report name avoids appending to prior releases.
    report=folder/'LRC_Finder_Report_v2_1_15.csv'
    reviews_path=folder/'LRC_Finder_Review_v2_1_15.csv'
    providers_path=folder/'LRC_Finder_Provider_Details_v2_1_15.csv'
    stats_path=folder/'LRC_Source_Statistics_v2_1_15.csv'
    http_details_path=folder/'LRC_HTTP_Diagnostics_v2_1_15.csv' 
    states={};rows=[];reviews=[];provider_rows=[];http_rows=[];saved=0
    lrclib_attempt_log=[]
    pending=list(missing)
    retry_by_song={}  # MP3 -> ONLY the actual timed-out providers
    completed_by_song={}  # help classify later-round failure accurately
    interrupted=False
    try:
        for rnd in (1,2,3):
            ROUND=rnd
            current=[p for p in pending if not p.with_suffix('.lrc').exists()]
            pending=[]
            if not current:break
            print(f'\n===== ROUND {rnd}/3 | {len(current)} songs | wait {rnd}x =====',flush=True)
            for index,path in enumerate(current,1):
                print(f'[{index}/{len(current)}] {path.name}',flush=True)
                review=CandidateReview();status='TIMEOUT';detail='';calls=[];hit=None
                new_retry=set();call_timings=[];call_traces=[]
                target_providers=retry_by_song.pop(path,None) if rnd>1 else None
                if rnd>1:
                    print('    Retry ONLY:',', '.join(sorted(target_providers or [])),flush=True)
                try:
                    title,artist,album,duration=metadata_cache.get(path) or song_info(path)
                    if title and artist and GREEK_MODE:
                        variants=query_variants(title,artist)
                        print('    Search title(s):', ' / '.join(v[0] for v in variants),flush=True)
                        if len(variants)==1: print('    No Greek title alternative; using original title only.',flush=True)
                    if not title or not artist:
                        status='NOT_FOUND';detail='No artist/title tags and no Artist - Title filename'
                    else:
                        hit,status,detail,calls=search_song(
                            title,artist,album,duration,review,
                            only_providers=target_providers,retry_targets=new_retry,timings=call_timings,request_traces=call_traces)
                        if hit:
                            try:save_hit(path,hit);saved+=1
                            except FileExistsError:status='EXISTS';detail='LRC appeared during the run'
                            except (OSError,ValueError) as ex:
                                status='SERVER_ERROR';detail=f'File save failed: {ex}'
                except KeyboardInterrupt:
                    states[path]=('INTERRUPTED','Interrupted while searching')
                    rows.append([str(path),rnd,'INTERRUPTED','Interrupted while searching','', ''])
                    interrupted=True
                    break
                except Exception as ex:
                    status='SERVER_ERROR';detail=f'Unexpected error {type(ex).__name__}: {str(ex)[:120]}'
                previous_completed=completed_by_song.get(path,set())
                now_completed={x.split('=',1)[0] for x in calls if x.endswith('=NO_MATCH')}
                completed_by_song[path]=previous_completed | now_completed
                if rnd>1 and status in {'SERVER_ERROR','DEFERRED_RATE_LIMIT'} and previous_completed:
                    status='NOT_FOUND_PARTIAL'
                    detail+='; earlier sources completed NO_MATCH, retry source unavailable'
                states[path]=(status,detail)
                lrclib_attempt_log.append((path,tuple(calls)))
                if status=='TIMEOUT' and new_retry:
                    retry_by_song[path]=new_retry
                reviews.extend(export_review_candidates(path,rnd,review))
                rows.append([str(path),rnd,status,detail,hit.provider if hit else '', ' | '.join(calls), hit.search_variation if hit else ''])
                for call_index,outcome in enumerate(calls):
                    prov,result=(outcome.split('=',1)+[''])[:2]
                    try:
                        tt,aa,_,_=metadata_cache.get(path) or song_info(path)
                        variants=query_variants(tt,aa)
                        query_titles=' / '.join(f'{a} - {t}' for t,a in variants)
                    except Exception:query_titles=''
                    elapsed=round(call_timings[call_index][1],2) if call_index<len(call_timings) else 0.0
                    events=call_traces[call_index] if call_index<len(call_traces) else []
                    diagnosis=http_summary(prov,events) if '=' in outcome else ''
                    provider_rows.append([str(path),rnd,prov,result,query_titles,elapsed,diagnosis,
                                          sum(1 for event in events if event['status'] not in
                                              {'LOCAL_DB_LOOKUP','LOCAL_DB_ERROR'})])
                    if events:
                        for e in events:
                            http_rows.append([str(path),rnd,prov,e['endpoint'],e['status'],
                                              e['detail'],e['elapsed_seconds']])
                    else:
                        reason=('not requested: '+result if result.startswith(('SKIPPED','UNAVAILABLE','CACHED'))
                                else 'HTTP status hidden by third-party library' if prov in LIBRARY_MANAGED_SOURCES
                                else 'no HTTP call recorded')
                        http_rows.append([str(path),rnd,prov,'', 'NOT_OBSERVED',reason,0])
                print(f'  {status}: {detail}',flush=True)
                if status=='TIMEOUT' and new_retry:pending.append(path)
            if interrupted:break
            print(f'Round {rnd} finished; {len(pending)} songs with specific timed-out provider(s) eligible.',flush=True)
            if pending and all(x in blocked for x in PROVIDERS):
                print('All providers disabled; no reason to repeat immediately.',flush=True)
                break
    finally:
        for path in missing:
            if path.with_suffix('.lrc').exists():states[path]=('SAVED','LRC present')
            elif path not in states:states[path]=('INTERRUPTED','Not attempted because run was interrupted')
        for f,header,output in (
            (report,['MP3 path','round','status','reason','saved provider','provider outcomes','successful search variation'],rows),
            (reviews_path,['MP3 path','round','provider','candidate title','candidate artist','rejected because','nearby candidate .lrc path'],reviews),
            (providers_path,['MP3 path','round','provider','outcome','planned title variants','elapsed_seconds','HTTP status summary','HTTP request count'],provider_rows),
            (http_details_path,['MP3 path','round','provider','endpoint (no query string)','HTTP status / transport outcome','reason','request elapsed seconds'],http_rows)):
            with f.open('w',encoding='utf-8-sig',newline='') as csv_file:
                writer=csv.writer(csv_file);writer.writerow(header);writer.writerows(output)
        coverage_path=folder/f'LRC_First_Attempt_Coverage_v{VERSION.replace(".", "_")}.csv'
        first_round={(Path(path),source):(result,int(request_count),summary)
                     for path,rnd,source,result,_queries,_seconds,summary,request_count in provider_rows
                     if rnd==1}
        source_order=tuple(ACTIVE_PROVIDERS or PROVIDERS)
        coverage_counts=Counter()
        with coverage_path.open('w',encoding='utf-8-sig',newline='') as cov:
            writer=csv.writer(cov)
            writer.writerow(['MP3 path','provider','first-pass coverage','outcome','HTTP requests','HTTP summary'])
            for path in missing:
                source_states={source:first_round.get((path,source)) for source in source_order}
                ended_early=any(item and item[0].startswith('SAVED') for item in source_states.values())
                for source in source_order:
                    item=source_states[source]
                    if item is None:
                        category='NOT_NEEDED_SAVED_EARLY' if ended_early or path.with_suffix('.lrc').exists() else 'NOT_REACHED'
                        result='';requests=0;summary=''
                    else:
                        result,requests,summary=item
                        if 'LOCAL_DB_LOOKUP' in summary and not any(x in summary for x in ('HTTP 2','HTTP 3','HTTP 4','HTTP 5')):
                            category='OFFLINE_SQLITE_LOOKUP'
                        elif requests>0:category='REQUEST_SENT'
                        elif result.startswith('CACHED_NO_MATCH'):category='ALREADY_SEARCHED_HISTORY'
                        elif source in LIBRARY_MANAGED_SOURCES and result.startswith(('NO_MATCH','REVIEW','SAVED')):
                            category='LIBRARY_SEARCH_HTTP_NOT_VISIBLE'
                        elif result.startswith(('SKIPPED','UNAVAILABLE')):category='NOT_CONTACTED_UNAVAILABLE'
                        else:category='NO_HTTP_REQUEST_OBSERVED'
                    coverage_counts[category]+=1
                    writer.writerow([str(path),source,category,result,requests,summary])
        print('FIRST-ATTEMPT COVERAGE:')
        for label,count in sorted(coverage_counts.items()):print('  ',label,':',count)
        print('First-attempt coverage detail:',coverage_path)
        lrclib_queue_path, lrclib_pending = write_lrclib_catchup_queue(folder,missing,lrclib_attempt_log)
        print(f'LRCLIB missed/failed-coverage queue: {lrclib_pending} song(s) — {lrclib_queue_path}')
        n,t=write_summary(folder,missing,states)
        statistics={source:Counter() for source in PROVIDERS}
        for path,rnd,source,result,_queries,elapsed,_status_summary,_request_count in provider_rows:
            if source in statistics:
                bucket=('SAVED' if result.startswith('SAVED') else
                        'REVIEW' if result.startswith('REVIEW') else
                        'CACHED' if result.startswith('CACHED_NO_MATCH') else
                        'NO_MATCH' if result.startswith('NO_MATCH') else
                        'SKIPPED' if result.startswith(('SKIPPED','UNAVAILABLE')) else
                        'ERROR' if result.startswith('ERROR') else 'OTHER')
                statistics[source][bucket]+=1
                statistics[source]['SECONDS']+=elapsed
        with stats_path.open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.writer(f)
            writer.writerow(['provider','saved','review','no_match','cached_no_match','error','skipped','other','total_outcomes','elapsed_seconds','average_seconds_per_outcome'])
            for source in PROVIDERS:
                cnt=statistics[source]
                total=sum(cnt[k] for k in ('SAVED','REVIEW','NO_MATCH','CACHED','ERROR','SKIPPED','OTHER'))
                writer.writerow([source,cnt['SAVED'],cnt['REVIEW'],cnt['NO_MATCH'],cnt['CACHED'],cnt['ERROR'],cnt['SKIPPED'],cnt['OTHER'],total,
                                 round(cnt['SECONDS'],2),round(cnt['SECONDS']/total,2) if total else 0])
        print('\n=============== FINAL SUMMARY ===============')
        print('New LRC saved:',saved)
        if HISTORY_ENABLED:print('Recent NO_MATCH history:',HISTORY_PATH)
        if G2G_TOOL:print('Local G2G cache:',G2G_TOOL.cache_file)
        print('LIVE tracks skipped (not searched):',len(live_skipped))
        print('NOT FOUND (including partial coverage):',n)
        print('UNFINISHED / TIMEOUT / SERVER ERRORS:',t)
        print('REVIEW REQUIRED:',sum(states[p][0] in {'REVIEW_AVAILABLE','REVIEW_PARTIAL'} for p in missing))
        print('NOTE: NOT_FOUND_PARTIAL means at least one lyrics provider was unavailable; not proof the lyrics do not exist.')
        print('Not Found list:',folder/'LRC_Not_Found.txt')
        print('Timeout list:',folder/'LRC_Timeouts.txt')
        print('Review-needed list:',folder/'LRC_Review_Needed.txt')
        print('Correctly structured detailed CSV:',report)
        print('Uncertain possible matches:',reviews_path)
        print('Review candidates: .candidate.lrc beside MP3; extra choices: .candidate.2.lrc, etc.')
        print('Provider-by-provider details:',providers_path)
        print('NEW HTTP status / failure diagnostics:',http_details_path)
        print('NEW source statistics:',stats_path)
        print('Provider coverage (request sent vs unavailable):',coverage_path)
        print('LRCLIB catch-up queue (option 3, never automatic):',lrclib_pending,'song(s)')
        print('Saved by provider:',', '.join(f'{source}: {statistics[source]["SAVED"]}' for source in PROVIDERS if statistics[source]['SAVED']) or 'none')
        try:
            run_id=datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_root=folder/'LRC_Run_Reports'
            archive=archive_root/('Run_'+run_id+'_v'+VERSION.replace('.','_'))
            count=2
            while archive.exists():
                archive=archive_root/('Run_'+run_id+'_v'+VERSION.replace('.','_')+f'_{count}')
                count+=1
            archive.mkdir(parents=True)
            archive_files=[report,reviews_path,providers_path,http_details_path,stats_path,coverage_path,
                           folder/'LRC_Not_Found.txt',folder/'LRC_Timeouts.txt',folder/'LRC_Review_Needed.txt',lrclib_queue_path]
            if GREEK_MODE:archive_files.extend([greek_plan_path,ai_plan_path])
            for file in archive_files:
                if file.exists():shutil.copy2(file,archive/file.name)
            print('Archived reports for this run:',archive)
        except OSError as ex:print('Warning: could not archive reports:',ex)

        print('\n--- NOT FOUND (no accepted synchronized result) ---')
        for path in missing:
            if states[path][0] in {'NOT_FOUND','NOT_FOUND_PARTIAL'} and not path.with_suffix('.lrc').exists():
                print('  '+path.name)
        print('\n--- TIMEOUT / INCOMPLETE ---')
        for path in missing:
            if states[path][0] in {'TIMEOUT','DEFERRED_RATE_LIMIT','SERVER_ERROR','INTERRUPTED'} and not path.with_suffix('.lrc').exists():
                print('  '+path.name+'  ['+states[path][0]+']')
        if blocked:print('Provider(s) disabled this run:',blocked)
        if interrupted:print('Interrupted by Ctrl+C; reports saved.')


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(f'FATAL ERROR: {type(exc).__name__}: {exc}')
    try:input('\nPress Enter to close this window...')
    except (EOFError,KeyboardInterrupt):pass
