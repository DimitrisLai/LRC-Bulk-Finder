LRC BULK FINDER v2.4.3 — START HERE
Created by Dimitris L. | Windows | Public Beta

Which package do I need?
- Standalone GUI ZIP: no Python installation for normal searches. Extract everything, keep both EXEs side by side, run LRC_Control_Center.exe.
- Complete Python/CMD ZIP: install Python 3.10+ if needed, extract everything, double-click OPEN_CONTROL_CENTER.cmd for the graphical Control Center or START_HERE.cmd for the classic five-option menu. Use this edition for optional local Greek AI.

YOUR FIRST SEARCH
1. Open Saved searches.
2. Choose the music folder. Select your existing large LRCLIB SQLite only if you already have it. Do NOT confuse it with the small Greek_Lexicon.sqlite3.
3. Without a large SQLite snapshot, choose Search action 1; with it, action 5 is offline-first, and action 4 is fully offline.
4. Choose 20 as Number of songs. Leave EXPERIMENTAL SimpMusic unchecked for the first run.
5. Save a named profile and click Save profile and START SEARCH.
6. Inspect new Song.lrc files, Song.candidate.lrc candidates, and the reports generated inside the music folder.
7. Open Candidate review for uncertain matches. Never approve an unknown remix/version blindly.

LIVE PROGRESS: Four counters reset with each stage (found, candidates, not found, skipped/no metadata); two cumulative totals remain (verified found, candidate found).
STOP is an immediate hard stop: completed checkpoints survive; unfinished song and final reports may not. Use Resume previous search once the earlier worker has stopped. If STOP NOT FULLY VERIFIED appears, check Windows Task Manager first.
PROVIDER HEALTH: Shows observed provider states, last successful HTTP responses, and actual verified sidecar writes. HTTP 200 does not prove a correct lyric.
MANUAL: LRC_Bulk_Finder_v2_4_3_Complete_User_Manual_EN.pdf (also separately available on GitHub).

Original audio/tags are read only; existing .lrc files are protected. The large LRCLIB SQLite database and optional heavy Greek AI model are not bundled in the program ZIP.
