LRC BULK FINDER v2.9.2 — RESPONSIVE SEARCH PREFLIGHT

Correct Windows entry point:
  LAUNCH_LRC_BULK_FINDER_WINDOWS.cmd
or
  LRC_Control_Center.exe

Do NOT open LRC_Bulk_Finder_Worker.exe manually. It requires a profile from Control Center.

1. Extract the ENTIRE standalone Windows ZIP into a new directory.
2. Keep both EXEs and supporting files together.
3. Quick Search > music folder > Greek / Greeklish ON > Test 20 songs.
4. Live Progress now shows Discovery (files), Indexing (SQLite), and Preflight (metadata).
5. A test limit of 20 is applied BEFORE reading all song ID3 tags; LIVE-tag songs do not use up slots.
6. Counters for saved lyrics stay at zero until an actual provider result arrives, as expected.
7. STOP remains supported during discovery, indexing and metadata preflight.
8. For offline-first action 5, a previously configured local LRCLIB .sqlite3 file is needed.
9. For Quick Search action 1, neither the local G2G AI model nor a SQLite snapshot is required.
10. Three privately supplied genuine Greek MP3s were checked, with unchanged source hashes;
    no music data is uploaded or bundled publicly.
11. Read the English/Greek PDF manuals and TEST_AUDIT_V2_9_2.md.
12. Windows binaries may show SmartScreen until independent code signing is approved.
