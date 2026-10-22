# LRC Bulk Finder v2.8.0 — Karaoke Edition (English / Ελληνικά Public Beta)

A major usability release built on the protected v2.7.0 Lyrics Studio. Search, strict matching, provider rate-limit handling, STOP, Library Manager safe undo, bilingual original strings, audio/ID3 no-overwrite guarantees and original LRC protection remain unchanged.

## Karaoke Edition

- New fourth **nested** Sync Lab tab: Karaoke Edition. Eight top-level Control Center tabs remain unchanged.
- **Persistent operator playlist** with up to 500 local audio files. Add audio, select/open, double-click, pair any specifically selected LRC, rearrange, remove without deleting files, previous/next, and restore last opened song. Playlist and preferences save to the private APPDATA folder, not music folders.
- **Instrumental pairing**: if an exact same-stem LRC exists in the audio folder, prefer it. Otherwise, for explicitly instrumental/karaoke/backing-track/minus-one named recordings, try a normalized matching LRC. Refuse ambiguous matches and ignore *.candidate.lrc for automatic pairing. A different-name LRC can always be paired manually.
- **Native Windows drag and drop** when tkdnd/tkinterdnd2 initializes; standard Add/Pair file-picker fallback everywhere. Multiple audio files are supported, and one audio + one LRC in a drop can be explicitly paired. No audio outside user-selected paths is read for playback.
- **Projector-friendly audience window** separate from the operator workspace: clean current and optional next timed line; 4 color themes (Midnight, Black & Gold, Ocean and High Contrast), configurable font size, optional local PNG/JPG background, F11 fullscreen, Escape closes, Space plays/pauses, Left/Right moves to previous/next playlist song. A detected secondary monitor may be selected; if unavailable, manually drag the audience window. Window geometry remembered.
- **Global timed-lyric calibration** ±0.1 and ±1 second with ±30-second range. Positive offset delays lyrics. The normal calibration only affects preview, not data. Explicit **Apply offset to ALL timestamps** makes an undoable in-memory Studio edit; actual Save still creates a NEW numbered UNVERIFIED candidate, never an original or previously saved file.
- **0/3/5/10-second countdown** option before playback; canceled when karaoke closes. Track-specific A–B loop markers are preserved in the app's private settings folder.
- **Read-only export preview** for your chosen UTF-8, precision or BOM profile; it validates and shows LRC content without writing anything. All actual exports still require confirmation and exclusive file creation.
- Continues v2.7 bounded-memory read-only waveform, sync warnings, recovery drafts, optional native VLC playback speed, keyboard time nudges and protected versioned exports.

## Safety, dependency and compatibility

- The app does not separate vocals, transcribe lyrics, automatically upload music, synchronize words, convert every codec or certify inaccurate lines.
- Drag-and-drop requires tkinterdnd2/tkdnd native extension and depends on the OS; optional secondary screen detection uses screeninfo; local photo backgrounds use Pillow. The packaged Windows EXE includes Python-side modules and native packaged dependencies, but some third-party Windows configurations may still need file-dialog/manual-move fallback.
- 0.75x and 1.25x still require compatible **separately installed** native VLC; the portable EXE bundles a python-vlc binding but not VLC.
- Music, tags, primary LRC, earlier candidate files and session reports are not modified by the new karaoke features. All sessions and custom settings are local to the user profile.
- Real audio/display/car-radio testing on the final user's hardware remains necessary. SignPath code signing is still awaiting independent approval; SmartScreen warnings may appear.

## Quality gates

Full offline regression matrix on Windows and Ubuntu Python 3.10/3.13, UI tests including Greek lyrics and projector/playlist journeys, original SHA256 protection, 10k-track inventory test, real pygame WAV smoke, repeated STOP, frozen GUI+worker test, bilingual PDF generation and independent ZIP + published SHA256 checks. See TEST_AUDIT_V2_8_0.md.

[Source](https://github.com/DimitrisLai/LRC-Bulk-Finder) · [Changelog](https://github.com/DimitrisLai/LRC-Bulk-Finder/blob/main/CHANGELOG.md) · [Issues](https://github.com/DimitrisLai/LRC-Bulk-Finder/issues)
