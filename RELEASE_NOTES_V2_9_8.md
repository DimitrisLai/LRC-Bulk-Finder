# v2.9.8 — Candidate Review Workbench

A usability and safety-focused upgrade to the Candidate Review tab, without changing lyrics providers, search logic, scoring, tiers or AI features.

## New review table

- **Sortable columns**: Audio, candidate filename, primary/alternative kind, status, candidate number, folder. Click column heading to change sort and click again to reverse.
- **Filter by status**: All statuses, Primary eligible, Primary needs review, Alternative, Already has LRC or Missing/ambiguous audio.
- **Live text filter** by filename, directory and status.
- **Counters**: Total candidates, Primary (the current unnumbered candidate per audio), Alternatives (.candidate.2/.candidate.3/etc.), Eligible primary, and Blocked primary. A separate count shows visible and selected rows.
- **Multiple selection**: hold Ctrl/Shift or click Select visible / Select eligible primaries; Clear selection to start again. Preview shows the focused row.

## Confirmed bulk actions

- **Promote selected primaries** acts on eligible primary candidates in your selection; numbered alternatives and blocked rows are not directly promoted.
- **Promote ALL eligible primaries** operates on eligible primary candidates across the current chosen music folder, respecting the Include subfolders setting, not only the visible filter. Its confirmation states the exact number and shows representative filenames.
- Both actions require affirmative confirmation; no search or background benchmark can run simultaneously. Progress is shown while the work happens in a separate thread. **Stop batch** interrupts between candidate files.
- Each promotion reuses the conservative existing promotion engine: adds the visible **[00:00.00] candidate** marker; NEVER upgrades lyrics to verified; NEVER overwrites an existing .lrc; NEVER edits MP3/audio/ID3; numbered alternatives are advanced through the existing exclusive-write safety routine. Errors and partial writes are recorded in the final UI tally. A batch may finish partially if the user presses Stop or a filesystem operation fails.
- If the chosen audio filename is missing or ambiguous, or a verified/existing LRC already exists, the candidate is blocked. The user can filter and inspect these cases but cannot accidentally bulk promote them.

## Validation and upgrade

- Real disposable audio/sidecar fixtures test sorting, filtering, counts, multi-selection, explicit approval, cancellation, batch STOP, exclusion of numbered alternatives, existing-LRC protection, and preservation of original audio.
- v2.9.7 Provider Intelligence, six cumulative provider packs, Greek G2G setup and all 15 presets remain unchanged.
- Extract the complete standalone ZIP to a NEW folder and run LRC_Control_Center.exe. Keep v2.9.7 and v2.9.6 as backups. The original candidate sidecars are only changed by an explicitly confirmed promotion action.

**Note:** Promoted LRC files are NOT verified for timing correctness. Listen and review before using them as final synced lyrics.
