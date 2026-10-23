# LRC Bulk Finder v2.9.5 — Modern Interface Refresh

This version changes the **appearance only**. It does not change the underlying lyric providers, matching rules, saved search profiles, G2G setup, the local LRCLIB database, audio/ID3 files or verified lyric-writing safety.

## What is new

- A clean, modern-looking Tkinter interface with more whitespace, Segoe UI typography, an attractive header, flatter buttons and better tab contrast.
- **Light and Dark modes**, selected from the top of Control Center. Changes apply immediately, without restarting the app or interrupting work.
- Choice is **saved per user**, together with the existing English/Greek language preference. Switching interface language never resets the theme.
- **Clear primary action** for Start Search, distinct red STOP button, larger metrics and redesigned status/tables.
- The long **Saved searches** screen is scrollable: setup and the Start Search button remain reachable even on smaller displays.
- Compatible with all eight original top-level tabs, all five nested Studio tabs, existing 15 presets, Greek G2G optional installation and both language options.
- Designed without heavyweight external UI frameworks or new web dependencies, so the standalone EXE can continue to ship normally.

## Safety and compatibility

- Original music, tags, existing LRCs, stored profiles and imported dictionaries are untouched.
- The theme preferences live in the standard `ui_settings.json` and use atomic writes. Unknown/broken values revert safely to Light.
- Automated QA covers light/dark contrast ratios, persistence, bilingual switching, selected-tab retention, search state and log preservation, plus the usual full Windows/Linux regression matrix.
- The two EXEs still operate separately: Control Center handles visuals; the frozen worker performs the unchanged search.

## Upgrade

Extract the entire v2.9.5 standalone ZIP into a fresh folder, keeping the prior v2.9.4 folder as backup. Start `LRC_Control_Center.exe`, then select **Appearance → Light / Dark** at the top-right. In the Greek interface, select **Εμφάνιση → Φωτεινό / Σκοτεινό**.

Users with lower-resolution screens can scroll the Saved searches form. Every control is still present and the bottom Start Search button is part of the scrollable form.

## Test caution

The refreshed visuals are verified with automatic GUI tests and frozen-EXE startup tests, but minor OS-specific cosmetic differences (Windows scaling, fonts, high contrast preferences) should still be checked on real hardware. The third-party Greek G2G model is separately installed only on request, and its first full download remains a hardware acceptance test independent of this appearance update.
