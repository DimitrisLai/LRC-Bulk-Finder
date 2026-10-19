LRC BULK FINDER v2.4.1 - STANDALONE WINDOWS GUI (PUBLIC BETA)
Created by Dimitris L.

EXTRACT ALL FILES TOGETHER IN ONE WRITABLE FOLDER:
  LRC_Control_Center.exe       - Python-free Windows graphical interface
  LRC_Bulk_Finder_Worker.exe   - separate packaged worker for searches
  all CSV/SQLite resources     - dictionaries and LRCLIB contact template

DOUBLE-CLICK LRC_Control_Center.exe. No separate Python needed for the
standard search workflows. Heavy optional Greek G2G model is NOT bundled.

RELIABLE STOP
  Click Stop search safely, then confirm. New per-run stop marker works
  without Ctrl+Break and without sharing the worker's console.
  Temporary recovery delays exit quickly; an active bounded network
  request may need to finish before the worker saves reports.
  After 8s, if still running, confirmed Force STOP is offered.
  Force STOP may drop the current in-flight result/final report, but
  previously written per-song JSONL checkpoints remain and can resume.

FIVE COUNTERS
  Stage LRC found, Candidate and Not found RESET TO ZERO after each round.
  ALL stages LRC found and Candidate totals persist across these rounds.
  Timed out/server-errored requests are NOT counted as definite not found.
  Previously installed LRCs are not counted as newly saved in a new run.

BUILT-IN GREEK/NIGHT/OFFLINE PRESETS, MOUSEOVER HELP,
INCREMENTAL LIBRARY, SEVEN AUDIO FORMATS AND EXPERIMENTAL SYNC LAB
  All v2.4 features retained; see 30-page full PDF manual.
  LRCLIB database download is consent-based and separate from this ZIP.
  Greek local AI model still requires complete Python CMD package.
  NO original audio/metadata changes; NO automatic verified labels on
  experimental timing drafts. No audio fingerprint identification.

Community-built EXEs are UNSIGNED and may show Microsoft SmartScreen
Unknown publisher; verify official GitHub release SHA256 before running.
Official release: https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/tag/v2.4.1
