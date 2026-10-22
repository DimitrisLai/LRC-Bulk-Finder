# LRC Bulk Finder v2.9.1 — Windows Startup & Version Display Stability Patch

This is a narrowly scoped stability update for the full-day pre-v3.0 test. All Smart Library, Lyrics Studio, Karaoke Edition, provider safety, music and LRC no-overwrite guarantees from v2.9.0 are retained.

## Fixed
- **Actual version display:** v2.9.0 opened with its correct title, then its language-refresh code silently changed the title to v2.7.0. Title generation now uses the same single current-version constant as the update checker and is checked on GUI startup plus every English/Greek switch.
- **Honest update version:** a version constant inherited from older GUI utilities was stuck at v2.7.0 even though the engine was v2.9.0. All version sources now identify **v2.9.1** consistently.
- **Direct worker invocation:** double-clicking LRC_Bulk_Finder_Worker.exe is not a way to launch the application. It requires a selected profile sent by Control Center. The error now explicitly directs the user to LRC_Control_Center.exe while preserving command-line validation and return codes.
- **Friendlier Windows launch:** new `LAUNCH_LRC_BULK_FINDER_WINDOWS.cmd` included in the Windows standalone ZIP. Double-click it to start the GUI and get clear guidance if either EXE was not extracted.
- The actual packaged Windows GUI is now smoke-tested for its **visible window title**, not merely that its executable stays running. This closes the previous QA gap.

## How to start
1. Download **v2.9.1 Windows Standalone GUI ZIP**.
2. Extract the **entire** ZIP into one folder (don't run anything inside the compressed ZIP).
3. Double-click **LAUNCH_LRC_BULK_FINDER_WINDOWS.cmd** or **LRC_Control_Center.exe**. Both start the same graphical application.
4. Do NOT double-click **LRC_Bulk_Finder_Worker.exe**; it is an invisible-to-the-user search process controlled by the GUI and will print a profile-argument error when manually launched.
5. Confirm the GUI title shows `LRC Bulk Finder v2.9.1 — Control Center` in both English and Greek.

**No original audio, tags or lyrics are changed by these startup fixes.** The two Windows EXEs must remain together with the ZIP's supporting files. SignPath signing still requires external approval, and Windows SmartScreen may continue to warn.

The purpose of v2.9.1 is to provide a reliable build for the planned one-day acceptance trial before the final v3.0 release in 2026.
