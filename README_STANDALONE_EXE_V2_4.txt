LRC BULK FINDER v2.4.0 — OPTIONAL STANDALONE WINDOWS GUI
PUBLIC BETA — Dimitris L.

Extract BOTH .EXE files and all supplied CSV/SQLite/config resources into
one writable folder, then double-click LRC_Control_Center.exe.
  LRC_Control_Center.exe      — native Windows GUI, presets, help, Sync Lab
  LRC_Bulk_Finder_Worker.exe — profile runner and LRCLIB database downloader

You do NOT need to install Python for the standalone app's core features.

BUILT-IN PRESETS
  Greek FULL Offline First, Greek Night Search Maximum Coverage,
  Greek Quick Test 20, Greek OFFLINE ONLY, Greek Local AI FULL
  (UNAVAILABLE in the standalone EXE), and International FAST 20.

BUTTONS
  LRCLIB Download opens an explicit, consent-based downloader in a
  separate worker console. It will request the storage location before
  downloading a potentially very large official SQLite database dump.
  Greek local transformer AI is NOT bundled with the frozen executable.
  Download and use the complete Python/CMD ZIP for that optional model.

HOVER HELP describes each search setting. The new incremental index caches
metadata under LRC_Incremental_Library_v2_4.sqlite3 in the music folder.
SUPPORTED INPUT: MP3, FLAC, M4A, MP4, OGG, OPUS, WAV (metadata read only).
SAME-STEM cross-format files are skipped instead of overwriting the same LRC.

SYNC LAB is EXPERIMENTAL: import your own plain lyrics, estimate rough timing
or tap along to an external player, edit, then explicitly save ONLY a MARKED
[00:00.00] candidate .lrc sidecar. No true automatic transcription/alignment.
MP3/audio/metadata and approved .lrc are NEVER changed or overwritten.

Your existing large LRCLIB SQLite dump is NOT included, nor is the G2G AI
model; connect or download the database using the UI.

Unsigned community EXEs may warn in Windows SmartScreen. Verify SHA256
against official GitHub release and scan before deciding whether to run.
Do NOT disable Windows protection globally.

Official releases:
https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/tag/v2.4.0
