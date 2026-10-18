# LRC Bulk Finder v2.1.16 — Marked Candidate Promotion (Public Beta)

**Created by Dimitris L.**

## New in v2.1.16
- **Option 2** now bulk-installs each first synchronized `.candidate.lrc` as a playable `.lrc` beginning with exactly **`[00:00.00] candidate`**.
- Each successfully consumed candidate is removed; `.candidate.2.lrc` moves to `.candidate.lrc`, `.candidate.3.lrc` to `.candidate.2.lrc`, and so on.
- Listening review is easy: remove only the marker line when lyrics are correct; delete the entire `.lrc` and repeat Option 2 when the lyrics are wrong.
- Existing `.lrc` files and MP3 audio/ID3 are never overwritten, and the mode is entirely offline.
- New `LRC_Candidate_Promotion_Report_v2_1_16.csv` and expanded offline regression tests on Windows/Linux.

## Unchanged
Normal SEARCH and OFFLINE ONLY search still use strict artist/title/version/duration matching before automatically saving an unmarked `.lrc`. Option 3 still requires a previous catch-up queue. Existing external LRCLIB SQLite dumps are reused without copying.

## Getting started
Extract the Windows ZIP, run `START_HERE.cmd`, select **2** to work on candidates. Start with a test folder. The old v2.1.15 release remains separately available.

## Public Beta warning
Promoted lyric candidates can be wrong. The marker is a visible reminder to listen and verify them. Some media players may not render lyrics displayed at exactly 00:00.

**Software:** Windows 10/11; Python 3.10+. **License:** original code MIT, © 2026 Dimitris L.; other libraries/lyrics may have different rights.
