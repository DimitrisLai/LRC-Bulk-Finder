# LRC Bulk Finder — STOP reliability and LRCLIB audit (Alpha 4)

This is a separate Windows **prerelease**, based on Alpha 3 commit
`f284a71c7cf81f3dfd112ac49305078422f03a80`. The engine remains 2.9.9 for
compatibility; the Control Center header identifies this Alpha 4 test.
Stable main and every previous release are unchanged.

## 1. Exactly what changed

- An exited parent no longer proves that STOP succeeded. Until the observed
  tree is independently verified, the GUI shows verification in progress.
  Failed verification shows **STOP NOT VERIFIED**, retains the cancellation
  marker, offers **RETRY STOP**, and blocks another search or normal app close.
  Existing search-busy guards also keep benchmarks, setup and candidate
  promotion/recycling blocked until shutdown is verified.
- RETRY STOP works after the parent has exited. The original observed child
  identities are retained. Windows retries use pinned process handles with
  matching creation times; they never target a reused child PID by number.
- Capture the tree on the background STOP thread **before** writing the
  cooperative marker. Otherwise a fast cooperative exit could erase its
  ownership relationships before discovery. Hard termination follows directly.
- STOP also responds if the parent already exited before the click but its
  stdout reader is still waiting. It must not silently do nothing or allow a
  second worker. If the original tree was never observed, the result is
  explicitly unverified; it never claims unknown descendants were killed.
- Ignore stale STOP results and reader errors from previous workers. Bind each
  reader to the process passed at launch. STOP-thread errors always return a
  failure result. Queued progress cannot replace the stopping/error status.
- Reduce each fallback CIM snapshot timeout from 9 to 3 seconds. Native
  Toolhelp remains preferred. Unavailable snapshots are never treated as success.
- LRCLIB request pacing cannot sleep beyond the active online budget or send
  before its required gap. Insufficient budget becomes incomplete catch-up
  work, **not NO_MATCH or a timeout-only retry**. No rate limit is bypassed.
- Reject responses completed after the deadline. All keyword requests and
  optional exact fallback share the 30-second **online** budget. Read-only local
  SQLite work occurs before that budget starts and remains usable if online
  LRCLIB is disabled. An active deadline is restored on every provider exit.
- Preserve the first stalled/budget-exhausted LRCLIB song in the manual
  catch-up CSV as well as later skipped songs. Previously that first error
  could be omitted. Genuine completed NO_MATCH remains excluded.
- Provider Health recognizes both hard-stall and exhausted-budget states
  immediately as online disabled, without implying a verified lyrics match.
- Add regression tests demonstrating eight Alpha 3 gaps, plus tests for retained
  child ownership/retry. Add explicit offline QA hooks for frozen GUI/worker
  tests; ordinary launches do not run them or create their synthetic fixtures.
- Preserve existing search presets, providers, Greek/Greeklish variants,
  history/retry/429/503 rules, Candidate Review, Studio, karaoke, light/dark,
  language settings and conservative file-writing behavior.

No search/review change writes audio or ID3, overwrites existing LRC, promotes
candidates automatically, or discards alternatives. Hard-stop can interrupt an
in-progress **new** sidecar/report; completed files are retained. Review the
latest interrupted outputs before relying on them.

## 2. Exactly what to test on Windows

1. Keep earlier installations. Extract the complete new ZIP into a **new empty
   folder**. Open `LRC_Control_Center.exe`; check the **Alpha 4** header.
2. Use a **COPY** of about 20 songs, including Greek/Unicode filenames and some
   preexisting LRC/candidates. Record hashes of the originals first if possible.
3. Load the same saved Quick Search/FAST profile. Keep recovery wait **No**.
   Disable exact-signature fallback initially; repeat with it enabled later.
4. **Highest priority:** while LRCLIB is running, click **STOP SEARCH**, confirm,
   and time both worker exit and final GUI status. Expect seconds on a healthy
   Windows PC. The GUI must remain usable and must not wait ten minutes.
5. An exited worker may briefly show **verifying child-process shutdown**. Only
   a successful tree check may show **verified stopped**. If verification fails,
   report the detail, use **RETRY STOP**, and confirm another search is blocked.
6. Restart after verified STOP; repeat during preflight and a later provider.
   Old logs must not change the new search's progress or end the new search.
7. Let one small run continue. A stalled online LRCLIB request must be bounded
   around its 30-second budget; other providers continue and incomplete LRCLIB
   work remains available for catch-up. A prompt 503 may finish sooner, obey
   Retry-After/cooldown and must not be described as a completed NO_MATCH.
8. Open the existing Candidate Review and read-only A/B comparison. Check
   grouping, original promotion/recycle controls, language, theme and your DPI.
   Playback in the comparison window is **not implemented in this stage**.
9. Compare original audio/ID3 and preexisting LRC/candidate hashes. They must be
   unchanged. Send only a short **redacted** log/screenshot and measured STOP
   times; do not upload music, full paths, profiles or local LRCLIB snapshots.

## 3. Download and verification

The official distinct tag is `v3.0.0-alpha.4`. Its standalone asset is
`LRC_Bulk_Finder_v3_Alpha4_STOP_LRCLIB_Windows_Test.zip`, accompanied by `.sha256`.
Only use the link once that real asset and its successful build exist. Both
executables, original resources, license, test notes and `BUILD_INFO.json` are
included. The manifest records the exact tested source commit.

The dedicated workflow requires Windows/Ubuntu × Python 3.10/3.13 regressions,
Windows source tests, real SDL mixer smoke, both frozen EXE builds, frozen
worker CLI smoke, visible frozen GUI title, and a frozen GUI STOP smoke with
synthetic inherited-stdout parent/child/grandchild trees and 5,000 candidates.
It also checks hashes of every synthetic original, language/theme/scaling
initialization, ZIP integrity and checksum before publishing. Scaling smoke is
not visual certification of every layout or a real monitor DPI change.

The synthetic blocking workloads are not evidence of the exact network fault
on the owner's PC. Optional MusicBrainz, local database processing and other
providers do not share LRCLIB's 30-second online budget. One daemon LRCLIB I/O
thread may finish later after a hard deadline; the circuit prevents additional
online LRCLIB launches in that worker. STOP terminates the worker process.
Only **observed** descendants can be verified from snapshots; enumeration
failures remain visibly unverified.

## Next stage and acceptance gate

The engineering tests do not replace the owner's real Windows acceptance.
After the owner confirms fast STOP, correct status and unchanged originals,
continue in a separate branch/prerelease with Candidate Review 3.0 Stage 2:
one existing Lyrics Studio playback session/clock, two independently timed
read-only lyric panes, shared play/pause/stop/seek, deterministic fake-player
tests, teardown/Studio/karaoke ownership and real Windows audio smoke.
Persistent decisions and numbered-candidate installation are later milestones.
Do not merge stable main or publish v3 stable without the owner's acceptance.
