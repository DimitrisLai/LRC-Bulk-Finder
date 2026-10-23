"""Prepare, independently inspect and checksum the v2.9.6 public Windows archives.
No network access, installation, API provider calls, or changes to user music.
"""
from __future__ import annotations
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from hashlib import sha256
import subprocess
import re
import sqlite3
import sys

BASE=Path(__file__).resolve().parent
DIST=BASE/'dist'
VER='2.9.6'
PREFIX='LRC_Bulk_Finder_v2_9_6/'
SOURCE_NAME='LRC_Bulk_Finder_Public_v2_9_6_GitHub_Release_Windows.zip'
STANDALONE_NAME='LRC_Bulk_Finder_v2_9_6_Standalone_Windows_GUI.zip'
EN='LRC_Bulk_Finder_v2_9_6_Complete_User_Manual_EN.pdf'
EL='LRC_Bulk_Finder_v2_9_6_User_Guide_EL.pdf'
MANIFEST='LRC_Bulk_Finder_v2_9_6_SHA256SUMS.txt'

def git_files():
    cmd=['git','ls-files','-z']
    data=subprocess.check_output(cmd,cwd=BASE)
    files=[Path(p) for p in data.decode('utf-8').split('\0') if p]
    def allowed(p):
        name=p.as_posix()
        return ((BASE/p).is_file() and not name.startswith(('.github/','QA_','downloads/'))
            and not name.endswith(('.zip','.pdf','.pyc'))
            and '__pycache__' not in name and not name.startswith('patch_gui_locale'))
    return sorted(p for p in files if allowed(p))

