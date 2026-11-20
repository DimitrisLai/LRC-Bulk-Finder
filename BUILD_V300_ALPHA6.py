"""Build the Alpha 6 standalone Windows test package."""
import json
import os
import subprocess

import BUILD_V300_FAST_STOP as package


def main():
    source = os.environ.get("GITHUB_SHA") or subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=package.BASE, text=True).strip()
    manifest = package.BASE / "BUILD_INFO.json"
    metadata = {
        "stage": "Candidate Review — Alpha 6",
        "tag": "v3.0.0-alpha.6",
        "source_commit": source,
        "baseline_alpha5_commit": "9668de9ba83d6f04cdb4726dd17272c66c11fa17",
        "engine_version": "2.9.9",
        "owner_windows_acceptance": "pending",
    }
    with manifest.open("x", encoding="utf-8") as stream:
        json.dump(metadata, stream, indent=2)
    try:
        package.main(
            name="LRC_Bulk_Finder_v3_Alpha6_Candidate_Review_Windows_Test.zip",
            files=package.FILES + ("README_V300_ALPHA4.md", "README_V300_ALPHA5.md",
                                   "CHECKLIST_ALPHA5.md", "README_V300_ALPHA6.md",
                                   "CHECKLIST_ALPHA6_EL.md", manifest.name))
    finally:
        manifest.unlink()


if __name__ == "__main__":
    main()
