REVIEW CANDIDATES — v2.1.16
Created by Dimitris L.

After searching, uncertain synchronized lyrics are stored beside MP3s:
  Song.mp3
  Song.candidate.lrc
  Song.candidate.2.lrc
  Song.candidate.3.lrc

NEW OPTION 2 — BULK PROMOTE, BUT STILL UNVERIFIED
Select the folder, optionally include subfolders, and confirm the action.
Each valid first .candidate.lrc becomes Song.lrc with a first line:
  [00:00.00] candidate
The used candidate disappears, and numbered alternatives shift by one:
  .candidate.2.lrc -> .candidate.lrc
  .candidate.3.lrc -> .candidate.2.lrc, and so forth.

Listen while the song plays. If the lyrics are correct, manually remove
only the [00:00.00] candidate line. If wrong, delete Song.lrc and run
Option 2 again; the next .candidate.lrc is already ready.

Existing .lrc, MP3 audio and ID3 tags are never overwritten.
No online provider requests; invalid or untimed candidates are skipped.
Report: LRC_Candidate_Promotion_Report_v2_1_16.csv.
Partially completed alternative shifts are logged and need manual review.
Test on a small folder before mass promotion.
