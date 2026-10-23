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


def configure_console_output():
    """Emit Unicode filenames safely to the GUI UTF-8 pipe on Windows.

    Frozen workers can start with cp1252/charmap stdout. One Greek or Unicode
    hyphen in a filename previously raised UnicodeEncodeError, aborting the
    entire scan with exit code 2. Retain legible UTF-8 in all normal streams;
    unencodable edge cases are escaped instead of terminating the worker.
    """
    for stream in (sys.stdout,sys.stderr):
        if callable(getattr(stream,"reconfigure",None)):
            try:
                stream.reconfigure(encoding="utf-8",errors="backslashreplace",
                                   line_buffering=True)
            except (OSError,ValueError,TypeError,AttributeError):
                pass  # A redirect with no writable encoding must not stop a run.



def run_profile(name,profiles_path=None):
    configure_console_output()  # Also protect direct/profile-API invocations.
    profiles=load_profiles(profiles_path)
    if name not in profiles:
        raise ValueError("Profile not found: "+name)
    profile=validate_profile(profiles[name])
    if getattr(sys,"frozen",False) and profile["local_ai"]:
        from g2g_auto import installed
        if not installed():
            # An older profile still works even if setup was never finished.
            profile={**profile,"local_ai":False}
            print("LOCAL AI UNAVAILABLE: one-click setup has not been verified. "
                  "Continuing safely with curated Greek dictionaries.",
                  flush=True)
    folder=Path(profile["folder"]).expanduser()
    if not folder.is_dir():
        raise ValueError("Selected music folder does not exist: "+str(folder))
    prior_exp=os.environ.get("LRC_EXPERIMENTAL_SIMPMUSIC")
    prior_pack=os.environ.get("LRC_PROVIDER_PACK")
    prior_excluded=os.environ.get("LRC_PROVIDER_EXCLUSIONS")
    selected_pack=profile.get("provider_pack","legacy")
    # Tier 6 explicitly includes SimpMusic; existing FAST/FULL toggles stay intact.
    os.environ["LRC_EXPERIMENTAL_SIMPMUSIC"]="1" if profile["action"]!="4" and (
        selected_pack=="6" or (selected_pack=="legacy" and
        profile.get("experimental_simpmusic",False) and profile["provider_mode"]=="full")) else "0"
    os.environ["LRC_PROVIDER_PACK"]=selected_pack
    os.environ["LRC_PROVIDER_EXCLUSIONS"]=",".join(profile.get("provider_exclusions",[]))
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
        if prior_pack is None:os.environ.pop("LRC_PROVIDER_PACK",None)
        else:os.environ["LRC_PROVIDER_PACK"]=prior_pack
        if prior_excluded is None:os.environ.pop("LRC_PROVIDER_EXCLUSIONS",None)
        else:os.environ["LRC_PROVIDER_EXCLUSIONS"]=prior_excluded
        if prior_incremental is None:os.environ.pop('LRC_INCREMENTAL',None)
        else:os.environ['LRC_INCREMENTAL']=prior_incremental
        if finder.LIBRARY_INDEX is not None:
            finder.LIBRARY_INDEX.close()
            finder.LIBRARY_INDEX=None


def main(argv=None):
    configure_console_output()
    parser=argparse.ArgumentParser(description="Run one saved LRC Bulk Finder search profile")
    parser.add_argument("--profile",help="Saved profile name")
    parser.add_argument("--benchmark",action="store_true",help="Test provider sources without installing or writing any LRC")
    parser.add_argument("--benchmark-folder",help="Audio folder to sample (read-only)")
    parser.add_argument("--benchmark-pack",default="legacy",help="Existing tier key, or legacy")
    parser.add_argument("--benchmark-mode",choices=("fast","full"),default="full")
    parser.add_argument("--benchmark-excluded",default="",help="Comma-separated disabled source names")
    parser.add_argument("--benchmark-sample",type=int,choices=(5,10,20),default=10)
    parser.add_argument("--benchmark-nonrecursive",action="store_true")
    parser.add_argument("--setup-lrclib",action="store_true",help="Run the consent-based official LRCLIB database downloader")
    parser.add_argument("--setup-g2g",action="store_true",help="Install and verify optional Greek AI into a separate user environment")
    parser.add_argument("--g2g-status",action="store_true",help="Print optional Greek AI status without downloads or installing anything")
    parser.add_argument("--g2g-model",choices=["g2g","g2g_lite"],default="g2g")
    parser.add_argument("--allow-python-install",action="store_true",help="Also install official Python 3.11 using Windows winget if missing")
    parser.add_argument("--profiles-path",help="Optional alternate profiles.json for portable/test runs")
    args=parser.parse_args(argv)
    if args.benchmark:
        try:
            from v297_provider_intelligence import benchmark
            if not args.benchmark_folder:
                raise ValueError("Benchmark needs a folder")
            benchmark(args.benchmark_folder,args.benchmark_pack,args.benchmark_mode,
                      [v.strip() for v in args.benchmark_excluded.split(",") if v.strip()],
                      args.benchmark_sample,not args.benchmark_nonrecursive)
            return 0
        except KeyboardInterrupt:
            print("BENCHMARK INTERRUPTED: no audio or lyric files changed.",flush=True)
            return 130
        except (OSError,RuntimeError,ValueError) as error:
            print("BENCHMARK ERROR:",error,file=sys.stderr,flush=True)
            return 2
    if args.setup_lrclib:
        from auto_install_lrclib_database import main as install_lrclib
        install_lrclib()
        return 0
    if args.g2g_status:
        from g2g_auto import installed
        print("G2G STATUS: verified and ready" if installed() else
              "G2G STATUS: not installed or not verified",flush=True)
        return 0
    if args.setup_g2g:
        from g2g_auto import setup
        try:
            setup(model=args.g2g_model, allow_python_install=args.allow_python_install)
            return 0
        except (OSError,RuntimeError,ValueError) as error:
            print("G2G SETUP FAILED:",str(error),file=sys.stderr,flush=True)
            return 2
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
