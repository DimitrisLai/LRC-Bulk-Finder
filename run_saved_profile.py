"""v2.3 non-interactive runner for user-selected GUI search profiles.

Existing command-line START_HERE.cmd remains fully interactive and unchanged.
Run: python -u run_saved_profile.py --profile "Greek FULL"
"""
from __future__ import annotations
import argparse
import builtins
import os
import sys
from pathlib import Path
from search_profiles import ProfileAnswers,load_profiles,validate_profile
from stop_control import check_stop


def run_profile(name,profiles_path=None):
    profiles=load_profiles(profiles_path)
    if name not in profiles:
        raise ValueError("Profile not found: "+name)
    profile=validate_profile(profiles[name])
    folder=Path(profile["folder"]).expanduser()
    if not folder.is_dir():
        raise ValueError("Selected music folder does not exist: "+str(folder))
    prior_exp=os.environ.get("LRC_EXPERIMENTAL_SIMPMUSIC")
    os.environ["LRC_EXPERIMENTAL_SIMPMUSIC"]="1" if profile.get("experimental_simpmusic",False) and profile["provider_mode"]=="full" and profile["action"]!="4" else "0"
    import LRC_Bulk_Finder as finder
    answers=ProfileAnswers(profile)
    prior_incremental=os.environ.get('LRC_INCREMENTAL')
    os.environ['LRC_INCREMENTAL']='1' if profile.get('incremental',True) else '0'
    old_input=builtins.input
    old_select=finder.select_folder
    finder.select_folder=lambda:folder
    builtins.input=answers
    try:
        check_stop()
        print("STARTING SAVED PROFILE:",name,flush=True)
        print("Selected MP3 folder:",folder,flush=True)
        finder.main()
        check_stop()  # interrupted stage may have returned after saving reports
    finally:
        builtins.input=old_input
        finder.select_folder=old_select
        if prior_exp is None:os.environ.pop("LRC_EXPERIMENTAL_SIMPMUSIC",None)
        else:os.environ["LRC_EXPERIMENTAL_SIMPMUSIC"]=prior_exp
        if prior_incremental is None:os.environ.pop('LRC_INCREMENTAL',None)
        else:os.environ['LRC_INCREMENTAL']=prior_incremental
        if finder.LIBRARY_INDEX is not None:
            finder.LIBRARY_INDEX.close()
            finder.LIBRARY_INDEX=None


def main(argv=None):
    parser=argparse.ArgumentParser(description="Run one saved LRC Bulk Finder search profile")
    parser.add_argument("--profile",help="Saved profile name")
    parser.add_argument("--setup-lrclib",action="store_true",help="Run the consent-based official LRCLIB database downloader")
    parser.add_argument("--profiles-path",help="Optional alternate profiles.json for portable/test runs")
    args=parser.parse_args(argv)
    if args.setup_lrclib:
        from auto_install_lrclib_database import main as install_lrclib
        install_lrclib()
        return 0
    if not args.profile:
        parser.error('This is the background search worker, not the main app. '
                     'Start LRC_Control_Center.exe for the graphical interface. '
                     '--profile is required for command-line searches.')
    try:
        run_profile(args.profile,args.profiles_path)
    except KeyboardInterrupt:
        print('STOP REQUESTED: search ended; completed checkpoints and reports preserved.',flush=True)
        return 130
    except (ValueError,RuntimeError,OSError) as error:
        print("PROFILE ERROR:",error,file=sys.stderr,flush=True)
        return 2
    return 0


if __name__=="__main__":
    sys.exit(main())
