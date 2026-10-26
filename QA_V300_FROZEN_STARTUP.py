"""Offline frozen Alpha 5 tests of the actual startup read/discovery paths."""
from __future__ import annotations
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time


def _root(value):
    root=Path(value).resolve()
    if root.parent!=Path(tempfile.gettempdir()).resolve() or not root.name.startswith('lrc_alpha5_startup_'):
        raise ValueError('Only disposable Alpha 5 QA directories are accepted')
    return root


@contextmanager
def _delayed_history(root):
    original=Path.open
    history=root/'history.jsonl'
    class Slow:
        def __init__(self,stream):self.stream=stream
        def __enter__(self):return self
        def __exit__(self,*args):self.stream.close()
        def readline(self,size):
            (root/'active').write_text('history')
            time.sleep(.04)
            return self.stream.readline(size)
    def open_file(path,*args,**kwargs):
        stream=original(path,*args,**kwargs)
        return Slow(stream) if path==history and args and args[0]=='rb' else stream
    Path.open=open_file
    try:yield
    finally:Path.open=original


@contextmanager
def _delayed_scan(root):
    original=os.scandir
    class Slow:
        def __init__(self,stream):self.stream=stream
        def __enter__(self):return self
        def __exit__(self,*args):self.stream.close()
        def __iter__(self):
            for entry in self.stream:
                (root/'active').write_text('enumeration')
                time.sleep(.04)
                yield entry
    os.scandir=lambda path:Slow(original(path))
    try:yield
    finally:os.scandir=original


def worker_fixture(value,mode):
    root=_root(value)
    import LRC_Bulk_Finder as engine
    from incremental_library import safe_audio_files
    started=time.monotonic()
    if mode in ('history','history-budget'):
        before=hashlib.sha256((root/'history.jsonl').read_bytes()).hexdigest()
        with _delayed_history(root):
            engine.load_search_history(root/'history.jsonl',progress=lambda msg:print(msg,flush=True))
        elapsed=time.monotonic()-started
        assert before==hashlib.sha256((root/'history.jsonl').read_bytes()).hexdigest()
        assert not engine.HISTORY_CACHE,'An incomplete history must not be used'
        print('QA STARTUP RESULT: '+json.dumps({'history_budget_seconds':round(elapsed,3),
              'partial_cache_used':False,'history_original_unchanged':True}),flush=True)
        return 0
    if mode=='enumeration':
        with _delayed_scan(root):
            safe_audio_files(root/'music',progress=lambda msg:print(msg,flush=True))
        raise AssertionError('Delayed enumeration should be stopped by the GUI')
    if mode=='normal-enumeration':
        def no_tags(*args,**kwargs):raise AssertionError('Filename discovery must not parse audio metadata')
        engine.AudioFile=no_tags
        tracks,collisions=safe_audio_files(root/'music',progress=lambda msg:print(msg,flush=True))
        assert len(tracks)==20 and len(collisions)==2
        print('QA STARTUP RESULT: '+json.dumps({'audio_tracks':len(tracks),'collisions':len(collisions),
              'audio_metadata_reads':0,'enumeration_seconds':round(time.monotonic()-started,3)}),flush=True)
        return 0
    raise ValueError('Unknown startup QA mode')


def smoke_entry(report,center_class):
    try:return smoke(report,center_class)
    except Exception:
        import traceback
        Path(report).write_text(json.dumps({'passed':False,'error':traceback.format_exc()},indent=2),encoding='utf-8')
        return 1


