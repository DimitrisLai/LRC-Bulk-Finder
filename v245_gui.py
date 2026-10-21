"""Optional beginner dashboard / timing-repair GUI for LRC Bulk Finder v2.4.5.

Never writes music or existing LRC files. Runs slow scans and GitHub update
checks in workers, updates Tk widgets only from the Tk main thread.
"""
from __future__ import annotations
import os
import queue
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext

from v245_features import (scan_library, inventory_counts, export_inventory,
    check_github_update, save_diagnostics, shift_lrc_timestamps, save_shifted_candidate,
    MAX_LRC_BYTES, VERSION)
from runtime_paths import program_folder
from search_profiles import DEFAULT


class V245Mixin:
    def _build_quick_search(self):
        area = self.quick_tab
        ttk.Label(area, text='Quick Search — get started in three steps',
                  style='Header.TLabel').pack(anchor='w', pady=(2, 14))
        ttk.Label(area, text='1. Choose your music folder').pack(anchor='w')
        first = ttk.Frame(area)
        first.pack(fill='x', pady=(4, 15))
        ttk.Entry(first, textvariable=self.folder).pack(side='left', fill='x', expand=True)
        ttk.Button(first, text='Browse...', command=self._browse_music).pack(side='left', padx=7)
        ttk.Label(area, text='2. Choose how much to scan').pack(anchor='w')
        self.quick_scope = tk.StringVar(value='20')
        ttk.Radiobutton(area, text='Test 20 songs (recommended)', variable=self.quick_scope,
                        value='20').pack(anchor='w', pady=(6, 2))
        ttk.Radiobutton(area, text='All songs', variable=self.quick_scope,
                        value='a').pack(anchor='w', pady=(2, 10))
        self.quick_include_subfolders = tk.BooleanVar(value=True)
        ttk.Checkbutton(area, text='Include subfolders',
                        variable=self.quick_include_subfolders).pack(anchor='w', pady=6)
        self.quick_greek = tk.BooleanVar(value=False)
        ttk.Checkbutton(area, text='Enable Greek / Greeklish matching',
                        variable=self.quick_greek).pack(anchor='w', pady=6)
        ttk.Label(area, text='3. Start a safe online search', style='Header.TLabel').pack(anchor='w', pady=(18, 6))
        ttk.Button(area, text='START QUICK SEARCH', command=self._quick_start).pack(fill='x', pady=(0, 10))
        ttk.Label(area, text='Online search requires no LRCLIB database. Existing audio and LRC files are protected.',
                  wraplength=870).pack(anchor='w')
        ttk.Separator(area).pack(fill='x', pady=22)
        tools = ttk.Frame(area)
        tools.pack(fill='x')
        ttk.Button(tools, text='Advanced settings',
                   command=lambda:self.notebook.select(self.search_tab)).pack(side='left', padx=5)
        ttk.Button(tools, text='Results dashboard',
                   command=lambda:self.notebook.select(self.dashboard_tab)).pack(side='left', padx=5)
        ttk.Button(tools, text='Check for updates', command=self._check_update).pack(side='left', padx=5)
        ttk.Button(tools, text='Save diagnostics...', command=self._diagnostics).pack(side='left', padx=5)
        self.update_notice=tk.StringVar(value='Updates are checked only when you click the button.')
        ttk.Label(area, textvariable=self.update_notice, wraplength=900).pack(anchor='w', pady=12)
        self.update_page=None
        self.update_open_button=ttk.Button(area,text='Open new GitHub release',
            command=self._open_update_page, state='disabled')
        self.update_open_button.pack(anchor='w')
        self._v245_queue=queue.Queue()
        self.after(150, self._poll_v245)

    def _quick_start(self):
        folder=self.folder.get().strip()
        if not folder or not Path(folder).is_dir():
            self._dialog('showerror','Quick Search','Choose an existing music folder first.')
            return
        if self.process is not None and self.process.poll() is None:
            self._dialog('showwarning','Search running','Stop the current search before starting another.')
            return
        name='Quick Search v2.4.5'
        if name in self.loaded_profiles and not self._dialog('askyesno','Replace quick profile?',
                'Overwrite the existing Quick Search settings? Your music files will not be changed.'):
            return
        profile={**DEFAULT, 'folder': folder, 'database':'', 'action':'1',
                 'provider_mode':'fast','order':'d','custom_order':'',
                 'limit':self.quick_scope.get(), 'greek':self.quick_greek.get(),
                 'recursive':self.quick_include_subfolders.get(),
                 'local_ai':False, 'experimental_simpmusic':False}
        self._set_values(profile)
        self.name.set(name)
        self._run_profile()

    def _poll_v245(self):
        try:
            while True:
                kind,data=self._v245_queue.get_nowait()
                if kind=='update':
                    self.update_notice.set(data['message'])
                    self.update_page=data.get('url')
                    self.update_open_button.configure(state='normal' if self.update_page else 'disabled')
                elif kind=='inventory':
                    if isinstance(data,Exception):
                        self._dashboard_scanning=False
                        self.dashboard_status.set('Cannot scan library: '+str(data))
                    else:
                        self.dashboard_all_rows=data
                        self._dashboard_filter()
        except queue.Empty:pass
        try:
            if self.winfo_exists():self.after(160,self._poll_v245)
        except tk.TclError:pass

    def _check_update(self):
        self.update_page=None
        self.update_open_button.configure(state='disabled')
        self.update_notice.set('Checking the official GitHub release...')
        def job():
            try:
                result=check_github_update(VERSION)
                text=('New version available: '+result['latest'] if result['newer']
                      else 'You already have the latest version ('+VERSION+').')
                self._v245_queue.put(('update',{'message':text,
                    'url':result['url'] if result['newer'] else None}))
            except Exception as ex:
                self._v245_queue.put(('update',{'message':'Could not check updates: '+str(ex)}))
        threading.Thread(target=job,daemon=True).start()

    def _open_update_page(self):
        if self.update_page:
            webbrowser.open(self.update_page)

    def _diagnostics(self):
        filename=self._file_dialog('asksaveasfilename',title='Save private diagnostic report',
                     defaultextension='.txt', initialfile='LRC_Diagnostics_v245.txt',
                     filetypes=[('Text files','*.txt')])
        if not filename:return
        if not self._dialog('askyesno','Save diagnostics?',
            'Save version and system checks only? No filenames, music tags, personal paths or lyrics will be included.'):
            return
        try:
            target=save_diagnostics(filename, frozen=getattr(sys,'frozen',False),
                worker_exists=(program_folder()/'LRC_Bulk_Finder_Worker.exe').is_file(),
                profiles=len(self.loaded_profiles))
            self._dialog('showinfo','Diagnostic report saved','Saved a private report to:\n'+str(target))
        except (OSError,ValueError) as e:
            self._dialog('showerror','Diagnostics',str(e))

    def _build_results_dashboard(self):
        area=self.dashboard_tab
        ttk.Label(area,text='Results dashboard — library overview',style='Header.TLabel').pack(anchor='w')
        ttk.Label(area,text='Read-only inventory of audio files and lyric sidecars. Existing LRC does not mean verified.',
                  wraplength=960).pack(anchor='w',pady=(4,10))
        controls=ttk.Frame(area);controls.pack(fill='x')
        ttk.Label(controls,text='Music folder:').pack(side='left')
        ttk.Entry(controls,textvariable=self.folder).pack(side='left',fill='x',expand=True,padx=5)
        ttk.Button(controls,text='Browse...',command=self._browse_music).pack(side='left',padx=4)
        ttk.Button(controls,text='Refresh results',command=self._dashboard_refresh).pack(side='left',padx=4)
        ttk.Button(controls,text='Export CSV...',command=self._dashboard_export).pack(side='left',padx=4)
        self.dashboard_status=tk.StringVar(value='Choose a music folder and click Refresh results.')
        ttk.Label(area,textvariable=self.dashboard_status,wraplength=950).pack(anchor='w',pady=9)
        second=ttk.Frame(area);second.pack(fill='x',pady=(3,9))
        ttk.Label(second,text='Status:').pack(side='left')
        self.dashboard_state=tk.StringVar(value='All statuses')
        self.dashboard_filter_picker=ttk.Combobox(second,textvariable=self.dashboard_state,
            values=('All statuses','Has LRC','Needs review','Missing LRC','Ambiguous audio'),
            state='readonly',width=20)
        self.dashboard_filter_picker.pack(side='left',padx=(4,13))
        self.dashboard_filter_picker.bind('<<ComboboxSelected>>',lambda e:self._dashboard_filter())
        ttk.Label(second,text='Find:').pack(side='left')
        self.dashboard_query=tk.StringVar()
        self.dashboard_query.trace_add('write',lambda *_:self._dashboard_filter())
        ttk.Entry(second,textvariable=self.dashboard_query).pack(side='left',fill='x',expand=True)
        tree=ttk.Treeview(area,columns=('song','status','candidates','directory'),show='headings',height=15)
        self.dashboard_tree=tree
        for key,caption,width in [('song','Audio filename',340),('status','LRC status',150),
                                  ('candidates','Candidates',100),('directory','Folder',380)]:
            tree.heading(key,text=caption)
            tree.column(key,width=width,stretch=True)
        tree.pack(fill='both',expand=True)
        bar=ttk.Frame(area);bar.pack(fill='x',pady=(8,0))
        ttk.Button(bar,text='Open selected audio',command=self._dashboard_play).pack(side='left',padx=4)
        ttk.Button(bar,text='Review candidates',command=self._dashboard_review).pack(side='left',padx=4)
        ttk.Label(bar,text='No existing LRC or audio files are modified.',wraplength=410).pack(side='right')
        self.dashboard_all_rows=[]
        self.dashboard_visible_rows={}
        self._dashboard_scanning=False

    def _dashboard_refresh(self):
        folder=self.folder.get().strip()
        if not folder or not Path(folder).is_dir():
            self._dialog('showerror','Results dashboard','Choose an existing music folder first.')
            return
        if self._dashboard_scanning:return
        self._dashboard_scanning=True
        self.dashboard_status.set('Scanning local library (read-only)...')
        def job():
            try:data=scan_library(folder,self.boolvars['recursive'].get())
            except (OSError,ValueError) as ex:data=ex
            self._v245_queue.put(('inventory',data))
        threading.Thread(target=job,daemon=True).start()

    def _dashboard_filter(self):
        if not hasattr(self,'dashboard_tree'):return
        self._dashboard_scanning=False
        self.dashboard_tree.delete(*self.dashboard_tree.get_children())
        self.dashboard_visible_rows={}
        state=self.dashboard_state.get()
        from v245_translations import UI_V245_EL
        state=next((key for key in ('All statuses','Has LRC','Needs review','Missing LRC','Ambiguous audio')
                    if state in (key,UI_V245_EL.get(key,key))),state)
        query=self.dashboard_query.get().casefold().strip()
        for row in self.dashboard_all_rows:
            if state!='All statuses' and row['status']!=state:continue
            if query and query not in (row['name']+' '+row['folder']).casefold():continue
            key=str(len(self.dashboard_visible_rows))
            self.dashboard_visible_rows[key]=row
            self.dashboard_tree.insert('','end',iid=key,values=(row['name'],self._tr(row['status']),
                                    row['candidates'],row['folder']))
        counts=inventory_counts(self.dashboard_all_rows)
        self.dashboard_status.set(' | '.join((f'Total: {counts["Total"]}',
            f'Has LRC: {counts["Has LRC"]}',f'Needs review: {counts["Needs review"]}',
            f'Missing: {counts["Missing LRC"]}',
            f'Visible: {len(self.dashboard_visible_rows)}')))

    def _dashboard_selected(self):
        selection=self.dashboard_tree.selection()
        return self.dashboard_visible_rows.get(selection[0]) if selection else None

    def _dashboard_play(self):
        row=self._dashboard_selected()
        if row is None:return
        try:
            path=Path(row['path'])
            if sys.platform=='win32':os.startfile(path)
            elif sys.platform=='darwin':subprocess.Popen(['open',str(path)])
            else:subprocess.Popen(['xdg-open',str(path)])
        except (OSError,AttributeError) as ex:self._dialog('showerror','Open audio',str(ex))

    def _dashboard_review(self):
        self._refresh_review()
        self.notebook.select(self.review_tab)

    def _dashboard_export(self):
        if not self.dashboard_all_rows:
            self._dialog('showinfo','Export results','Refresh a non-empty music library first.')
            return
        dest=self._file_dialog('asksaveasfilename',title='Export library overview',
                   defaultextension='.csv',initialfile='LRC_Library_Overview.csv',
                   filetypes=[('CSV file','*.csv')])
        if not dest:return
        try:
            export_inventory(self.dashboard_all_rows,dest)
            self._dialog('showinfo','Export complete','Results exported to:\n'+str(dest))
        except (OSError,ValueError) as ex:self._dialog('showerror','Export results',str(ex))

    def _build_timing_repair(self):
        area=self.repair_tab
        ttk.Label(area,text='Timing repair — shift existing timestamps',
                  style='Header.TLabel').pack(anchor='w',pady=(0,6))
        ttk.Label(area,text='Correct lyrics that play early or late. Positive seconds = later, negative = earlier. The original LRC and audio are never overwritten.',
                  wraplength=970).pack(anchor='w',pady=(0,14))
        first=ttk.Frame(area);first.pack(fill='x',pady=3)
        ttk.Label(first,text='Audio track').pack(side='left')
        self.repair_audio=tk.StringVar()
        ttk.Entry(first,textvariable=self.repair_audio).pack(side='left',expand=True,fill='x',padx=6)
        ttk.Button(first,text='Choose audio...',command=self._repair_choose_audio).pack(side='left')
        second=ttk.Frame(area);second.pack(fill='x',pady=3)
        ttk.Label(second,text='Existing timed LRC').pack(side='left')
        self.repair_lrc=tk.StringVar()
        ttk.Entry(second,textvariable=self.repair_lrc).pack(side='left',expand=True,fill='x',padx=6)
        ttk.Button(second,text='Choose LRC...',command=self._repair_choose_lrc).pack(side='left')
        controls=ttk.Frame(area);controls.pack(fill='x',pady=(12,4))
        ttk.Label(controls,text='Shift (seconds, -300 to +300):').pack(side='left')
        self.repair_offset=tk.StringVar(value='0.50')
        ttk.Entry(controls,textvariable=self.repair_offset,width=12).pack(side='left',padx=6)
        ttk.Button(controls,text='Preview shifted lyrics',command=self._repair_preview).pack(side='left',padx=6)
        ttk.Button(controls,text='Save UNVERIFIED candidate...',command=self._repair_save).pack(side='right',padx=6)
        self.repair_status=tk.StringVar(value='Choose a track and its LRC, then preview an offset.')
        ttk.Label(area,textvariable=self.repair_status,wraplength=920).pack(anchor='w',pady=(6,4))
        self.repair_output=scrolledtext.ScrolledText(area,height=21,wrap='none',font=('Consolas',10))
        self.repair_output.pack(fill='both',expand=True)
        self.repair_output.configure(state='disabled')
        self.repair_preview_value=None
        self.repair_preview_sources=None

    def _repair_choose_audio(self):
        path=self._file_dialog('askopenfilename',title='Choose audio track for timing repair',
            filetypes=[('Audio','*.mp3 *.flac *.m4a *.mp4 *.ogg *.opus *.wav'),('All files','*.*')])
        if path:
            self.repair_audio.set(path)
            candidate=str(Path(path).with_suffix('.lrc'))
            if Path(candidate).is_file():self.repair_lrc.set(candidate)
            self.repair_preview_value=None

    def _repair_choose_lrc(self):
        path=self._file_dialog('askopenfilename',title='Choose existing timed LRC',
            filetypes=[('LRC lyrics','*.lrc'),('All files','*.*')])
        if path:self.repair_lrc.set(path);self.repair_preview_value=None

    def _repair_preview(self):
        try:
            src=Path(self.repair_lrc.get())
            track=Path(self.repair_audio.get())
            if not src.is_file() or src.is_symlink() or not track.is_file() or track.is_symlink():
                raise ValueError('Choose an existing audio track and its LRC file')
            if src.stat().st_size>MAX_LRC_BYTES:raise ValueError('LRC file is larger than 150 KB')
            if src.parent!=track.parent:
                raise ValueError('Audio and LRC must be in the same folder')
            source=src.read_text(encoding='utf-8-sig',errors='replace')
            shifted,n=shift_lrc_timestamps(source,self.repair_offset.get())
            self.repair_preview_value=shifted
            self.repair_preview_sources=(str(track),str(src),self.repair_offset.get(),src.stat().st_mtime_ns)
            self.repair_output.configure(state='normal')
            self.repair_output.delete('1.0','end')
            self.repair_output.insert('1.0',shifted)
            self.repair_output.configure(state='disabled')
            self.repair_status.set(f'Preview: {n} timestamps adjusted. UNVERIFIED until you listen and confirm.')
        except (OSError,ValueError) as ex:
            self.repair_preview_value=None
            self._dialog('showerror','Timing repair',str(ex))

    def _repair_save(self):
        if self.process is not None and self.process.poll() is None:
            self._dialog('showwarning','Search running','Finish the search before writing candidate files.')
            return
        sources=(self.repair_audio.get(),self.repair_lrc.get(),self.repair_offset.get())
        if not self.repair_preview_value or not self.repair_preview_sources or self.repair_preview_sources[:3]!=sources:
            self._dialog('showerror','Timing repair','Preview your current audio, LRC and offset before saving.')
            return
        if not self._dialog('askyesno','Save unverified timing correction?',
             'Save a NEW numbered .candidate.lrc file? Your original LRC and audio will remain unchanged. This is NOT verified lyric alignment.'):
            return
        try:
            track,src,off,mtime=self.repair_preview_sources
            if Path(src).stat().st_mtime_ns!=mtime:
                raise ValueError('The original LRC changed since preview. Preview again.')
            dest=save_shifted_candidate(track,src,self.repair_preview_value)
            self.repair_status.set('Saved UNVERIFIED candidate: '+str(dest))
            self._dialog('showinfo','Timing correction saved','Saved a separate UNVERIFIED candidate:\n'+str(dest))
        except (OSError,ValueError) as ex:self._dialog('showerror','Timing repair',str(ex))
