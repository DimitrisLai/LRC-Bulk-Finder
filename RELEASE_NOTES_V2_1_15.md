# v2.1.15 — Offline LRCLIB Folder Search (Public Beta)

**Created by Dimitris L.**

### Highlights
- **Option 4 — OFFLINE LRCLIB ONLY** scans any folder without a previous LRCLIB catch-up queue and without lyrics-provider HTTP requests.
- **CONNECT_EXISTING_LRCLIB_DATABASE.cmd** reuses an already extracted LRCLIB SQLite snapshot, with no copy or redownload.
- New dedicated offline-only result and review CSVs.
- Existing menu options 1 (SEARCH), 2 (PROMOTE) and 3 (CATCH-UP) preserved.
- Strict matching of artist, title, recording version and duration (within 3 seconds).

### Install
1. Extract the Windows ZIP.
2. If a local DB is already available, run `CONNECT_EXISTING_LRCLIB_DATABASE.cmd` and select its `.sqlite3` path.
3. Run `START_HERE.cmd`. Choose 4 for offline-only, or 1 for offline-first with online sources.
4. Start with 20 songs, then use A to scan all eligible MP3s.

### Assets expected for this release
- `LRC_Bulk_Finder_Public_v2_1_15_GitHub_Release_Windows.zip`
- `LRC_Bulk_Finder_v2_1_15_Complete_User_Manual_EN.pdf`

The gigantic LRCLIB database and any actual lyrics are NOT included. Windows 10/11 + Python 3.10+. External services can fail or be rate limited. **Public Beta**.

### Suggested repository topics
`lyrics`, `lrc`, `synchronized-lyrics`, `windows`, `python`, `music-library`, `lrclib`, `sqlite`, `offline-first`, `greeklish`, `mp3`, `command-line-tool`.
