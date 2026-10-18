REVIEW CANDIDATES — v2.1.8
Created by Dimitris L.

Unverified synchronized lyrics go into the SAME FOLDER as the MP3:
  TheProdigy.mp3
  TheProdigy.candidate.lrc
  TheProdigy.candidate.2.lrc  (if a different candidate exists)

Approved lyrics still use TheProdigy.lrc. Never automatically replace them.
Candidate files are real LRC text with timestamps, but their artist, version
and timing may be WRONG. Opening a candidate file does not mean it is verified.

At START_HERE.cmd, choose:
  1 — SEARCH for lyrics (normal downloader, candidates saved beside MP3)
  2 — PROMOTE reviewed .candidate.lrc to .lrc across folder and subfolders

Mode 2 requires a final confirmation, skips songs with an existing .lrc,
checks that a matching MP3 exists and the candidate contains timed LRC,
then copies candidate to .lrc and removes the .candidate.lrc after success.
It does NOT promote .candidate.2.lrc or other alternates automatically.
It generates LRC_Candidate_Promotion_Report_v2_1_8.csv.

WARNING: A mass promotion can install lyrics for the WRONG VERSION!
Check the candidate files against your audio before approving.

Previous versions' LRC_Review_Only_v2_1_6 folder and random .candidate.txt
names are not automatically migrated by this menu. Keep the legacy CSV and
files for later mapping/import; do NOT just rename hashed files blindly.
