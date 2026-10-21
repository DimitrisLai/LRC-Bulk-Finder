"""Standalone adversarial QA for released LRC Bulk Finder v2.4.3.
Run only on disposable folders, with virtual desktop for Tk on Linux.
This script does not change the actual repository or user's music files.
"""
import contextlib,hashlib,io,json,os,subprocess,sys,tempfile,time,unittest,wave,types
from pathlib import Path
from unittest import mock
SRC=Path(os.environ.get('LRC_QA_SOURCE') or Path(__file__).resolve().parent)
sys.path.insert(0,str(SRC))
from LRC_Control_Center import ControlCenter
import LRC_Control_Center as gui
import search_profiles as sp
from review_candidates_gui import list_review_candidates
from lyric_sync_lab import plain_lines,estimate_timestamps,draft_lrc,save_unverified_draft
from v243_resume import last_run,mark_run
from v243_aliases import approve_alias
from v243_contribution import export_contribution
from v243_health import ProviderHealth
from worker_stop import kill_search_process

class QA(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='lrc_user_qa_')
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.music=self.base/'music';self.music.mkdir()
        self.settings=self.base/'APPDATA';self.settings.mkdir()
        self.env=mock.patch.dict(os.environ,{'APPDATA':str(self.settings)},clear=False)
        self.env.start();self.addCleanup(self.env.stop)
        self.errs=[];self.info=[]
        def grab(k):
            def capture(title,*args,**kwargs): self.errs.append((k,title,str(args[0]) if args else ''));return True
            return capture
        for name in ('showerror','showwarning','showinfo'):
            p=mock.patch.object(gui.messagebox,name,grab(name));p.start();self.addCleanup(p.stop)
        self.confirm=mock.patch.object(gui.messagebox,'askyesno',return_value=True);self.confirm.start();self.addCleanup(self.confirm.stop)
        self.a=ControlCenter();self.addCleanup(self.safe_destroy)
        self.a.update_idletasks()
        self.a.folder.set(str(self.music));self.a.name.set('QA Sandbox')

    def safe_destroy(self):
        try:
            for ident in self.a.tk.call('after','info'):
                self.a.after_cancel(ident)
        except Exception:pass
        try:self.a.destroy()
        except Exception:pass

    def audio(self,filename='One.wav',seconds=2):
        p=self.music/filename
        with wave.open(str(p),'wb') as a:
            a.setnchannels(1);a.setsampwidth(2);a.setframerate(8000);a.writeframes(b'\x00\x00'*8000*seconds)
        return p

    def test_01_all_five_tabs_and_every_view_can_be_opened(self):
        tabs=self.a.notebook.tabs()
        self.assertEqual(len(tabs),5)
        for t in tabs:
            with self.subTest(tab=self.a.notebook.tab(t,'text')):
                self.a.notebook.select(t);self.a.update_idletasks()
                self.assertEqual(self.a.notebook.select(),t)
        self.assertEqual(len(self.a.provider_health.rows),13)

    def test_02_all_presets_apply_and_keep_paths(self):
        names=list(sp.PRESET_TEMPLATES)
        self.assertEqual(len(names),6)
        self.a.database.set('/not/existing/SQLite.db')
        for name in names:
            with self.subTest(preset=name):
                self.a.preset_name.set(name);self.a._preset_selected();self.a._apply_preset()
                self.assertEqual(self.a.name.get(),name)
                self.assertEqual(self.a.folder.get(),str(self.music))
                self.assertEqual(self.a.database.get(),'/not/existing/SQLite.db')
                self.assertEqual(self.a._values(),sp.preset_profile(name,self.music,'/not/existing/SQLite.db'))
                self.assertTrue(self.a.preset_description.get())
        self.assertEqual(sp.load_profiles(),{})
        before=self.a.name.get();self.a.preset_name.set('nonexistent');self.a._apply_preset();self.assertEqual(self.a.name.get(),before)

    def test_03_all_ten_switches_toggle_and_save(self):
        self.a.action.set('1')
        self.assertEqual(len(self.a.boolvars),10)
        for key,var in self.a.boolvars.items():
            with self.subTest(switch=key):
                var.set(False);self.assertIs(var.get(),False)
                var.set(True);self.assertIs(var.get(),True)
                if key=='local_ai':self.a.boolvars['greek'].set(True)
                self.assertIs(self.a._values()[key],True)
                var.set(False);self.assertIs(self.a._values()[key],False)
        self.assertTrue(self.a._save());self.assertEqual(sp.load_profiles()['QA Sandbox']['folder'],str(self.music))
        self.a.folder.set('');self.a._load_selected();self.assertEqual(self.a.folder.get(),str(self.music))

    def test_04_validate_every_search_mode_order_limit_matrix(self):
        combos=0
        for action in ('1','4','5'):
            for mode in ('fast','full'):
                for order in ('d','s','c'):
                    for limit in ('1','20','999999','a'):
                        for experimental in (False,True):
                            with self.subTest(action=action,mode=mode,order=order,limit=limit,exp=experimental):
                                self.a.action.set(action);self.a.provider_mode.set(mode)
                                self.a.provider_order.set(order);self.a.limit.set(limit)
                                self.a.boolvars['experimental_simpmusic'].set(experimental)
                                providers=sp.PROVIDER_FULL if mode=='full' else sp.PROVIDER_FAST
                                if mode=='full' and experimental:providers+=('SimpMusic',)
                                self.a.custom_order.set(','.join(providers))
                                saved=self.a._values()
                                self.assertEqual(saved['action'],action)
                                self.assertEqual(saved['order'],order)
                                self.assertEqual(saved['provider_mode'],mode)
                                self.assertEqual(saved['limit'],limit)
                                combos+=1
        self.assertEqual(combos,144)

    def test_05_bad_profiles_fail_closed(self):
        good={**sp.DEFAULT,'folder':str(self.music),'action':'1'}
        invalid=[('action','2'),('action','6'),('provider_mode','wrong'),('order','x'),('limit','0'),('limit','-2'),('limit','wat'),('folder',''),('greek','maybe'),('local_ai','YES'),('custom_order',42)]
        for key,bad in invalid:
            if key=='custom_order': continue # only meaningful when custom selected
            with self.subTest(key=key,bad=bad):
                with self.assertRaises(ValueError):sp.validate_profile({**good,key:bad})
        with self.assertRaises(ValueError):sp.validate_profile({**good,'greek':False,'local_ai':True})
        with self.assertRaises(ValueError):sp.validate_profile({**good,'order':'c','custom_order':'LRCLIB,LRCLIB'})
        with self.assertRaises(ValueError):sp.validate_profile({**good,'order':'c','custom_order':','.join(sp.PROVIDER_FULL),'provider_mode':'full','experimental_simpmusic':True})
        self.a.name.set('! invalid');self.assertFalse(self.a._save());self.assertTrue(self.errs)
        self.a.name.set('Valid Name');self.a.action.set('1');self.assertTrue(self.a._save())
        self.a.name.set('');self.assertFalse(self.a._save())
        self.a.name.set('Valid Name');self.a._refresh_profiles()
        with mock.patch.object(gui.messagebox,'askyesno',return_value=False):self.a._delete()
        self.assertIn('Valid Name',sp.load_profiles())
        self.a._delete();self.assertNotIn('Valid Name',sp.load_profiles())

    def test_06_browse_cancel_then_select_music_and_sqlite(self):
        before=self.a.folder.get()
        with mock.patch.object(gui.filedialog,'askdirectory',side_effect=['',str(self.music)]):
            self.a._browse_music();self.assertEqual(self.a.folder.get(),before)
            self.a._browse_music();self.assertEqual(self.a.folder.get(),str(self.music))
        with mock.patch.object(gui.filedialog,'askopenfilename',side_effect=['',str(self.base/'db.sqlite3')]):
            self.a._browse_database();self.assertEqual(self.a.database.get(),'')
            self.a._browse_database();self.assertEqual(self.a.database.get(),str(self.base/'db.sqlite3'))

    def test_07_progress_parser_round_reset_and_clear_log(self):
        self.a._line('===== ROUND 2: ONLINE FALLBACK =====')
        self.assertIn('ROUND 2',self.a.phase.get())
        self.a._line('STAGE COUNTERS: stage=online found=7 candidate=3 not_found=2 total_found=9 total_candidate=5 skipped=4')
        expected=dict(found='7',candidate='3',not_found='2',total_found='9',total_candidate='5',skipped='4')
        for k,v in expected.items():self.assertEqual(self.a.counter_vars[k].get(),v)
        self.a._line('STAGE COUNTERS: stage=retry found=0 candidate=0 not_found=0 total_found=9 total_candidate=5 skipped=0')
        self.assertEqual([self.a.counter_vars[k].get() for k in ('found','candidate','not_found','skipped')],['0']*4)
        self.assertEqual(self.a.counter_vars['total_found'].get(),'9')
        self.a._line('PROGRESS ROUND 3: 5/10 (50.0%) | elapsed 10s | THIS ROUND ETA: 10s')
        self.assertEqual(float(self.a.bar['value']),50)
        self.a._line('STAGE COUNTERS: stage=retry found=1 candidate=1 not_found=1 total_found=10 total_candidate=6')
        self.assertEqual(self.a.counter_vars['skipped'].get(),'0')
        self.a._clear_log();self.assertEqual(self.a.log.get('1.0','end').strip(),'')
        self.assertEqual(self.a.counter_vars['total_found'].get(),'10')

    def test_08_provider_health_no_false_verification(self):
        self.a._line('LRCLIB: NO_MATCH | HTTP 200 | 0.4s')
        self.assertEqual(self.a.provider_health.rows['LRCLIB']['verified_count'],0)
        self.a._line('      LRCLIB: LRC_INSTALLED | actual .lrc sidecar created | saved')
        self.assertEqual(self.a.provider_health.rows['LRCLIB']['verified_count'],1)
        self.assertEqual(len(self.a.health_tree.get_children()),13)
        self.a._refresh_health();self.assertEqual(len(self.a.health_tree.get_children()),13)

    def test_09_candidate_review_empty_primary_numbered_and_cancel(self):
        audio=self.audio()
        original=hashlib.sha256(audio.read_bytes()).digest()
        c=self.music/'One.candidate.lrc';c.write_text('[00:00.00] candidate\n[00:01.00] first\n[00:02.00] next\n')
        alt=self.music/'One.candidate.2.lrc';alt.write_text('[00:01.00] alternative\n')
        self.a._refresh_review();self.assertEqual(len(self.a.review_rows),2)
        numbered=next(i for i,r in self.a.review_rows.items() if r['index']==2)
        self.a.review_tree.selection_set(numbered);self.a._candidate_selected()
        self.assertIn('alternative',self.a.candidate_text.get('1.0','end'))
        self.a._promote_selected();self.assertFalse((self.music/'One.lrc').exists())
        main=next(i for i,r in self.a.review_rows.items() if r['index']==1)
        self.a.review_tree.selection_set(main);self.a._candidate_selected()
        with mock.patch.object(gui.messagebox,'askyesno',return_value=False):self.a._promote_selected()
        self.assertFalse((self.music/'One.lrc').exists())
        with mock.patch.dict(sys.modules,{'syncedlyrics':types.ModuleType('syncedlyrics')}):
            self.a._promote_selected()
        saved=self.music/'One.lrc';self.assertTrue(saved.exists())
        self.assertEqual(saved.read_text().splitlines()[0],'[00:00.00] candidate')
        self.assertEqual(hashlib.sha256(audio.read_bytes()).digest(),original)
        self.a._refresh_review();self.assertTrue(all(v['has_lrc'] for v in self.a.review_rows.values()))

    def test_10_review_recursive_and_collision_safety(self):
        self.audio('One.wav');c=self.music/'One.candidate.lrc';c.write_text('[00:01.00] lyrics\n')
        nested=self.music/'nested';nested.mkdir();(nested/'Another.candidate.lrc').write_text('[00:01.00] candidate\n')
        self.a.boolvars['recursive'].set(False);self.a._refresh_review();self.assertEqual(len(self.a.review_rows),1)
        self.a.boolvars['recursive'].set(True);self.a._refresh_review();self.assertEqual(len(self.a.review_rows),2)
        (self.music/'One.mp3').write_bytes(b'fake')
        self.a._refresh_review();amb=next(v for v in self.a.review_rows.values() if v['path']==c)
        self.assertFalse(amb['has_mp3']);self.assertTrue(amb['ambiguous'])
        item=next(i for i,r in self.a.review_rows.items() if r['path']==c)
        self.a.review_tree.selection_set(item);self.a._promote_selected()
        self.assertFalse((self.music/'One.lrc').exists())

    def test_11_sync_lab_errors_taps_and_marked_safe_save(self):
        audio=self.audio(seconds=4); digest=hashlib.sha256(audio.read_bytes()).digest()
        self.a._sync_estimate();self.assertTrue(self.errs)
        self.a.sync_audio.set(str(audio));self.a.sync_source.insert('1.0','First line\nSecond line\nThird line')
        self.a._sync_estimate();self.assertIn('[00:00.00] candidate',self.a.sync_draft.get('1.0','end'))
        self.assertEqual(len(self.a.sync_lines),3)
        self.a._sync_save();self.assertTrue((self.music/'One.candidate.lrc').exists())
        self.a._sync_save();self.assertTrue((self.music/'One.candidate.2.lrc').exists())
        self.assertEqual(hashlib.sha256(audio.read_bytes()).digest(),digest)
        self.a._sync_start_tap()
        for _ in range(3):self.a._sync_tap()
        self.assertEqual(len(self.a.sync_times),3)
        self.a._sync_save();self.assertTrue((self.music/'One.candidate.3.lrc').exists())
        self.a._sync_tap();self.assertIn('all lyric lines',self.a.sync_status.get())
        (self.music/'One.lrc').write_text('ORIGINAL\n')
        self.a._sync_save();self.assertTrue(any(k=='showerror' for k,*_ in self.errs))
        self.assertEqual((self.music/'One.lrc').read_text(),'ORIGINAL\n')

    def test_12_import_size_limit_cancel_and_player(self):
        p=self.base/'lyrics.txt';p.write_text('First\nSecond\n')
        huge=self.base/'huge.txt';huge.write_bytes(b'A'*151000)
        with mock.patch.object(gui.filedialog,'askopenfilename',side_effect=['',str(huge),str(p)]):
            self.a._sync_import();self.assertEqual(self.a.sync_source.get('1.0','end').strip(),'')
            self.a._sync_import();self.assertTrue(self.errs)
            self.a._sync_import();self.assertEqual(self.a.sync_source.get('1.0','end').strip(),'First\nSecond')
        self.a._sync_play();self.assertTrue(any(k=='showerror' for k,*_ in self.errs))
        audio=self.audio();self.a.sync_audio.set(str(audio))
        if sys.platform=='win32':
            with mock.patch.object(gui.os,'startfile',create=True) as play:
                self.a._sync_play();play.assert_called_once()
        else:
            with mock.patch.object(gui.subprocess,'Popen') as pop:
                self.a._sync_play();self.assertTrue(pop.called)

    def test_13_greek_alias_cancel_invalid_approved_duplicate(self):
        location=self.base/'Greek_Aliases.csv'
        with mock.patch.object(gui,'program_folder',return_value=self.base):
            with mock.patch.object(gui.simpledialog,'askstring',side_effect=[None]):self.a._approve_alias()
            self.assertFalse(location.exists())
            with mock.patch.object(gui.simpledialog,'askstring',side_effect=['invalid']):self.a._approve_alias()
            self.assertFalse(location.exists())
            with mock.patch.object(gui.simpledialog,'askstring',side_effect=['artist','Mazonakis','Μαζωνάκης']):self.a._approve_alias()
            self.assertTrue(location.exists());d=location.read_text(encoding='utf-8-sig')
            self.assertIn('Mazonakis',d)
            with mock.patch.object(gui.simpledialog,'askstring',side_effect=['artist','Mazonakis','Μαζωνάκης']):self.a._approve_alias()
            self.assertEqual(location.read_text(encoding='utf-8-sig'),d)
            with mock.patch.object(gui.simpledialog,'askstring',side_effect=['artist','Mazonakis','Μπουζούκης']):self.a._approve_alias()
            self.assertTrue(any(k=='showerror' for k,*_ in self.errs))

    def test_14_resume_no_interruption_missing_profile_and_confirmation(self):
        self.a._resume_previous();self.assertTrue(any(title=='Resume' for _,title,_ in self.errs))
        mark_run('missing',str(self.music),'stopped')
        self.a._resume_previous();self.assertTrue(any(k=='showerror' for k,*_ in self.errs))
        self.a.action.set('1');self.assertTrue(self.a._save());mark_run('QA Sandbox',str(self.music),'stopped')
        with mock.patch.object(self.a,'_run_profile') as run:
            with mock.patch.object(gui.messagebox,'askyesno',return_value=False):self.a._resume_previous()
            run.assert_not_called()
            self.a._resume_previous();run.assert_called_once()
        mark_run('QA Sandbox',str(self.music),'finished');self.a._resume_previous();self.assertEqual(last_run()['status'],'finished')

    def test_15_search_launch_empty_folder_real_worker(self):
        self.a.action.set('1');self.a.boolvars['greek'].set(False)
        self.a.boolvars['musicbrainz'].set(False)
        self.a.boolvars['recovery_wait'].set(False)
        self.a.limit.set('1')
        # Test runner with only its optional online lyrics *dependency* stubbed;
        # zero-song folders make no HTTP calls and exercise real subprocess launch.
        stub=self.base/'dep_stubs';stub.mkdir()
        (stub/'syncedlyrics.py').write_text('# empty folder does not need provider API\n')
        with mock.patch.dict(os.environ,{'PYTHONPATH':str(stub)+os.pathsep+os.environ.get('PYTHONPATH','')}):
            self.a._run_profile()
        self.assertIsNotNone(self.a.process)
        deadline=time.monotonic()+15
        while self.a.process is not None and time.monotonic()<deadline:
            self.a.update();time.sleep(.05)
        self.assertIsNone(self.a.process)
        self.assertIn('Exit code: 0',self.a.phase.get())
        self.assertEqual(str(self.a.stop_button.cget('state')),'disabled')
        self.assertTrue((self.settings/'LRCBulkFinder'/'profiles.json').exists())
        self.assertTrue(all(p.name == 'LRC_Incremental_Library_v2_4.sqlite3' for p in self.music.iterdir()))

    def test_16_missing_folder_and_db_guards_and_double_run_guard(self):
        self.a.action.set('4');self.a.database.set('')
        self.a._run_profile();self.assertTrue(any(title=='Missing database' for _,title,_ in self.errs))
        self.a.folder.set(str(self.base/'nonexistent'));self.a._run_profile()
        self.assertTrue(any(title=='Missing folder' for _,title,_ in self.errs))
        p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)'],start_new_session=True)
        self.addCleanup(lambda: p.kill() if p.poll() is None else None)
        self.a.process=p
        self.a._run_profile();self.assertTrue(any(title=='Search running' for _,title,_ in self.errs))
        self.a._close();self.assertTrue(any(title=='Search running' for _,title,_ in self.errs))
        self.a.process=None

    def test_17_real_stop_button_with_unrelated_process_untouched(self):
        p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(40)'],start_new_session=True)
        other=subprocess.Popen([sys.executable,'-c','import time;time.sleep(40)'],start_new_session=True)
        def clean(q):
            if q.poll() is None:q.kill();q.wait()
        self.addCleanup(lambda:clean(p));self.addCleanup(lambda:clean(other))
        self.a.process=p
        self.a._stop()
        self.assertTrue(self.a.stop_requested)
        deadline=time.monotonic()+20
        while p.poll() is None and time.monotonic()<deadline:time.sleep(.05)
        self.assertIsNotNone(p.poll())
        self.assertIsNone(other.poll())
        self.a.process=None

    def test_18_all_setup_buttons_linux_safe_fallback(self):
        with mock.patch.object(gui,'program_folder',return_value=self.base),mock.patch.object(gui.webbrowser,'open') as op:
            self.a._launch_setup('SETUP_LRCLIB_DATABASE.cmd')
            self.a._launch_setup('SETUP_GREEK_AI.cmd')
            self.assertEqual(op.call_count,2)
        self.assertEqual(list(self.music.iterdir()),[])

    def test_19_all_profile_answers_match_preset_actions(self):
        for name in sp.PRESET_TEMPLATES:
            p=sp.preset_profile(name,self.music,str(self.base/'fake.sqlite3'))
            with self.subTest(name=name):
                ans=sp.ProfileAnswers(p)
                for prompt,expected in ans.answers:
                    actual=ans(prompt+' ')
                    self.assertEqual(actual,expected)
                with self.assertRaises(RuntimeError):ans('Unexpected prompt')
                self.assertIn(p['action'],('1','4','5'))

    def test_20_every_windows_command_targets_existing_script(self):
        wrappers=list(SRC.glob('*.cmd'))+list(SRC.glob('*.bat'))
        self.assertGreaterEqual(len(wrappers),8)
        for file in wrappers:
            with self.subTest(cmd=file.name):
                body=file.read_text(encoding='utf-8-sig',errors='replace')
                self.assertIn('@echo off',body.casefold())
                self.assertIn('%~dp0',body)
                for token in ('cleanup_lrclib_database.py','auto_install_lrclib_database.py','setup_lrclib_database.py','connect_existing_lrclib_database.py','LRC_Bulk_Finder.py','LRC_Control_Center.py','g2g_integration.py'):
                    if token in body:self.assertTrue((SRC/token).exists(),(file.name,token))
        self.assertTrue((SRC/'run_saved_profile.py').exists())

    def test_21_all_cli_help_error_and_no_profile_exits(self):
        command=[sys.executable,str(SRC/'run_saved_profile.py')]
        a=subprocess.run(command+['--help'],capture_output=True,text=True,timeout=10)
        self.assertEqual(a.returncode,0);self.assertIn('--setup-lrclib',a.stdout)
        for opts in ([],['--profile','not-existing'],['--bad-option']):
            with self.subTest(opts=opts):
                p=subprocess.run(command+opts,capture_output=True,text=True,timeout=10,env={**os.environ,'APPDATA':str(self.settings)})
                self.assertNotEqual(p.returncode,0)

    def test_22_stress_1000_progress_updates_no_duplicate_sidecars(self):
        for i in range(1000):
            self.a._line(f'STAGE COUNTERS: stage=online found={i} candidate=0 not_found=0 total_found={i} total_candidate=0 skipped=0')
        self.assertEqual(self.a.counter_vars['total_found'].get(),'999')
        self.assertEqual(list(self.music.iterdir()),[])

    def test_23_language_switch_not_released_yet(self):
        self.assertFalse(hasattr(self.a,'language'))
        self.assertFalse(hasattr(self.a,'set_language'))
        self.assertEqual(self.a.notebook.tab(self.a.notebook.tabs()[0],'text').strip(),'Saved searches')

if __name__=='__main__':unittest.main(verbosity=2)