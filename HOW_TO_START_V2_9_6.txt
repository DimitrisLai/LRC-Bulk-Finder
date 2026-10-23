LRC Bulk Finder v2.9.6 — Windows cumulative provider tiers

1. Extract the FULL Windows Standalone ZIP to a new folder. Keep the v2.9.5 folder as backup.
2. Open LRC_Control_Center.exe > Saved searches.
3. Find 'Provider pack / cumulative tier'. Choose:
   Tier 1 CORE — LRCLIB, SyncLRC, Unison (3)
   Tier 2 CORE + LrcAPI — adds LrcAPI (4)
   Tier 3 BROAD — adds NetEase, Musixmatch, Megalobiz (7)
   Tier 4 EXTENDED — adds LiriQo, BetterKuGou (9)
   Tier 5 MAXIMUM — adds BetterQQ, YouLyTTML, BetterTTML, Tencent (13)
   Tier 6 EXPERIMENTAL — adds SimpMusic (14)
4. All tiers retain sources from lower tiers. Use Legacy to keep original FAST/FULL behavior (unchanged saved profiles and built-in presets).
5. Source pack does NOT change number of songs, search action or Greek mode. Test on 20 songs, then change limit to A if you wish.
6. BetterQQ QRC XML becomes a manually reviewable LRC candidate, never a verified automatic save: resolved song identity and duration are not supplied.
7. Provider order DEFAULT respects the tier sequence; SMART reorders according to locally recorded verified performance, while CUSTOM must include exactly the selected names.
8. OFFLINE ONLY does not contact online sources. High tiers can take longer; rate limits, timeouts and third-party unavailable status must be respected.
9. Existing MP3, ID3, saved and unverified LRC, SQLite and Greek AI configuration remain unchanged.
