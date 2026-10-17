"""Public-edition basic offline smoke tests. No HTTP requests."""
import csv,unittest,tempfile
from pathlib import Path
import sys,types
sys.modules.setdefault('syncedlyrics',types.SimpleNamespace(search=lambda *args,**kwargs: None))
import LRC_Bulk_Finder as app
from g2g_integration import G2GManager
class PublicPackageTests(unittest.TestCase):
 def test_no_presupplied_private_aliases(self):
  with (Path(__file__).with_name('Greek_Aliases.csv')).open(encoding='utf-8-sig',newline='') as f:
   self.assertEqual(list(csv.DictReader(f)),[])
  self.assertEqual(app.GREEK_TITLE_ALIASES,{})
 def test_timeout_only_retry_in_search(self):
  import unittest.mock as mock
  with mock.patch.object(app,'PROVIDERS',('LRCLIB',)),mock.patch.object(app,'provider_lrclib',return_value=None):
   _,status,_,_=app.search_song('Sample','Artist','',190,app.CandidateReview())
   self.assertEqual(status,'NOT_FOUND')
  app.blocked.clear()
  with mock.patch.object(app,'PROVIDERS',('LRCLIB',)),mock.patch.object(app,'provider_lrclib',side_effect=app.ProviderFailure('network timeout',timeout=True)):
   retry=set()
   _,status,_,_=app.search_song('Sample','Artist','',190,app.CandidateReview(),retry_targets=retry)
   self.assertEqual(status,'TIMEOUT');self.assertEqual(retry,{'LRCLIB'})
 def test_g2g_local_cache_and_no_mp3_write(self):
  class Engine:
   def __call__(self,t):return types.SimpleNamespace(text='Καλημέρα')
  with tempfile.TemporaryDirectory() as tmp:
   audio=Path(tmp)/'Example.mp3'; audio.write_bytes(b'audio bytes unchanged')
   mgr=G2GManager(cache_file=Path(tmp)/'cache.json',factory=lambda:Engine())
   text,flag=mgr.convert('Kalimera','title');mgr.flush()
   self.assertEqual(text,'Καλημέρα')
   self.assertEqual(audio.read_bytes(),b'audio bytes unchanged')
if __name__=='__main__': unittest.main()
