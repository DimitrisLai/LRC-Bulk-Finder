# v2.9.2 — QA and real MP3 validation

User-reported slow startup: 3,183 tracks, Greek FULL offline first, 0 counters for five minutes. Root cause: unbounded metadata preflight before song limit, without detailed progress. Fix: filename-only discovery with status every 250, limit before ID3 metadata reads, LIVE-tag exclusion retained, cache only chosen music for test. Existing full-library Smart Library feature untouched.

Three private MP3 files inspected via Mutagen: Summer In Greece - Mazwnakhs Giwrgos (267.94 seconds, artist/title tags), H Gkeisa - Iwanna Koutalidou (258.20 seconds, artist/title tags), _ Aniko Se Mena - unknown artist (38.98 seconds, title tag but no artist tag). Original recordings are not committed to GitHub or distributed in release assets. Public tests use synthetic names and metadata only.

Required release gates: Windows and Linux Python 3.10/3.13, historical regression suite and 10,000-track performance, native Tk tests, real frozen EXE GUI title/STOP tests, both PDFs and all five public SHA256 checks. Live network providers and user Windows hardware must be independently rechecked.
