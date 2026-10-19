"""Offline v2.1.17 Greeklish title quality regressions: no AI download or HTTP."""
import types
import unittest
from unittest import mock
import sys

sys.modules.setdefault('syncedlyrics',types.SimpleNamespace(search=lambda *a,**k:None))
import LRC_Bulk_Finder as app
from g2g_integration import english_skip


class FakeAI:
    def __init__(self, title='φωναζο', artist='2002 γρ'):
        self.title=title
        self.artist=artist
        self.calls=[]
    def convert(self,text,kind='title'):
        self.calls.append((text,kind))
        return (self.title if kind=='title' else self.artist,'REVIEW_UNACCENTED')


class GreekTitleQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.load_greek_words()
    def setUp(self):
        app.GREEK_MODE=True
        app.G2G_SONG_PLANS.clear()
        app.MB_CACHE.clear()
        app.GREEK_TITLE_ALIASES.clear()
        app.GREEK_ARTIST_ALIASES.clear()

    def test_fonazo_correct_spelling_beats_cached_ai(self):
        ai=FakeAI()
        plan=app.precompute_greek_plan('Fonazo','2002 GR',ai)
        self.assertEqual(plan['Greek title alternative'],'Φωνάζω')
        self.assertEqual(plan['title origin'],'DICTIONARY_TITLE')
        self.assertEqual(ai.calls,[])

    def test_user_examples_have_correct_accents(self):
        examples=[
            ('Den Ise Erotas Esi','Δεν Είσαι Έρωτας Εσύ'),
            ('Den Eisai Erotas Esy','Δεν Είσαι Έρωτας Εσύ'),
            ('Esy Horeveis Kai Ego Pethaino','Εσύ Χορεύεις Και Εγώ Πεθαίνω'),
            ('Fevgis Ke Hanese','Φεύγεις Και Χάνεσαι'),
            ('Diadromi','Διαδρομή'),
            ('Barouti','Μπαρούτι'),
            ('Avrio','Αύριο'),
            ('Nyhtes','Νύχτες'),
            ('Diastimoploio','Διαστημόπλοιο'),
            ('Fovamai','Φοβάμαι'),
            ('Ah Maria','Αχ Μαρία'),
        ]
        for original,correct in examples:
            with self.subTest(title=original):
                self.assertEqual(app.dictionary_greek_title(original),correct)

    def test_year_numbers_hyphens_and_punctuation_preserved(self):
        self.assertEqual(app.dictionary_greek_title('2002 Nyhtes'),'2002 Νύχτες')
        self.assertEqual(app.dictionary_greek_title('Ah-Kaimeni'),'Αχ-καημένη')
        self.assertEqual(app.dictionary_greek_title("Ego De Sou Eipa S' Agapo"),
                         "Εγώ Δε Σου Είπα Σ' Αγαπώ")

    def test_english_title_never_turned_into_phonetic_greek(self):
        for title in ['Best of Times','Best Music','Happy Birthday','Love You Forever']:
            with self.subTest(title=title):
                self.assertTrue(english_skip(title,'title'))
                self.assertIsNone(app.dictionary_greek_title(title))
                ai=FakeAI(title='βεστ οστ οτιμες')
                plan=app.precompute_greek_plan(title,'2002 GR',ai)
                self.assertEqual(plan['Greek title alternative'],'')
                self.assertFalse(ai.calls)

    def test_preserve_remix_and_remastered_suffix(self):
        ai=FakeAI()
        cases=[
            ('Fonazo - 2025 Remastered','Φωνάζω - 2025 Remastered'),
            ('Den Ise Erotas Esi - Extended Remix',
             'Δεν Είσαι Έρωτας Εσύ - Extended Remix'),
            ('Esy Horeveis Kai Ego Pethaino - 2024 Remix',
             'Εσύ Χορεύεις Και Εγώ Πεθαίνω - 2024 Remix')
        ]
        for title, expected in cases:
            with self.subTest(title=title):
                self.assertEqual(app.precompute_greek_plan(title,'2002 GR',ai)['Greek title alternative'],
                                 expected)

    def test_original_query_stays_first_and_artist_preserved(self):
        plan=app.precompute_greek_plan('Fonazo','2002 GR',FakeAI())
        self.assertEqual(plan['Greek artist alternative'],'')
        self.assertEqual(app.query_variants('Fonazo','2002 GR'),
                         [('Fonazo','2002 GR'),('Φωνάζω','2002 GR')])

    def test_english_mixed_artist_brand_not_transliterated(self):
        for artist in ['2002 GR','Costas Critikos, 2002 GR, Meditelectro',
                       '2002 GR, Ilias Asvestopoulos','DJ Kostas',
                       'MC TheBand']:
            with self.subTest(artist=artist):
                self.assertFalse(app.safe_to_convert_artist(artist))
                ai=FakeAI()
                app.precompute_greek_plan('Fonazo',artist,ai)
                self.assertFalse(any(kind=='artist' for _,kind in ai.calls))

    def test_user_defined_title_alias_wins_over_dict_and_ai(self):
        app.GREEK_TITLE_ALIASES['fonazo']='Φώναξέ με'
        ai=FakeAI()
        plan=app.precompute_greek_plan('Fonazo','2002 GR',ai)
        self.assertEqual(plan['Greek title alternative'],'Φώναξέ με')
        self.assertEqual(plan['title origin'],'MANUAL_TITLE')
        self.assertEqual(ai.calls,[])

    def test_fallback_ai_corrects_only_aligned_known_tokens(self):
        self.assertEqual(app.patch_known_greek_words('Esy Unlisted','εσει αστατο'),
                         'Εσύ αστατο')
        self.assertEqual(app.patch_known_greek_words('Esy Two Words','εσει αστατο'),
                         'εσει αστατο')

    def test_ai_output_is_not_assumed_verified(self):
        ai=FakeAI(title='εσει αστατο')
        plan=app.precompute_greek_plan('Esy Unlisted','2002 GR',ai)
        self.assertEqual(plan['title origin'],'AI_TITLE')
        self.assertEqual(plan['Greek title alternative'],'Εσύ αστατο')
        self.assertIn('REVIEW_AI_SPELLING',plan['review flag'])
        self.assertEqual(plan['AI title output'],'εσει αστατο')
        self.assertEqual(plan['AI title flag'],
                         'REVIEW_UNACCENTED; DICTIONARY_WORD_CORRECTIONS')

    def test_artist_g2g_allowed_when_no_brand_or_multi_credits(self):
        self.assertTrue(app.safe_to_convert_artist('Ilias Asvestopoulos'))
        self.assertFalse(app.safe_to_convert_artist('2002 GR, Ilias Asvestopoulos'))


if __name__=='__main__':
    unittest.main(verbosity=2)
