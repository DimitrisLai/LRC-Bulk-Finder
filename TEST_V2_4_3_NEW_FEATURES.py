import csv
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stage_counters import StageCounters
from v243_health import ProviderHealth
from v243_aliases import approve_alias
from v243_resume import last_run,mark_run
from v243_contribution import export_contribution
from v243_provider_lab import provider_simpmusic
from worker_stop import kill_search_process


class CounterTests(unittest.TestCase):
    def test_skips_and_misses_are_distinct_and_deduplicated(self):
        x=StageCounters();x.start(1)
        x.add('a.mp3','NO_METADATA');x.add('a.mp3','NO_METADATA')
        x.add('b.mp3','NOT_FOUND');x.add('c.mp3','TIMEOUT')
        self.assertEqual((x.values()['not_found'],x.values()['skipped']),(1,1))
        x.add('b.mp3','SAVED');x.add('b.mp3','SAVED')
        self.assertEqual((x.values()['not_found'],x.values()['total_found']),(0,1))
        x.start(2)
        self.assertEqual((x.values()['skipped'],x.values()['total_found']),(0,1))

    def test_candidate_across_stages(self):
        x=StageCounters();x.start(1)
        for _ in range(3):x.add('a.mp3','REVIEW_AVAILABLE',reviewed=True)
        x.start(2);x.add('a.mp3','SAVED')
        self.assertEqual((x.values()['total_found'],x.values()['total_candidate']),(1,1))

class HealthTests(unittest.TestCase):
    def test_only_verified_hit_is_success(self):
        h=ProviderHealth(['LRCLIB','SimpMusic'])
        self.assertEqual(h.observe('   LRCLIB: NO_MATCH | HTTP 200 | 0.5s',now='T1'),'LRCLIB')
        self.assertEqual(h.rows['LRCLIB']['last_verified'],'')
        h.observe('   LRCLIB: LRC_FOUND | HTTP 200 | 0.5s',now='T2')
        self.assertEqual(h.rows['LRCLIB']['last_verified'],'')
        h.observe('   LRCLIB: LRC_INSTALLED | actual .lrc sidecar created | saved',now='T2B')
        self.assertEqual(h.rows['LRCLIB']['last_verified'],'T2B')
        h.observe('   LRCLIB: TIMEOUT | NETWORK_TIMEOUT | 0.5s',now='T3')
        self.assertEqual(h.rows['LRCLIB']['status'],'Timed out')
        self.assertEqual(h.rows['LRCLIB']['last_verified'],'T2B')
        self.assertIsNone(h.observe('  Unknown: LRC_FOUND | HTTP 200 | 1s'))

