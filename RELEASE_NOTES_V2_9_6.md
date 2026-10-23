# LRC Bulk Finder v2.9.6 — Cumulative Lyrics-Provider Packs

A maintenance release before v3.0: choose exactly how many online sources are searched, without losing existing FAST/FULL presets or user settings.

## Packs are cumulative, in the selected order

| Tier | Added at this tier | Total |
|---|---|---|
| 1 — CORE | LRCLIB, SyncLRC, Unison | 3 |
| 2 — CORE + LrcAPI | LrcAPI | 4 |
| 3 — BROAD | NetEase, Musixmatch, Megalobiz | 7 |
| 4 — EXTENDED | LiriQo, BetterKuGou | 9 |
| 5 — MAXIMUM | **New BetterQQ**, YouLyTTML, BetterTTML, Tencent | 13 |
| 6 — EXPERIMENTAL ALL | SimpMusic | 14 |

Each tier contains **all previous tiers**, in their original sequence. Existing six-source and other previous presets stay as before because old profiles default to **Legacy — FAST/FULL unchanged**. Tier selection does NOT change your action (offline first / online / offline only), song limit, Greek mode, or local AI. OFFLINE ONLY never contacts these internet sources. Some high-tier services are rate-limited, unauthorized or unavailable and may be skipped.

Tier 5 introduces **Better Lyrics QQ** at its documented public `/qq/getLyrics` endpoint (QRC XML). The safe converter extracts line start timestamps and removes word-level timing markup. QRC has no proven resolved recording metadata in the used response, so **QQ can only create review candidates**, not verified auto-saved LRCs. Even if lyrics look right, the same approved candidate review applies.

## Why the tiers were chosen: user diagnostics, October 23, 2026

The owner provided three local diagnostic files. **None contain or transfer the user's music or file paths to GitHub.** The performance summary CSV has zero totals throughout, while its associated JSONL contains **979** recorded attempts; the CSV must not be used as proof no providers were contacted.

The JSONL contains 139 attempts each for SyncLRC, Unison, YouLyTTML, LrcAPI, NetEase, Musixmatch and Megalobiz. It records **no verified installs** in those samples and just 1 review on SyncLRC. Recorded average attempt times: YouLyTTML ~10.9s, Unison ~9.1s, SyncLRC ~4.8s, NetEase ~4.3s, Musixmatch ~4.1s, Megalobiz ~3.9s and LrcAPI ~3.6s. LRCLIB recorded 3 errors, while BetterKuGou/BetterTTML/LiriQo had one error each. The HTTP CSV has 69 *local SQLite* LRCLIB lookups, not online HTTP evidence. Thus these results support **selection and caution**, not claiming a provider is globally down or removal without broader testing.

## User experience

In Saved searches, use the **Provider pack / cumulative tier** dropdown. The current source count and cautionary description appear below it. Select one of the tiers, save your profile and run a small **20-song test first**. Your previous settings remain unchanged until you deliberately choose a tier. For manual fine-tuning, CUSTOM order validates every name in the selected tier.

Greek/English labels describe the same stable tier keys. Searches report the selected source list and include the new QQ provider in provider health, full CSV reports and saved performance history. Existing source-specific Retry-After/backoff, restart protection, STOP and strict recording-duration/version verification remain.

## Limitations

Many sources expose only search-only text or incomplete metadata, and so will only produce human-review candidates. More sources **do not necessarily mean more verified LRCs**. Unison's long response time or TTML's access restrictions are reasons to move them into cautious choices, not unilaterally declare them dead. BetterQQ requires real-world acceptance on each user's network; experimental API availability can change. No external provider was load-tested during this release QA.
