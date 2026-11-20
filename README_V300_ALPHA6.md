# LRC Bulk Finder v3.0.0-alpha.6

Windows preview for Candidate Review and folder discovery. The window displays **Alpha 6**. The search engine uses version 2.9.9 for compatibility with existing profiles.

- Two separate album folders such as `Strasse` and `Straße` can each contain `Track.wav`. Preflight searches both tracks. Candidate Review gives each recording its own group and shows its folder. The same basename shared by two audio formats in one folder still triggers the existing collision check.
- The main Candidate Review preview now decodes older Greek Windows-1253 lyrics the same way as Lyrics Studio and A/B. Comparison calculates the duplicate fingerprint from the same bounded read used to display the lines.
- Reopening comparison after changing the music folder or **Include subfolders** loads candidates from the current selection.
- A search with zero matches stays on page **1/1**. Navigation buttons are enabled only when another page is available.

Extract the complete Windows ZIP into a fresh folder and start **LRC_Control_Center.exe**. Test with a copy of your music. The ordered Greek owner test list is in **CHECKLIST_ALPHA6_EL.md**. **CHECKLIST_ALPHA5.md** contains the detailed English startup and STOP checks.

Real-PC acceptance is pending for both startup and STOP. The next planned Candidate Review feature is read-only A/B playback with one shared audio clock. This build provides the existing timed-text A/B view.
