# LRC Bulk Finder v2.4.5 — Quick Search, Results dashboard and Timing repair

Free, open-source Windows application. **Public Beta**, English / Ελληνικά.

## What's new

- **Quick Search:** Simple starting tab with a folder picker, a 20-song test / all-songs selection, subfolder toggle, optional Greek/Greeklish matching and one START button. Uses FAST online mode; no LRCLIB snapshot required. Saves its profile under the local user settings.
- **Results dashboard:** Read-only inventory, counts for `Has LRC`, `Needs review`, `Missing LRC` and `Ambiguous audio`, filename search, filtering, open audio externally and safe CSV export. The presence of an LRC is *not* proof its content or timing is verified.
- **Timing repair:** Select an audio file and an existing LRC in the same folder; enter a global offset from -300 to +300 seconds, preview corrected timestamps, and explicitly save a NEW numbered `.candidate.lrc`. Negative timestamps are refused; the source LRC, metadata and audio are never overwritten. This is **not AI transcription or automatic word alignment**. Review by listening.
- **Manual GitHub update check:** Only when clicked, checks the official GitHub release API; no automatic downloads/installs.
- **Private diagnostics:** One click exports application and companion-worker status without personal filenames, paths, music titles, lyrics, credentials or tags. Exports use exclusive create.
- **Polish and bilingual navigation:** Three additional tabs and Greek UI labels; all v2.4.4 approved translations remain unchanged.
- **Existing engine unchanged:** Strict version/duration checks, offline modes 4/5, candidate safeguards, STOP process verification, profiles, reports and provider health remain available.

## Download

Download the **LRC_Bulk_Finder_v2_4_5_Standalone_Windows_GUI.zip** for the easiest Windows GUI: extract the whole ZIP and open `LRC_Control_Center.exe` (no Python). Both English and Greek are in the same EXE.

Advanced users: **LRC_Bulk_Finder_Public_v2_4_5_GitHub_Release_Windows.zip** (Python 3.10+ and optional local Greek AI setup). The English complete manual and Greek user guide are available as separate PDF assets and bundled in the standalone archive.

## Safety and limitations

Ordinary searches never modify audio or ID3 tags, and never overwrite an existing `.lrc`. New timing repairs are explicitly marked UNVERIFIED. Only use an existing .lrc from the same folder as its matching audio track. Existing candidates get numbered alternatives rather than being overwritten.

Dashboard statistics are based on *existing files*, not independent verification of synchronization. External providers and music metadata vary. Check results on a small copied 20-song library first.

The standalone executables are currently unsigned, so Windows SmartScreen may warn. Verify the official repository and release SHA256 checksums; respect organization security policies.

## QA

Release gates include Windows/Linux Python 3.10 and 3.13 regression tests, safe GUI tests, repeated STOP and nested process-tree checks, PyInstaller executable startup and worker STOP, module verification, PDFs, ZIP integrity and published SHA256 checksums. No live provider coverage guarantee.

Previous public release: [v2.4.4](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/tag/v2.4.4)

Source: https://github.com/DimitrisLai/LRC-Bulk-Finder
Issues: https://github.com/DimitrisLai/LRC-Bulk-Finder/issues
