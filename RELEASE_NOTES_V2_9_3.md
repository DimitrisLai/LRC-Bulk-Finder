# LRC Bulk Finder v2.9.3 — Unicode Search Stability, Greek Vocabulary & Presets

This is a focused maintenance and vocabulary release. It fixes **two real errors
reported from the Windows v2.9.2 standalone EXE** and brings the expanded
Greek source-linked dictionaries and international presets into the actual
Windows standalone package.

## Fix 1 — Unicode filenames no longer crash long searches

The user's 5,150-song run stopped after track 15 with:
`PROFILE ERROR: 'charmap' codec can't encode character '\\u2010'`.
The worker now configures UTF-8 output before printing filenames and search
progress; the GUI also explicitly requests UTF-8 for the child worker. Windows
CP1252 cannot encode the Unicode hyphen U+2010, but UTF-8 can. All 5,135
unfinished songs are **incomplete due to the crash, not proven lyrics misses**.
Previously saved verified lyrics and review candidates stay where they were.

## Fix 2 — No unsupported Local AI preset in standalone

The standalone EXE does **not** bundle the external G2G transformer model or
Python dependencies. It now hides/disables the Local AI preset, toggle and
installer button. Old saved profiles that request Local AI transparently
continue with conservative Greek dictionary matching. The worker also
handles independently launched old saved AI profiles without editing
`profiles.json`. The full Python build can still use an separately installed
compatible G2G model.

## Named preset consistency and better failure reporting

If a named built-in preset, such as `International FAST — 20 Songs`, has been
saved with different action/scope settings (e.g. Offline First and ALL),
Control Center asks whether to restore the actual built-in settings, or
cancel and save custom settings under a different name. Worker failures are
labelled as failures, not as successful completion.

## More Greek vocabulary

- **730** Greek singer aliases, including 113 owner-approved, source-audited.
- **92** additional *unverified* word suggestions from 105 Greek Wikipedia
  song-title pages across 15 categories. These are words from **titles only**,
  never copyrighted full lyrics. Romanizations are conservative and
  may require review; preexisting curated spellings always take precedence.
- New `Greek_Words_Wikipedia.csv` and independently built
  `Greek_Lexicon.sqlite3` are shipped with the standalone application.

## Better preset list

**15 presets**, all Greek grouped together, followed by international/foreign
options; broadest provider coverage before lighter/faster/smaller scans. The
six old preset names remain compatible. All new GUI entries have English and
Greek descriptions.

## QA and release discipline

Four-cell Windows/Linux Python 3.10/3.13 regression matrix, frozen two-EXE
smoke, Windows title and Unicode tests, 10k-file search/STOP protections,
PDF manual verification, two inspected ZIPs and independent published SHA256
verification are release gates. Source music/ID3/existing LRC are not changed
by upgrades; candidate lyrics remain unverified until reviewed. A successful
CI scan cannot guarantee external provider availability, user PC playback or
private collection performance. SignPath signing remains pending until verified.

## How to upgrade

1. Close the old app. Extract the **entire** new v2.9.3 standalone ZIP into a
   separate folder. Keep both EXEs, CSVs and SQLite together.
2. Run `LAUNCH_LRC_BULK_FINDER_WINDOWS.cmd` (or
   `LRC_Control_Center.exe`), never the worker directly.
3. Select your music folder and optional LRCLIB database. For a foreign test,
   **Apply preset** `International FAST — 20 Songs`, then start the search.
4. If you formerly stored that built-in name with custom all-song settings,
   choose to restore the built-in values, or save your custom configuration
   under a different name. All existing lyric files and MP3s are preserved.
