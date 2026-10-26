# LRC Bulk Finder — startup, performance and STOP recheck (Alpha 5)

Based on Alpha 4 source `7f4c7395831e1995265104b2366e9714aaf6fa09`.
This is a separate prerelease. Engine compatibility remains 2.9.9; the GUI
header identifies **Alpha 5**. No stable branch or older release is replaced.

## What changed

- **History is visible before any file read.** `PREFLIGHT HISTORY` reports a
  start, elapsed time, heartbeat and completion. The same applies to optional
  MusicBrainz caches, provider statistics and resume checkpoints. A separate
  `STARTUP COMPLETE` line reports setup/preflight time; round timers remain
  separate and include only their own round.
- **Bound optional cache reads.** A complete cache snapshot is accepted only
  within 10 seconds and 64 MiB. Oversize/timed-out reads discard their partial
  in-memory snapshot, preserve the original file and continue without reuse.
  Providers are then checked normally under the existing rate limits. Short
  malformed journal rows remain tolerated. Oversize individual records are
  rejected (1 MiB, or 4 MiB for checkpoint records). Nothing clears, compacts,
  truncates or replaces the owner's old history to make startup faster.
- **Faster, cancellable file discovery.** Native `scandir` checks extensions
  before fetching file attributes, reports entries/folders/audio counts and
  elapsed time, checks cancellation and preserves ordering, recursion and
  same-stem collision exclusion. Discovery has a 120-second ceiling; failure
  aborts the search rather than searching a partial library. The 20-song
  limit still bounds metadata parsing; collision-safe discovery must inspect
  filenames throughout the selected scope first.
- **Bound other direct HTTP response reads.** LRCLIB retains its existing
  shared 30-second online song budget. Other direct HTTP requests have a
  15-second total request budget, in addition to the existing socket timeout.
  A hard streaming stall disables that source for the current run, records
  incomplete coverage and does not create a socket-timeout retry. Optional
  MusicBrainz shows when a lookup starts and disables failing optional lookups
  after a hard stall/timeout/access denial; original artist/title searches
  continue. HTTP error response streams are closed without reading their body.
- **Cooperative cancellation in third-party search waits.** A library's client
  deadline is distinguished from a recorded socket timeout. It remains
  disabled for that run and is not automatically retried as a network timeout.
- **Truthful 503 reporting.** The third LRCLIB 503 now reports
  `HTTP_503_DISABLED`; it no longer claims the provider remains enabled after
  opening the circuit. Provider Health immediately shows the circuit state.
- **Candidate suffix correction.** Candidates 10–19, 100–199 and higher are
  recognized consistently by review, promotion listing and the creation-only
  undo journal. Canonical names start at 2; `.candidate.1` and leading-zero
  suffixes remain invalid. No candidate is installed, shifted or recycled by
  scanning or comparison.
- **GUI thread and STOP guards.** Background review refresh no longer checks
  the folder on Tk's thread. Manual refresh/initial comparison loading run in
  the background; obsolete scan results cannot replace newer inventory.
  Library Manager retry/undo also respect unresolved worker-tree shutdown.
- **Defensive metadata cache validation.** Invalid/future history timestamps,
  invalid MusicBrainz suggestions and invalid provider timing values cannot
  silently become trusted cache data or crash the final statistics export.

All existing profiles, provider selections, Greek/Greeklish matching, offline
LRCLIB, history/retry policy, candidate operations, Studio, precision tools,
karaoke, Smart Library, language/theme and audio/tag protections remain.

## What was rechecked

The audit covered the search engine and all provider routes; startup readers;
filesystem traversal; profile/worker launch and STOP; checkpoint/retry/cache
semantics; local SQLite access; candidate parsing/grouping/promotion/recycling;
creation-only undo; Studio/player/precision/karaoke; Smart Library exports;
language/theme and package contents. Static syntax/undefined-name checks cover
the production Python modules; the full offline regression suite is run on
Windows/Ubuntu and Python 3.10/3.13. This is not a claim that every possible
hardware, codec, external service or filesystem failure is reproducible in CI.

Windows build gates additionally require both frozen EXEs, normal worker/GUI
startup, real synthetic WAV playback, inherited-stdout parent/child/grandchild
STOP, **the actual frozen history and enumeration code paths with artificial
I/O delays**, a real default 10-second cache cutoff, original-fixture hashes,
and ZIP CRC/SHA256 verification. No user media or public provider traffic is
used for these tests. Scaling initialization is tested; visual layout and
actual monitor DPI still need owner acceptance.

## Windows download and one-by-one test

The uniquely tagged prerelease is `v3.0.0-alpha.5`. The verified standalone
asset is `LRC_Bulk_Finder_v3_Alpha5_Startup_STOP_Windows_Test.zip`, accompanied
by `.sha256`. `BUILD_INFO.json` identifies its exact source commit.

Follow **CHECKLIST_ALPHA5.md** inside the ZIP, in order, using a COPY of music.
Both `LRC_Control_Center.exe` and `LRC_Bulk_Finder_Worker.exe` must stay together.
If the existing database path was stored only in an older installation's
`LRCLIB_LOCAL_DB.txt`, select that same existing database once; do not download
another snapshot merely to test this build. Saved profiles are not reset.

## Known boundaries and next milestone

The owner's original ten-minute startup gap has no per-stage timestamps, so
its exact cause remains unproven. Alpha 5 removes silent/unbounded cache paths
and adds measurements to distinguish cache loading, discovery and metadata.
A broken or very slow filesystem may still fail; incomplete discovery is never
accepted as a complete scan. STOP reports unverified shutdown if ownership or
termination cannot be established, rather than pretending every child exited.

The 30-second LRCLIB budget covers online requests, not local SQLite processing
or optional metadata. Other direct requests are individually bounded, not a
single 15-second budget for an entire multi-query provider/song. Existing stage
counter reset behavior and persistent total counters are preserved.

Original audio/ID3 and existing LRC/candidates must remain unchanged except
for separately and explicitly approved existing promotion/recycle/undo actions.
A hard stop can interrupt a newly created sidecar/report; inspect the latest
partial output on the test copy. New completed sidecars remain available.

Owner startup/STOP acceptance is required before treating stability as closed.
After that, Candidate Review Stage 2 adds synchronized read-only A/B playback
using the existing Studio/Karaoke player and clock with explicit ownership.
Persistent decisions and safe numbered-candidate installation follow later.
Do not merge stable main or publish v3 stable without owner acceptance.
