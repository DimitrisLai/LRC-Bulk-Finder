"""Create release v2.9.7 English full manual and Greek guided manual; no web calls.
The English v2.4.3 manual is preserved page-for-page, with version references
updated and a new clearly separated v2.9.7 bilingual section appended.
"""
from pathlib import Path
from io import BytesIO
import os
import fitz
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether, Table, TableStyle
from reportlab.lib.utils import simpleSplit
from xml.sax.saxutils import escape

BASE = Path(__file__).resolve().parent
OUT = BASE / 'dist'
OUT.mkdir(parents=True, exist_ok=True)
OLD = BASE / 'docs/manuals/LRC_Bulk_Finder_v2.4.3_Complete_Step_by_Step_User_Manual_EN.pdf'
NAVY=colors.HexColor('#122641'); TEAL=colors.HexColor('#098E9C'); BLACK=colors.HexColor('#263950'); GRAY=colors.HexColor('#596A80')
font_candidates=[('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),('C:/Windows/Fonts/arial.ttf','C:/Windows/Fonts/arialbd.ttf')]
for normal,bold in font_candidates:
    if Path(normal).is_file() and Path(bold).is_file():
        pdfmetrics.registerFont(TTFont('ManualGreek', normal))
        pdfmetrics.registerFont(TTFont('ManualGreekBold',bold))
        pdfmetrics.registerFontFamily('ManualGreek',normal='ManualGreek',bold='ManualGreekBold',italic='ManualGreek',boldItalic='ManualGreekBold')
        break
else:
    raise RuntimeError('Greek-capable font required for manual build (DejaVu or Arial).')

H=ParagraphStyle('head',fontName='ManualGreekBold',fontSize=16,leading=22,textColor=NAVY,spaceBefore=18,spaceAfter=10,keepWithNext=1)
Sub=ParagraphStyle('sub',fontName='ManualGreekBold',fontSize=11,leading=16,textColor=TEAL,spaceBefore=12,spaceAfter=6,keepWithNext=1)
Body=ParagraphStyle('body',fontName='ManualGreek',fontSize=9.3,leading=15.0,textColor=BLACK,spaceAfter=9)
Bul=ParagraphStyle('bullet',parent=Body,leftIndent=15,firstLineIndent=-10,spaceAfter=5)
Small=ParagraphStyle('small',parent=Body,fontSize=8.2,leading=12.8,textColor=GRAY)
Cover=ParagraphStyle('cover',parent=Body,fontName='ManualGreekBold',fontSize=34,leading=43,textColor=NAVY,spaceAfter=14)
CoverSub=ParagraphStyle('coversub',parent=Body,fontSize=14,leading=22,textColor=TEAL)

def para(s, style=Body):
    return Paragraph(escape(s).replace('\n','<br/>'),style)

def make_pdf(path,title,subtitle,sections,lang):
    def footer(c,doc):
        c.saveState(); w,h=A4
        c.setStrokeColor(colors.HexColor('#DCE7EB'));c.line(46,43,w-46,43)
        c.setFont('ManualGreek',8);c.setFillColor(GRAY)
        c.drawString(46,28,f'LRC Bulk Finder v2.9.7  |  {lang}  |  Public Beta')
        c.drawRightString(w-46,28,str(doc.page))
        c.restoreState()
    doc=SimpleDocTemplate(str(path),pagesize=A4,topMargin=48,bottomMargin=58,leftMargin=48,rightMargin=48,allowSplitting=1,
                          title=f'LRC Bulk Finder v2.9.7 — {lang} User Manual',author='Dimitris L.')
    items=[Spacer(1,64),para('LRC BULK FINDER',Cover),para('v2.9.7  |  ENGLISH + ΕΛΛΗΝΙΚΑ',CoverSub),Spacer(1,19),para(title,H),para(subtitle,Body),Spacer(1,27),para('PUBLIC BETA  •  Windows  •  October 2026',Sub),para('Created by Dimitris L. — official open-source project, MIT License.',Small),Spacer(1,30),para('This guide covers the two-language graphical interface, ordinary searches, offline mode, candidate review, STOP/resume and data protection.',Small),PageBreak()]
    for heading,paras in sections:
        items.append(para(heading,H))
        for p in paras:
            if p.startswith('• '):items.append(para('– '+p[2:],Bul))
            elif p.startswith('## '):items.append(para(p[3:],Sub))
            else:items.append(para(p,Body))
    doc.build(items,onFirstPage=footer,onLaterPages=footer)

en_sections=[
('v2.9.7 — Correct Control Center launch on Windows',[
'IMPORTANT: The standalone release contains two EXEs. Run LAUNCH_LRC_BULK_FINDER_WINDOWS.cmd or LRC_Control_Center.exe. Both open the graphical interface. Do NOT double-click LRC_Bulk_Finder_Worker.exe: the Worker is a subordinate search process and requires --profile supplied automatically by Control Center.',
'Extract the ENTIRE Windows standalone ZIP to a folder first, keeping both EXEs and all accompanying files together. A manual run of the Worker reports that a search profile is missing; this is not a broken lyrics search and does not touch your music.',
'The previous v2.9.0 GUI could display v2.7.0 in its title because the language-refresh process reinserted a stale string. The fix ensures the visible title stays LRC Bulk Finder v2.9.7 — Control Center on startup and after switching English or Ελληνικά. A new Windows frozen-GUI title regression test is included.',
'Continue your full-day music-library and karaoke tests using the detailed v2.9.0 chapters in this guide. Signing from SignPath remains separately pending.'],
),

('v2.9.7 — Smart Library quality-control review queue',[
'Open Sync Lab (experimental) > Smart Library. The fifth inner tab scans your chosen folder to find missing primary lyrics, candidate-only tracks, ambiguous same-stem audio and questionable LRC timing. It never changes audio, ID3 tags, existing primary LRC or candidates. Scan/Incremental Refresh creates a private SQLite index in APPDATA/LRCBulkFinder/smart_library_v290.sqlite3 and reuses unchanged prior LRC evaluations by size and modification time.',
'Review warnings include duplicate timestamps, out-of-order lines, large gaps, suspicious early or late lyrics, unexpectedly large LRC offsets, encoding issues (Greek CP1253 or unsupported UTF-16), malformed timed-LRC syntax, empty/oversized sidecars and potential title-metadata mismatches. Some warnings are subjective; they DO NOT prove the track has incorrect lyrics. Optional Deep duration checks examine available audio metadata and warn if lyrics extend beyond known recording duration. This may take longer and some files have no reliable duration.',
'The results are paged 200 at a time with a search box and filters for All, Issues only, Missing LRC, Needs review, Has LRC and Ambiguous audio. Mark any selected song Bookmarked/Reviewed or clear the mark, without touching its files. Double-click or Open in Lyrics Studio to correct lines; Studio still asks before discarding edits and Save makes only a NEW, numbered, explicitly UNVERIFIED candidate.',
'Cancel during indexing rolls back the current SQLite transaction; your previous successful index remains. The app keeps a bounded scan history with counts, timing, and cached versus reaudited files. A filtered UTF-8 BOM CSV report is only created after user confirmation and never overwrites an existing report. Dangerous spreadsheet formula prefixes in music filenames/paths are neutralized in CSV cells.',
]),
('v2.9.7 — Stability update, performance and privacy',[
'Safety review focuses on provider STOP/resume, distinct worker/GUI processes, previous Library Manager undo, protected candidate export, karaoke instrumentals and playlist settings, Unicode/Greek paths, native drop registration, waveform cancellation and variable playback dependencies. Search providers, matching and rate-limit strategy are intentionally NOT rewritten in v2.9.',
'The new SQLite cache is local private metadata, not a copy of lyrics or recordings. It holds file paths, size/mtime fingerprints, problem classifications and optional review bookmarks. It does not upload filenames or LRC content. Do not treat cached equality as a cryptographic check: if file contents are altered without changing size and timestamp, use a fresh audit or remove the private cache after backing it up.',
'Large-collection scans remain bounded to 100,000 music files and do not follow symbolic links. They support safe cancellation and row pagination; scanning all filesystem entries still takes time even with an index. This version adds index speed to repeat quality checks, not an instant full drive scan or an automatic lyric repair engine.',
]),
('v2.9.7 — Full-day pre-v3.0 acceptance',[
'1. First extract the entire standalone ZIP, verify SHA-256, then start the Windows GUI and worker from the same directory.',
'2. Test Quick Search, saved profiles, read-only Results dashboard, provider health, candidate review, Review/Promote confirmation, and safe STOP/Resume on a COPY of a small music folder, including Greek and Greeklish names.',
'3. In Smart Library run an initial scan, then rerun unchanged (verify reused cached entries), change one LRC and rerun (only changed content should be inspected), review issue filters and Greek filename search, cancel a long scan, and generate/inspect an exclusive CSV report.',
'4. Open an LRC needing repair directly in Lyrics Studio, use Undo/Redo and nudge, review WAV/MP3 seek, A/B looping, personal draft recovery and save a NEW UNVERIFIED candidate; inspect original file SHA-256.',
'5. Test Karaoke Edition playlist, manual/safe auto lyric pairing, native Windows drag/drop, two-screen projector view, themes/Greek typography, fullscreen controls, global offset, countdown and optional VLC 0.75x/1.25x if separately installed.',
'6. Test Greek/English language switching, 100%–150% Windows scaling, offline operation, restarting the program, recoverable settings and source/document ZIP integrity.',
'7. Capture precise reproduction details in an issue or support report. A v2.9.7 fix release is appropriate only if your full-day trial uncovers actual defects, before beginning the v3.0 architecture.',
]),

('v2.9.7 — Karaoke Edition: operator playlist and clean audience display',[
'Open Sync Lab > Karaoke Edition. The fourth inner workspace provides a dedicated operator playlist and a separate audience lyric screen. Click Add audio files to choose up to 500 local songs, double-click any entry to open it in the established Lyrics Studio. The operator keeps playback controls; the audience sees only the lyrics on a canvas. F11 toggles fullscreen, Escape closes, Space plays/pauses and Left/Right navigate the playlist.',
'Tracks named Instrumental, Karaoke, Backing Track or Minus One may auto-pair with an exact base-name LRC in the same folder; exact audio-stem matching takes precedence. Candidate lyrics and ambiguous same-name alternatives are NEVER installed automatically. Use Pair selected LRC to assign a specific permitted LRC from another location. Audio files, metadata, original lyrics and search journals are read-only.',
'Playlist order can be moved up/down and entries removed without deleting actual files. The playlist, last opened track and display preferences are saved only as private JSON in APPDATA/LRCBulkFinder/karaoke_v280.json. Missing/moved tracks are skipped on reload; no audio automatically starts. Drag audio and LRC into the playlist if tkinterdnd2/tkdnd is available; otherwise the file pickers work. On Windows, the portable ZIP bundles the native drag-and-drop support.',
]),
('v2.9.7 — Projector modes, timing calibration and countdowns',[
'Choose the target audience screen from detected monitors; otherwise drag the floating audience window manually. You can persist window geometry, pick Midnight / Black & Gold / Ocean / High Contrast themes, change font size, hide the next line, and supply a small local PNG/JPEG background image. The image is read-only, with filesize and pixel limits; no images are uploaded.',
'Set a lyric offset between -30 and +30 seconds by 0.1 or 1.0 seconds. Positive values delay lyric display. Display-only calibration NEVER changes the LRC; Apply offset to ALL lyric timestamps requires explicit confirmation, modifies only the undoable in-memory Studio document, and the regular Save action still creates only a NEW marked UNVERIFIED candidate file. Preview export shows exact bytes represented as text but never writes anything.',
'Countdown 0/3/5/10 seconds is supported before playback. Closing the audience screen cancels any pending countdown, and switching songs does not automatically play another song. A–B points are remembered separately for each track and can be reset. The underlying audio engine supports the same codecs and VLC limitation documented for v2.7.',
]),
('v2.9.7 — Safe operations and practical checks',[
'Check a copied test library with Greek lyrics and common instrumentals. Confirm wrong-stem and ambiguous pairings are never guessed, candidate sidecars are never auto-selected as trusted LRC, and original audio/ID3/LRC checksums remain identical after practice.',
'Projector detection uses optional screeninfo; native file drag/drop uses optional tkinterdnd2 and Tcl/Tk tkdnd. Standard file picker and manual window move remain available when those optional integrations are not present. A custom local photo background uses Pillow.',
'Exported lyrics may require UTF-8 BOM or a two-decimal profile for some car radios. Check compatibility on the actual player. Karaoke timing is line-by-line and approximate, not automatic voice removal or word-by-word sync. The portable app is still Public Beta and Windows SmartScreen may warn until separately approved code signing is operational.',
]),

('v2.9.7 — Karaoke using your instrumental and LRC files',[
 'Choose Sync Lab (experimental) > Lyrics Studio. Open your own instrumental MP3/WAV/FLAC/OGG file. A same-name .lrc will load read-only if available; otherwise press Load LRC to choose any owned or licensed existing LRC (you can import a different-name lyric file). The Classic Sync Lab still assists with timing your own plain text.',
 'Select the Precision & Karaoke inner tab and press Open karaoke display. The large window displays the current timed lyric line and the next line against a dark background; press F11 for fullscreen, Escape to close. The music is controlled in Lyrics Studio. This is line-level karaoke, not per-word karaoke. No vocal extraction, transcription or automatic lyrics download is performed by the display.',
 'All original audio, ID3 and primary LRCs remain read-only; karaoke is playback plus visualization. Follow copyright rules for lyrics, instrumental recordings and public performance.',
]),
('v2.9.7 — A–B looping, read-only waveform and speed',[
 'For repeating a difficult section, play the audio, press A = current time at the beginning and B = current time at the end. B must be after A. Clear A–B to disable looping. Rewind 1 s and Rewind 5 s let you review entrances.',
 'Waveforms are generated from bounded read-only audio samples and never modify the original recording. PCM WAV is supported by the standard library. Compressed MP3/FLAC/OGG waveform display depends on the optional soundfile/libsndfile decoder. Use zoom 1x–8x, scroll for a later portion, and click within the waveform to seek. The sampled waveform is an overview, not an audio-grade spectrogram.',
 'The speed choices are 0.75x, 1.00x and 1.25x. The normal 1x engine is pygame. The non-1x option needs a compatible installed native 64-bit VLC player and the python-vlc binding. If VLC is unavailable or the codec rejects rate control, the app reports that limitation instead of pretending to play at the requested speed.',
]),
('v2.9.7 — Validation, recovery, shortcuts and export',[
 'Check all timestamp warnings after importing or adjusting lyrics: duplicate or out-of-order lines and timestamps beyond the audio duration block saving. Large gaps and very closely spaced lines are warnings for review, not proof of an error.',
 'The app autosaves private editing drafts under APPDATA/LRCBulkFinder/studio_drafts. It uses an audio file fingerprint and source LRC hash to reject stale recovery. A matching draft is restored only after a user confirmation; the draft never overwrites original music or lyrics.',
 'Use multiple-line selection and 0.01/0.05/0.10-second nudge sizes. Configure three distinct keyboard shortcuts for Stamp, Rewind and Forward; these only work when the lyric table has focus.',
 'Select an LRC export profile: Standard 2 decimals (UTF-8), Precise 3 decimals (UTF-8), or Car radio UTF-8 BOM (2 decimals). Click Save NEW UNVERIFIED candidate. The exclusive file create operation saves .candidate.lrc or a numbered .candidate.N.lrc, never an existing primary LRC. Device compatibility varies; verify in your own car radio.',
 'Open directly in Lyrics Studio from Results dashboard or Candidate review to avoid searching for files manually. Selected candidates load read-only; nothing is promoted without an explicit separate action.',
]),

('v2.9.7 — Lyrics Studio overview',[
 'Open Sync Lab (experimental), then choose the new Lyrics Studio inner tab. The original Classic Sync Lab remains available in its own inner tab. All eight main Control Center tabs remain accessible.',
 'Select a local MP3, WAV, OGG or FLAC. The built-in player uses pygame/SDL_mixer; file decoding and seeking depend on the local audio backend. For source use, install pygame separately. The Windows standalone package must bundle it.',
 'When a same-named .lrc exists, it is opened read-only. You may also use Load LRC to choose a file, or From Classic Sync Lab to import previously tapped/estimated lyrics. Audio, ID3 and existing lyrics are never modified by opening or editing.',
]),
('v2.9.7 — Player, preview and timing workflow',[
 '1. Choose audio. If the internal player reports an unsupported codec or audio-device error, switch to a supported track or open the music in your external player.',
 '2. Play, Pause, Stop, drag the seek bar or use the plus/minus five-second buttons. Play time is estimated for display: use your ears to confirm alignment, especially after seeking.',
 '3. The lyric table shows timestamps and text. The currently active line is highlighted. Double-click a line to seek to its beginning.',
 '4. Select one or more lines and nudge minus/plus 0.10s. For a single line, enter exact seconds or select a line and press Stamp selected at playback. Space in the focused lyric table also stamps and advances. Undo/Redo keep up to 100 editing states.',
 '5. If corrected timestamps become equal/out-of-order, resolve the validation message before saving. Automatic AI transcription and word-by-word karaoke timing are NOT part of version 2.6.',
]),
('v2.9.7 — Save candidate, preserve originals',[
 'Click Save NEW UNVERIFIED candidate and confirm. Studio exclusively creates a new .candidate.lrc or .candidate.N.lrc, even when a matching original primary .lrc exists. It never replaces an existing candidate, primary lyric file, audio or ID3 tag.',
 'The Studio save is a manual user action, not a search session. Library Manager session undo deliberately does not remove manually edited Studio candidates. Review the saved candidate before approval in Candidate review.',
 'Import supports standard timed LRC, UTF-8 and legacy Greek Windows-1253. The global LRC offset is applied to the displayed timing; other metadata or unsupported proprietary formatting is not guaranteed to round-trip.',
]),

('v2.9.7 — Library Manager overview',[
 'The Results dashboard now includes a Library Manager with three additional controls: Why was this rejected?, Retry selected tracks, and Undo last search session. Both English and Greek labels are included. The previous Quick Search, strict multi-provider matcher, manual candidate review and timing repair still work.',
 'Click Refresh results to inspect the library; use the status filter and filename search to narrow the table. Select one or more rows. Has LRC means that a sidecar file EXISTS; it does not mean the lyrics or timestamps have been independently verified.',
 'Historical rejection reasons come from the existing LRC_Finder_Report_v2_1_15.csv and LRC_Finder_Review_v2_1_15.csv reports. Some providers reject a recording because of title/version/duration mismatch; some have no matches, or are unavailable. The screen labels these records as historical, not a fresh provider lookup.',
]),
('v2.9.7 — Retry only selected tracks',[
 '1. In Results dashboard, refresh your music folder and filter Missing LRC or Needs review.',
 '2. Select one or more songs, up to 2500 at a time. Select only tracks without an existing primary .lrc and without ambiguous same-stem audio formats.',
 '3. Click Retry selected tracks. Read the confirmation carefully; it uses FULL online provider mode 1 and retries only the exact chosen tracks. It does not require a large offline LRCLIB database.',
 '4. This user-initiated retry ignores old definite NO_MATCH history and uses its own independent checkpoint. Provider rate limits still apply. If the track was deleted, moved, changed or gained an LRC before execution, selection validation fails closed rather than scanning the rest of the library.',
 '5. The previous default search profiles and original audio/ID3 files are not modified. Selected retries save a dedicated reusable profile name; you can still use all original advanced search modes.',
]),
('v2.9.7 — Rejection explanations',[
 'Select one song and choose Why was this rejected?. The right-hand details section shows the saved search status, provider outcomes, and candidate rejection notes from the existing detailed CSV reports.',
 'Rejection reasons may include wrong title/artist, different recording version, incompatible duration, missing metadata, server errors or provider rate limits. Only explanations actually present in saved reports are shown; if no report exists, the app explicitly says so.',
 'Reports may be stale after a later search or manual changes. These are historical clues, not a statement that a specific online service was checked just now.',
]),
('v2.9.7 — Safe session undo',[
 'Every search started from the GUI records a new private session under the current user APPDATA/LRCBulkFinder/manager_sessions. When the worker exclusively creates a new .lrc or .candidate.lrc, the session records its relative filename, byte count, exact modification timestamp and SHA256 hash. No original music or pre-existing lyrics are journaled.',
 'In Results dashboard click Undo last search session. The program shows an explicit confirmation before deleting. It re-checks each journaled file immediately before removal and SKIPS files that were edited, moved, replaced, removed, symlinked, or otherwise changed.',
 'Undo only removes unchanged new sidecar lyrics from the most recent eligible recorded session for this same selected library. It does NOT reverse modifications to audio/ID3, saved search profiles, cached metadata, archived reports, preferences, or manually-created timing repair candidates. Undo is permanent and cannot restore its removed files.',
 'Older releases v2.4.5 and before did NOT create this journal and cannot be safely undone by this function. The journal lives in local application settings; it is never uploaded.',
]),

('v2.9.7 — Beginner Quick Search',[
 '1. Open the new Quick Search tab. Choose a music folder, then select Test 20 songs or All songs.',
 '2. Select Include subfolders if required. Enable Greek/Greeklish matching if your collection contains Greek names. Press START QUICK SEARCH.',
 '3. This shortcut chooses action 1 (online), FAST providers and default provider order. It requires no downloaded LRCLIB SQLite snapshot. The advanced Saved searches tab remains fully available for offline-first scans and precise settings.',
 '4. Quick Search saves its settings as Quick Search v2.9.7 under your user account. Replacing those saved settings requires confirmation. It never changes original audio or ID3 tags.',
]),
('v2.9.7 — Results dashboard',[
 'The Results dashboard reads your chosen folder and, optionally, subfolders. Press Refresh results. This is a read-only inventory: no tags, music or LRC files are edited.',
 'Filter by Has LRC, Needs review, Missing LRC or Ambiguous audio. Search filenames, open the selected audio externally, or navigate to Candidate review. Export CSV creates a new report and refuses to overwrite an existing one.',
 'Has LRC means a sidecar exists; it is NOT a claim that the lyric text or synchronization is correct. Missing LRC includes files that have no LRC or review candidate. Scans over 100,000 tracks require a smaller folder.',
]),
('v2.9.7 — Safe timing repair',[
 'Open Timing repair, select an audio track and its matching existing .lrc in the SAME directory, and enter a positive or negative number of seconds. Positive delays subtitles; negative brings them earlier. Use Preview shifted lyrics.',
 'The correction shifts supported [mm:ss.xx] timestamps by the same offset while preserving lyric text and metadata lines. If the offset would produce a negative timestamp, the tool refuses it rather than silently clamping.',
 'Press Save UNVERIFIED candidate only after listening and confirming the preview. The application writes a NEW .candidate.lrc or numbered .candidate.2.lrc file. It never overwrites the original audio or existing .lrc. Even corrected timing remains UNVERIFIED until reviewed.',
]),
('v2.9.7 — Updates and diagnostics',[
 'Quick Search includes Check for updates. It contacts only the official GitHub release API when you explicitly click; there is no automatic upload or automatic executable installation. If a newer release is available, use Open new GitHub release.',
 'Save diagnostics creates a local TXT file with application version, operating system and companion worker status. It intentionally does not include filenames, library paths, music titles, lyrics, tags, credentials or environmental variables. The destination is chosen by you and existing reports are protected.',
]),

('v2.9.7: Switch the interface language',[
 'At the top-right of the Control Center, use Interface language / Γλώσσα εφαρμογής and select English or Ελληνικά. You do not need to restart. The active tab, values, profiles, and running search remain in place. The language choice is remembered for the next time you open the application.',
 'Only the user interface changes language: labels, tooltips, messages, common statuses and warnings. Lyrics, artist/title metadata, saved search keys, provider names, internal machine codes (such as NO_MATCH), audio files and report formats are not translated.',
 'If you share the application, new users start in English. Each Windows user may select Greek independently. No online account is needed to change the display language.',
 '## Greek UI examples',
 'Saved searches → Αποθηκευμένες αναζητήσεις; Live progress → Ζωντανή πρόοδος; Candidate review → Έλεγχος υποψήφιων στίχων; Provider health → Κατάσταση πηγών στίχων; Save profile → Αποθήκευση προφίλ.',
]),
('How to install the new Windows edition',[
 'Download the v2.9.7 standalone Windows GUI ZIP from the official GitHub Releases page. Extract the WHOLE archive first. Keep LRC_Control_Center.exe and LRC_Bulk_Finder_Worker.exe together with dictionaries, the instructions and manual.',
 'Double-click LRC_Control_Center.exe. Neither Python nor a separate installation is required for the ordinary standalone edition. You can change language immediately at the top-right.',
 'If you want the optional local Greek AI setup scripts or the full command-line menu, obtain the v2.9.7 Python/CMD source package instead, and install Python 3.10 or newer with required dependencies.',
 'Windows SmartScreen may warn because the open-source EXE is unsigned. A warning is not proof of malware or proof of safety. Verify the official release URL, asset hashes and security policy before executing any downloaded file.',
]),
('First search — practical checklist',[
 '1. Select Saved searches / Αποθηκευμένες αναζητήσεις, and browse to the music folder. Start on a COPY of a small folder if you want to examine the results first.',
 '2. Choose action 1 (normal online) if you do not have a large LRCLIB database. Action 4 is OFFLINE ONLY; action 5 is OFFLINE FIRST then online for misses, and both require a configured existing database.',
 '3. For a first trial, select FAST providers, default order, 20 missing songs. Turn experimental providers and optional Greek AI off initially.',
 '4. Save the search profile and press START SEARCH / Έναρξη αναζήτησης. Watch Live progress for per-stage and cumulative counts.',
 '5. Check newly created .lrc files beside the audio files, read the not-found/timeout reports, and inspect .candidate.lrc sidecars separately.',
]),
('Safety, STOP and resume',[
 'Normal searching writes separate .lrc sidecars, candidate sidecars, cache metadata and reports. It does not modify existing audio, ID3 tags, or already-present .lrc files. Same-stem format collisions and ambiguous matches are skipped conservatively.',
 'If you click STOP, the GUI asks for confirmation. It attempts to terminate its own worker tree and independently checks for surviving child processes. If verification is uncertain, treat the warning seriously: use Task Manager before restarting. Completed checkpoints remain eligible for safe resume.',
 'The STOP implementation in v2.9.7 uses a native Windows process snapshot before falling back to PowerShell. This avoids unnecessary dependence on slow PowerShell startup but cannot guarantee every unusual machine state.',
 'Candidate lyrics must not be treated as verified. The manual Promote action is explicitly marked UNVERIFIED and never overwrites an existing approved .lrc.',
]),
('Where settings are kept / troubleshooting',[
 'Saved search profiles and the interface-language preference are separate local settings. On Windows, they live under your own application-data directory (APPDATA/LRCBulkFinder). Changing English/Greek must not change a search profile.',
 'If the GUI launches but searches fail, confirm music-folder permissions, metadata, installed companion worker, database path and internet connection. If online providers return rate limits or timeouts, consult reports and retry only genuinely timed-out checks.',
 'Large offline LRCLIB dumps are external downloads and are NOT bundled in the standalone ZIP. The small Greek words SQLite shipped with the application is not the large LRCLIB database.',
 'Provider services and lyric copyright restrictions are external. The application cannot guarantee synchronized lyrics for every recording. Review the source data and player compatibility before sharing files.',
]),
('For the detailed workflows',[
 'The complete chapters earlier in the English manual remain applicable to v2.9.7 unless this bilingual addendum explicitly changes a step. All original advanced search and console options remain available; v2.9.7 adds selective retries, report-based reasons and session undo to the dashboard.',
 'Project and issues: https://github.com/DimitrisLai/LRC-Bulk-Finder',
])]

greek_sections=[
('32  Έκδοση 2.9.2: σωστή εκκίνηση της εφαρμογής',[
'ΠΡΟΣΟΧΗ: Η εύκολη έκδοση για Windows περιλαμβάνει δύο εκτελέσιμα αρχεία. Ανοίξτε το LAUNCH_LRC_BULK_FINDER_WINDOWS.cmd ή το LRC_Control_Center.exe. Και τα δύο ανοίγουν το γραφικό περιβάλλον. ΜΗΝ εκτελείτε χειροκίνητα το LRC_Bulk_Finder_Worker.exe.',
'Ο Worker είναι βοηθητική διεργασία αναζήτησης. Χρειάζεται την παράμετρο --profile, που αποστέλλεται αυτόματα από το Control Center. Αν ανοίξετε τον Worker μόνο του, το σφάλμα για την παράμετρο δεν σημαίνει πως υπάρχει πρόβλημα με τη μουσική σας.',
'Αποσυμπιέστε ΟΛΟΚΛΗΡΟ το επίσημο ZIP στον ίδιο φάκελο· κρατήστε μαζί τα δύο EXE και τα βοηθητικά αρχεία. Το νέο αρχείο εκκίνησης παρέχει οδηγίες αν λείπουν αρχεία.',
'Στην έκδοση 2.9.0 ο τίτλος του Control Center μπορούσε λανθασμένα να αλλάξει σε 2.7.0 κατά την αρχική φόρτωση της γλώσσας. Αυτό διορθώθηκε. Ο τίτλος παραμένει 2.9.2 ακόμη και μετά την αλλαγή Ελληνικών/Αγγλικών.',
'Συνεχίστε τον ημερήσιο πλήρη έλεγχο πριν την τελική έκδοση 3.0 με τα προηγούμενα κεφάλαια του οδηγού. Η υπογραφή εφαρμογής μέσω SignPath παραμένει εκκρεμής.'],
),

('29  Έξυπνη Βιβλιοθήκη v2.9: σάρωση και έλεγχος στίχων',[
'Από Sync Lab > Έξυπνη Βιβλιοθήκη επιλέξτε φάκελο μουσικής και πατήστε Σάρωση / σταδιακή ενημέρωση. Η εφαρμογή δημιουργεί τοπικό, ιδιωτικό ευρετήριο SQLite στον φάκελο APPDATA. Τα αρχικά μουσικά αρχεία, τα ID3 και τα LRC δεν τροποποιούνται.',
'Εντοπίζονται στίχοι που λείπουν, υποψήφιοι προς έλεγχο, πολλαπλά αρχεία ήχου με ίδιο όνομα, διπλές χρονικές σημάνσεις, λανθασμένη σειρά, μεγάλα κενά, ύποπτες μετατοπίσεις, προβλήματα κωδικοποίησης και διαφορετικός τίτλος στο LRC.',
'Ορισμένες προειδοποιήσεις είναι ενδεικτικές, δεν αποδεικνύουν λάθος. Ο προαιρετικός αναλυτικός έλεγχος διάρκειας χρησιμοποιεί τα διαθέσιμα μεταδεδομένα των ηχογραφήσεων και μπορεί να είναι πιο αργός.',
]),
('30  Φίλτρα, ουρά ελέγχου, ακύρωση και εξαγωγή CSV',[
'Η ουρά εμφανίζει 200 τραγούδια ανά σελίδα. Φιλτράρετε προβλήματα, τραγούδια χωρίς LRC και αμφίβολα αρχεία, κάντε αναζήτηση και σημειώστε εγγραφές ως σελιδοδείκτη ή ελεγμένες. Καμία τέτοια ενέργεια δεν διορθώνει ή αντικαθιστά LRC.',
'Με διπλό κλικ ανοίγει το επιλεγμένο κομμάτι στο Στούντιο στίχων. Οι αλλαγές παραμένουν προσωρινές, με Αναίρεση και νέο μη επαληθευμένο υποψήφιο αρχείο μόνο μετά από ξεχωριστή επιβεβαίωση.',
'Η ακύρωση της σάρωσης αναστρέφει την τρέχουσα συναλλαγή SQLite, αφήνοντας διαθέσιμο το τελευταίο ολοκληρωμένο ευρετήριο. Εμφανίζεται το ιστορικό σαρώσεων και οι ήδη επεξεργασμένες εγγραφές χρησιμοποιούνται ξανά όταν δεν έχουν αλλάξει.',
'Εξαγωγή CSV: επιλέξτε φίλτρο, ορίστε νέο όνομα αναφοράς και επιβεβαιώστε. Η εξαγωγή είναι UTF-8 BOM και προστατεύει από κίνδυνο τύπων στο Excel. Δεν αντικαθίσταται υπάρχουσα αναφορά.',
]),
('31  Τελικός έλεγχος πριν την έκδοση 3.0',[
'Κρατήστε ένα αντίγραφο της μουσικής σας για τη δοκιμή. Ελέγξτε την αναζήτηση, τα ελληνικά ονόματα, το STOP, το ιστορικό και το Undo της διαχείρισης, την ουρά υποψηφίων και τις αναφορές.',
'Στην Έξυπνη Βιβλιοθήκη δοκιμάστε πρώτη και δεύτερη σάρωση, τροποποίηση ενός αντιγράφου LRC, ακύρωση σε μεγάλο φάκελο και ανοίξτε ένα πρόβλημα απευθείας στο Στούντιο.',
'Δοκιμάστε αναπαραγωγή WAV/MP3, Undo/Redo, αποθήκευση νέου υποψηφίου, Καραόκε με ορχηστρική μουσική, λίστες τραγουδιών, φόρτωση LRC, δεύτερη οθόνη, γραμματοσειρές, χρονικές μετατοπίσεις και ελληνικό περιβάλλον.',
'Ελέγξτε Windows 100–150% DPI, προστασία πραγματικών αρχείων, τις δύο εκδόσεις PDF, τα ZIP και τα SHA-256. Εφόσον υπάρξουν διορθώσεις, μπορεί να κυκλοφορήσει η μικρή έκδοση 2.9.2, πριν το τελικό μεγάλο v3.0.',
]),

('26  Καραόκε v2.8: λίστα τραγουδιών και χωριστή οθόνη κοινού',[
'Ανοίξτε Sync Lab > Έκδοση Καραόκε. Προσθέστε έως 500 τραγούδια από τον υπολογιστή σας, διπλοπατήστε ένα κομμάτι για να ανοίξει στο Στούντιο στίχων, αλλάξτε τη σειρά στη λίστα ή αφαιρέστε μια εγγραφή χωρίς να διαγραφεί κανένα πραγματικό αρχείο.',
'Για κομμάτι που περιέχει Instrumental, Karaoke, Backing Track ή Minus One στο όνομα, το πρόγραμμα αναζητά αρχείο LRC με ίδιο βασικό όνομα. Προηγείται πάντα η ακριβής αντιστοίχιση. Αν υπάρχει αμφιβολία ή περισσότερα πιθανά αρχεία, ο χρήστης επιλέγει ο ίδιος στίχους. Το πρόγραμμα δεν εμπιστεύεται αυτόματα υποψήφια .candidate.lrc.',
'Μπορείτε να εισαγάγετε ήχο και στίχους με σύρσιμο αρχείων, όταν υποστηρίζεται η λειτουργία από την εγκατάσταση. Διαφορετικά χρησιμοποιήστε τα κουμπιά επιλογής αρχείων. Οι ρυθμίσεις και η λίστα αποθηκεύονται μόνο στον ιδιωτικό φάκελο APPDATA του προγράμματος· δεν αλλάζουν τα αρχεία μουσικής, οι στίχοι ή τα tags.',
]),
('27  Οθόνη προβολέα, εμφάνιση στίχων και αντίστροφη μέτρηση',[
'Διαλέξτε διαθέσιμη οθόνη προβολής ή μετακινήστε το παράθυρο χειροκίνητα σε δεύτερο μόνιτορ. Η οθόνη κοινού δείχνει μόνο τους στίχους, χωρίς τα χειριστήρια. F11 = πλήρης οθόνη, Escape = κλείσιμο, Space = παύση/αναπαραγωγή, ← και → = προηγούμενο/επόμενο τραγούδι.',
'Υπάρχουν τέσσερις χρωματικές εμφανίσεις (Μεσονύχτιο, Μαύρο και Χρυσό, Ωκεανός, Υψηλή αντίθεση), μεγέθη γραμματοσειράς, επιλογή εμφάνισης επόμενης γραμμής, καθώς και προαιρετική τοπική εικόνα PNG/JPG για φόντο. Δεν αποστέλλονται εικόνες στο διαδίκτυο.',
'Μπορείτε να ορίσετε αντίστροφη μέτρηση 0, 3, 5 ή 10 δευτερολέπτων πριν ξεκινήσει η μουσική. Με κλείσιμο του παραθύρου διακόπτεται η εκκρεμής αντίστροφη μέτρηση. Τα σημεία επανάληψης Α–Β αποθηκεύονται ξεχωριστά για κάθε τραγούδι.',
]),
('28  Χρονισμός, προεπισκόπηση εξαγωγής και προστασία αρχείων',[
'Με τα πλήκτρα μετατόπισης διορθώστε προσωρινά τους στίχους κατά ±0,1 ή ±1 δευτερόλεπτο. Το θετικό πρόσημο καθυστερεί την εμφάνιση. Αυτό είναι απλή προεπισκόπηση — δεν αλλάζει κανένα LRC.',
'Το κουμπί εφαρμογής του χρόνου σε ΟΛΟΥΣ τους στίχους απαιτεί επιβεβαίωση και αλλάζει μόνο το προσωρινό έγγραφο με δυνατότητα αναίρεσης. Για να δημιουργηθεί αρχείο απαιτείται ξεχωριστή εντολή αποθήκευσης, η οποία δημιουργεί μόνο ΝΕΟ αριθμημένο και ΜΗ ΕΠΑΛΗΘΕΥΜΕΝΟ υποψήφιο LRC.',
'Η προεπισκόπηση εξαγωγής δείχνει ακριβώς το κείμενο της μορφής που επιλέξατε χωρίς καμία εγγραφή. Οι στίχοι εμφανίζονται ανά γραμμή, όχι ανά λέξη. Δεν γίνεται αυτόματη αφαίρεση φωνής ή δημιουργία συγχρονισμένων στίχων.',
'Τα πρωτότυπα μουσικά αρχεία, τα ID3 και οι υπάρχοντες στίχοι προστατεύονται. Η έκδοση παραμένει Public Beta· ελέγξτε τη συμβατότητα με το δικό σας ραδιόφωνο αυτοκινήτου και την ποιότητα αναπαραγωγής στον υπολογιστή σας.',
]),

('23  Καραόκε με ορχηστρικό αρχείο και χρονισμένους στίχους',[
 'Ανοίξτε Sync Lab (πειραματικό) > Στούντιο στίχων. Επιλέξτε το ορχηστρικό σας τραγούδι. Αν υπάρχει ίδιο όνομα .lrc, φορτώνεται μόνο για ανάγνωση· διαφορετικά πατήστε Φόρτωση LRC για να διαλέξετε στίχους, ακόμη και με άλλο όνομα. Το παλιό Sync Lab βοηθά στη δημιουργία χρόνων για δικό σας κείμενο.',
 'Ανοίξτε την καρτέλα «Ακρίβεια και Καραόκε» και επιλέξτε την προβολή καραόκε. Εμφανίζεται η ενεργή γραμμή και η επόμενη, με μεγάλα γράμματα. Με F11 ανοίγετε πλήρη οθόνη, με Escape κλείνετε. Δεν αφαιρούνται φωνητικά ούτε δημιουργούνται αυτόματα στίχοι.',
 'Η προβολή χρησιμοποιεί απλό χρονισμό ανά γραμμή, όχι ανά λέξη. Η μουσική, τα ID3 και τα υπάρχοντα LRC δεν τροποποιούνται. Για δημόσια χρήση ελέγξτε τα δικαιώματα στίχων και ηχογράφησης.',
]),
('24  Εργαλεία ακριβείας: επανάληψη, κυματομορφή και ταχύτητα',[
 'Ορίστε το σημείο Α στην αρχή του κομματιού που θέλετε να επαναλαμβάνεται και το Β μετά το Α. Το πρόγραμμα προσπαθεί να επιστρέφει στο Α μετά το Β. Υπάρχουν επίσης κουμπιά για κίνηση πίσω κατά 1 ή 5 δευτερόλεπτα.',
 'Η κυματομορφή διαβάζει δειγματοληπτικά τον ήχο, χωρίς εγγραφή σε αυτόν. Το απλό WAV PCM υποστηρίζεται εγγενώς· συμπιεσμένα αρχεία απαιτούν προαιρετικά soundfile/libsndfile. Μεγεθύνετε από 1x έως 8x, μετακινήστε το παράθυρο και πατήστε στην κυματομορφή για αναζήτηση χρόνου.',
 'Η προεπιλεγμένη ταχύτητα 1.00x χρησιμοποιεί pygame. Οι 0.75x και 1.25x απαιτούν εγκατεστημένο VLC 64 bit και python-vlc· αν λείπει, θα εμφανιστεί σαφής προειδοποίηση. Η αναπαραγωγή δεν εγγυάται ίδια ακρίβεια χρονισμού για κάθε κωδικοποίηση.',
]),
('25  Έλεγχος χρόνων, ανάκτηση, πλήκτρα και ασφαλής εξαγωγή',[
 'Ο έλεγχος χρόνων εμφανίζει διπλές χρονικές σημάνσεις, λανθασμένη σειρά, μεγάλες αποστάσεις, πολύ κοντινές γραμμές ή χρόνους πέρα από τη διάρκεια. Οι σοβαρές αστοχίες εμποδίζουν την αποθήκευση, όχι όμως κάθε υποκειμενικά μεγάλη παύση.',
 'Ένα ιδιωτικό προσχέδιο μπορεί να αποθηκεύεται αυτόματα στον φάκελο APPDATA/LRCBulkFinder/studio_drafts και επαναφέρεται μόνο με ερώτηση, αν συμφωνούν τα στοιχεία προέλευσης. Ούτε τα τραγούδια ούτε τα αρχικά LRC αντικαθίστανται.',
 'Επιλέξτε περισσότερες γραμμές για μετατόπιση 0,01 / 0,05 / 0,10 δευτερολέπτων. Μπορείτε να αλλάξετε τρεις συντομεύσεις που λειτουργούν μόνο στον πίνακα στίχων.',
 'Οι μορφές αποθήκευσης είναι UTF-8 δύο δεκαδικών, UTF-8 τριών δεκαδικών ή UTF-8 BOM για ραδιόφωνο αυτοκινήτου. Κάθε αποθήκευση δημιουργεί ΝΕΟ, ρητά ΜΗ ΕΠΑΛΗΘΕΥΜΕΝΟ .candidate.lrc ή αριθμημένο υποψήφιο. Ελέγξτε τη συμβατότητα με τη δική σας συσκευή.',
 'Από τον Πίνακα αποτελεσμάτων ή την Προεπισκόπηση υποψηφίων μπορείτε να μεταβείτε κατευθείαν στο Στούντιο με το επιλεγμένο τραγούδι.',
]),

('20  Στούντιο στίχων (v2.9.7)',[
 'Ανοίξτε την καρτέλα Sync Lab (πειραματικό) και μέσα της το νέο «Στούντιο στίχων». Το παλιό Sync Lab παραμένει διαθέσιμο ως «Κλασικό εργαστήριο συγχρονισμού». Οι οκτώ βασικές καρτέλες διατηρούνται.',
 'Επιλέξτε τραγούδι MP3, WAV, OGG ή FLAC. Η ενσωματωμένη αναπαραγωγή χρησιμοποιεί pygame/SDL_mixer, οπότε η υποστήριξη αρχείων και η ακρίβεια μετακίνησης ενδέχεται να διαφέρουν. Στην έκδοση πηγαίου κώδικα εγκαταστήστε pygame.',
 'Αν υπάρχει αντίστοιχο .lrc, φορτώνεται μόνο για ανάγνωση. Μπορείτε επίσης να επιλέξετε άλλο LRC ή να εισαγάγετε στίχους από το παλιό Sync Lab.',
]),
('21  Ακρόαση, προεπισκόπηση και διορθώσεις',[
 '1. Πατήστε Αναπαραγωγή, Παύση, Διακοπή ή μετακινηθείτε κατά πέντε δευτερόλεπτα. Επιβεβαιώνετε πάντοτε τον συγχρονισμό ακούγοντας τη μουσική: η ένδειξη χρόνου είναι προσεγγιστική για ορισμένα αρχεία.',
 '2. Ο πίνακας δείχνει τις γραμμές και τη χρονική τους σήμανση. Η ενεργή γραμμή επισημαίνεται αυτόματα κατά την ακρόαση.',
 '3. Επιλέξτε γραμμή και πατήστε χρονισμό στην τρέχουσα θέση. Με τα πλήκτρα ή τα κουμπιά διορθώστε κατά 0,10 δευτερόλεπτα, ορίστε ακριβή χρόνο και χρησιμοποιήστε Αναίρεση / Επανάληψη.',
 '4. Αν δύο χρόνοι ταυτιστούν ή βρεθούν σε λανθασμένη σειρά, διορθώστε τους πριν αποθηκεύσετε. Δεν γίνεται αυτόματη αναγνώριση τραγουδιού ή συγχρονισμός ανά λέξη.',
]),
('22  Ασφαλής αποθήκευση νέων υποψηφίων',[
 'Η αποθήκευση δημιουργεί πάντοτε ΝΕΟ, ρητά ΜΗ ΕΠΑΛΗΘΕΥΜΕΝΟ αρχείο .candidate.lrc ή αριθμημένο .candidate.N.lrc. Δεν αντικαθίστανται αρχεία ήχου, ID3, αρχικοί στίχοι ή προϋπάρχοντα υποψήφια.',
 'Τα αρχεία που δημιουργούνται χειροκίνητα στο Στούντιο δεν ανήκουν στο ιστορικό αναίρεσης προηγούμενων αναζητήσεων. Ελέγξτε τα στο Candidate review.',
 'Υποστηρίζεται εισαγωγή συγχρονισμένου LRC UTF-8 και παλαιότερης ελληνικής κωδικοποίησης Windows-1253. Οι νέες αποθηκεύσεις χρησιμοποιούν UTF-8.',
]),

('17  Διαχείριση βιβλιοθήκης (v2.9.7)',[
 'Ο Πίνακας αποτελεσμάτων διαθέτει πλέον Διαχείριση βιβλιοθήκης: επανάληψη επιλεγμένων τραγουδιών, εμφάνιση αποθηκευμένων αιτιών απόρριψης και ασφαλή αναίρεση μιας προηγούμενης αναζήτησης.',
 'Ανανεώστε τα αποτελέσματα, χρησιμοποιήστε το φίλτρο κατάστασης ή την αναζήτηση ονόματος και επιλέξτε ένα ή περισσότερα τραγούδια. Η ένδειξη «Υπάρχει LRC» δείχνει μόνο παρουσία αρχείου, όχι επαληθευμένο συγχρονισμό.',
]),
('18  Επανάληψη ΜΟΝΟ επιλεγμένων τραγουδιών',[
 'Επιλέξτε τραγούδια με κατάσταση «Δεν υπάρχει LRC» ή «Χρειάζεται έλεγχο». Πατήστε «Επανάληψη επιλεγμένων τραγουδιών» και επιβεβαιώστε.',
 'Γίνεται διαδικτυακή αναζήτηση ΜΟΝΟ για τα συγκεκριμένα αρχεία, έως 2.500 κάθε φορά, με όλες τις κανονικές διαδικτυακές πηγές. Δεν απαιτείται μεγάλη βάση LRCLIB. Παλαιότερα αρνητικά αποτελέσματα δεν εμποδίζουν αυτή τη ρητά ζητημένη επανάληψη.',
 'Αν ένα επιλεγμένο αρχείο μετακινηθεί, αποκτήσει ήδη LRC ή παύσει να είναι κατάλληλο, η αναζήτηση ακυρώνεται με ασφάλεια αντί να ελέγξει ολόκληρο τον φάκελο. Οι περιορισμοί των υπηρεσιών και η προστασία αρχείων εξακολουθούν να ισχύουν.',
]),
('19  Γιατί απορρίφθηκαν οι στίχοι;',[
 'Επιλέξτε ένα τραγούδι και πατήστε «Γιατί απορρίφθηκε;». Το πρόγραμμα διαβάζει παλιότερες αναφορές CSV με πληροφορίες πηγών, αμφίβολων αποτελεσμάτων και αιτιών όπως λάθος εκτέλεση, διαφορετική διάρκεια ή μη διαθέσιμη πηγή.',
 'Οι πληροφορίες είναι ιστορικές και μπορεί να είναι παρωχημένες. Δεν αποτελούν ζωντανή αναζήτηση, ούτε πιστοποίηση ότι οι στίχοι δεν υπάρχουν.',
]),
('20  Ασφαλής αναίρεση τελευταίας αναζήτησης',[
 'Οι νέες αναζητήσεις μέσω της γραφικής εφαρμογής καταγράφουν τοπικά ποια αρχεία LRC ή candidate δημιούργησαν. Για την αναίρεση πατήστε «Αναίρεση τελευταίας αναζήτησης...» και διαβάστε την επιβεβαίωση.',
 'Αφαιρούνται ΜΟΝΟ αρχεία που δημιουργήθηκαν από την καταγεγραμμένη αναζήτηση και παραμένουν ακριβώς αμετάβλητα σύμφωνα με μέγεθος, χρόνο τροποποίησης και SHA256. Τα αλλαγμένα, ήδη υπάρχοντα ή άγνωστα αρχεία διατηρούνται.',
 'Δεν αγγίζονται μουσική, ετικέτες ID3, παλιά LRC, αναφορές, cache, ρυθμίσεις ή οι χειροκίνητες διορθώσεις χρονισμού. Η ενέργεια είναι οριστική. Αναζητήσεις της v2.4.5 και παλαιότερες δεν είχαν αντίστοιχο ημερολόγιο και δεν μπορούν να αναιρεθούν με αυτή τη λειτουργία.',
]),

('13  Γρήγορη αναζήτηση (v2.9.7)',[
 'Στην καρτέλα «Γρήγορη αναζήτηση» επιλέξτε φάκελο μουσικής, δοκιμή 20 τραγουδιών ή όλα τα τραγούδια και, αν χρειάζεται, υποφακέλους και αντιστοίχιση Ελληνικών/Greeklish.',
 'Πατήστε «ΕΝΑΡΞΗ ΓΡΗΓΟΡΗΣ ΑΝΑΖΗΤΗΣΗΣ». Χρησιμοποιούνται οι γρήγορες διαδικτυακές πηγές και δεν απαιτείται μεγάλη τοπική βάση LRCLIB. Οι προχωρημένες ρυθμίσεις παραμένουν διαθέσιμες στην καρτέλα αποθηκευμένων αναζητήσεων.',
 'Τα πρωτότυπα αρχεία ήχου και οι ετικέτες τους δεν τροποποιούνται. Οι ρυθμίσεις της γρήγορης αναζήτησης αποθηκεύονται σε ξεχωριστό προφίλ.',
]),
('14  Πίνακας αποτελεσμάτων (v2.9.7)',[
 'Ο «Πίνακας αποτελεσμάτων» διαβάζει μόνο τα ονόματα αρχείων και την ύπαρξη αρχείων LRC. Πατήστε «Ανανέωση αποτελεσμάτων» για να δείτε το σύνολο της βιβλιοθήκης.',
 'Μπορείτε να φιλτράρετε τα τραγούδια που διαθέτουν LRC, όσα χρειάζονται έλεγχο και όσα δεν διαθέτουν LRC, να αναζητήσετε όνομα αρχείου ή να κάνετε εξαγωγή CSV χωρίς αντικατάσταση υπάρχουσας αναφοράς.',
 'Η ένδειξη «Υπάρχει LRC» δεν σημαίνει ότι οι στίχοι είναι επαληθευμένοι ή συγχρονισμένοι σωστά. Η αναφορά είναι μόνο μια επισκόπηση.',
]),
('15  Ασφαλής διόρθωση χρονισμού (v2.9.7)',[
 'Επιλέξτε την καρτέλα «Διόρθωση χρονισμού», το αρχείο ήχου και το αντίστοιχο συγχρονισμένο LRC από τον ίδιο φάκελο.',
 'Εισαγάγετε μετατόπιση σε δευτερόλεπτα: θετική τιμή σημαίνει ότι οι στίχοι θα εμφανίζονται αργότερα, αρνητική νωρίτερα. Πατήστε προεπισκόπηση, ακούστε το τραγούδι και ελέγξτε το αποτέλεσμα.',
 'Η αποθήκευση δημιουργεί μόνο νέο ΜΗ ΕΠΑΛΗΘΕΥΜΕΝΟ αρχείο .candidate.lrc, με αρίθμηση όταν χρειάζεται. Το αρχικό .lrc και ο ήχος παραμένουν αμετάβλητα και η εφαρμογή αρνείται χρονικές σημάνσεις πριν από το 0.',
]),
('16  Ενημερώσεις και διαγνωστικά (v2.9.7)',[
 'Ο έλεγχος ενημερώσεων εκτελείται μόνο εάν πατήσετε το σχετικό κουμπί και χρησιμοποιεί την επίσημη σελίδα εκδόσεων του GitHub. Δεν γίνεται αυτόματη εγκατάσταση.',
 'Η λειτουργία «Αποθήκευση διαγνωστικών» δημιουργεί τοπική αναφορά με έκδοση, στοιχεία συστήματος και παρουσία του βοηθητικού προγράμματος. Δεν περιλαμβάνει προσωπικούς φακέλους, τίτλους τραγουδιών, στίχους ή στοιχεία σύνδεσης.',
]),

('01  Τι είναι το LRC Bulk Finder',[
 'Το LRC Bulk Finder είναι δωρεάν εφαρμογή ανοιχτού κώδικα για Windows. Αναζητά συγχρονισμένους στίχους τραγουδιών και τους αποθηκεύει ως ξεχωριστά αρχεία .lrc, δίπλα στα αρχεία μουσικής.',
 'Ένα τραγούδι Song Name.mp3 μπορεί να έχει δίπλα του ένα Song Name.lrc. Οι γραμμές του LRC περιέχουν χρονικές σημάνσεις, για παράδειγμα [00:12.40] Πρώτη γραμμή, ώστε να εμφανίζονται την κατάλληλη στιγμή σε συμβατό πρόγραμμα ή ραδιόφωνο αυτοκινήτου.',
 'Η εφαρμογή δεν εγγυάται ότι θα βρει στίχους για κάθε τραγούδι. Οι σπάνιες ηχογραφήσεις, οι διασκευές, οι ζωντανές εκτελέσεις και τα remix απαιτούν ιδιαίτερη προσοχή.',
]),
('02  Εγκατάσταση στα Windows',[
 '1. Ανοίξτε την επίσημη σελίδα GitHub Releases: https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/latest',
 '2. Κατεβάστε το αρχείο LRC_Bulk_Finder_v2_9_7_Standalone_Windows_GUI.zip, εφόσον θέλετε την εύκολη έκδοση χωρίς εγκατάσταση Python.',
 '3. Κάντε πλήρη αποσυμπίεση του ZIP σε έναν φάκελο όπου έχετε δικαίωμα εγγραφής. Μην εκκινήσετε το πρόγραμμα μέσα από το συμπιεσμένο αρχείο.',
 '4. Αφήστε μαζί τα LRC_Control_Center.exe και LRC_Bulk_Finder_Worker.exe, τα αρχεία ελληνικών λεξικών, τις οδηγίες και το εγχειρίδιο.',
 '5. Εκκινήστε το LRC_Control_Center.exe. Η απλή χρήση της αυτόνομης έκδοσης δεν απαιτεί Python.',
 'Για την πλήρη έκδοση Python/CMD χρειάζεται Python 3.10+ και οι εξαρτήσεις που εξηγούνται στα συνοδευτικά README. Το προαιρετικό τοπικό μοντέλο ελληνικής μεταγραφής AI δεν περιλαμβάνεται στο αυτόνομο EXE.',
]),
('03  Αλλαγή γλώσσας: English / Ελληνικά',[
 'Στο επάνω δεξί μέρος της εφαρμογής βρείτε το πεδίο «Γλώσσα εφαρμογής». Επιλέξτε «Ελληνικά» ή «English». Η αλλαγή εφαρμόζεται άμεσα χωρίς επανεκκίνηση.',
 'Η επιλογή διατηρείται όταν κλείσετε και ξανανοίξετε την εφαρμογή. Κάθε χρήστης μπορεί να επιλέξει τη δική του γλώσσα.',
 'Η μετάφραση αφορά μόνο το περιβάλλον χρήσης: καρτέλες, κουμπιά, περιγραφές, υποδείξεις και κοινά μηνύματα. ΔΕΝ αλλάζει τους στίχους, τους τίτλους, τα ονόματα καλλιτεχνών, τους παρόχους, τα αρχεία αναφορών ή τις αποθηκευμένες ρυθμίσεις αναζήτησης.',
]),
('04  Περιήγηση στις πέντε καρτέλες',[
 '• Αποθηκευμένες αναζητήσεις (Saved searches): φάκελος μουσικής, τρόπος αναζήτησης, προφίλ, έτοιμες ρυθμίσεις.',
 '• Ζωντανή πρόοδος (Live progress): καταγραφή ενεργειών, χρόνος, κατάσταση αναζήτησης, αποτελέσματα κάθε σταδίου.',
 '• Έλεγχος υποψήφιων στίχων (Candidate review): αρχεία που χρειάζονται χειροκίνητο έλεγχο πριν χρησιμοποιηθούν.',
 '• Sync Lab (πειραματικό): χειροκίνητη δημιουργία μη επαληθευμένου προσχεδίου στίχων με χρονισμό.',
 '• Κατάσταση πηγών στίχων (Provider health): αποτελέσματα και κατάσταση των πηγών με βάση πραγματικά συμβάντα χρήσης.',
]),
('05  Η πρώτη αναζήτηση: βήμα προς βήμα',[
 '1. Επιλέξτε τον φάκελο της μουσικής σας. Για την πρώτη δοκιμή προτιμήστε έναν μικρό φάκελο ή ένα αντίγραφο αρχείων.',
 '2. Αν ΔΕΝ έχετε τη μεγάλη τοπική βάση LRCLIB, διαλέξτε «1 — Κανονική διαδικτυακή αναζήτηση». Δεν χρειάζεται να κατεβάσετε τη μεγάλη βάση για μια απλή δοκιμή.',
 '3. Επιλέξτε λειτουργία FAST, προεπιλεγμένη σειρά παρόχων και όριο «20 τραγούδια». Μην ενεργοποιήσετε πειραματικούς παρόχους στην αρχή.',
 '4. Αποθηκεύστε το προφίλ, πατήστε «Έναρξη αναζήτησης» και δείτε την καρτέλα «Ζωντανή πρόοδος».',
 '5. Ελέγξτε τα νέα αρχεία .lrc, τις αναφορές και όσα αρχεία έχουν κατάληξη .candidate.lrc. Δοκιμάστε τη λειτουργία σε συμβατή συσκευή αναπαραγωγής.',
]),
('06  Οι επιλογές αναζήτησης 1 / 4 / 5',[
 'Επιλογή 1: Διαδικτυακή αναζήτηση μέσω των διαθέσιμων παρόχων. Ενδείκνυται όταν δεν έχετε τοπική βάση LRCLIB.',
 'Επιλογή 4: Αποκλειστικά τοπική αναζήτηση σε υπάρχουσα βάση LRCLIB, χωρίς διαδικτυακούς παρόχους. Η βάση πρέπει να είναι διαθέσιμη και σωστά ρυθμισμένη.',
 'Επιλογή 5: Πρώτα αναζήτηση στην τοπική βάση LRCLIB και στη συνέχεια διαδικτυακή αναζήτηση για όσα δεν βρέθηκαν. Οι πραγματικές προσωρινές αποτυχίες μπορούν να επανελεγχθούν ξεχωριστά.',
 'Υπάρχουν έτοιμα προφίλ για πλήρη ελληνική αναζήτηση, νυχτερινή αναζήτηση, δοκιμή 20 τραγουδιών, λειτουργία χωρίς σύνδεση, προαιρετικό AI και γρήγορη διεθνή αναζήτηση. Μπορείτε να τα εφαρμόσετε και να τα προσαρμόσετε.',
]),
('07  Τι σημαίνουν τα αποτελέσματα',[
 '• .lrc: αποθηκευμένο αρχείο συγχρονισμένων στίχων που πέρασε τους αυτοματοποιημένους ελέγχους, ή επιβεβαιώθηκε χειροκίνητα με ρητή σήμανση.',
 '• .candidate.lrc: υποψήφιο αρχείο που ΔΕΝ έχει επαληθευτεί. Χρειάζεται έλεγχο τραγουδιού, έκδοσης και συγχρονισμού.',
 '• .candidate.2.lrc: πρόσθετη εναλλακτική, επίσης μη επαληθευμένη.',
 '• Not Found / Δεν βρέθηκε: δεν βρέθηκε κατάλληλο αποτέλεσμα για το συγκεκριμένο τραγούδι.',
 '• Timeouts / Χρονικές υπερβάσεις: πάροχος δεν απάντησε έγκαιρα. Δεν σημαίνει ότι δεν υπάρχουν στίχοι.',
 'Οι αναφορές βοηθούν να εντοπίσετε αρχεία χωρίς επαρκή metadata και να δείτε από ποια πηγή προήλθαν έγκυρα αποτελέσματα.',
]),
('08  STOP και ασφαλής συνέχιση',[
 'Για να διακόψετε μια αναζήτηση, πατήστε STOP και επιβεβαιώστε. Η εφαρμογή επιχειρεί να σταματήσει τον δικό της worker και ελέγχει αν έχουν απομείνει θυγατρικές διεργασίες.',
 'Στην έκδοση 2.9.2 ο έλεγχος των Windows χρησιμοποιεί πρώτα τη φυσική λειτουργία καταγραφής διεργασιών του συστήματος, με εναλλακτικό μηχανισμό ελέγχου όπου χρειάζεται.',
 'Αν εμφανιστεί μήνυμα ότι η διακοπή δεν έχει επαληθευτεί πλήρως, ΜΗΝ θεωρήσετε ότι όλες οι διεργασίες έχουν τερματιστεί. Ελέγξτε τη Διαχείριση Εργασιών πριν ξεκινήσετε νέα αναζήτηση.',
 'Η ασφαλής συνέχιση αξιοποιεί έγκυρα σημεία αποθήκευσης προόδου. Μπορεί να επαναληφθεί η επεξεργασία εργασίας που είχε μείνει στη μέση.',
]),
('09  Έλεγχος υποψήφιων στίχων',[
 'Στην καρτέλα ελέγχου μπορείτε να δείτε υποψήφια αρχεία, να διαβάσετε το κείμενο και να ανοίξετε το τραγούδι στον προεπιλεγμένο αναπαραγωγέα.',
 'Ελέγξτε ότι ταιριάζουν ο καλλιτέχνης, ο τίτλος, η συγκεκριμένη έκδοση (remix, live κ.λπ.) και οι χρονικές σημάνσεις.',
 'Όταν υπάρχει διαθέσιμη ρητή ενέργεια έγκρισης, η χειροκίνητη προαγωγή προσθέτει ορατή ένδειξη ότι το αποτέλεσμα είναι μη επαληθευμένο. Δεν πρέπει να συγχέεται με αυστηρά επαληθευμένους στίχους.',
 'Η εφαρμογή δεν πρέπει να αντικαθιστά ήδη υπάρχον αρχείο .lrc κατά τις κανονικές αναζητήσεις.',
]),
('10  Ελληνικά / Greeklish και Sync Lab',[
 'Η προαιρετική λειτουργία Ελληνικών και Greeklish δημιουργεί εναλλακτικά ερωτήματα αναζήτησης, αξιοποιώντας ελεγχόμενες γραφές και λεξικά. ΔΕΝ μετονομάζει αρχεία μουσικής ούτε τροποποιεί τα tags.',
 'Το προαιρετικό τοπικό μοντέλο Greek AI είναι διαφορετικό από το απλό λεξικό Greek_Words.csv και δεν διανέμεται με την αυτόνομη έκδοση EXE.',
 'Το Sync Lab είναι πειραματικό: μπορεί να προτείνει πρόχειρους χρονισμούς ή να καταγράψει χειροκίνητα πατήματα. Αποθηκεύει μόνο μη επαληθευμένα προσχέδια για έλεγχο, όχι υποτίθεται έγκυρους στίχους.',
]),
('11  Αρχεία, δεδομένα και δικαιώματα',[
 'Οι συνηθισμένες αναζητήσεις διαβάζουν τη μουσική αλλά δεν αλλάζουν MP3/FLAC/M4A/MP4/OGG/OPUS/WAV ούτε τα ID3 tags. Αποθηκεύουν ξεχωριστά LRC, προσωρινές πληροφορίες, υποψήφια και αναφορές.',
 'Οι ρυθμίσεις προφίλ και η προτίμηση γλώσσας αποθηκεύονται τοπικά στον λογαριασμό Windows, συνήθως στον φάκελο APPDATA/LRCBulkFinder, σε διαφορετικά αρχεία.',
 'Για χρήση σε ραδιόφωνο αυτοκινήτου αντιγράψτε το αρχείο .lrc δίπλα στο μουσικό αρχείο, διατηρώντας το ίδιο όνομα χωρίς την επέκταση. Ελέγξτε αν η συσκευή υποστηρίζει LRC και σε ποια μορφοποίηση.',
 'Οι στίχοι ενδέχεται να προστατεύονται από πνευματικά δικαιώματα. Η άδεια MIT αφορά τον κώδικα του προγράμματος, όχι το περιεχόμενο των στίχων τρίτων.',
]),
('12  Αντιμετώπιση προβλημάτων',[
 '• Το πρόγραμμα δεν ανοίγει: βεβαιωθείτε ότι έχετε αποσυμπιέσει όλο το ZIP και ότι οι δύο εφαρμογές .exe βρίσκονται στον ίδιο φάκελο.',
 '• Εμφανίζεται προειδοποίηση των Windows: οι εφαρμογές της κοινότητας ενδέχεται να μην είναι υπογεγραμμένες. Ελέγξτε την επίσημη πηγή, τα SHA256 και την πολιτική ασφαλείας σας πριν τις ανοίξετε.',
 '• Δεν βρίσκονται στίχοι: ελέγξτε καλλιτέχνη, τίτλο, διάρκεια, σωστό φάκελο, σύνδεση και τις αναφορές χρονικών υπερβάσεων.',
 '• Η λειτουργία 4/5 δεν προχωρά: ελέγξτε ότι έχετε επιλέξει τη ΜΕΓΑΛΗ βάση LRCLIB και όχι το μικρό ελληνικό λεξικό SQLite.',
 '• Η γλώσσα δεν αποθηκεύεται: ελέγξτε αν ο λογαριασμός έχει δικαίωμα εγγραφής στον τοπικό φάκελο ρυθμίσεων.',
 '• Δεν εμφανίζονται στίχοι στη συσκευή: ελέγξτε ίδιο όνομα αρχείων, κωδικοποίηση, μορφή LRC και συμβατότητα του player.',
 'Για αναφορές σφαλμάτων και βελτιώσεις: https://github.com/DimitrisLai/LRC-Bulk-Finder/issues',
])]


# New v2.9.7 chapters added without removing the detailed older instructions.
en_sections.insert(0, ('v2.9.3 - Fixed unexpected stops and expanded Greek search',[
'Windows standalone safety: Local G2G AI is optional and NOT included in the standalone EXE. The Windows GUI no longer offers its unsupported checkbox or Local AI preset. Previously saved Local AI profiles safely continue with the curated Greek dictionary instead. The full Python edition can still use an externally installed compatible model.',
'Unicode bug fix: an unusual Unicode hyphen U+2010 in an audio filename previously caused a CP1252 charmap UnicodeEncodeError after several successful tracks and made the worker stop. The worker and GUI use UTF-8 for progress output; this fixes the encoding crash without altering audio, tags or LRC files.',
'If the worker exits with a nonzero code, Live progress now reports a failed search instead of success. Existing completed LRC files, review candidates and checkpoints remain; restart to retry unfinished songs. An unfinished item is NOT evidence that all providers returned NO_MATCH.',
'Named presets cannot quietly run different scope: International FAST - 20 Songs should show action 1 / FAST / limit 20. If an old saved profile bearing that name contains Offline First or ALL, the GUI offers to restore the standard preset. Choose No to cancel and save your customization under a different name.',
'The preset chooser now contains 15 search configurations, Greek together followed by international/foreign. Broad full-provider searches appear before lightweight/faster searches. An offline-first or offline-only profile needs a real LRCLIB SQLite song database; the optional Greek word SQLite is not that lyrics database.',
'Vocabulary: 730 Wikipedia-linked Greek singer aliases including 113 original approved mappings; 92 additional unverified Greeklish suggestions derived from the titles of 105 Wikipedia Greek-song articles in 15 categories. These are TITLE WORDS, not copied song lyrics. The app loads generated suggestions first and reviewed word spellings last, so curated words win. Every saved review candidate still needs human inspection.',
'Windows upgrade: close v2.9.2, extract the complete v2.9.7 ZIP to a fresh folder, keep both EXEs, Greek_Artists.csv, Greek_Words.csv, Greek_Words_Expanded.csv, Greek_Words_Wikipedia.csv and Greek_Lexicon.sqlite3 together. Open the Control Center using the launcher, never the Worker directly.',
'Pre-v3 hardware acceptance: begin with a 20-song test including a Unicode-hyphen filename, a Greek title and a foreign title. Then try your longer run and STOP. Verify your car stereo and optional third-party providers on real hardware. Avoid testing on your only copy of recordings.',
]))
greek_sections.insert(0, ('33  Έκδοση 2.9.3: αναζήτηση χωρίς απρόσμενη διακοπή',[
'Η έκδοση Windows EXE δεν περιλαμβάνει το εξωτερικό μοντέλο G2G AI. Η αντίστοιχη επιλογή απενεργοποιείται, ενώ παλιότερα αποθηκευμένα προφίλ συνεχίζουν με το ασφαλές ελληνικό λεξικό. Η πλήρης έκδοση Python μπορεί να χρησιμοποιήσει ξεχωριστά εγκατεστημένο συμβατό μοντέλο.',
'Διορθώθηκε πραγματικό σφάλμα κωδικοποίησης: ένας ιδιαίτερος χαρακτήρας παύλας Unicode (U+2010) σε όνομα τραγουδιού προκαλούσε UnicodeEncodeError στη γραμμή προόδου και τερμάτιζε όλη την αναζήτηση. Η έξοδος λειτουργεί πλέον με UTF-8, χωρίς αλλαγή στα MP3, ID3 ή υπάρχοντα LRC.',
'Όταν ο Worker σταματά με κωδικό σφάλματος, η εφαρμογή δείχνει αποτυχία και όχι επιτυχημένο τέλος. Τα τραγούδια που δεν εξετάστηκαν παραμένουν εκκρεμή και μπορούν να αναζητηθούν ξανά. Τα ήδη σωσμένα αρχεία και τα checkpoints προστατεύονται.',
'Τα ονόματα προφίλ πρέπει να συμφωνούν με τις ρυθμίσεις τους. Για το International FAST - 20 Songs επιλέγονται action 1, FAST και όριο 20. Αν το παλιό αποθηκευμένο προφίλ έχει διαφορετικές ρυθμίσεις, εμφανίζεται επιλογή επαναφοράς ή ακύρωσης για να οριστεί διαφορετικό όνομα.',
'Διατίθενται 15 προφίλ αναζήτησης: πρώτα όλα τα ελληνικά, έπειτα όλα τα ξένα, με πιο πλήρη κάλυψη στην αρχή και ταχύτερες ή μικρότερες αναζητήσεις στο τέλος. Οι λειτουργίες offline χρειάζονται πραγματική τοπική βάση LRCLIB με στίχους.',
'Περιλαμβάνονται 730 συνδέσεις ονομάτων Ελλήνων τραγουδιστών (113 ήδη εγκεκριμένες) και 92 επιπλέον μη επιβεβαιωμένες προτάσεις λέξεων από τίτλους 105 ελληνικών τραγουδιών της Wikipedia. Δεν εισάγονται πλήρεις στίχοι. Οι αρχικές εγκεκριμένες γραφές έχουν προτεραιότητα έναντι των αυτόματων προτάσεων.',
'Για αναβάθμιση, κλείστε το παλιό πρόγραμμα και αποσυμπιέστε ολόκληρο το νέο ZIP 2.9.3 σε νέο φάκελο. Κρατήστε μαζί τα δύο EXE, τα CSV και το Greek_Lexicon.sqlite3. Ανοίξτε το Control Center, όχι τον Worker χειροκίνητα. Ξεκινήστε με δοκιμή 20 τραγουδιών.',
]))



# 2.9.7 new chapter: one-click setup and verified model lifecycle
en_sections.insert(0,('v2.9.4 - One-click optional Greek G2G AI installation',[
'WHY THIS WAS DISABLED: the standalone Windows EXE deliberately omitted the large third-party gr-nlp-toolkit (AUEB) Greeklish-to-Greek AI and its heavy PyTorch/model dependencies. v2.9.3 safely disabled a nonworking checkbox. In this edition it can be enabled AFTER a successful real model verification.',
'Press Install / verify Greek G2G AI (one click), then explicitly approve the download notice. No command prompt, manual folder selection or separate setup archive is needed. Installation progress appears inside Control Center. The full G2G model is approximately 1.2 GB, and CPU PyTorch plus other dependencies can consume several additional gigabytes and substantial RAM.',
'When Python 3.10-3.13 exists, the installer uses it only to create a private virtual environment in your Local AppData LRCBulkFinder/G2G directory. If Python is missing and Windows winget exists, consent permits installing official Python 3.11 automatically. Windows may still request approval. If winget or network is unavailable, the app reports what is missing; it never falsely marks AI ready.',
'The installer obtains the published gr-nlp-toolkit 0.3.0 package, downloads the G2G model from its upstream provider, and runs a real Greeklish-to-Greek sample conversion. Only after success does it write an atomic verified marker and enable Use installed local Greek AI and the Greek Local AI - FULL preset.',
'The standalone search worker invokes a persistent local Python companion with CPU mode and offline model flags, not a newly loaded model for every song. The program intentionally avoids loading a large model into the 4 GB GPU. First use can be slow; Greek AI conversion remains a suggestion needing review, not proof of an authentic or correctly timed lyric.',
'You can run Greek FULL without AI at any time. Failed/interrupted setup keeps the checkbox disabled and preserves existing MP3, ID3, LRC, saved profiles and verified lyric matches. Setup does not alter global Python packages. To remove the optional AI manually, close the app and delete the local LRCBulkFinder/G2G directory.',
'Privacy: model inference is local after installation; model and Python downloads require internet, but song/artist metadata are sent only to the local companion. External lyrics-search providers continue to follow the existing app rules. The exact model weight/download environment must be tested on your own Windows hardware; CI simulates install operations and tests frozen entrypoints, not the actual 1.2 GB upstream download.',
]))
greek_sections.insert(0,('34  Έκδοση 2.9.4: αυτόματη εγκατάσταση Greek G2G AI',[
'Στο παλιότερο Windows EXE η επιλογή τοπικού Greek AI ήταν ανενεργή επειδή το μεγάλο εξωτερικό μοντέλο G2G της AUEB και οι βιβλιοθήκες PyTorch δεν συμπεριλαμβάνονταν στην εφαρμογή. Τώρα ενεργοποιείται ΜΟΝΟ μετά από πραγματική επιτυχή δοκιμή του μοντέλου.',
'Πατήστε Install / verify Greek G2G AI (one click) και επιβεβαιώστε τη λήψη. Δεν χρειάζεται επιλογή φακέλου, χειροκίνητη εγκατάσταση pip ή ξεχωριστό αρχείο CMD. Η πρόοδος και τυχόν σφάλματα εμφανίζονται μέσα στο Control Center.',
'Το πλήρες μοντέλο G2G είναι περίπου 1,2 GB, συν επιπλέον μεγάλες βιβλιοθήκες και χώρο στον δίσκο. Η εγκατάσταση δημιουργεί ξεχωριστό περιβάλλον Python μέσα στο Local AppData του χρήστη. Αν δεν υπάρχει Python, μπορεί να χρησιμοποιήσει το επίσημο winget για Python 3.11 με την έγκρισή σας.',
'Μετά την εγκατάσταση εκτελείται πραγματική μετατροπή δοκιμής. Μόνο αν ολοκληρωθεί σωστά, ενεργοποιούνται το checkbox Use installed local Greek AI και το ελληνικό preset με AI. Σε αποτυχία παραμένουν απενεργοποιημένα και δεν χάνονται αρχεία ή παλιές ρυθμίσεις.',
'Στην αναζήτηση το πρόγραμμα διατηρεί ένα τοπικό Python AI companion, χρησιμοποιώντας επεξεργαστή CPU ώστε να μην εξαρτάται από GPU 4 GB. Οι προτάσεις AI είναι μη επιβεβαιωμένες και πρέπει να ελεγχθούν προτού θεωρηθούν σωστά ελληνικά ή στίχοι.',
'Οι αναζητήσεις χωρίς AI λειτουργούν κανονικά. Τα MP3, ID3, υπάρχοντα LRC και αποθηκευμένα προφίλ παραμένουν ανέπαφα. Οι δοκιμές GitHub δεν υποκαθιστούν την πρώτη πραγματική εγκατάσταση στο δικό σας μηχάνημα.',
]))



# New theme controls are a visual-only enhancement. Older chapter references are retained.
en_sections.insert(0,('v2.9.5 - Modern Light / Dark interface',[
'Control Center now has a modernized native Windows layout, with an indigo accent, softer surfaces, clearer tabs, Segoe UI typography, primary Start Search and visually separate STOP controls. There is no subscription, browser UI, login or extra GUI dependency.',
'Choose Appearance > Light or Dark at the top right. In the Greek interface, choose Εμφάνιση > Φωτεινό or Σκοτεινό. The theme changes immediately without recreating tabs, losing fields, starting a search or touching your audio.',
'Language and appearance persist together in the same local per-user settings JSON file. Changing English/Ελληνικά no longer deletes the chosen appearance. Corrupt or missing theme values fall back to Light; saved search profiles are stored separately and never modified by theme changes.',
'The advanced Saved searches form is vertically scrollable. This keeps Save profile and START SEARCH reachable on smaller monitors and when larger UI scaling is enabled. All 15 built-in presets, eight top-level tabs and five nested Studio tabs stay present.',
'The latest GUI styling affects appearance only: actual lyric source selection, online/offline search actions, STOP behavior, Greek AI installation, candidate review and stored verification status are unchanged. Do not mistake an accent button or highlighted result for confirmation that lyrics are verified.',
'Automated tests cover accessible high-contrast text, reversible light/dark and English/Greek switching, non-destructive log/state preservation, scrollable settings, frozen Windows GUI startup and the full independent Python regression suite. Exact Windows font and scaling appearance may differ on a particular desktop.',
]))
greek_sections.insert(0,('35  Έκδοση 2.9.5: νέα εμφάνιση Light / Dark',[
'Η εφαρμογή αποκτά σύγχρονη εμφάνιση με πιο ευανάγνωστες καρτέλες, μεγαλύτερες γραμματοσειρές, ήπιες χρωματικές επιφάνειες και καθαρή διάκριση ανάμεσα στα κουμπιά έναρξης και διακοπής αναζήτησης. Δεν χρειάζεται νέο πρόσθετο ή άλλη υπηρεσία.',
'Στο επάνω δεξί μέρος επιλέξτε Εμφάνιση και μετά Φωτεινό ή Σκοτεινό. Η αλλαγή γίνεται αμέσως, χωρίς επανεκκίνηση και χωρίς απώλεια του επιλεγμένου προφίλ, της τρέχουσας καρτέλας ή των καταγραφών.',
'Οι επιλογές γλώσσας και εμφάνισης αποθηκεύονται μαζί στις προσωπικές ρυθμίσεις. Η εναλλαγή μεταξύ Ελληνικών και Αγγλικών δεν μηδενίζει το θέμα. Αν οι ρυθμίσεις εμφάνισης είναι αλλοιωμένες, το πρόγραμμα επιστρέφει στη φωτεινή μορφή.',
'Η καρτέλα Αποθηκευμένες αναζητήσεις επιτρέπει πλέον κάθετη κύλιση, ώστε τα εργαλεία και το κουμπί εκκίνησης να παραμένουν προσβάσιμα και σε μικρότερη οθόνη ή αυξημένη κλίμακα Windows.',
'Καμία αλλαγή στους παρόχους, στα 15 presets, στη βάση LRCLIB, στο Greek G2G AI, στις επαληθεύσεις υποψήφιων στίχων, στα MP3/ID3 ή στα ήδη υπάρχοντα LRC. Τα χρώματα δεν πιστοποιούν την ορθότητα των στίχων.',
'Οι αυτόματες δοκιμές ελέγχουν αντίθεση κειμένου, εναλλαγή εμφάνισης και γλώσσας, αποθήκευση προτιμήσεων, προστασία καταγραφών και εκκίνηση του αυτόνομου Windows EXE.',
]))



# Additive bilingual chapter: old detailed pages remain intact.
en_sections.insert(0,('v2.9.6 - Cumulative lyrics source tiers',[
'In Saved searches, select the new Provider pack / cumulative tier menu. This is separate from the original Provider mode FAST/FULL control. Existing profiles default to Legacy and continue to use their old source lists until you deliberately pick a tier.',
'Tier 1 CORE: LRCLIB + SyncLRC + Unison (3 providers). Tier 2 CORE + LrcAPI: adds LrcAPI (4). Tier 3 BROAD: adds NetEase, Musixmatch and Megalobiz (7). Tier 4 EXTENDED: adds LiriQo and BetterKuGou (9). Tier 5 MAXIMUM: adds BetterQQ, YouLyTTML, BetterTTML and Tencent (13). Tier 6 EXPERIMENTAL ALL: adds SimpMusic (14). Every higher tier retains all previous lower-tier providers, in order.',
'The Tier menu only changes selected online sources: it NEVER silently changes Greek mode, MusicBrainz, song limit, search action or offline database. Offline-only action 4 remains a local SQLite search without internet. Save under a fresh profile name if you want to keep different custom source choices.',
'DEFAULT provider order uses the tier sequence, SMART uses locally recorded verified saves per second when sufficient measurements exist, and CUSTOM requires exactly all providers within the selected tier, once each, comma separated. Custom is ordering, not removing individual providers.',
'BetterQQ is a new public QRC XML timing source added only in advanced tiers. Because the API response does not independently verify resolved recording title, artist or duration, QQ results are exported only as .candidate.lrc and never auto-installed as verified LRC. The existing strict artist/title/version/duration checks for other sources remain unchanged.',
'User diagnostics showed 979 logged historical attempts but a separate CSV had zero totals, so do not interpret that CSV as evidence a provider is dead. The experimental sources may timeout, return access restrictions or provide review-only results. Rate limits and Retry-After must be respected.',
'Recommended first acceptance test: set Search action 1, 20 songs, Tier 1, run; then keep the same songs and use Tier 2 to compare coverage, finally higher tiers if useful. Watch Provider health and source statistics, and inspect manual review candidates before installing lyrics.',
]))
greek_sections.insert(0,('36  Έκδοση 2.9.6: αθροιστικά επίπεδα πηγών',[
'Στην καρτέλα Αποθηκευμένες αναζητήσεις υπάρχει νέα επιλογή Πακέτο παρόχων / αθροιστικό επίπεδο. Τα ήδη αποθηκευμένα προφίλ συνεχίζουν με το παλιό FAST/FULL μέχρι να επιλέξετε ρητά νέο επίπεδο.',
'Επίπεδο 1: LRCLIB, SyncLRC, Unison (3 πηγές). Επίπεδο 2: οι τρεις προηγούμενες συν LrcAPI (4). Επίπεδο 3: συν NetEase, Musixmatch, Megalobiz (7). Επίπεδο 4: συν LiriQo και BetterKuGou (9). Επίπεδο 5: συν BetterQQ, YouLyTTML, BetterTTML, Tencent (13). Επίπεδο 6: συν την πειραματική SimpMusic (14). Κάθε επόμενο επίπεδο περιλαμβάνει όλες τις προηγούμενες πηγές.',
'Η επιλογή επιπέδου ΔΕΝ αλλάζει αριθμό τραγουδιών, λειτουργία offline ή online, ελληνική μετατροπή, MusicBrainz, G2G AI ή αποθηκευμένα MP3. Η λειτουργία μόνο offline εξακολουθεί να χρησιμοποιεί την τοπική βάση χωρίς διαδικτυακά αιτήματα.',
'Ο νέος πάροχος BetterQQ επιστρέφει QRC XML με χρονισμούς λέξεων που μετατρέπονται σε απλό LRC ανά στίχο. Επειδή δεν διαθέτει επαληθευμένη ταυτότητα και διάρκεια ηχογράφησης, τα αποτελέσματα αποθηκεύονται ΜΟΝΟ ως υποψήφια προς χειροκίνητο έλεγχο και όχι ως επιβεβαιωμένα LRC.',
'Η σειρά DEFAULT ακολουθεί τη σειρά του επιπέδου, η SMART βασίζεται σε πραγματικές επιβεβαιωμένες αποθηκεύσεις και η CUSTOM απαιτεί ολόκληρη τη λίστα παρόχων του συγκεκριμένου επιπέδου χωρίς διπλότυπα.',
'Τα διαγνωστικά αρχεία χρήστη περιείχαν 979 προσπάθειες σε JSONL αλλά μηδενικά σύνολα στο αντίστοιχο CSV. Τα μηδενικά δεν αποδεικνύουν ότι οι πηγές είναι ανενεργές. Οι πειραματικοί πάροχοι μπορεί να έχουν timeout ή περιορισμούς πρόσβασης. Τα υπάρχοντα MP3/ID3/LRC παραμένουν ανέπαφα.',
'Προτείνεται δοκιμή 20 τραγουδιών με Επίπεδο 1 και στη συνέχεια Επίπεδο 2, ώστε να φανεί αν προστέθηκαν χρήσιμα αποτελέσματα. Ελέγξτε την καρτέλα υγείας παρόχων και τα υποψήφια LRC πριν από χειροκίνητη εγκατάσταση.',
]))



# 2.9.7 release chapter: two requested features only.
en_sections.insert(0,('v2.9.7 - Provider benchmark and per-source exclusions',[
'Open Provider health and press Test My Providers. Choose 5, 10 or 20 songs from your selected library. The Control Center will ask permission before ANY live online API requests. The ordinary Offline-only search action is not changed; the benchmark itself is explicitly online. For a new collection, start with 5 tracks.',
'The benchmark uses a stable shuffled sample across the library and independently checks each enabled provider. It counts metadata-verified matches, unique verified matches attributed to the first source in current tier order, review-only candidates, clean misses, timeouts, network errors, unavailable providers, and average seconds per attempted track.',
'Benchmark NEVER creates or overwrites an MP3, ID3 tag, original .lrc, .candidate.lrc, search checkpoint, or ordinary lyric-search journal. It writes ONLY a summary CSV containing provider aggregates under AppData/LRCBulkFinder/benchmarks. Real providers can still require updating their normal safety cooldown state. The summary deliberately excludes filenames, title and artist metadata.',
'Use Stop benchmark to stop its own worker and return to Control Center. If the worker is killed immediately, a partial report might not be generated. The benchmark does not run simultaneously with an ordinary search or with a Greek AI installation.',
'On Saved searches, choose a source tier, then use Individual provider exclusions checkboxes. Untick any unwanted provider and save the profile. The application validates the names, forbids excluding EVERY source, and skips excluded providers from normal searches and future benchmark runs. Old profiles have no exclusions and continue to work without migration.',
'All Tier 1-6 packs REMAIN cumulative and unchanged. Exclusion preferences are individual to saved profiles. If CUSTOM order is enabled, continue to specify every source in the underlying tier, then the app removes excluded sources after ordering. This preserves the custom order if a source is enabled again. Offline-only mode makes no lyrics-provider network requests.',
'For comparison, run the same 5/10/20 song size against two nearby tiers. The sampled tracks are deterministic for the same library; an absent verified match is not proof that a provider is dead. Real third-party API reliability, access restrictions and performance need on-device acceptance testing.',
]))
greek_sections.insert(0,('37  Έκδοση 2.9.7: Benchmark παρόχων και εξαίρεση πηγών',[
'Στην καρτέλα Κατάσταση παρόχων πατήστε Test My Providers και επιλέξτε δείγμα 5, 10 ή 20 τραγουδιών. Απαιτείται ρητή επιβεβαίωση, επειδή η δοκιμή επικοινωνεί διαδικτυακά με τους παρόχους ακόμη κι αν η συνήθης αναζήτηση είναι σε λειτουργία offline.',
'Το εργαλείο δοκιμάζει ξεχωριστά κάθε ενεργή πηγή και υπολογίζει επιβεβαιωμένα αποτελέσματα, μοναδική συνεισφορά, υποψήφιους στίχους προς έλεγχο, κανονικές αποτυχίες εύρεσης, timeouts, σφάλματα, παραλείψεις και μέσο χρόνο απόκρισης. Το σταθερό δείγμα επιτρέπει δίκαιες συγκρίσεις επιπέδων.',
'Το benchmark ΔΕΝ γράφει ή τροποποιεί MP3, ID3, υπάρχοντα LRC, υποψήφια LRC ή αρχεία προόδου αναζήτησης. Αποθηκεύει μόνο συνοπτικό CSV χωρίς ονόματα τραγουδιών μέσα στον προσωπικό φάκελο AppData/LRCBulkFinder/benchmarks. Μπορεί να ενημερώνεται ο απαραίτητος μηχανισμός προσωρινής αναστολής παρόχων για λόγους ορίων χρήσης.',
'Με το Stop benchmark σταματά ο ξεχωριστός worker χωρίς να κλείσει η εφαρμογή. Σε άμεση αναγκαστική διακοπή ίσως δεν δημιουργηθεί μερικό CSV. Η κανονική αναζήτηση και η εγκατάσταση Greek AI δεν εκτελούνται ταυτόχρονα με το benchmark.',
'Στην καρτέλα Αποθηκευμένες αναζητήσεις επιλέξτε Tier 1-6 και στο πλαίσιο Individual provider exclusions αποεπιλέξτε όποιες πηγές δεν θέλετε. Αποθηκεύστε το προφίλ. Χρειάζεται να παραμείνει τουλάχιστον μία ενεργή πηγή. Τα παλιότερα προφίλ φορτώνονται χωρίς καμία εξαίρεση.',
'Τα υπάρχοντα αθροιστικά επίπεδα παραμένουν απαράλλαχτα. Η επιλογή CUSTOM περιγράφει όλες τις πηγές του επιπέδου και η αφαίρεση γίνεται κατά την εκτέλεση, ώστε να μην χάνεται η προσωπική σειρά αν ξαναενεργοποιήσετε μία πηγή. Η λειτουργία Offline only εξακολουθεί να μην επικοινωνεί με online παρόχους.',
'Συγκρίνετε πρώτα 5 τραγούδια στο Tier 1 και κατόπιν στο Tier 2. Ένα κενό αποτέλεσμα δεν αποδεικνύει ότι μία πηγή είναι μόνιμα εκτός λειτουργίας. Οι πραγματικοί χρόνοι και η διαθεσιμότητα χρειάζονται δοκιμή στον δικό σας υπολογιστή.',
]))


def build():
    if not OLD.is_file():raise FileNotFoundError(OLD)
    en_out=OUT/'LRC_Bulk_Finder_v2_9_7_Complete_User_Manual_EN.pdf'
    gr_out=OUT/'LRC_Bulk_Finder_v2_9_7_User_Guide_EL.pdf'
    addon=OUT/'_v294_en_addendum.pdf'
    make_pdf(addon,'English/Greek UI — v2.9.7 addendum','Please read these changes together with the complete 29-page original manual.',en_sections,'EN')
    src=fitz.open(str(OLD))
    for page_index,page in enumerate(src):
        # Both spellings keep their exact width; update references conservatively.
        for old,new in [('2.4.3','2.9.2'),('2_4_3','2_9_2')]:
            for box in page.search_for(old):
                # Modify the exact text region only, avoid white overlays on cover.
                info=page.get_text('dict',clip=box)
                sizes=[span['size'] for block in info['blocks'] if 'lines' in block for line in block['lines'] for span in line['spans']]
                size=min(13, max(7.2, min(sizes) if sizes else 9.5))
                page.add_redact_annot(box,fill=((17/255,40/255,59/255) if page_index==0 else (1,1,1)))
                page.apply_redactions(images=0,graphics=0)
                page.insert_text((box.x0,box.y1-1),new,fontsize=size,fontname='helv',color=((1,1,1) if page_index==0 else (0.08,0.20,0.36)))
    # Original document kept at its original page positions so page references stay correct.
    add=fitz.open(str(addon));src.insert_pdf(add)
    src.set_metadata({**src.metadata,'title':'LRC Bulk Finder v2.9.7 - Complete English Manual','subject':'Approved English/Greek interface edition'})
    src.save(str(en_out),garbage=4,deflate=True)
    src.close();add.close()
    make_pdf(gr_out,'ΑΝΑΛΥΤΙΚΟΣ ΟΔΗΓΟΣ ΧΡΗΣΗΣ','Εγκατάσταση, αλλαγή γλώσσας, αναζήτηση στίχων, έλεγχος αποτελεσμάτων και ασφαλής διακοπή.',greek_sections,'Ελληνικά')
    with fitz.open(str(en_out)) as check:
        assert len(check)>=31
        text='\n'.join(p.get_text() for p in check)
        assert 'v2.9.7' in text
        assert 'v2.4.3' not in text and 'v2_4_3' not in text
    with fitz.open(str(gr_out)) as check:
        text='\n'.join(p.get_text() for p in check)
        assert 'Αποθηκευμένες αναζητήσεις' in text
        assert len(check)>=4
    print('PASS manuals:',en_out.name,gr_out.name)
    return en_out,gr_out
if __name__=='__main__':build()
