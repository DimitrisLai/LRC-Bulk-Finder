# LRC Bulk Finder v2.4.4 — English / Ελληνικά (Public Beta)

The latest public Windows edition now offers a **live English / Greek graphical interface** and improved **Windows STOP verification**. This is a feature and reliability update; the strict lyrics matching, file-protection and manual candidate-review behavior remain unchanged.

## What's new

- **Language dropdown:** switch between **English** and **Ελληνικά** in the Control Center without restarting; the current tab and profile values are preserved.
- **Approved Greek translations:** 266 reviewed user-interface phrases (265 distinct source keys) cover the main tabs, settings, tips, presets, status messages and common dialogs. Provider names, internal codes, reports, filenames and lyrics are not translated.
- **Remembered language:** stored locally in the user's `APPDATA/LRCBulkFinder/ui_settings.json`, separate from saved search profiles.
- **Safer Windows STOP verification:** native Windows process enumeration, with conservative fallback, checks worker/child termination. Uncertain termination still results in a warning. Search resume remains checkpoint-based.
- **New bilingual documentation:** complete English manual updated for v2.4.4, plus a Greek user guide, each included in the standalone download and available separately.

## What to download

**Recommended — no Python needed:** `LRC_Bulk_Finder_v2_4_4_Standalone_Windows_GUI.zip`. Extract the entire ZIP to a writable folder, keep the two bundled EXEs together, then launch **`LRC_Control_Center.exe`**. At the top-right choose **English** or **Ελληνικά**. The Windows application is not code-signed; verify its official source and published SHA-256 checksums before running.

**Advanced — Python/CMD:** `LRC_Bulk_Finder_Public_v2_4_4_GitHub_Release_Windows.zip`. Requires Python 3.10+ and dependencies. Unpack the whole archive and run `OPEN_CONTROL_CENTER.cmd` for the GUI or `START_HERE.cmd` for the five-option console. Optional heavyweight Greek AI setup is available only with the full Python edition.

**Manuals:** `LRC_Bulk_Finder_v2_4_4_Complete_User_Manual_EN.pdf` and `LRC_Bulk_Finder_v2_4_4_User_Guide_EL.pdf`.

## First run and limitations

- Trial a **20-song** folder first. Action **1** is an online search and requires no large offline LRCLIB database. Actions **4** (offline only) and **5** (offline first) need a separately configured large LRCLIB database, not the bundled small Greek vocabulary database.
- Existing audio (MP3, FLAC, M4A, MP4, OGG, OPUS, WAV), its tags and already-present `.lrc` are not modified by ordinary searches. `.candidate.lrc` remains **UNVERIFIED** and must be reviewed.
- Internet lyrics providers may impose rate limits, remove endpoints, or fail. No guarantee is made that every track will obtain synchronized lyrics; version, duration, title and artist matching remains strict.
- STOP is tested extensively, but **any warning that children could not be verified must be acted on**. Inspect Task Manager before launching a fresh search.
- The standalone EXEs are unsigned. Windows SmartScreen warnings may appear; do not bypass your organization's security policy.
- The MIT license governs the project's code, not the third-party lyrics content.

## Quality checks

- Windows and Linux, Python 3.10 and 3.13: **261 regression tests** plus **27 additional interactive/adversarial GUI checks** per configuration.
- On each tested Windows Python version: all **10 Windows launchers**, **8 STOP stress trials** and **15 nested parent/child/grandchild STOP trials** passed using disposable test data and safe command stubs.
- The Windows standalone package is independently rebuilt and smoke-tested for GUI launch, worker execution, STOP IPC, ZIP integrity, needed modules and bundled resources before release.
- Testing cannot exhaustively verify all external lyric providers or every Windows security/antivirus configuration; please report specific issues using GitHub Issues.

## Links

- Project: https://github.com/DimitrisLai/LRC-Bulk-Finder
- Issue reports: https://github.com/DimitrisLai/LRC-Bulk-Finder/issues
- Previous release: https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/tag/v2.4.3

Created by Dimitris L. — Public Beta, October 2026.
