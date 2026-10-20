#!/usr/bin/env python3
"""Build the complete v2.4.3 Windows Python/CMD ZIP and user PDF; no publication."""
from __future__ import annotations
import hashlib
import shutil
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DIST=ROOT/"dist"
PDF=ROOT/"docs"/"manuals"/"LRC_Bulk_Finder_v2.4.3_Complete_Step_by_Step_User_Manual_EN.pdf"
PDF_NAME="LRC_Bulk_Finder_v2_4_3_Complete_User_Manual_EN.pdf"
ZIP_NAME="LRC_Bulk_Finder_Public_v2_4_3_GitHub_Release_Windows.zip"
REQUIRED={"LRC_Bulk_Finder.py","LRC_Control_Center.py","START_HERE.cmd",
          "OPEN_CONTROL_CENTER.cmd","run_saved_profile.py","worker_stop.py",
          "stage_counters.py","search_profiles.py","v243_health.py",
          "v243_aliases.py","v243_resume.py","v243_contribution.py",
          "v243_provider_lab.py","TEST_V2_4_3_NEW_FEATURES.py",
          "README_FIRST.txt","README_STANDALONE_EXE_V2_4_3.txt",
          "Greek_Artists.csv","Greek_Aliases.csv","Greek_Lexicon.sqlite3",
          "LRCLIB_CONTACT.txt","LICENSE"}
SUFFIXES={".py",".cmd",".bat",".txt",".csv",".md",".sqlite3"}

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    return h.hexdigest()

def main():
    DIST.mkdir(exist_ok=True)
    if not PDF.is_file() or not PDF.read_bytes().startswith(b"%PDF-"):
        raise RuntimeError("Final checked user manual PDF missing")
    files=sorted(p for p in ROOT.iterdir() if p.is_file() and
                 (p.suffix.lower() in SUFFIXES or p.name=="LICENSE"))
    missing=REQUIRED-{p.name for p in files}
    if missing:raise RuntimeError("Missing files: "+", ".join(sorted(missing)))
    out=DIST/ZIP_NAME
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:z.write(p,arcname=p.name)
        z.write(PDF,arcname=PDF_NAME)
    with zipfile.ZipFile(out) as z:
        if z.testzip() is not None:raise RuntimeError("Archive CRC failed")
        names=set(z.namelist())
        if not REQUIRED.issubset(names) or PDF_NAME not in names:
            raise RuntimeError("Release files missing from ZIP")
        if any(n.endswith((".pyc",".pyo")) or "__pycache__" in n for n in names):
            raise RuntimeError("Unsafe generated Python files in ZIP")
    pdf_export=DIST/PDF_NAME
    shutil.copy2(PDF,pdf_export)
    print("Windows ZIP",out,"files",len(files)+1,"sha256",sha256(out),flush=True)
    print("User PDF",pdf_export,"sha256",sha256(pdf_export),flush=True)

if __name__=="__main__":main()
