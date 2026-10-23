"""Safe, GUI-only bilingual presentation (the search engine remains English)."""
from __future__ import annotations
import json
import os
import re
import string
import tempfile
from pathlib import Path
from ui_translations import UI_EL

SUPPORTED=('en','el')
REVERSE_EL={value:key for key,value in UI_EL.items() if value!=key}
# Longest static forms first for template matching. Placeholders are data, never eval'd.
PATTERNS=[]
for original,translated in UI_EL.items():
    if '{' not in original or '}' not in original:continue
    parts=list(string.Formatter().parse(original))
    rx='^'
    capture=[]
    for literal,field,fmt,conv in parts:
        rx+=re.escape(literal)
        if field is not None:
            var=re.sub('[^a-zA-Z0-9_]','_',field)
            if var in capture: continue
            capture.append(var)
            rx+=f'(?P<{var}>[\\s\\S]*?)'
    rx+='$'
    try:PATTERNS.append((re.compile(rx),translated,tuple(capture)))
    except re.error:pass
PATTERNS.sort(key=lambda item:len(item[0].pattern),reverse=True)

class GuiLocale:
    def __init__(self,language='en'):
        self.language=language if language in SUPPORTED else 'en'
    def tr(self,text):
        if not isinstance(text,str) or self.language=='en':return text
        # No network, no rewriting of audio/lyrics or structured machine states.
        if text in UI_EL:return UI_EL[text]
        if text in REVERSE_EL:return text
        lead=text[:len(text)-len(text.lstrip())]
        tail=text[len(text.rstrip()):]
        base=text.strip()
        if base in UI_EL:return lead+UI_EL[base]+tail
        for rx,translation,names in PATTERNS:
            match=rx.fullmatch(text)
            if match:
                try:
                    # f-string precision placeholders are for dynamic output matching,
                    # not a new numeric formatting operation on strings.
                    return re.sub(r'\{([A-Za-z_]\w*)(?::[^}]+)?\}',
                        lambda m:match.group(m.group(1)) if m.group(1) in names else m.group(0),
                        translation)
                except (KeyError,IndexError):pass
        return text

def settings_file(appdata=None):
    appdata=appdata if appdata is not None else os.environ.get('APPDATA')
    return (Path(appdata) if appdata else Path.home()/'.config')/'LRCBulkFinder'/'ui_settings.json'

def read_language(path=None):
    try:
        value=json.loads(Path(path or settings_file()).read_text(encoding='utf-8')).get('interface_language','en')
        return value if value in SUPPORTED else 'en'
    except (OSError,ValueError,TypeError,AttributeError):return 'en'

def save_language(language,path=None):
    if language not in SUPPORTED:raise ValueError('Unsupported UI language')
    target=Path(path or settings_file())
    target.parent.mkdir(parents=True,exist_ok=True)
    temp=None
    try:
        try:
            existing=json.loads(target.read_text(encoding='utf-8'))
            if not isinstance(existing,dict):existing={}
        except (OSError,ValueError,TypeError):
            existing={}
        existing.update({'schema':1,'interface_language':language})
        with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=target.parent,
                                        prefix='.ui_settings-',suffix='.tmp',delete=False) as f:
            temp=Path(f.name)
            json.dump(existing,f,ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(temp),str(target))
    finally:
        if temp and temp.exists():temp.unlink()
