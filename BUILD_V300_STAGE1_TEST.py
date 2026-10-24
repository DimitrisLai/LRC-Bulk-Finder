"""Build user-testable Stage 1 standalone ZIP; never touches an existing release."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from hashlib import sha256
import sys

BASE = Path(__file__).resolve().parent
DIST = BASE / "dist"
NAME = "LRC_Bulk_Finder_v3_Stage1_Windows_Test.zip"
FILES = (
    "LRC_Control_Center.exe", "LRC_Bulk_Finder_Worker.exe",
    "Greek_Artists.csv", "Greek_Aliases.csv", "Greek_Words.csv",
    "Greek_Words_Expanded.csv", "Greek_Words_Wikipedia.csv",
    "Greek_Lexicon.sqlite3", "g2g_sidecar.py",
    "LICENSE", "LRCLIB_CONTACT.txt",
    "LAUNCH_LRC_BULK_FINDER_WINDOWS.cmd",
    "README_STANDALONE_EXE_V2_9_9.txt",
    "README_V300_STAGE1_TEST.md",
)
def main():
    import LRC_Bulk_Finder
    assert LRC_Bulk_Finder.VERSION == "2.9.9", "Do not silently change stable engine version"
    assert (BASE / "candidate_review_v3.py").is_file()
    assert (BASE / "v300_candidate_compare_gui.py").is_file()
    DIST.mkdir(exist_ok=True)
    destination = DIST / NAME
    with ZipFile(destination, "w", ZIP_DEFLATED, compresslevel=7) as archive:
        for filename in FILES:
            origin = (DIST if filename.endswith(".exe") else BASE) / filename
            if not origin.is_file() or origin.stat().st_size == 0:
                raise RuntimeError("Missing required Stage 1 test asset: " + str(origin))
            archive.write(origin, filename)
    with ZipFile(destination) as archive:
        assert archive.testzip() is None, "ZIP integrity failed"
        names = archive.namelist()
        assert len(names) == len(set(names))
        assert set(names) == set(FILES)
        assert all(".." not in Path(name).parts and not name.startswith("/") for name in names)
        assert not any(n.lower().endswith((".mp3",".wav",".flac",".ogg",".mp4",".m4a"))
                       for n in names)
        assert b"Stage 1" in archive.read("README_V300_STAGE1_TEST.md")
    digest = sha256(destination.read_bytes()).hexdigest()
    (DIST / (NAME + ".sha256")).write_text(f"{digest}  {NAME}\n", encoding="ascii")
    print("PASS", destination, "SHA256", digest, "bytes", destination.stat().st_size)

if __name__ == "__main__":
    main()
