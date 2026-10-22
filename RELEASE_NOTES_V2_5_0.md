# LRC Bulk Finder v2.5.0 — Library Manager (EN / Ελληνικά)

This is a major **Library Manager** usability update on top of the already-tested bilingual v2.4.5 application.

## What's new

**Selective retries:** In Results dashboard, select only the audio tracks without existing LRCs which need another attempt, then choose *Retry selected tracks*. A private, exact allowlist limits the engine to the chosen files (maximum 2500) using FULL online mode. Prior negative-result history is bypassed for this explicit request, and a dedicated checkpoint preserves the normal scan's resume history. If even one selected file moves, changes eligibility or gains an LRC, the job fails closed instead of silently scanning the whole folder. Provider cooldown rules remain unchanged.

**Why was this rejected?** See the original saved rejection reasons, candidate uncertainty and provider outcomes from the detailed per-song CSV reports. The screen explicitly identifies them as historical clues, not a claim of freshly checking a service or verifying the audio.

**Safe session undo:** Every v2.5.0 GUI search gets an independent, local per-session creation journal under the current user's APPDATA. Newly created .lrc and .candidate.lrc sidecars are journaled ONLY after exclusive creation, recording their path relative to the library, SHA256, size and modification timestamp. Undo previews the candidate count, asks for confirmation, revalidates each file, and deletes only unchanged, tracked sidecars from the selected library. Modified, pre-existing, untracked, missing, symlinked or mismatched files are skipped. **Original audio, ID3 tags, existing LRCs, archives and settings are never removed by undo.** Undo is irreversible; older v2.4.5 sessions were not journaled and cannot be undone.

**Bilingual Library Manager:** Additional English/Greek GUI labels complement all the previous owner-approved translations. Quick Search, status filtering, timing offset repair, diagnostics, update checker and strict provider matching are preserved.

## Downloads

- Standalone Windows GUI ZIP — `LRC_Bulk_Finder_v2_5_0_Standalone_Windows_GUI.zip` (recommended; no Python required).
- Complete Python/CMD ZIP — `LRC_Bulk_Finder_Public_v2_5_0_GitHub_Release_Windows.zip` (Python 3.10+).
- English complete manual PDF and Greek guide PDF.
- SHA256 checksum manifest.

Both languages are in the *same* standalone application. Extract the whole ZIP, keeping the GUI EXE and console worker EXE together.

## Important limits

- A present `.lrc` file does not prove accurate or verified timing.
- Last saved rejection reasons may be stale; unavailable providers are not the same as definitive "no lyrics exist".
- Session undo only covers journaled NEW files from v2.5.0 GUI searches, not old runs or manually created timing repairs. It never restores removed files.
- External lyrics providers can change or rate-limit requests; no automatic retries that ignore their restrictions.
- Windows EXEs remain unsigned while code signing is pending. Verify the official GitHub source and SHA256 before execution.

Previous public release: [v2.4.5](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/tag/v2.4.5)
Repo and issues: https://github.com/DimitrisLai/LRC-Bulk-Finder
