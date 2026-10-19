# LRC Bulk Finder project: Created by Dimitris L.
# AUEB G2G model is a separate third-party project.
"""Optional, lazy local AUEB G2G adapter for LRC Bulk Finder.

No network calls or media-file writes. It relies on the user's already
installed/cached gr-nlp-toolkit and saves only a JSON conversion cache.
AI results are SEARCH SUGGESTIONS, not evidence of a matching recording.
"""
from __future__ import annotations
import json
import os
import re
import tempfile
import unicodedata
from pathlib import Path

GREEK = re.compile(r'[\u0370-\u03ff\u1f00-\u1fff]')
LATIN = re.compile(r'[A-Za-z]')
LATIN_RUN = re.compile(r"[A-Za-z][A-Za-z0-9'’\-]*(?:\s+[A-Za-z][A-Za-z0-9'’\-]*)*")
# Strong indicators, not a complete Greeklish detector. Greek-folder mode is
# opt-in; nevertheless avoid obvious English words and international artists.
ENGLISH_WORDS = {'the','and','with','you','your','love','baby','summer','greece',
    'tonight','dance','night','girl','boy','beautiful','forever','world','music',
    'english','please','never','always','one','two','three','only','feel','this',
    'that','from','back','again','happy','birthday','heart','christmas','song',
    'street','club','myself','life','going','through','little','something','more',
    'best','of','time','times','memories','original','greatest','hits',
    'golden','classics','collection','english','all','day','dreams','first',
    'last','way','away','ever','no','yes','every','home','good','bad','new',
    'old','just','friend','friends','is','are','we','us','our','in','on','at',
    'for','not','but','what','who','when','where','how','here','there',
    'music','mix','album','song','songs','work','play','party','dancefloor',
    'sexy'}
GREEKLISH_WORDS = {'mou','sou','mas','sas','ime','eimai','ise','eisai','ime','kai',
    'gia','gi','ena','mia','den','min','oxi','nai','alla','apo','edo','esi','esy',
    'pou','pos','pote','an','tha','to','ti','ta','na','me','se','stin','sto','stis',
    'agapi','agapo','thelo','theleis','agapame','pali','mono','monos','mona',
    'xoris','xorismou','ksana','etsi','eho','echo','exei','maria','moro',
    'fili','kardia','kardia','tragoudi','tragoudo','iparxi','zoi','ponao',
    'pote','fos','asteri','asteria','fygame','fyge','mprosta','brosta',
    'nikos','giorgos','giannis','stelios','vasilis','despina','antonis',
    'kostas','konstantinos','vertis','remos','rokkos','mazonakis','alkaios',
    'petros','pantos','pantos','panos','pantelis','manolis','manos','thanasis',
    'thanos','michalis','mikis','sakis','yannis','yiannis','notis','stratos',
    'stamatis','alexandros','christos','christina','eleni','katerina','kaiti',
    'katerina','katy','stella','stefanos','sophia','sofia','aris','foivos',
    'vaggelis','vanggelis','rouvas','vandi','karras','argiros','argyros',
    'kokotas','mitropanos','paparizou','ploutarhos','ploutarchos','terzis',
    'kontolazos','chalkitis','halkitis','glykerya','glykeria'}
VERSION_WORDS = {'feat','ft','featuring','remix','edit','extended','instrumental',
    'radio','live','intro','outro','ost','soundtrack','remaster','version'}
ARTIST_ENGLISH_MARKERS = {'the','dj','feat','ft','project','band','boys','girls','mc'}
CACHE_SCHEMA = 1
MODEL_ID = 'gr-nlp-toolkit:Pipeline(g2g)'


def normalize(value):
    value = unicodedata.normalize('NFKD',str(value or '')).casefold()
    value = ''.join(c for c in value if not unicodedata.combining(c))
    return ' '.join(''.join(c if c.isalnum() else ' ' for c in value).split())


def greek_share(value):
    greek = len(GREEK.findall(value or ''))
    latin = len(LATIN.findall(value or ''))
    return greek / (greek + latin) if greek + latin else 0.0


def english_skip(text, kind='title'):
    words = re.findall(r'[a-z]+', str(text or '').lower())
    if not words:
        return False
    # An explicit title in Greek remains unchanged; mixed titles handled separately.
    nonversions = [w for w in words if w not in VERSION_WORDS]
    if not nonversions:
        return True
    english = [w for w in nonversions if w in ENGLISH_WORDS]
    greekish = [w for w in nonversions if w in GREEKLISH_WORDS]
    strong_greekish = [w for w in greekish if w not in {'i','me','to','an','se','ti','na','ma','ta'}]
    if len(nonversions) >= 2 and len(english) >= 2 and not strong_greekish:
        return True
    if kind == 'artist':
        likely_greek_surname=any(w.endswith(('akis','idis','opoulos','opoulou','oglou','ellis','elis','poulos','iades')) for w in nonversions)
        if len(nonversions)>=2 and not strong_greekish and not likely_greek_surname:
            return True
        if any(w in ARTIST_ENGLISH_MARKERS for w in nonversions) and not strong_greekish:
            return True
        if len(nonversions)==1 and len(nonversions[0])<=3 and not greekish:
            return True
    if len(nonversions)==1 and nonversions[0] in ENGLISH_WORDS and not greekish:
        return True
    return False


