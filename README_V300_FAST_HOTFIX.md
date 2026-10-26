# LRC Bulk Finder v3.0 Stage 1 Alpha 2 — Quick Search LRCLIB latency fix

This hotfix includes the read-only Candidate Review Stage 1 comparison from
v3.0-alpha.1 PLUS a repair for severe LRCLIB first-track waits. It remains a
separate **alpha test build**, with engine version 2.9.9 for compatibility.
The stable v2.9.9 and earlier alpha assets are never modified.

## Change
- LRCLIB gets a **30-second maximum wall-clock budget per song**, across its
  up-to-two search requests and optional exact-signature fallback.
- This catches a server or proxy that keeps sending tiny amounts of data or
  stalls during connection setup, which evades ordinary 10-second socket timeouts.
- If exceeded, mark LRCLIB as UNRESPONSIVE_DISABLED and skip **only online
  LRCLIB** for remaining tracks in the current run. Don't mistake this for
  NO_MATCH, don't add it to timeout-only retry rounds, and keep LRCLIB catch-up
  status incomplete.
- Other online providers keep running. Local LRCLIB SQLite searches remain
  available and are not subject to the remote HTTP circuit.
- A regular HTTP 503 still follows the previous 503 recovery policy; HTTP
  429 still follows the previous persisted cooldown policy.

## Windows test
1. Keep v2.9.9 and alpha.1. Extract alpha.2 into its own new folder.
2. On a COPY of a 20-song test folder, launch LRC_Control_Center.exe.
3. Run the same Quick Search profile (FAST, no recovery waits). Keep the
   20-song limit; initially disable optional exact LRCLIB fallback to reduce
   extra network calls, then test with it separately.
4. Watch LRCLIB duration on first track. It must not spend ~400 seconds.
   It should either respond normally, show 503 quickly or be cut off at
   about 30 seconds of combined LRCLIB activity on that song.
5. If budget expires, confirm the next song skips online LRCLIB immediately
   while SyncLRC, NetEase, Unison and LrcAPI continue.
6. Check LRCLIB is NOT marked a confirmed NO_MATCH when it was interrupted;
   verify any incomplete queue still captures it for later catch-up.
7. Confirm all preexisting music, tags and LRC sidecars remain unchanged.
8. Verify Candidate Review Stage 1 read-only A/B comparison still opens.

Never test new write/promotion/recycling actions on original music before
acceptance on copies. No private MP3, lyrics or diagnostic paths are uploaded.

Technical note: on deadline, one daemon network thread may finish in the
background later but only the main thread records provider outcomes. The
online LRCLIB circuit prevents spawning additional threads for this run.

If LRCLIB reports a normal quick 503 rather than stalling, the hard deadline
may not activate, which is expected. It doesn't bypass Retry-After or rate limits.
