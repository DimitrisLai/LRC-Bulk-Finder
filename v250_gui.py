"""v2.5.0 Library Manager GUI controls, piggybacking on v2.4.5 dashboard.
All scan/report operations are read-only; selective search is explicit and gated.
"""
from __future__ import annotations
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, scrolledtext
from v250_manager import (make_selection_manifest, load_rejection_explanations,
    reason_for_row, start_session, latest_session, session_entries, undo_session)
from search_profiles import DEFAULT

class V250Mixin:
    def _build_manager_controls(self, area):
        group=ttk.LabelFrame(area,text='Library Manager — retry, rejection reasons and safe undo',padding=8)
        group.pack(fill='x',pady=(8,0))
        self.dashboard_tree.configure(selectmode='extended')
        buttons=ttk.Frame(group);buttons.pack(fill='x')
        ttk.Button(buttons,text='Why was this rejected?',command=self._manager_explain).pack(side='left',padx=3)
        ttk.Button(buttons,text='Retry selected tracks',command=self._manager_retry_selected).pack(side='left',padx=3)
        ttk.Button(buttons,text='Undo last search session...',command=self._manager_undo).pack(side='left',padx=3)
        ttk.Label(group,text='Select one or more missing/review tracks. A retry searches ONLY selected tracks. Undo removes only unchanged files created by that session.',
                  wraplength=960).pack(anchor='w',pady=(6,3))
        self.manager_reason=scrolledtext.ScrolledText(group,height=5,wrap='word',font=('Segoe UI',9))
        self.manager_reason.pack(fill='both',expand=False)
        self.manager_reason.configure(state='disabled')
        self._manager_selection_manifest=None
        self._manager_session_id=None
        self._manager_explain_request=0

    def _manager_set_reason(self,text):
        self.manager_reason.configure(state='normal')
        self.manager_reason.delete('1.0','end')
        self.manager_reason.insert('1.0',text)
        self.manager_reason.configure(state='disabled')

    def _manager_selection(self):
        return [self.dashboard_visible_rows[x] for x in self.dashboard_tree.selection()
                if x in self.dashboard_visible_rows]

    def _manager_explain(self):
        selected=self._manager_selection()
        if not selected:
            self._dialog('showinfo','Why was this rejected?','Select a track in the results table first.')
            return
        root=self.folder.get().strip()
        if not Path(root).is_dir():return
        row=selected[0]
        self._manager_explain_request+=1
        request_id=self._manager_explain_request
        self._manager_set_reason('Reading the last saved search report (not a live provider check)...')
        def run():
            try:
                detail=load_rejection_explanations(root,[row['path']])
                message=reason_for_row(row,detail)
            except (ValueError,OSError) as ex:
                message='Could not load historical report: '+str(ex)
            self._v245_queue.put(('manager_reason',(request_id,row['path'],message)))
        threading.Thread(target=run,daemon=True).start()

    def _manager_retry_selected(self):
        if self._search_is_active_or_stopping():
            self._dialog('showwarning','Search running','Stop the current search before starting another.')
            return
        rows=self._manager_selection()
        if not rows:
            self._dialog('showinfo','Retry selected tracks','Select one or more missing or review tracks first.')
            return
        if len(rows)>2500:
            self._dialog('showerror','Retry selected tracks','Select no more than 2500 tracks at a time.')
            return
        if any(row['status'] not in ('Needs review','Missing LRC') for row in rows):
            self._dialog('showwarning','Retry selected tracks',
                'Only tracks without an existing LRC and without ambiguous audio can be retried.')
            return
        root=self.folder.get().strip()
        if not self._dialog('askyesno','Retry ONLY selected tracks?',
              f'Search exactly {len(rows)} selected tracks using FULL online providers?\n\n'
              'This explicit retry bypasses prior NO_MATCH history and does NOT re-scan the whole library. '
              'Existing audio/LRC files remain protected. Provider rate limits still apply.'):
            return
        try:
            manifest=make_selection_manifest(root,[row['path'] for row in rows])
        except (ValueError,OSError) as ex:
            self._dialog('showerror','Retry selected tracks',str(ex));return
        self._manager_selection_manifest=manifest
        new={**DEFAULT,'folder':root,'action':'1','provider_mode':'full','order':'d',
             'custom_order':'','history':False,'limit':'a','local_ai':False,
             'recursive':True,'experimental_simpmusic':False}
        # Keep Greek search alternatives from the current library's settings.
        new['greek']=bool(self.boolvars['greek'].get())
        try:
            self._set_values(new)
            self.name.set('Selected retry v2.5.0')
            self._run_profile()
        except Exception:
            self._manager_cleanup_selection()
            raise
        if self.process is None:
            self._manager_cleanup_selection()

    def _manager_cleanup_selection(self):
        item=getattr(self,'_manager_selection_manifest',None)
        self._manager_selection_manifest=None
        if item:
            try:Path(item).unlink(missing_ok=True)
            except OSError:pass

    def _manager_undo(self):
        if self._search_is_active_or_stopping():
            self._dialog('showwarning','Search running',
                'Finish or stop the current search before undoing a previous session.')
            return
        folder=self.folder.get().strip()
        if not Path(folder).is_dir():
            self._dialog('showerror','Undo search session','Choose an existing library folder first.')
            return
        try:
            sid=latest_session(folder)
            if not sid:
                self._dialog('showinfo','Undo search session',
                    'No v2.5.0 search session with journaled new lyric files was found for this folder.')
                return
            items=session_entries(sid,expected_root=folder)
            candidates=[item for item in items if item['eligible']]
            skipped=len(items)-len(candidates)
            if not candidates:
                self._dialog('showinfo','Undo search session',
                    'No unchanged files remain eligible for undo. Modified files are always preserved.')
                return
            preview='\n'.join(' • '+item['path'].name for item in candidates[:7])
            prompt=(f'Permanently remove {len(candidates)} unchanged .lrc / .candidate.lrc sidecars '
                    f'created by the last recorded search session?\n\n{preview}\n\n'
                    f'{skipped} changed, missing or previously undone files will be preserved.\n'
                    'Existing LRCs, audio, ID3 tags, reports, cache and user edits will NOT be deleted.\n'
                    'This deletion cannot be undone. Continue?')
            if not self._dialog('askyesno','Confirm safe session undo',prompt):return
            result=undo_session(sid,expected_root=folder)
            self._dialog('showinfo','Undo result',
                f'Removed {len(result["removed"])} unchanged files created by that session. '
                f'Skipped {len(result["skipped"])} protected files.')
            self._dashboard_refresh()
        except (OSError,ValueError) as error:
            self._dialog('showerror','Undo search session',str(error))
