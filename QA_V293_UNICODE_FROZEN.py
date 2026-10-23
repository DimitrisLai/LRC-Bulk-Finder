"""Packaged Windows Worker smoke: UTF-8 Unicode-hyphen path with no private audio.

Creates an empty synthetic music folder. The frozen Worker must print the
Unicode path without CP1252/charmap UnicodeEncodeError, even if no songs exist.
"""
from __future__ import annotations
import argparse
import subprocess
import tempfile
from pathlib import Path
from search_profiles import DEFAULT, save_profiles


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("worker",type=Path)
    args=parser.parse_args(argv)
    if not args.worker.is_file():
        raise FileNotFoundError(args.worker)
    with tempfile.TemporaryDirectory(prefix="lrc_unicode_frozen_") as temp:
        root=Path(temp)
        music=root/"Collection‐Καλημέρα"  # Unicode U+2010, Greek text
        music.mkdir()
        profile={**DEFAULT,"folder":str(music),"greek":False,"local_ai":False,
                 "action":"1","provider_mode":"fast","musicbrainz":False,
                 "limit":"20","recursive":False,"history":False}
        profiles_path=root/"profiles.json"
        save_profiles({"Unicode Smoke":profile},profiles_path)
        result=subprocess.run(
            [str(args.worker.resolve()),"--profile","Unicode Smoke",
             "--profiles-path",str(profiles_path)],
            capture_output=True,encoding="utf-8",errors="replace",timeout=45,
            cwd=str(args.worker.resolve().parent),
        )
        output=(result.stdout or "")+"\n"+(result.stderr or "")
        if "PROFILE ERROR: 'charmap'" in output or "UnicodeEncodeError" in output:
            raise AssertionError("Frozen Worker failed UTF-8: "+output[-1400:])
        if str(music) not in output:
            raise AssertionError("Frozen Worker failed to round-trip Unicode path: "+output[-1400:])
        if result.returncode not in (0,2):
            raise AssertionError(f"Unexpected Worker status {result.returncode}: "+output[-1400:])
        if result.returncode == 2 and "PROFILE ERROR:" in output:
            # Some no-audio folders legitimately report a no-files error.
            if not any(t in output.lower() for t in ("no audio","no mp3","no eligible","no supported")):
                raise AssertionError("Frozen Worker reported an unrelated error: "+output[-1400:])
        print("PASS: Unicode U+2010 / Greek path survived packaged frozen worker output")
        return 0


if __name__=="__main__":
    raise SystemExit(main())
