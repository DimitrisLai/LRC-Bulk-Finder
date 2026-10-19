# v2.3.0 Test Audit — Saved Profiles, GUI Safety & ETA

The v2.2 CI suite is retained unchanged and expanded with
`TEST_USER_EXPERIENCE_V2_3.py` (17 new portable tests):

- Atomic UTF-8 saved profiles and Unicode names.
- Corrupt preferences rejected without overwriting existing JSON.
- Unsafe action, invalid limits, non-Boolean flags and local AI mode validated.
- Custom provider permutations require all 5 FAST or 12 FULL routes exactly once.
- All scripted profile prompt responses verified in precise real CLI sequence,
  with Greek/English/offline variants and unknown-prompt fail-closed behavior.
- Existing local SQLite path can be provided without an unexpected prompt.
- Search profile runner restores monkeypatched input and chooser after errors.
- Candidate browser includes subfolders and numbered alternatives, ordered
  primary first. Preview never modifies candidate bytes.
- Unconfirmed and numbered candidate promotions are refused.
- Explicit marked candidate installation retains original MP3 and advances
  numbered candidates. Existing LRC files cannot be overwritten.
- Per-round ETA handles low samples, checkpoints, and zero/complete totals.
- GUI module imports without requiring an active desktop window.

Test environments: GitHub-hosted Windows and Ubuntu, Python 3.10 and 3.13.
CI uses `python -m unittest discover -p 'TEST_*.py' -v`.
All candidate safety checks are performed on disposable test fixture files;
no user audio tracks, IDs or downloaded local LRCLIB snapshots are uploaded.