def smoke(report,center_class):
    if os.name!='nt' or not getattr(sys,'frozen',False):
        raise RuntimeError('Run startup QA through the frozen Windows GUI')
    from runtime_paths import program_folder
    from worker_stop import kill_search_process,StopContext
    cases=[]
    with tempfile.TemporaryDirectory(prefix='lrc_alpha5_startup_') as td:
        root=Path(td);music=root/'music';music.mkdir()
        os.environ['APPDATA']=str(root/'appdata')
        for n in range(5000):(music/f'cover{n}.txt').touch()
        for n in range(20):(music/f'Δοκιμή {n}.wav').write_bytes(b'original read-only sentinel')
        (music/'Overlap.mp3').write_bytes(b'a');(music/'Overlap.flac').write_bytes(b'b')
        (music/'Δοκιμή 0.lrc').write_text('[00:01.00] original\n',encoding='utf-8')
        (music/'Δοκιμή 1.candidate.10.lrc').write_text('[00:01.00] candidate\n',encoding='utf-8')
        (root/'history.jsonl').write_text(''.join(json.dumps({'key':str(n),'at':time.time()-1,'state':'NO_MATCH'})+'\n'
                                                for n in range(1000)),encoding='utf-8')
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in music.iterdir()}
        executable=str(program_folder()/'LRC_Bulk_Finder_Worker.exe')
        def command(mode):return [executable,'--qa-startup-fixture',str(root),'--qa-startup-mode',mode]
        def cli(mode):
            result=subprocess.run(command(mode),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                  encoding='utf-8',errors='replace',timeout=30)
            assert result.returncode==0,result.stdout
            lines=[line for line in result.stdout.splitlines() if line.startswith('QA STARTUP RESULT: ')]
            assert len(lines)==1,result.stdout
            return json.loads(lines[0].split(': ',1)[1])
        enumeration=cli('normal-enumeration')
        budget=cli('history-budget')
        assert 9<=budget['history_budget_seconds']<20,budget
        app=center_class();app.withdraw();app.folder.set(str(music))
        app._dialog=lambda *args,**kwargs:True
        heartbeat=[0]
        def tick():
            heartbeat[0]+=1;app.after(30,tick)
        app.after(30,tick)
        try:
            for mode in ('history','enumeration'):
                (root/'active').unlink(missing_ok=True)
                app.stop_requested=False;app._stop_verification_failed=False
                app._stopping_process=None;app._stop_context=None
                app.stop_directory=root/'marker';app.stop_directory.mkdir(exist_ok=True)
                app.stop_path=app.stop_directory/'stop.request'
                worker=subprocess.Popen(command(mode),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                    encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                app.process=worker
                threading.Thread(target=app._read_process,args=(worker,),daemon=True).start()
                try:
                    ready=time.monotonic()+20
                    while not (root/'active').exists() or ('loading search history' if mode=='history' else 'enumerating audio') not in app.phase.get().lower():
                        app.update()
                        if worker.poll() is not None or time.monotonic()>ready:
                            raise AssertionError('Real startup stage did not become active: '+app.phase.get())
                        time.sleep(.01)
                    ticks=heartbeat[0];started=time.monotonic();app._stop()
                    callback=time.monotonic()-started
                    assert callback<.5,'Startup STOP callback blocked Tk'
                    while app._hardstop_pending or app.process is not None:
                        app.update()
                        if time.monotonic()-started>20:raise AssertionError('Startup STOP exceeded 20s')
                        time.sleep(.01)
                    assert not app._stop_verification_failed,app.phase.get()
                    assert heartbeat[0]>ticks,'GUI heartbeat did not advance'
                    cases.append({'stage':mode,'verified_stop_seconds':round(time.monotonic()-started,3),
                                  'callback_seconds':round(callback,3),'gui_responsive':True})
                finally:
                    if worker.poll() is None:
                        context=StopContext()
                        kill_search_process(worker,context=context)
                        context.close()
                    worker.wait(timeout=10)
            after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in music.iterdir()}
            assert before==after,'Original fixtures changed'
            Path(report).write_text(json.dumps({'passed':True,'frozen_gui_worker':True,
                'actual_startup_paths':cases,'history_budget':budget,'enumeration':enumeration,
                'fixture_hashes_unchanged':len(before)},indent=2),encoding='utf-8')
        finally:app.destroy()
    return 0
