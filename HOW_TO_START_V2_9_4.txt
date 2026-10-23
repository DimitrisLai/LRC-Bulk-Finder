LRC Bulk Finder v2.9.4 — Windows one-click Greek AI

1. Extract the complete standalone v2.9.4 ZIP into a NEW folder. Keep both EXEs, g2g_sidecar.py, Greek dictionaries and local word SQLite together.
2. Run LRC_Control_Center.exe or the supplied launcher. In Saved searches → Downloads & local setup, click "Install / verify Greek G2G AI (one click)".
3. Read the confirmation carefully. The full G2G model is roughly 1.2 GB, with several more GB potentially required for Python, CPU PyTorch and other libraries. An internet connection and free disk space are necessary.
4. Approve once. Control Center will handle Python detection (and optional official winget Python 3.11 installation), create an isolated user environment, install Python dependencies, download the model and test Greeklish conversion. The setup window shows progress. Do not close the app or start a search until it finishes.
5. Only after "G2G READY" can you enable "Use installed local Greek AI" or apply "Greek Local AI — FULL". If setup fails, check its log and retry. Regular Greek dictionary searches do not depend on the AI.
6. The model is invoked as a persistent local CPU companion during searches. It does not need a powerful GPU, but initial load and inference may be slow, particularly on older PCs. Generated spellings remain unverified suggestions.
7. None of your MP3, tags or existing LRC files are edited by setup. For a full library search, start with 20 songs. Offline-first/only searches require a separate actual LRCLIB lyrics snapshot, NOT the optional small Greek word SQLite.
8. Use a different folder than v2.9.3 so you can roll back. Signing via SignPath is a separate process.
