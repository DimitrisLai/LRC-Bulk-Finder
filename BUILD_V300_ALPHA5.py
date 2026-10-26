"""Package the distinct Alpha 5 Windows test, with owner checkbox checklist."""
import json
import os
import subprocess

import BUILD_V300_FAST_STOP as package


def main():
    commit=os.environ.get('GITHUB_SHA') or subprocess.check_output(
        ['git','rev-parse','HEAD'],cwd=package.BASE,text=True).strip()
    info=package.BASE/'BUILD_INFO.json'
    if info.exists():raise RuntimeError('Refusing to replace an existing build manifest')
    info.write_text(json.dumps({'stage':'Startup and STOP audit — Alpha 5','tag':'v3.0.0-alpha.5',
        'source_commit':commit,'baseline_alpha4_commit':'7f4c7395831e1995265104b2366e9714aaf6fa09',
        'engine_version':'2.9.9','owner_windows_acceptance':'pending',
        'candidate_synchronized_playback':'pending startup/STOP acceptance'},indent=2),encoding='utf-8')
    try:
        package.NAME='LRC_Bulk_Finder_v3_Alpha5_Startup_STOP_Windows_Test.zip'
        package.FILES+=('README_V300_ALPHA4.md','README_V300_ALPHA5.md','CHECKLIST_ALPHA5.md','BUILD_INFO.json')
        package.main()
    finally:info.unlink()


if __name__=='__main__':main()
