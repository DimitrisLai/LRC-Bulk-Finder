# v2.9.9 — Candidate Review progress and alternative disposal

Maintenance release after v2.9.8. No changes to lyrics source selection, verified lyric matching or G2G.

## Progress

Candidate Review displays a determinate 0–100% progress bar and processed / total counter. Both Promote selected primaries, Promote ALL eligible primaries, and Delete selected alternatives report live progress, including skipped/error files. Stop batch stops between files. A cancelled batch retains the actual completion percentage instead of showing 100%.

## Delete selected alternatives (Recycle Bin)

Select numbered alternatives (for example .candidate.2.lrc or .candidate.3.lrc) using Ctrl/Shift or Select visible alternatives. Click Delete selected alternatives (Recycle Bin), review the exact count and example filenames, and confirm. Only those specific numbered candidates are sent to the operating-system Recycle Bin or Trash via send2trash. Primary candidates, ordinary LRCs, audio, ID3, directories and out-of-scope/symlink files are never touched. If the Recycle Bin operation fails, the file is left in place: no permanent deletion fallback. Mixed selection skips nonalternatives.

Delete does not renumber remaining numbered alternatives; the original conservative promotion and candidate-shifting behavior is unchanged. The new Recycle Bin dependency is packaged with both Windows executables.

## Acceptance and safety

Automated tests use only disposable music fixtures and a mocked recycler. Validate first with copies of several alternative candidate files. Check the progress bar, inspect Windows Recycle Bin, restore one file, and confirm audio and original primary candidates remain unchanged. System policies may block recycling; those failures are reported rather than bypassed.
