LRC Bulk Finder v2.9.3 — Windows

1. Extract ALL files from the standalone ZIP into one folder. Do not run the
   EXE inside the ZIP. Keep LRC_Control_Center.exe, LRC_Bulk_Finder_Worker.exe,
   both Greek dictionaries, Greek_Words_Wikipedia.csv and Greek_Lexicon.sqlite3
   together.
2. Run LAUNCH_LRC_BULK_FINDER_WINDOWS.cmd or LRC_Control_Center.exe.
   Do not manually launch the Worker EXE; Control Center starts it correctly.
3. For your foreign collection, choose Ready-made preset →
   International FAST — 20 Songs and click Apply preset. Verify action 1,
   FAST providers and 20 songs. Save profile and START SEARCH.
4. Your old profile might have a built-in preset NAME while actually using
   different values. The app will offer to restore the named preset before
   starting, rather than silently scanning all songs. Use a different name
   if you wish to keep a custom profile.
5. Greek FULL presets work without local G2G AI. The standalone EXE does not
   include the external AI model, and the unsupported option is disabled.
   Offline first/only requires a working LRCLIB SQLite database.
6. Unicode filenames, including unusual hyphens, should no longer terminate
   search output. Incomplete songs can be retried; previous verified LRCs,
   existing LRCs, MP3s and ID3 tags are preserved.
7. Unverified .candidate.lrc lyrics need manual review; do not confuse them
   with a verified timed match. External providers can rate-limit or fail.
8. Always use the source folder backup / copied music for the full-day
   acceptance test before the major v3.0 milestone.
