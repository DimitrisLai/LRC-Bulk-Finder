# LRC Bulk Finder v3.0 — Stage 1 Windows Test (ALPHA)

This is a **preview build** from a feature branch. It is NOT the final/stable v3.0.
The original v2.9.9 search engine, UI version header and existing functions remain.
Extract the ENTIRE ZIP into a new directory. Keep your working v2.9.9 folder.

## What's new
- Open **Candidate Review** and click **Compare candidates side by side (v3 Stage 1 — read-only)**.
- Candidates are grouped by song inside their album folders, not by title alone.
- Search song/folder; browse 200 song groups per page.
- Select candidate A and B from the SAME song.
- Compare timed text, line counts, timing differences and exact duplicates.
- See available duration/timestamp warnings and an honest "Unknown source".
- Large, malformed, missing and symbolic-link candidate files show errors, not writes.
- No provider calls or audio uploads during review.

## Not yet included
Stage 1 has **NO synchronized audio playback** in the comparison window.
The same shared Lyrics Studio player will be integrated in Stage 2.
There is also no new candidate installation, preference history or AI feature.
Old v2.9.9 promotion and Recycle Bin actions still exist, separately, unchanged.

## What to test
1. Back up a small music folder, COPY it, and use only that copy.
2. Extract this ZIP into a NEW application folder (do not overwrite v2.9.9).
3. Run LRC_Control_Center.exe (never launch Worker.exe directly).
4. Choose the copied music folder and open Candidate Review.
5. Click the new Compare button. Find songs with 1/2/3+ candidates.
6. Change Candidate A/B; compare Greek, Greeklish and international files.
7. Search by filename/folder; test Next/Previous pages if you have many candidates.
8. Try a malformed LRC in the COPY: preview should show an error but never crash.
9. Verify original MP3s, normal LRCs and candidate sidecars are unchanged.
10. Close comparison, then confirm existing v2.9.9 search/Studio/Candidate Review still works.

**Only use the read-only comparison features for this test.** Existing promotion
and Recycle Bin buttons are separate actions and may change a copied folder.

Report the first error with a screenshot and whether you used English/Greek UI.
Do not post private music files, lyrics or absolute personal paths to GitHub.
