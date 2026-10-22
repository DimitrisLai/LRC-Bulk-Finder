# v2.9.2 — QA and real MP3 validation

User-reported slow startup: 3,183 tracks, Greek FULL offline first, 0 counters for five minutes. Root cause: unbounded metadata preflight before song limit, without detailed progress. Fix: filename-only discovery with status every 250, limit before ID3 metadata reads, LIVE-tag exclusion retained, cache only chosen music for test. Existing full-library Smart Library feature untouched.

Three private MP3 files inspected via Mutagen: Summer In Greece - Mazwnakhs Giwrgos (267.94 seconds, artist/title tags), H Gkeisa - Iwanna Koutalidou (258.20 seconds, artist/title tags), _ Aniko Se Mena - unknown artist (38.98 seconds, title tag but no artist tag). Original recordings are not committed to GitHub or distributed in release assets. Public tests use synthetic names and metadata only.

Required release gates: Windows and Linux Python 3.10/3.13, historical regression suite and 10,000-track performance, native Tk tests, real frozen EXE GUI title/STOP tests, both PDFs and all five public SHA256 checks. Live network providers and user Windows hardware must be independently rechecked.


## Final release verification, 22 October 2026

- PR #17 merged to main as \`bd6887413631ad7959b1f71e8735cd933f8cc3f7\`.
- **469** Windows regression tests successfully completed on the official release runner, plus **27** further adversarial Tk/GUI tests; four-platform Windows/Linux Python 3.10 and 3.13 tests all green. Test matrix: https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/runs/39855697401
- Native final Windows frozen GUI launch, GUI v2.9.2 title, standalone worker missing-profile user guidance, actual WAV playback original integrity and frozen child STOP with exit 130 passed. Two independent 10k-song stress paths exercised. New 3,183 synthetic candidate test checks only 23 metadata parses for 20 eligible songs when three are tagged LIVE.
- Windows Smart Library 10k SQLite read-only test observed 1.98 sec initial scan and 1.39 sec cached scan in the synthetic runner fixture; these are *not* user-drive performance promises.
- Standalone 15 items; complete source 234 items; updated English and Greek manuals.
- Public GitHub v2.9.2 release contains two ZIPs, two PDF manuals and one SHA-256 manifest. Official workflow **independently downloaded all five assets** and logged "PASS: all five official release assets match the published SHA256 manifest." https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/runs/39855697333
- Three user-uploaded copyrighted MP3 recordings were inspected only in the private working runtime with Mutagen, and original SHA-256 hashes remained identical. Music bytes were never placed in GitHub or a release. The third track's artist tag is missing; synthetic test data exercises this case.
- Physical user Windows launch, actual 3,183 music library indexing throughput, online provider success, monitor/audio devices and car-radio LRC support are still **NOT** certified by virtual CI.
