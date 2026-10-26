# Alpha 5 — test one item at a time

Use a COPY of your music. Stop at the first failure and report its number.
Write seconds beside steps 5–8; a redacted short log is enough.

- [ ] **1. New installation.** Extract the entire ZIP into a new empty folder;
  keep old installations. Run `LRC_Control_Center.exe`. Confirm the header says
  **Alpha 5** and both EXEs are present.
- [ ] **2. Settings preserved.** Confirm saved profiles, language/theme and
  provider selection are still available. Select a COPY of the test collection.
  If needed, point to the same existing offline database; do not fetch a new one.
- [ ] **3. Same test profile.** Choose International FAST / 20 songs, recursive
  search, recovery wait **No**, history **Yes**. Keep the same provider order.
  Initially keep the optional LRCLIB exact fallback **No**.
- [ ] **4. Visible startup.** Immediately after the history answer, expect
  `PREFLIGHT HISTORY: started`, then completion or an explicit cache warning.
  Expect `PREFLIGHT ENUMERATION` before discovery finishes, with counts and
  elapsed time. There must be no unexplained ten-minute blank interval.
- [ ] **5. Record startup time.** Note history time ___ s; enumeration time
  ___ s; and `STARTUP COMPLETE` ___ s. A cache exceeding its limit must warn
  and remain preserved. Failed discovery must stop visibly, not search a
  partial collection or label it empty.
- [ ] **6. STOP during startup.** Start again and press STOP while history or
  enumeration is active. Confirm once. Record worker exit ___ s and verified
  stopped GUI status ___ s. The app should stay responsive. If too fast to
  catch, record "not caught"; do not artificially slow your real drive.
- [ ] **7. STOP during a provider.** Start again, press STOP while LRCLIB or
  another provider is active. Record ___ s. Only verified shutdown may show
  verified stopped. An unavailable tree check must show STOP NOT VERIFIED,
  block overlapping work and offer RETRY STOP.
- [ ] **8. Restart after STOP.** After verified shutdown, start a new 20-song
  run. Old logs/results must not end it or replace its progress. Record any
  restart delay ___ s. Library Manager retry/undo must remain blocked while
  shutdown is unresolved.
- [ ] **9. Let one run finish.** Check totals and new sidecars. HTTP 503/429
  must not create timeout retries. After LRCLIB's third 503, expect circuit
  open/disabled consistently, with incomplete songs retained for manual
  catch-up. Provider success and new lyric matches depend on service availability.
- [ ] **10. Candidate Review.** Refresh/open the read-only A/B comparison.
  Confirm loading is responsive, groups stay in their correct folders, and
  existing `.candidate.10.lrc` or higher alternatives appear if present.
  Do not rename/create candidates on your original collection for this test.
- [ ] **11. Appearance and existing tools.** Check English/Greek, Light/Dark
  and your normal display scaling. Open the Studio, precision, karaoke and
  Smart Library tools you normally use. Comparison playback is still pending.
- [ ] **12. Original-file check.** Confirm preexisting audio/tag bytes, LRCs
  and candidates on the COPY remain unchanged; newly created sidecars are
  expected. Keep original history/checkpoint files; ordinary new journal
  entries may be appended, but they must not be deleted/reset by startup.

Report: step number; PASS/FAIL; measured seconds; Alpha 5 header; and short
redacted error/startup lines. Do not send music, full private paths, database
dumps, or complete personal history files.