def suspicious(original, converted):
    """Reject clear nonsense and flag ambiguous AI outputs for user review."""
    original = str(original or '').strip()
    converted = str(converted or '').strip()
    if not converted or not GREEK.search(converted):
        return 'INVALID_NO_GREEK'
    if len(converted)>180 or '\n' in converted or '\r' in converted:
        return 'INVALID_LENGTH'
    if greek_share(converted)<0.70:
        return 'INVALID_MOSTLY_LATIN'
    il = len(LATIN.findall(original))
    gl = len(GREEK.findall(converted)) - len(GREEK.findall(original))
    if il and not (0.35 * il <= gl <= 2.3 * il):
        return 'INVALID_LENGTH_RATIO'
    # This model often emits unaccented lowercase text. It is still searchable
    # but human review is recommended (e.g. ησουν / ήσουν).
    if not any(c in 'άέήίόύώΆΈΉΊΌΎΏΐΰ' for c in converted):
        return 'REVIEW_UNACCENTED'
    if len(re.findall(r'[A-Za-zΑ-Ωα-ωάέήίόύώ]+',original))<=2:
        return 'REVIEW_SHORT_AMBIGUOUS'
    return 'AI_SUGGESTION_REVIEW'


class G2GManager:
    def __init__(self, cache_file=None, factory=None):
        self.cache_file=Path(cache_file) if cache_file else Path(__file__).with_name('G2G_AI_Cache.json')
        self.factory=factory
        self.engine=None
        self.attempted_load=False
        self.load_error=''
        self.cache={}
        self.pending=0
        self.inferences=0
        self.hits=0
        self._read_cache()

    def _read_cache(self):
        if not self.cache_file.is_file():return
        try:
            payload=json.loads(self.cache_file.read_text(encoding='utf-8'))
            if payload.get('schema')==CACHE_SCHEMA and payload.get('model')==MODEL_ID and isinstance(payload.get('entries'),dict):
                self.cache=payload['entries']
        except (OSError,ValueError,TypeError):
            print('    G2G cache unreadable; ignoring it without deleting.',flush=True)

    def _load(self):
        if self.engine is not None:return True
        if self.attempted_load:return False
        self.attempted_load=True
        try:
            if self.factory:
                self.engine=self.factory()
            else:
                from gr_nlp_toolkit import Pipeline
                print('    Loading installed/cached local G2G model once...',flush=True)
                self.engine=Pipeline('g2g')
            print('    Local G2G model ready.',flush=True)
            return True
        except Exception as exc:
            self.load_error=f'{type(exc).__name__}: {str(exc)[:200]}'
            print('    G2G unavailable; continuing with manual aliases and original tags. '+self.load_error,flush=True)
            return False

    def _infer(self,value):
        output=self.engine(value)
        text=str(output.text if hasattr(output,'text') else output).strip()
        return text

    def flush(self):
        if not self.pending:return
        self.cache_file.parent.mkdir(parents=True,exist_ok=True)
        handle=None
        try:
            with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=self.cache_file.parent,
                       prefix='.g2g_cache_',suffix='.tmp',delete=False) as f:
                handle=Path(f.name)
                json.dump({'schema':CACHE_SCHEMA,'model':MODEL_ID,'entries':self.cache},f,ensure_ascii=False,indent=1)
            os.replace(handle,self.cache_file)
            self.pending=0
        except OSError as exc:
            print('    G2G cache could not be saved:',exc,flush=True)
            if handle and handle.exists():
                try:handle.unlink()
                except OSError:pass

    def release_model(self):
        # CPU RAM used by the large model is not needed while searching servers.
        if self.engine is not None:
            self.engine=None
            import gc
            gc.collect()

    def convert(self,text,kind='title'):
        """Return (Greek alternative, status). Never write to any media file."""
        original=str(text or '').strip()
        if not original or not LATIN.search(original):return '', 'ALREADY_GREEK_OR_EMPTY'
        if english_skip(original,kind):return '', 'SKIP_OBVIOUS_ENGLISH'
        key=f'{kind}|{normalize(original)}'
        if key in self.cache:
            self.hits+=1
            entry=self.cache[key]
            return entry.get('greek',''), entry.get('flag','AI_CACHED')
        if not self._load():return '', 'MODEL_UNAVAILABLE'
        try:
            # For mixed Greek/Greeklish text, leave Greek words untouched.
            if GREEK.search(original):
                pieces=[]; pos=0
                for match in LATIN_RUN.finditer(original):
                    chunk=match.group(0)
                    pieces.extend((original[pos:match.start()],
                                   chunk if english_skip(chunk,kind) else self._infer(chunk)))
                    pos=match.end()
                pieces.append(original[pos:])
                proposal=''.join(pieces).strip()
            else:
                proposal=self._infer(original)
            flag=suspicious(original,proposal)
            value='' if flag.startswith('INVALID') else proposal
            self.cache[key]={'greek':value,'flag':flag}
            self.pending+=1;self.inferences+=1
            if self.pending>=5:self.flush()
            return value,flag
        except KeyboardInterrupt:
            self.flush();raise
        except Exception as exc:
            return '',f'AI_ERROR: {type(exc).__name__}: {str(exc)[:120]}'