def sha_file(p):
    digest=sha256()
    with open(p,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def assert_zip(path,required):
    with ZipFile(path,'r') as z:
        bad=z.testzip()
        assert bad is None,(path,bad)
        names=z.namelist()
        assert len(names)==len(set(names)),f'Duplicate ZIP entry: {path}'
        assert all(p in names for p in required),('Missing',set(required)-set(names))
        for x in names:
            assert not x.startswith('/') and '..' not in Path(x).parts,f'Unsafe archive path: {x}'
            assert not any(x.lower().endswith(e) for e in ('.mp3','.flac','.m4a','.opus','.wav','.ogg','.mp4'))
            assert 'lrclib-db-dump-' not in x.lower()
        assert z.getinfo(required[0]).file_size>0
        return len(names)

def build():
    DIST.mkdir(parents=True,exist_ok=True)
    assert "VERSION = '2.9.6'" in (BASE/'LRC_Bulk_Finder.py').read_text(encoding='utf-8')
    assert 'from v245_features import VERSION as APP_VERSION' in (BASE/'LRC_Control_Center.py').read_text(encoding='utf-8')
    assert 'self.title(f\'LRC Bulk Finder v{APP_VERSION} — Control Center\')' in (BASE/'LRC_Control_Center.py').read_text(encoding='utf-8')
    assert "VERSION = '2.9.6'" in (BASE/'v245_features.py').read_text(encoding='utf-8')
    assert 'English' in (BASE/'LRC_Control_Center.py').read_text(encoding='utf-8')
    assert 'Ελληνικά' in (BASE/'ui_translations.py').read_text(encoding='utf-8')
    assert 'APPROVED_UI_ROWS = 266' in (BASE/'ui_translations.py').read_text(encoding='utf-8')
    assert 'Quick Search' in (BASE/'v245_gui.py').read_text(encoding='utf-8')
    assert 'save_shifted_candidate' in (BASE/'v245_features.py').read_text(encoding='utf-8')
    assert 'filter_selected_tracks' in (BASE/'v250_manager.py').read_text(encoding='utf-8')
    assert 'undo_session' in (BASE/'v250_manager.py').read_text(encoding='utf-8')
    assert 'Retry selected tracks' in (BASE/'v250_gui.py').read_text(encoding='utf-8')
    assert 'save_candidate' in (BASE/'v260_studio.py').read_text(encoding='utf-8')
    assert 'pygame' in (BASE/'v260_player.py').read_text(encoding='utf-8')
    assert 'Lyrics Studio' in (BASE/'v260_studio_gui.py').read_text(encoding='utf-8')
    assert 'Precision & Karaoke' in (BASE/'v270_gui.py').read_text(encoding='utf-8')
    assert 'render_export' in (BASE/'v270_precision.py').read_text(encoding='utf-8')
    assert 'read_waveform' in (BASE/'v270_waveform.py').read_text(encoding='utf-8')
    assert 'VLCPlayer' in (BASE/'v270_vlc.py').read_text(encoding='utf-8')
    assert 'KaraokeSession' in (BASE/'v280_karaoke_core.py').read_text(encoding='utf-8')
    assert 'Open audience screen' in (BASE/'v280_karaoke_gui.py').read_text(encoding='utf-8')
    assert 'Έκδοση Καραόκε' in (BASE/'v280_translations.py').read_text(encoding='utf-8')
    assert 'Smart Library' in (BASE/'v290_smart_gui.py').read_text(encoding='utf-8')
    assert 'scan_index' in (BASE/'v290_smart_library.py').read_text(encoding='utf-8')
    assert 'Έξυπνη Βιβλιοθήκη' in (BASE/'v290_translations.py').read_text(encoding='utf-8')
    with sqlite3.connect(str(BASE/'Greek_Lexicon.sqlite3')) as db:
        assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        assert db.execute('SELECT COUNT(*) FROM words').fetchone()[0]>=1000
    # A current standalone MUST include both source-linked Greek vocabularies.
    import csv
    with (BASE/'Greek_Artists.csv').open(encoding='utf-8-sig',newline='') as f:
        artists=list(csv.DictReader(f))
    with (BASE/'Greek_Words_Wikipedia.csv').open(encoding='utf-8-sig',newline='') as f:
        song_words=list(csv.DictReader(f))
    assert len(artists)>=730, f'Greek artist data missing: {len(artists)}'
    assert len(song_words)>=90, f'Greek song title word data missing: {len(song_words)}'
    required_docs=[DIST/EN,DIST/EL]
    for doc in required_docs:
        assert doc.is_file() and doc.stat().st_size>10000,doc
    required_assets=[
        'LRC_Control_Center.exe','LRC_Bulk_Finder_Worker.exe',
        'Greek_Artists.csv','Greek_Aliases.csv','Greek_Words.csv',
        'Greek_Words_Expanded.csv','Greek_Words_Wikipedia.csv','Greek_Lexicon.sqlite3',
        'g2g_sidecar.py',
        'LICENSE','LRCLIB_CONTACT.txt',
        'LAUNCH_LRC_BULK_FINDER_WINDOWS.cmd',
        'README_STANDALONE_EXE_V2_9_6.txt','HOW_TO_START_V2_9_6.txt',
        'RELEASE_NOTES_V2_9_6.md',EN,EL,
    ]
    standalone=DIST/STANDALONE_NAME
    with ZipFile(standalone,'w',ZIP_DEFLATED,compresslevel=6) as z:
        for name in required_assets:
            loc=DIST/name if name.endswith(('.exe','.pdf')) else BASE/name
            assert loc.is_file(),loc
            z.write(loc,name)
    n1=assert_zip(standalone,required_assets)
    # The separate model entrypoint MUST accompany frozen EXEs, or the Setup
    # control would look installed but searches could not start the model.
    with ZipFile(standalone) as z:
        assert b'--self-test' in z.read('g2g_sidecar.py')

    # Check the exported ZIP, not merely local source files.
    with ZipFile(standalone,'r') as z:
        assert len(z.read('Greek_Words_Wikipedia.csv'))>1000
        assert len(z.read('Greek_Artists.csv'))>15000
    src=DIST/SOURCE_NAME
    tracked=git_files()
    with ZipFile(src,'w',ZIP_DEFLATED,compresslevel=8) as z:
        paths=set()
        for p in tracked:
            name=p.as_posix()
            z.write(BASE/p,PREFIX+name)
            paths.add(name)
        for name in ('Greek_Lexicon.sqlite3',):
            if name not in paths:
                z.write(BASE/name,PREFIX+name)
        for name in (EN,EL):
            z.write(DIST/name,PREFIX+name)
    required_source=['LRC_Control_Center.py','LRC_Bulk_Finder.py','run_saved_profile.py',
                     'ui_locale.py','ui_translations.py','ui_appearance.py','search_profiles.py','v245_features.py','v245_gui.py',
                     'v245_translations.py','v250_manager.py','v250_gui.py',
                     'v250_translations.py','TEST_V250_MANAGER.py','TEST_V250_ENGINE.py',
                     'TEST_V250_GUI.py','v260_studio.py','v260_studio_gui.py',
                     'v260_player.py','v260_translations.py','TEST_V260_STUDIO.py',
                     'TEST_V260_GUI.py','TEST_V270_GUI.py','TEST_V270_FEATURES.py',
                     'v270_gui.py','v270_precision.py','v270_waveform.py','v270_vlc.py',
                     'v270_translations.py','v280_karaoke_core.py','v280_karaoke_gui.py',
                     'v280_translations.py','TEST_V280_KARAOKE.py','TEST_V280_GUI.py',
                     'v290_smart_library.py','v290_smart_gui.py','v290_translations.py',
                     'TEST_V290_SMART_LIBRARY.py','TEST_V290_GUI.py','TEST_V290_SCALE.py',
                     'TEST_V291_STARTUP.py','LAUNCH_LRC_BULK_FINDER_WINDOWS.cmd',
                     'TEST_V292_PREFLIGHT.py','BUILD_V296_MANUALS.py',
                     'ROADMAP_V2_8_V2_9_V3_0.md','worker_stop.py',
                     'Greek_Words_Wikipedia.csv','Greek_Artists.csv','Greek_Artists_Baseline_Approved.csv',
                     'TEST_NEXT_UPDATE_WINDOWS_STABILITY.py','UPDATE_GREEK_SONG_WORDS_WIKIPEDIA.py',
                     'TEST_G2G_ONE_CLICK.py','g2g_auto.py','g2g_sidecar.py',
                     'TEST_MODERN_APPEARANCE.py',
                     'v296_provider_tiers.py','TEST_V296_PROVIDER_TIERS.py',
                     'README_STANDALONE_EXE_V2_9_6.txt','HOW_TO_START_V2_9_6.txt',
                     'BUILD_V296_MANUALS.py','LRC_Control_Center.py','START_HERE.cmd',
                     'OPEN_CONTROL_CENTER.cmd','Greek_Lexicon.sqlite3',EN,EL]
    n2=assert_zip(src,[PREFIX+n for n in required_source])
    with ZipFile(src) as z:
        assert b"VERSION = '2.9.6'" in z.read(PREFIX+'LRC_Bulk_Finder.py')
        assert b'English' in z.read(PREFIX+'LRC_Control_Center.py')
        assert b'APPROVED_UI_ROWS = 266' in z.read(PREFIX+'ui_translations.py')
        assert b'def install_theme' in z.read(PREFIX+'ui_appearance.py')
        assert b'appearance_choice' in z.read(PREFIX+'LRC_Control_Center.py')
        assert b'better_qq_review_only' in z.read(PREFIX+'v296_provider_tiers.py')
        assert b'provider_pack' in z.read(PREFIX+'search_profiles.py')
        assert b'PACKS' in z.read(PREFIX+'v296_provider_tiers.py')
    assets=[standalone,src,DIST/EN,DIST/EL]
    manifest=DIST/MANIFEST
    manifest.write_text(''.join(f'{sha_file(p)}  {p.name}\n' for p in assets),encoding='ascii')
    for p in assets:
        assert sha_file(p) in manifest.read_text(encoding='ascii')
    print(f'PASS release v{VER}: {n1} standalone items, {n2} source items; 4 assets + checksum manifest')
    for p in assets:
        print(f'{sha_file(p)}  {p.name}  {p.stat().st_size:,} bytes')
    return [*assets,manifest]

if __name__=='__main__':build()
