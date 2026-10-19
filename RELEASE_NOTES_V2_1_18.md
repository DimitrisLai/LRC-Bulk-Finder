# LRC Bulk Finder v2.1.18 — Expanded Greeklish Lexicon

Public Beta · Created by Dimitris L.

## Additions

- Added **950 public, accent-aware Greeklish spelling variants** in `Greek_Words_Expanded.csv`; together with the original editable CSV, there are over 1,000 unique entries.
- Added `BUILD_GREEK_LEXICON_DB.py` and bundled `Greek_Lexicon.sqlite3`, a small reproducible read-only SQLite vocabulary separate from the huge LRCLIB lyrics database.
- The SQLite database contains **only standalone word spellings**, not private song listings, folder paths, or ID3 data.
- The program validates the database signature, schema, and CSV source fingerprints. If absent, corrupt, or out of date after edits, CSV fallback continues safely.
- The pre-existing `Greek_Words.csv` and personal `Greek_Aliases.csv` take priority over generic entries. Original title, artist, and recording labels are preserved.
- Tests cover database construction, cross-platform Windows file locks, fallback, user overrides and common Greeklish examples.

## Why word mappings are not enough for every song

Whole-title context matters: `kaneis` can mean `κάνεις` or `κανείς`, `ton` can mean `τον` or `των`, `pote` can mean `ποτέ` or `πότε`. No single unconditional word replacement solves all contexts. Add reviewed whole-title aliases privately for such examples.

## Unchanged

- Option 2: the `[00:00.00] candidate` marker, offline bulk promotion and alternative rotation.
- Strict version, artist, title and length verification for auto-approved lyrics.
- No MP3/audio/ID3 editing, and no overwriting existing LRC files.
- Huge external LRCLIB SQLite snapshots are never bundled or duplicated.
- v2.1.15, v2.1.16 and v2.1.17 releases remain separately available.

## Usage

Extract the Windows ZIP, optionally reconnect your LRCLIB database, run `START_HERE.cmd`, choose Greek mode, and begin with the 20-song preview. Review the preview CSV before a large unattended run. To rebuild your small Greek dictionary database after adding words, run `python BUILD_GREEK_LEXICON_DB.py`.
