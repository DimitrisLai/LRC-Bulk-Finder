# LRC Bulk Finder v2.4 — Regression/Integration Scope

The previous full v2.3 suite is preserved and expanded to cover:
- All six built-in editable presets, especially Greek Night / Greek Offline.
- Legacy profiles without an incremental toggle default safely to enabled.
- Seven audio extensions; same-stem multi-format collisions are skipped.
- SQLite index creation, metadata hits, file/sidecar changes, invalidation,
  and persistence across process restarts.
- Genuine WAV header with untagged Mutagen duration: no false zero.
- Experimental plain text cleanup, estimate/tap timestamp encoding, explicit
  UNVERIFIED marker, primary and numbered candidate sidecars, no overwrite.
- Incorrectly ordered/invalid edited timestamp lines cannot be installed.
- FLAC/OPUS candidate discovery, original audio and existing LRC protection.
- Windows GUI widget test for selecting Greek Night/Offline templates,
  verifying setup button launches separately and generating a candidate from
  a real WAV file.

Release packaging additionally verifies complete CMD/BAT Windows ZIP,
readable 29-page PDF manual, candidate and profile modules, and optional
Windows standalone GUI+worker smoke tests. Real third-party provider and
large private SQLite snapshot testing remains environment-dependent.
