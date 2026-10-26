# LRC Bulk Finder v3 Stage 1 — Alpha 3 (STOP reliability fix)

This is an **alpha test** built from the Stage 1 Candidate Review comparison
and the alpha 2 LRCLIB wall-clock latency hotfix. Engine label remains v2.9.9
until v3 features are accepted. Existing v2.9.9, alpha 1 and alpha 2
downloads are NOT replaced.

## What changed
- STOP no longer depends on the log pipe reaching EOF to show the worker
  has exited. A descendant can inherit stdout and keep the reader thread
  blocked even after the worker process is already gone.
- The Control Center directly polls the worker exit after STOP and finalizes
  the search exactly once even when there is no final "ended" log message.
- A late log line or late ended event from the previous search cannot finish
  a newly launched one.
- STOP writes its existing cooperative cancellation marker immediately,
  before the existing process-tree kill.
- After STOP, candidate discovery runs on a background thread to avoid
  freezing the Control Center on libraries with thousands of files.
- Keep the marker in place until tree-kill verification has completed.
- Prevent a new search from starting before child-process termination is
  checked; show retry STOP if force-kill fails.
- LRCLIB 30-second budget and prior timeout/503/429 rules retained.

## What to test (on a COPY of music)
1. Extract alpha3 ZIP to a NEW directory. Do not overwrite alpha2 or v2.9.9.
2. Run LRC_Control_Center.exe (not Worker.exe).
3. Start Quick Search with 20 songs and provider recovery waits disabled.
4. While the first provider is still searching, press "STOP SEARCH".
   Confirm once. The worker should disappear quickly; Control Center
   should remain responsive and show the stopped status, without waiting
   ten minutes or requiring log EOF.
5. Start a fresh Quick Search after STOP has completed; old log output
   must not overwrite the new run's status.
6. Repeat STOP during preflight discovery, mid-song, and on a 503/slow source.
7. Open Candidate Review; it should populate without freezing the UI.
8. Verify MP3, ID3 and preexisting LRC hashes on your COPY remain unchanged.
   Interrupted in-progress candidate/report data may need to be rechecked.

If STOP itself cannot terminate a Windows worker, the GUI must report this
and offer RETRY STOP, rather than incorrectly claiming the child tree stopped.

Note: Hard-stopping a write is not a guarantee of perfect report/checkpoint
consistency. The existing exclusive LRC/no-overwrite code remains intact,
but review partially completed files before using them.

Do not post private MP3s or unredacted personal folder paths in a public issue.
