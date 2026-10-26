"""Package a distinct verified Alpha 4; preserve every previous release."""
import json
import os
from pathlib import Path
import subprocess

import BUILD_V300_FAST_STOP as package


def main():
    commit = os.environ.get("GITHUB_SHA") or subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=package.BASE, text=True).strip()
    info = package.BASE / "BUILD_INFO.json"
    if info.exists():
        raise RuntimeError("Refusing to replace an existing build manifest")
    info.write_text(json.dumps({
        "stage": "STOP/LRCLIB reliability audit — Alpha 4",
        "tag": "v3.0.0-alpha.4", "source_commit": commit,
        "baseline_alpha3_commit": "f284a71c7cf81f3dfd112ac49305078422f03a80",
        "engine_version": "2.9.9", "owner_windows_acceptance": "pending",
        "candidate_synchronized_playback": "next separate stage after STOP acceptance"
    }, indent=2), encoding="utf-8")
    try:
        package.NAME = "LRC_Bulk_Finder_v3_Alpha4_STOP_LRCLIB_Windows_Test.zip"
        package.FILES += ("README_V300_ALPHA4.md", "BUILD_INFO.json")
        package.main()
    finally:
        info.unlink()


if __name__ == "__main__":
    main()
