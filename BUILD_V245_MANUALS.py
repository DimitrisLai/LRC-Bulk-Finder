"""Create release v2.4.5 English full manual and Greek guided manual; no web calls.
The English v2.4.3 manual is preserved page-for-page, with version references
updated and a new clearly separated v2.4.5 bilingual section appended.
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
        c.drawString(46,28,f'LRC Bulk Finder v2.4.5  |  {lang}  |  Public Beta')
        c.drawRightString(w-46,28,str(doc.page))
        c.restoreState()
    doc=SimpleDocTemplate(str(path),pagesize=A4,topMargin=48,bottomMargin=58,leftMargin=48,rightMargin=48,allowSplitting=1,
                          title=f'LRC Bulk Finder v2.4.5 — {lang} User Manual',author='Dimitris L.')
    items=[Spacer(1,64),para('LRC BULK FINDER',Cover),para('v2.4.5  |  ENGLISH + ΕΛΛΗΝΙΚΑ',CoverSub),Spacer(1,19),para(title,H),para(subtitle,Body),Spacer(1,27),para('PUBLIC BETA  •  Windows  •  October 2026',Sub),para('Created by Dimitris L. — official open-source project, MIT License.',Small),Spacer(1,30),para('This guide covers the two-language graphical interface, ordinary searches, offline mode, candidate review, STOP/resume and data protection.',Small),PageBreak()]
    for heading,paras in sections:
        items.append(para(heading,H))
        for p in paras:
            if p.startswith('• '):items.append(para('– '+p[2:],Bul))
            elif p.startswith('## '):items.append(para(p[3:],Sub))
            else:items.append(para(p,Body))
    doc.build(items,onFirstPage=footer,onLaterPages=footer)

en_sections=[
('v2.4.5 — Beginner Quick Search',[
 '1. Open the new Quick Search tab. Choose a music folder, then select Test 20 songs or All songs.',
 '2. Select Include subfolders if required. Enable Greek/Greeklish matching if your collection contains Greek names. Press START QUICK SEARCH.',
 '3. This shortcut chooses action 1 (online), FAST providers and default provider order. It requires no downloaded LRCLIB SQLite snapshot. The advanced Saved searches tab remains fully available for offline-first scans and precise settings.',
 '4. Quick Search saves its settings as Quick Search v2.4.5 under your user account. Replacing those saved settings requires confirmation. It never changes original audio or ID3 tags.',
]),
('v2.4.5 — Results dashboard',[
 'The Results dashboard reads your chosen folder and, optionally, subfolders. Press Refresh results. This is a read-only inventory: no tags, music or LRC files are edited.',
 'Filter by Has LRC, Needs review, Missing LRC or Ambiguous audio. Search filenames, open the selected audio externally, or navigate to Candidate review. Export CSV creates a new report and refuses to overwrite an existing one.',
 'Has LRC means a sidecar exists; it is NOT a claim that the lyric text or synchronization is correct. Missing LRC includes files that have no LRC or review candidate. Scans over 100,000 tracks require a smaller folder.',
]),
('v2.4.5 — Safe timing repair',[
 'Open Timing repair, select an audio track and its matching existing .lrc in the SAME directory, and enter a positive or negative number of seconds. Positive delays subtitles; negative brings them earlier. Use Preview shifted lyrics.',
 'The correction shifts supported [mm:ss.xx] timestamps by the same offset while preserving lyric text and metadata lines. If the offset would produce a negative timestamp, the tool refuses it rather than silently clamping.',
 'Press Save UNVERIFIED candidate only after listening and confirming the preview. The application writes a NEW .candidate.lrc or numbered .candidate.2.lrc file. It never overwrites the original audio or existing .lrc. Even corrected timing remains UNVERIFIED until reviewed.',
]),
('v2.4.5 — Updates and diagnostics',[
 'Quick Search includes Check for updates. It contacts only the official GitHub release API when you explicitly click; there is no automatic upload or automatic executable installation. If a newer release is available, use Open new GitHub release.',
 'Save diagnostics creates a local TXT file with application version, operating system and companion worker status. It intentionally does not include filenames, library paths, music titles, lyrics, tags, credentials or environmental variables. The destination is chosen by you and existing reports are protected.',
]),

('v2.4.5: Switch the interface language',[
 'At the top-right of the Control Center, use Interface language / Γλώσσα εφαρμογής and select English or Ελληνικά. You do not need to restart. The active tab, values, profiles, and running search remain in place. The language choice is remembered for the next time you open the application.',
 'Only the user interface changes language: labels, tooltips, messages, common statuses and warnings. Lyrics, artist/title metadata, saved search keys, provider names, internal machine codes (such as NO_MATCH), audio files and report formats are not translated.',
 'If you share the application, new users start in English. Each Windows user may select Greek independently. No online account is needed to change the display language.',
 '## Greek UI examples',
 'Saved searches → Αποθηκευμένες αναζητήσεις; Live progress → Ζωντανή πρόοδος; Candidate review → Έλεγχος υποψήφιων στίχων; Provider health → Κατάσταση πηγών στίχων; Save profile → Αποθήκευση προφίλ.',
]),
('How to install the new Windows edition',[
 'Download the v2.4.5 standalone Windows GUI ZIP from the official GitHub Releases page. Extract the WHOLE archive first. Keep LRC_Control_Center.exe and LRC_Bulk_Finder_Worker.exe together with dictionaries, the instructions and manual.',
 'Double-click LRC_Control_Center.exe. Neither Python nor a separate installation is required for the ordinary standalone edition. You can change language immediately at the top-right.',
 'If you want the optional local Greek AI setup scripts or the full command-line menu, obtain the v2.4.5 Python/CMD source package instead, and install Python 3.10 or newer with required dependencies.',
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
 'The STOP implementation in v2.4.5 uses a native Windows process snapshot before falling back to PowerShell. This avoids unnecessary dependence on slow PowerShell startup but cannot guarantee every unusual machine state.',
 'Candidate lyrics must not be treated as verified. The manual Promote action is explicitly marked UNVERIFIED and never overwrites an existing approved .lrc.',
]),
('Where settings are kept / troubleshooting',[
 'Saved search profiles and the interface-language preference are separate local settings. On Windows, they live under your own application-data directory (APPDATA/LRCBulkFinder). Changing English/Greek must not change a search profile.',
 'If the GUI launches but searches fail, confirm music-folder permissions, metadata, installed companion worker, database path and internet connection. If online providers return rate limits or timeouts, consult reports and retry only genuinely timed-out checks.',
 'Large offline LRCLIB dumps are external downloads and are NOT bundled in the standalone ZIP. The small Greek words SQLite shipped with the application is not the large LRCLIB database.',
 'Provider services and lyric copyright restrictions are external. The application cannot guarantee synchronized lyrics for every recording. Review the source data and player compatibility before sharing files.',
]),
('For the detailed workflows',[
 'The complete chapters earlier in the English manual remain applicable to v2.4.5 unless this bilingual addendum explicitly changes a step. All original tabs and classic console options remain available; v2.4.5 adds Quick Search, Results dashboard and Timing repair.',
 'Project and issues: https://github.com/DimitrisLai/LRC-Bulk-Finder',
])]

greek_sections=[
('13  Γρήγορη αναζήτηση (v2.4.5)',[
 'Στην καρτέλα «Γρήγορη αναζήτηση» επιλέξτε φάκελο μουσικής, δοκιμή 20 τραγουδιών ή όλα τα τραγούδια και, αν χρειάζεται, υποφακέλους και αντιστοίχιση Ελληνικών/Greeklish.',
 'Πατήστε «ΕΝΑΡΞΗ ΓΡΗΓΟΡΗΣ ΑΝΑΖΗΤΗΣΗΣ». Χρησιμοποιούνται οι γρήγορες διαδικτυακές πηγές και δεν απαιτείται μεγάλη τοπική βάση LRCLIB. Οι προχωρημένες ρυθμίσεις παραμένουν διαθέσιμες στην καρτέλα αποθηκευμένων αναζητήσεων.',
 'Τα πρωτότυπα αρχεία ήχου και οι ετικέτες τους δεν τροποποιούνται. Οι ρυθμίσεις της γρήγορης αναζήτησης αποθηκεύονται σε ξεχωριστό προφίλ.',
]),
('14  Πίνακας αποτελεσμάτων (v2.4.5)',[
 'Ο «Πίνακας αποτελεσμάτων» διαβάζει μόνο τα ονόματα αρχείων και την ύπαρξη αρχείων LRC. Πατήστε «Ανανέωση αποτελεσμάτων» για να δείτε το σύνολο της βιβλιοθήκης.',
 'Μπορείτε να φιλτράρετε τα τραγούδια που διαθέτουν LRC, όσα χρειάζονται έλεγχο και όσα δεν διαθέτουν LRC, να αναζητήσετε όνομα αρχείου ή να κάνετε εξαγωγή CSV χωρίς αντικατάσταση υπάρχουσας αναφοράς.',
 'Η ένδειξη «Υπάρχει LRC» δεν σημαίνει ότι οι στίχοι είναι επαληθευμένοι ή συγχρονισμένοι σωστά. Η αναφορά είναι μόνο μια επισκόπηση.',
]),
('15  Ασφαλής διόρθωση χρονισμού (v2.4.5)',[
 'Επιλέξτε την καρτέλα «Διόρθωση χρονισμού», το αρχείο ήχου και το αντίστοιχο συγχρονισμένο LRC από τον ίδιο φάκελο.',
 'Εισαγάγετε μετατόπιση σε δευτερόλεπτα: θετική τιμή σημαίνει ότι οι στίχοι θα εμφανίζονται αργότερα, αρνητική νωρίτερα. Πατήστε προεπισκόπηση, ακούστε το τραγούδι και ελέγξτε το αποτέλεσμα.',
 'Η αποθήκευση δημιουργεί μόνο νέο ΜΗ ΕΠΑΛΗΘΕΥΜΕΝΟ αρχείο .candidate.lrc, με αρίθμηση όταν χρειάζεται. Το αρχικό .lrc και ο ήχος παραμένουν αμετάβλητα και η εφαρμογή αρνείται χρονικές σημάνσεις πριν από το 0.',
]),
('16  Ενημερώσεις και διαγνωστικά (v2.4.5)',[
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
 '2. Κατεβάστε το αρχείο LRC_Bulk_Finder_v2_4_5_Standalone_Windows_GUI.zip, εφόσον θέλετε την εύκολη έκδοση χωρίς εγκατάσταση Python.',
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
 'Στην έκδοση 2.4.5 ο έλεγχος των Windows χρησιμοποιεί πρώτα τη φυσική λειτουργία καταγραφής διεργασιών του συστήματος, με εναλλακτικό μηχανισμό ελέγχου όπου χρειάζεται.',
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

def build():
    if not OLD.is_file():raise FileNotFoundError(OLD)
    en_out=OUT/'LRC_Bulk_Finder_v2_4_5_Complete_User_Manual_EN.pdf'
    gr_out=OUT/'LRC_Bulk_Finder_v2_4_5_User_Guide_EL.pdf'
    addon=OUT/'_v245_en_addendum.pdf'
    make_pdf(addon,'English/Greek UI — v2.4.5 addendum','Please read these changes together with the complete 29-page original manual.',en_sections,'EN')
    src=fitz.open(str(OLD))
    for page_index,page in enumerate(src):
        # Both spellings keep their exact width; update references conservatively.
        for old,new in [('2.4.3','2.4.5'),('2_4_3','2_4_5')]:
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
    src.set_metadata({**src.metadata,'title':'LRC Bulk Finder v2.4.5 - Complete English Manual','subject':'Approved English/Greek interface edition'})
    src.save(str(en_out),garbage=4,deflate=True)
    src.close();add.close()
    make_pdf(gr_out,'ΑΝΑΛΥΤΙΚΟΣ ΟΔΗΓΟΣ ΧΡΗΣΗΣ','Εγκατάσταση, αλλαγή γλώσσας, αναζήτηση στίχων, έλεγχος αποτελεσμάτων και ασφαλής διακοπή.',greek_sections,'Ελληνικά')
    with fitz.open(str(en_out)) as check:
        assert len(check)>=31
        text='\n'.join(p.get_text() for p in check)
        assert 'v2.4.5' in text
        assert 'v2.4.3' not in text and 'v2_4_3' not in text
    with fitz.open(str(gr_out)) as check:
        text='\n'.join(p.get_text() for p in check)
        assert 'Αποθηκευμένες αναζητήσεις' in text
        assert len(check)>=4
    print('PASS manuals:',en_out.name,gr_out.name)
    return en_out,gr_out
if __name__=='__main__':build()
