"""Offline v2.1.19 Greek artist identity and bilingual title regression tests."""
import sys
import types
import unittest
sys.modules.setdefault('syncedlyrics',types.SimpleNamespace(search=lambda *a,**k:None))
import LRC_Bulk_Finder as app


class NeverTrustArtistAI:
    def __init__(self):
        self.calls=[]
    def convert(self,text,kind='title'):
        self.calls.append((text,kind))
        if kind=='artist':
            return 'γιοργος αλκαιος','REVIEW_UNACCENTED'
        return 'σεξυ κοριτσια','REVIEW_UNACCENTED'


class GreekArtistRegression(unittest.TestCase):
    def setUp(self):
        app.GREEK_MODE=True
        app.MB_ENABLED=False
        app.G2G_SONG_PLANS.clear()
        app.MB_CACHE.clear()
        app.GREEK_ARTIST_ALIASES.clear()
        app.GREEK_TITLE_ALIASES.clear()
        app.load_aliases()
        app.load_greek_words()

    def test_exact_provided_artist_examples(self):
        wanted={
            'Giorgos Alkaios':'Γιώργος Αλκαίος',
            'Alkinoos Ioannidis':'Αλκίνοος Ιωαννίδης',
            'Alinoos Ioannidis':'Αλκίνοος Ιωαννίδης',
            'Ditikes Sinikies':'Δυτικές Συνοικίες',
            'Antidrasi':'Αντίδραση',
            'Giorgos Mazwnakis':'Γιώργος Μαζωνάκης',
            'Despoina Vandi':'Δέσποινα Βανδή',
            'Ksilina Spathia':'Ξύλινα Σπαθιά',
            'Ypogeia Revmata':'Υπόγεια Ρεύματα',
            'Pyx Lax':'Πυξ Λαξ',
            'Giannis Miliokas':'Γιάννης Μηλιώκας',
            'Filippos Pliatsikas':'Φίλιππος Πλιάτσικας',
        }
        for roman,greek in wanted.items():
            with self.subTest(roman=roman):
                self.assertEqual(app.approved_artist_alias(roman),greek)

    def test_original_name_kept_and_approved_name_second_for_lrclib(self):
        ai=NeverTrustArtistAI()
        cases=[
          ('Kimata','Giorgos Alkaios','Κύματα','Γιώργος Αλκαίος'),
          ('Mesanychta Savvatou','Alkinoos Ioannidis',
           'Μεσάνυχτα Σαββάτου','Αλκίνοος Ιωαννίδης'),
          ('Sexy koritsia','Ditikes Sinikies','Sexy κορίτσια','Δυτικές Συνοικίες'),
          ('Antidrasi','Antidrasi','Αντίδραση','Αντίδραση'),
        ]
        for title,artist,translated,official in cases:
            with self.subTest(title=title,artist=artist):
                app.G2G_SONG_PLANS.clear()
                p=app.precompute_greek_plan(title,artist,ai)
                self.assertEqual(p['Greek title alternative'],translated)
                self.assertEqual(p['Greek artist alternative'],official)
                self.assertEqual(p['artist origin'],'APPROVED_ARTIST')
                variants=app.query_variants(title,artist)
                self.assertEqual(variants[0],(title,artist))
                self.assertEqual(variants[1],(title,official))
                self.assertEqual(variants[2],(translated,official))
                self.assertFalse(any(kind=='artist' for _,kind in ai.calls))

    def test_unknown_artist_is_never_transliterated_from_ai(self):
        ai=NeverTrustArtistAI()
        p=app.precompute_greek_plan('Kimata','A Completely Unknown Artist',ai)
        self.assertEqual(p['Greek artist alternative'],'')
        self.assertIn('SKIP_UNVERIFIED_ARTIST_G2G',p['AI artist flag'])
        self.assertFalse(any(kind=='artist' for _,kind in ai.calls))
        self.assertTrue(all(a=='A Completely Unknown Artist' for _,a in app.query_variants(
            'Kimata','A Completely Unknown Artist')))

    def test_safe_brand_identity_is_preserved(self):
        for artist in ['2002 GR','Magic De Spell','Unknown DJ Brand']:
            with self.subTest(artist=artist):
                self.assertFalse(app.approved_artist_alias(artist))
        p=app.precompute_greek_plan('Fonazo','2002 GR',NeverTrustArtistAI())
        self.assertEqual(p['Greek artist alternative'],'')
        self.assertEqual(app.query_variants('Fonazo','2002 GR'),
                         [('Fonazo','2002 GR'),('Φωνάζω','2002 GR')])

    def test_mixed_credits_all_verifiable_only(self):
        self.assertEqual(app.approved_artist_alias('Filippos Pliatsikas, Antonis Remos'),
                         'Φίλιππος Πλιάτσικας, Αντώνης Ρέμος')
        self.assertEqual(app.approved_artist_alias('2002 GR, Ilias Asvestopoulos'),
                         '2002 GR, Ηλίας Ασβεστόπουλος')
        self.assertEqual(app.approved_artist_alias('Sakis Rouvas & Katy Garbi'),
                         'Σάκης Ρουβάς & Καίτη Γαρμπή')
        self.assertEqual(app.approved_artist_alias('Giorgos Alkaios, Random Unknown'),
                         '')

    def test_greek_words_are_not_artist_names(self):
        # Context sensitive: the word Αντίδραση is not interchangeable with
        # the verb 'αντιδράσει'. This identity is a full artist alias.
        self.assertEqual(app.dictionary_greek_title('Antidrasi'),'Αντίδραση')
        self.assertFalse(app.approved_artist_alias('antidrasei'))

    def test_manual_override_still_wins(self):
        app.GREEK_ARTIST_ALIASES[app.normalize('Giorgos Alkaios')]='Γιώργος Αλκαίος (Custom)'
        self.assertEqual(app.approved_artist_alias('Giorgos Alkaios'),
                         'Γιώργος Αλκαίος (Custom)')

    def test_musicbrainz_does_not_displace_official_artist_query(self):
        p=app.precompute_greek_plan('Kimata','Giorgos Alkaios',NeverTrustArtistAI())
        app.MB_ENABLED=True
        app.MB_CACHE[(app.normalize('Kimata'),app.normalize('Giorgos Alkaios'))]=(
            'Κύματα','Γιώργος Αλκαίος')
        q=app.query_variants('Kimata','Giorgos Alkaios')
        self.assertEqual(q[0],('Kimata','Giorgos Alkaios'))
        self.assertEqual(q[1],('Kimata','Γιώργος Αλκαίος'))
        self.assertEqual(len(q),3)
        app.MB_ENABLED=False


if __name__=='__main__':
    unittest.main(verbosity=2)