class AliasTests(unittest.TestCase):
    def test_approval_dedup_conflicting_spelling_and_file(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'Greek_Aliases.csv'
            self.assertTrue(approve_alias(path,'artist','Giorgos Alkaios','Γιώργος Αλκαίος'))
            self.assertFalse(approve_alias(path,'artist','giorgos alkaios','Γιώργος Αλκαίος'))
            with self.assertRaises(ValueError):
                approve_alias(path,'artist','Giorgos Alkaios','Γιώργος Αλκέος')
            self.assertIn('Γιώργος',path.read_text(encoding='utf-8-sig'))
            with self.assertRaises(ValueError):approve_alias(path,'title','Test','Latin only')

class ResumeTests(unittest.TestCase):
    def test_mark_and_restore(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'resume.json'
            mark_run('Greek Night','D:/Music',path=path)
            self.assertEqual(last_run(path)['profile'],'Greek Night')
            mark_run('Greek Night','D:/Music','stopped',path=path)
            self.assertEqual(last_run(path)['status'],'stopped')
            path.write_text('{ invalid',encoding='utf-8')
            self.assertIsNone(last_run(path))

class ContributionTests(unittest.TestCase):
    def test_counts_only_saved_with_sidecars(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); song=p/'song.mp3';song.write_bytes(b'ID3notreal');song.with_suffix('.lrc').write_text('[00:05.00] x')
            with (p/'LRC_Finder_Report_v2_1_15.csv').open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.DictWriter(f,fieldnames=['MP3 path','status','saved provider']);w.writeheader()
                for status in ('SAVED','SAVED','REVIEW_AVAILABLE'):
                    w.writerow({'MP3 path':str(song),'status':status,'saved provider':'SimpMusic'})
            dest=export_contribution(p)
            with dest.open(encoding='utf-8-sig') as fp:
                rows=list(csv.DictReader(fp))
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['unique_tracks_with_verified_installs_in_report'],'1')

class SimpMusicTests(unittest.TestCase):
    class Review:
        def __init__(self):self.items=[]
        def add(self,*args,**kwargs):self.items.append((args,kwargs))
    @staticmethod
    def fake_acceptable(*a):
        if a[5] is None:return False,'Provider has no verified recording duration'
        return True,'duration and identity verified'
    @staticmethod
    def payload(duration=None):
        r={'songTitle':'Sample Song','artistName':'Artist','syncedLyrics':'[00:01.00] Hello\n[00:40.00] Another line\n[01:30.00] Last'}
        if duration is not None:r['duration']=duration
        return {'success':True,'data':[r]}
    def run_source(self,payload):
        from collections import namedtuple
        Hit=namedtuple('Hit','lyrics provider note search_variation verified')
        review=self.Review()
        hit=provider_simpmusic('Sample Song','Artist','',99,review,
            direct_json=lambda p,u,q:payload,
            acceptable=self.fake_acceptable,Hit=Hit,
            query_variants=lambda t,a:[(t,a)],label_for_query=lambda *x:'ORIGINAL',
            plausible_lrc=lambda text,d:'[00:' in text)
        return hit,review
    def test_missing_duration_is_candidate_only(self):
        hit,review=self.run_source(self.payload())
        self.assertIsNone(hit);self.assertEqual(len(review.items),1)
    def test_resolved_duration_passes_identity_gate(self):
        hit,review=self.run_source(self.payload(99))
        self.assertIsNotNone(hit);self.assertTrue(hit.verified)
    def test_non_synced_skipped(self):
        hit,review=self.run_source({'success':True,'data':[{'songTitle':'X','artistName':'Y','syncedLyrics':'just text'}]})
        self.assertIsNone(hit);self.assertEqual(len(review.items),0)

class PackagingTests(unittest.TestCase):
    def test_v243_modules_import_from_distribution(self):
        import importlib.util
        root=Path(__file__).parent
        for mod in ('v243_health','v243_provider_lab','v243_resume',
                    'v243_contribution','v243_aliases','worker_stop','stage_counters'):
            self.assertTrue((root/(mod+'.py')).is_file(),mod)
            self.assertIsNotNone(importlib.util.find_spec(mod),mod)


class StopTests(unittest.TestCase):
    def test_real_owned_worker_stops(self):
        kwargs={'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP} if os.name=='nt' else {'start_new_session':True}
        p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],**kwargs)
        try:
            success,detail=kill_search_process(p)
            self.assertTrue(success,detail)
            self.assertIsNotNone(p.poll())
        finally:
            if p.poll() is None:p.kill()
    def test_windows_all_observed_children_confirmed(self):
        class P:
            pid=4100
            exited=False
            def poll(self):return 0 if self.exited else None
            def wait(self,timeout):self.exited=True;return 0
        tables=iter(({4100:1,4101:4100,4102:4101},{1:0}))
        with mock.patch('worker_stop._windows_process_table',side_effect=lambda:next(tables)),\
             mock.patch('worker_stop.subprocess.run',return_value=mock.Mock(returncode=0,stdout='ok',stderr='')):
            ok,detail=kill_search_process(P(),platform='nt')
        self.assertTrue(ok,detail)
        self.assertIn('2 observed',detail)

    def test_windows_observed_child_survives_reports_failure(self):
        class P:
            pid=4100
            exited=False
            def poll(self):return 0 if self.exited else None
            def wait(self,timeout):self.exited=True;return 0
        tables=iter(({4100:1,4101:4100,4102:4101},{1:0,4102:77}))
        with mock.patch('worker_stop._windows_process_table',side_effect=lambda:next(tables)),\
             mock.patch('worker_stop.subprocess.run',return_value=mock.Mock(returncode=0,stdout='ok',stderr='')):
            ok,detail=kill_search_process(P(),platform='nt')
        self.assertFalse(ok)
        self.assertIn('4102',detail)

    def test_real_child_process_stop_on_posix(self):
        if os.name=='nt':self.skipTest('POSIX specific')
        import time
        with tempfile.TemporaryDirectory() as d:
            pidfile=Path(d)/'child.pid'
            script=("import subprocess,sys,time; p=subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(180)']); "
                    f"open({str(pidfile)!r},'w').write(str(p.pid));time.sleep(180)")
            worker=subprocess.Popen([sys.executable,'-u','-c',script],start_new_session=True)
            try:
                for _ in range(100):
                    if pidfile.exists():break
                    time.sleep(.05)
                self.assertTrue(pidfile.exists())
                ok,detail=kill_search_process(worker)
                self.assertTrue(ok,detail)
                self.assertIsNotNone(worker.poll())
            finally:
                if worker.poll() is None:worker.kill()

    def test_windows_fallback_never_claims_tree_verified(self):
        class P:
            pid=1234
            def __init__(self):self.killed=False
            def poll(self):return None
            def kill(self):self.killed=True
        fake=P()
        with mock.patch('worker_stop.subprocess.run',return_value=mock.Mock(returncode=1,stderr='Denied',stdout='')):
            ok,detail=kill_search_process(fake,platform='nt')
        self.assertFalse(ok);self.assertTrue(fake.killed);self.assertIn('MAY REMAIN',detail)

if __name__=='__main__':unittest.main()
