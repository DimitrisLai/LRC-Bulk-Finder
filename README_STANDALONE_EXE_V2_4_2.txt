LRC BULK FINDER v2.4.2 - STANDALONE WINDOWS GUI
PUBLIC BETA - Created by Dimitris L.

Extract ALL files into ONE writable folder. Launch:
  LRC_Control_Center.exe     - graphical Control Center
  LRC_Bulk_Finder_Worker.exe - independent lyrics worker
Keep both files and the bundled Greek dictionaries/SQLite/contact resources
together. Standard search works without separately installed Python.

STOP SEARCH - KEEP APP OPEN
  One click + confirmation IMMEDIATELY kills the SEARCH WORKER TREE only,
  not the graphical Control Center. There is no delay or second Force Stop.
  The current song and not-yet-written final reports may be lost.
  Previously completed, synced JSONL checkpoints remain for resume.

LIVE COUNTERS:
  Current stage: Songs / LRC found, Songs / Candidate found, Not found.
  ALL stages: LRC Count, Candidate Count.
  After each round the first 3 reset; the last 2 stay cumulative.
  Two or three candidate files for the SAME song count as ONE candidate
  song. Only actually saved candidate sidecars count in the totals.
  Stage errors/timeouts are not counted as confirmed NOT FOUND.

Other v2.4 features: built-in Greek/Night/Offline presets, hover help,
LRCLIB database downloader, incremental metadata library, MP3/FLAC/M4A/
MP4/OGG/OPUS/WAV support and experimental, UNVERIFIED Sync Lab.

The heavyweight optional Greek G2G AI model is NOT embedded.
Use the complete Python/CMD ZIP if you want the separate local AI model.

Standalone community EXEs are UNSIGNED; Windows SmartScreen may warn.
Check the original official release and SHA-256 before executing.
https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/tag/v2.4.2
