"""v2.3 non-interactive runner for user-selected GUI search profiles.

Existing command-line START_HERE.cmd remains fully interactive and unchanged.
Run: python -u run_saved_profile.py --profile "Greek FULL"
"""
from __future__ import annotations
import argparse
import builtins
import sys
from pathlib import Path
from search_profiles import ProfileAnswers,load_profiles,validate_profile


def run_profile(name,profiles_path=None):
    profiles=load_profiles(profiles_path)
    if name not in profiles:
        raise ValueError("Profile not found: "+name)
    profile=validate_profile(profiles[name])
    folder=Path(profile["folder"]).expanduser()
    if not folder.is_dir():
        raise ValueError("Selected music folder does not exist: "+str(folder))
    import LRC_Bulk_Finder as finder
    answers=ProfileAnswers(profile)
    old_input=builtins.input
    old_select=finder.select_folder
    finder.select_folder=lambda:folder
    builtins.input=answers
    try:
        print("STARTING SAVED PROFILE:",name,flush=True)
        print("Selected MP3 folder:",folder,flush=True)
        finder.main()
    finally:
        builtins.input=old_input
        finder.select_folder=old_select


def main(argv=None):
    parser=argparse.ArgumentParser(description="Run one saved LRC Bulk Finder search profile")
    parser.add_argument("--profile",required=True,help="Saved profile name")
    parser.add_argument("--profiles-path",help="Optional alternate profiles.json for portable/test runs")
    args=parser.parse_args(argv)
    try:
        run_profile(args.profile,args.profiles_path)
    except (ValueError,RuntimeError,OSError) as error:
        print("PROFILE ERROR:",error,file=sys.stderr,flush=True)
        return 2
    return 0


if __name__=="__main__":
    sys.exit(main())
