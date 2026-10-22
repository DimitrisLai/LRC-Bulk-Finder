"""LRC Bulk Finder v2.4 Control Center (standard-library Tkinter).

Search runs execute in a separate Python process using the unchanged strict
matching engine; GUI never writes MP3/audio/ID3 or unmarked 'verified' lyrics.
"""
from __future__ import annotations
import os
import queue
import re
import signal
import subprocess
import time
import webbrowser
import sys
import threading
import tempfile
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog,messagebox,scrolledtext,ttk,simpledialog

from search_profiles import (DEFAULT,PROVIDER_FAST,PROVIDER_FULL,load_profiles,
                             save_profiles,validate_profile,PRESET_TEMPLATES,
                             PRESET_DESCRIPTIONS,preset_profile)
from tooltip_help import ToolTip
from lyric_sync_lab import plain_lines,estimate_timestamps,draft_lrc,save_unverified_draft
from review_candidates_gui import (list_review_candidates,preview_candidate,
                                   explicitly_promote)
from runtime_paths import program_folder
from worker_stop import kill_search_process
from v243_health import ProviderHealth
from v243_resume import last_run, mark_run
from v243_aliases import approve_alias
from v243_contribution import export_contribution
from ui_locale import GuiLocale, read_language, save_language
from v250_manager import start_session
from v245_gui import V245Mixin


class ControlCenter(V245Mixin,tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LRC Bulk Finder v2.5.0 — Control Center")
        self.gui_locale=GuiLocale(read_language())
        self._locale_widgets={}
        self._status_vars={}
        self._locale_is_refreshing=False
        self.geometry("1140x910")
        self.minsize(970,770)
        self.process=None
        self.reader=None
        self.stop_directory=None
        self.stop_path=None
        self.stop_requested=False
        self.active_profile=None
        self.active_folder=None
        self.active_action=None
        self.messages=queue.Queue()
        self.review_rows={}
        self.loaded_profiles={}
        self._build()
        self._refresh_profiles()
        self._init_language_status_tracking()
        self._refresh_language()
        self.after(110,self._poll)
        self.protocol("WM_DELETE_WINDOW",self._close)

    def _tr(self,value):
        return self.gui_locale.tr(value)

    def _tool_tip(self,widget,english):
        tooltip=ToolTip(widget,self._tr(english))
        self._locale_widgets[widget]=english
        widget._lrc_original_tooltip=english
        widget._lrc_tooltip=tooltip
        return tooltip

    def _preset_key(self,display):
        if display in PRESET_TEMPLATES:return display
        # Display text is independent of the persisted/internal preset key.
        for original in PRESET_TEMPLATES:
            if GuiLocale('el').tr(original)==display:return original
        return display

    def _language_selected(self,_event=None):
        new='el' if self.language_choice.get()=='Ελληνικά' else 'en'
        if new==self.gui_locale.language:return
        old=self.gui_locale.language
        self.gui_locale.language=new
        self._refresh_language()
        try:save_language(new)
        except OSError as error:
            # Do not falsely claim the preference was saved.
            messagebox.showwarning(self._tr('Interface language'),str(error))

    def _iter_ui_children(self,parent):
        for child in parent.winfo_children():
            yield child
            yield from self._iter_ui_children(child)

    def _status_changed(self,var):
        if self._locale_is_refreshing:return
        raw=var.get()
        self._status_vars[str(var)]=(var,raw)
        localized=self._tr(raw)
        if localized!=raw:
            self._locale_is_refreshing=True
            try:var.set(localized)
            finally:self._locale_is_refreshing=False

    def _init_language_status_tracking(self):
        # Keep the canonical status text, so reversing Greek to English never
        # damages file paths, counters, logs or current search state.
        for var in (self.phase,self.progress_text,self.sync_status,self.preset_description):
            self._status_vars[str(var)]=(var,var.get())
            var.trace_add('write',lambda *args,v=var:self._status_changed(v))

    def _refresh_language(self):
        self._locale_is_refreshing=True
        try:
            self.title('LRC Bulk Finder v2.4.5 — Control Center')
            # Preserve active notebook tab and all fields; no _build() or profile reload.
            for widget in self._iter_ui_children(self):
                if isinstance(widget,(ttk.Label,ttk.Button,ttk.Checkbutton,ttk.LabelFrame,
                                      ttk.Radiobutton,tk.Label,tk.Button,tk.Checkbutton,tk.LabelFrame)):
                    try:shown=widget.cget('text')
                    except tk.TclError:continue
                    base=getattr(widget,'_lrc_original_text',None)
                    if base is None:
                        base=shown
                        widget._lrc_original_text=base
                    translated=self._tr(base)
                    if shown!=translated:widget.configure(text=translated)
                original=getattr(widget,'_lrc_original_tooltip',None)
                if original is not None:widget._lrc_tooltip.message=self._tr(original)
            if hasattr(self,'notebook'):
                for tab in self.notebook.tabs():
                    value=self.notebook.tab(tab,'text')
                    original=self._locale_widgets.get(('tab',tab))
                    if original is None:
                        original=value
                        self._locale_widgets[('tab',tab)]=original
                    self.notebook.tab(tab,text=self._tr(original))
            for tree in (getattr(self,'health_tree',None),getattr(self,'review_tree',None),
                         getattr(self,'dashboard_tree',None)):
                if tree is None:continue
                for key in tree['columns']:
                    original=self._locale_widgets.get(('heading',str(tree),key))
                    if original is None:
                        original=tree.heading(key,'text')
                        self._locale_widgets[('heading',str(tree),key)]=original
                    tree.heading(key,text=self._tr(original))
            if hasattr(self,'preset_choice'):
                current=self._preset_key(self.preset_name.get())
                self.preset_choice.configure(values=[self._tr(k) for k in PRESET_TEMPLATES])
                if current in PRESET_TEMPLATES:self.preset_name.set(self._tr(current))
            for var,raw in self._status_vars.values():
                localized=self._tr(raw)
                if var.get()!=localized:var.set(localized)
            if hasattr(self,'health_tree'):self._refresh_health()
            if hasattr(self,'dashboard_filter_picker'):
                from v245_translations import UI_V245_EL
                keys=('All statuses','Has LRC','Needs review','Missing LRC','Ambiguous audio')
                current=self.dashboard_state.get()
                canonical=next((k for k in keys if current in (k,UI_V245_EL.get(k,k))),'All statuses')
                self.dashboard_filter_picker.configure(values=[self._tr(k) for k in keys])
                self.dashboard_state.set(self._tr(canonical))
            # Existing review results contain original English statuses; transform only
            # the presentation column and never the underlying selected file data.
            if hasattr(self,'review_tree'):
                for item in self.review_tree.get_children():
                    vals=list(self.review_tree.item(item,'values'))
                    if len(vals)>2:
                        english=self._locale_widgets.get(('review_status',item))
                        if english is None:
                            english=vals[2]
                            self._locale_widgets[('review_status',item)]=english
                        vals[2]=self._tr(english)
                        self.review_tree.item(item,values=vals)
            if hasattr(self,'dashboard_tree'):self._dashboard_filter()
        finally:self._locale_is_refreshing=False

    def _dialog(self,method,title,message,*args,**kwargs):
        # Translate at the display edge; all internal error/report codes are untouched.
        return getattr(messagebox,method)(self._tr(title),self._tr(message),*args,**kwargs)

    def _askstring(self,title,prompt,*args,**kwargs):
        return simpledialog.askstring(self._tr(title),self._tr(prompt),*args,**kwargs)

    def _file_dialog(self,method,*args,**kwargs):
        if 'title' in kwargs:kwargs['title']=self._tr(kwargs['title'])
        if 'filetypes' in kwargs:
            kwargs['filetypes']=[(self._tr(caption),mask) for caption,mask in kwargs['filetypes']]
        return getattr(filedialog,method)(*args,**kwargs)

    def _build(self):
        style=ttk.Style(self)
        if "clam" in style.theme_names():style.theme_use("clam")
        style.configure("Header.TLabel",font=("Segoe UI",16,"bold"))
        style.configure("Hint.TLabel",font=("Segoe UI",9))
        style.configure("TButton",padding=5)
        header=ttk.Frame(self,padding=(18,16,18,8))
        header.pack(fill="x")
        ttk.Label(header,text="LRC Bulk Finder",style="Header.TLabel").pack(side="left",anchor="w")
        self.language_choice=tk.StringVar(value="Ελληνικά" if self.gui_locale.language=='el' else "English")
        self.language_control=ttk.Combobox(header,textvariable=self.language_choice,
                                           values=("English","Ελληνικά"),state="readonly",width=13)
        self.language_control.pack(side="right",padx=(8,0))
        self.language_control.bind("<<ComboboxSelected>>",self._language_selected)
        ttk.Label(header,text="Interface language").pack(side="right",padx=4)
        ttk.Label(header,text="Search profiles · honest per-round ETA · safe review of unverified lyrics",style="Hint.TLabel").pack(anchor="w")
        self.notebook=ttk.Notebook(self)
        self.notebook.pack(fill="both",expand=True,padx=15,pady=(0,15))
        self.quick_tab=ttk.Frame(self.notebook,padding=12)
        self.search_tab=ttk.Frame(self.notebook,padding=12)
        self.run_tab=ttk.Frame(self.notebook,padding=12)
        self.review_tab=ttk.Frame(self.notebook,padding=12)
        self.sync_tab=ttk.Frame(self.notebook,padding=12)
        self.health_tab=ttk.Frame(self.notebook,padding=12)
        self.dashboard_tab=ttk.Frame(self.notebook,padding=12)
        self.repair_tab=ttk.Frame(self.notebook,padding=12)
        self.notebook.add(self.quick_tab,text='  Quick Search  ')
        self.notebook.add(self.search_tab,text="  Saved searches  ")
        self.notebook.add(self.run_tab,text="  Live progress  ")
        self.notebook.add(self.review_tab,text="  Candidate review  ")
        self.notebook.add(self.dashboard_tab,text='  Results dashboard  ')
        self.notebook.add(self.sync_tab,text="  Sync Lab (experimental)  ")
        self.notebook.add(self.repair_tab,text='  Timing repair  ')
        self.notebook.add(self.health_tab,text="  Provider health  ")
        self._build_profiles()
        self._build_quick_search()
        self._build_progress()
        self._build_review()
        self._build_sync_lab()
        self._build_timing_repair()
        self._build_health()
        self._build_results_dashboard()

    def _build_health(self):
        """States are derived from this run's actual provider output."""
        names=tuple(dict.fromkeys(PROVIDER_FULL+("SimpMusic",)))
        self.provider_health=ProviderHealth(names)
        ttk.Label(self.health_tab,text="Provider health — current run",style="Header.TLabel").pack(anchor="w")
        ttk.Label(self.health_tab,text="No network probes are made by this screen. An HTTP 200 is not a verified LRC.",wraplength=900).pack(anchor="w",pady=8)
        fields=("provider","status","last_http_success","last_verified","verified_count","detail")
        self.health_tree=ttk.Treeview(self.health_tab,columns=fields,show="headings",height=17)
        for key,label,width in (("provider","Provider",120),("status","Latest state",170),("last_http_success","Latest HTTP 2xx",145),("last_verified","Last verified hit",155),("verified_count","Verified hits",100),("detail","Latest response",340)):
            self.health_tree.heading(key,text=label)
            self.health_tree.column(key,width=width,stretch=True)
        self.health_tree.pack(fill="both",expand=True,pady=8)
        self._refresh_health()

    def _refresh_health(self):
        self.health_tree.delete(*self.health_tree.get_children())
        for provider,data in self.provider_health.rows.items():
            self.health_tree.insert("","end",values=(provider,self._tr(data["status"]),data["last_http_success"],data["last_verified"],data["verified_count"],data["detail"]))

    def _approve_alias(self):
        if self.process is not None and self.process.poll() is None:
            self._dialog("showwarning","Search running","Finish the current search before editing aliases.")
            return
        kind=self._askstring("Approve Greek alias","Type artist or title:",parent=self)
        if kind is None:return
        kind=kind.strip().lower()
        if kind not in ("artist","title"):
            self._dialog("showerror","Invalid type","Choose artist or title.");return
        original=self._askstring("Greeklish original","Enter exact original artist/title:",parent=self)
        if original is None:return
        approved=self._askstring("Approved Greek spelling","Enter reviewed Greek spelling:",parent=self)
        if approved is None:return
        if not self._dialog("askyesno","Confirm reviewed spelling",f"Save {kind} alias?\n\n{original}  →  {approved}\n\nIt will be used by NEW searches only."):
            return
        try:
            changed=approve_alias(program_folder()/"Greek_Aliases.csv",kind,original,approved)
            self._dialog("showinfo","Greek aliases","Saved. Restart the search to apply." if changed else "Already approved.")
        except (OSError,ValueError) as error:self._dialog("showerror","Alias error",str(error))

    def _resume_previous(self):
        if self.process is not None and self.process.poll() is None:
            self._dialog("showwarning","Search running","Stop the current search first.");return
        record=last_run()
        if not record or record["status"]=="finished":
            self._dialog("showinfo","Resume","No interrupted search has been recorded.");return
        name=record["profile"]
        profiles=load_profiles()
        if name not in profiles or profiles[name]["folder"]!=record["folder"]:
            self._dialog("showerror","Resume","Saved profile was moved or changed; review it manually.");return
        if not self._dialog("askyesno","Resume earlier search",f"Resume saved profile {name}?\n\nCompleted matching checkpoints will be reused; unfinished work retried."):
            return
        self.name.set(name)
        self._set_values(profiles[name])
        self._run_profile()

    def _build_profiles(self):
        outer=self.search_tab
        outer.columnconfigure(1,weight=1)
        self.name=tk.StringVar()
        self.folder=tk.StringVar()
        self.database=tk.StringVar()
        self.action=tk.StringVar(value="5")
        self.provider_mode=tk.StringVar(value="full")
        self.provider_order=tk.StringVar(value="d")
        self.custom_order=tk.StringVar()
        self.limit=tk.StringVar(value="20")
        self.boolvars={}
        for field in ("greek","local_ai","musicbrainz","recovery_wait","recursive","history","exact_fallback","auto_search","incremental","experimental_simpmusic"):
            self.boolvars[field]=tk.BooleanVar(value=DEFAULT[field])
        row=0
        self.preset_name=tk.StringVar()
        self.preset_description=tk.StringVar(value="Choose a built-in example, then click Apply. Your saved profiles are not replaced.")
        ttk.Label(outer,text="Ready-made preset").grid(row=row,column=0,sticky="w",padx=5,pady=5)
        preset_choice=ttk.Combobox(outer,textvariable=self.preset_name,
                                   values=list(PRESET_TEMPLATES),state="readonly",width=44)
        self.preset_choice=preset_choice
        preset_choice.grid(row=row,column=1,sticky="ew",padx=5)
        preset_choice.bind("<<ComboboxSelected>>",self._preset_selected)
        ttk.Button(outer,text="Apply preset",command=self._apply_preset).grid(row=row,column=2,sticky="ew",padx=5)
        self._tool_tip(preset_choice,"Built-in examples: Greek full search, Greek overnight maximum coverage, offline only, quick 20-song test, optional local AI and international FAST. Saved profiles remain yours.")
        row+=1
        ttk.Label(outer,textvariable=self.preset_description,wraplength=950,
                  style="Hint.TLabel").grid(row=row,column=0,columnspan=3,sticky="w",padx=5,pady=(0,8))
        row+=1
        ttk.Label(outer,text="Saved profile").grid(row=row,column=0,sticky="w",padx=5,pady=5)
        self.name_choice=ttk.Combobox(outer,textvariable=self.name,width=40)
        self.name_choice.grid(row=row,column=1,sticky="ew",padx=5)
        self.name_choice.bind("<<ComboboxSelected>>",self._load_selected)
        controls=ttk.Frame(outer)
        controls.grid(row=row,column=2,padx=5)
        ttk.Button(controls,text="Save",command=self._save).pack(side="left",padx=2)
        ttk.Button(controls,text="Delete",command=self._delete).pack(side="left",padx=2)
        row+=1
        ttk.Label(outer,text="MP3 folder").grid(row=row,column=0,sticky="w",padx=5,pady=5)
        ttk.Entry(outer,textvariable=self.folder).grid(row=row,column=1,sticky="ew",padx=5)
        ttk.Button(outer,text="Browse...",command=self._browse_music).grid(row=row,column=2,padx=5)
        row+=1
        ttk.Label(outer,text="Existing local LRCLIB SQLite (optional for 1, required for 4/5)").grid(row=row,column=0,columnspan=3,sticky="w",padx=5,pady=(10,0))
        row+=1
        ttk.Entry(outer,textvariable=self.database).grid(row=row,column=1,sticky="ew",padx=5,pady=5)
        ttk.Button(outer,text="Choose database",command=self._browse_database).grid(row=row,column=2,padx=5)
        row+=1
        ttk.Label(outer,text="Search action").grid(row=row,column=0,sticky="w",padx=5,pady=5)
        ttk.Combobox(outer,textvariable=self.action,state="readonly",
                     values=("5","1","4"),width=9).grid(row=row,column=1,sticky="w",padx=5)
        ttk.Label(outer,text="5=Offline first  |  1=Normal online  |  4=Offline only",
                  style="Hint.TLabel").grid(row=row,column=2,sticky="w",padx=5)
        row+=1
        ttk.Label(outer,text="Provider mode").grid(row=row,column=0,sticky="w",padx=5,pady=5)
        ttk.Combobox(outer,textvariable=self.provider_mode,state="readonly",
                     values=("fast","full"),width=12).grid(row=row,column=1,sticky="w",padx=5)
        row+=1
        ttk.Label(outer,text="Provider order").grid(row=row,column=0,sticky="w",padx=5,pady=5)
        ttk.Combobox(outer,textvariable=self.provider_order,state="readonly",
                     values=("d","s","c"),width=12).grid(row=row,column=1,sticky="w",padx=5)
        ttk.Label(outer,text="d=DEFAULT  |  s=SMART  |  c=CUSTOM",
                  style="Hint.TLabel").grid(row=row,column=2,sticky="w",padx=5)
        row+=1
        ttk.Label(outer,text="CUSTOM order").grid(row=row,column=0,sticky="w",padx=5,pady=5)
        ttk.Entry(outer,textvariable=self.custom_order).grid(row=row,column=1,columnspan=2,sticky="ew",padx=5)
        row+=1
        ttk.Label(outer,text="Number of songs").grid(row=row,column=0,sticky="w",padx=5,pady=5)
        ttk.Entry(outer,textvariable=self.limit,width=14).grid(row=row,column=1,sticky="w",padx=5)
        ttk.Label(outer,text="20 for testing, or A for all",style="Hint.TLabel").grid(row=row,column=2,sticky="w",padx=5)
        row+=1
        frame=ttk.LabelFrame(outer,text="Search configuration",padding=9)
        frame.grid(row=row,column=0,columnspan=3,sticky="nsew",pady=13)
        toggles=[
            ("greek","Greeklish / Greek folder"),
            ("local_ai","Use installed local Greek AI"),
            ("musicbrainz","MusicBrainz variants"),
            ("recursive","Include subfolders"),
            ("recovery_wait","Wait for unavailable providers"),
            ("history","Use cached completed NO_MATCH history"),
            ("exact_fallback","Extra LRCLIB exact-signature request"),
            ("auto_search","Search after Greek preview"),
            ("incremental","Incremental library tracking (fast repeat scans)"),
            ("experimental_simpmusic","EXPERIMENTAL SimpMusic (FULL mode only)"),
        ]
        descriptions={
            "greek":"Create approved Greek/Greeklish title and artist search alternatives. Not a filter that excludes non-Greek audio.",
            "local_ai":"Optional locally downloaded G2G model to propose Greek spelling. Not bundled in standalone EXE.",
            "musicbrainz":"Use MusicBrainz to improve title and artist metadata, with a persistent 30-day cache.",
            "recursive":"Include audio files in every subfolder under your chosen music directory.",
            "recovery_wait":"When enabled, waits for temporarily unavailable providers before first attempts. Overnight mode can take many hours.",
            "history":"Skip provider searches that already returned a definite NO_MATCH recently; does not hide review candidates.",
            "exact_fallback":"Optional extra exact LRCLIB lookup after ordinary requests; may add network calls.",
            "auto_search":"After Greek conversion preview, automatically continue searching without asking again.",
            "incremental":"Save a local SQLite metadata index; unchanged tracks reuse metadata while changed/new tracks are refreshed.",
            "experimental_simpmusic":"Opt-in 13th route for FULL mode. Response MUST pass strict artist/title/version/duration checks, else it is candidate only.",
        }
        for i,(key,label) in enumerate(toggles):
            widget=ttk.Checkbutton(frame,text=label,variable=self.boolvars[key])
            widget.grid(row=i//2,column=i%2,sticky="w",padx=12,pady=4)
            self._tool_tip(widget,descriptions[key])
        row+=1
        setup=ttk.LabelFrame(outer,text="Downloads & local setup",padding=8)
        setup.grid(row=row,column=0,columnspan=3,sticky="ew",pady=5)
        lrclib_button=ttk.Button(setup,text="Download / set up LRCLIB database",
                                 command=lambda:self._launch_setup("SETUP_LRCLIB_DATABASE.cmd"))
        lrclib_button.pack(side="left",padx=5)
        ai_button=ttk.Button(setup,text="Download / set up Greek G2G AI",
                             command=lambda:self._launch_setup("SETUP_GREEK_AI.cmd"))
        ai_button.pack(side="left",padx=5)
        self._tool_tip(lrclib_button,"Starts the bundled LRCLIB setup script in a separate Windows terminal, with its own prompts. Already downloaded? Use Choose database instead.")
        self._tool_tip(ai_button,"Starts the bundled local Greek AI installation guide/setup. Optional and model-heavy; standalone EXE cannot embed this model.")
        row+=1
        ttk.Button(outer,text="Save profile and START SEARCH",
                   command=self._run_profile).grid(row=row,column=0,columnspan=3,sticky="ew",padx=5,pady=8)
        ttk.Label(outer,text="The GUI stores profiles in your local user settings. Original MP3s/ID3 files are never modified.",
                  style="Hint.TLabel").grid(row=row+1,column=0,columnspan=3,sticky="w",padx=5)

    def _build_progress(self):
        ttk.Label(self.run_tab,text="Search progress",style="Header.TLabel").pack(anchor="w",pady=(0,10))
        self.phase=tk.StringVar(value="No search is running.")
        self.progress_text=tk.StringVar(value="Choose a profile and start from the Saved searches tab.")
        ttk.Label(self.run_tab,textvariable=self.phase).pack(anchor="w")
        self.bar=ttk.Progressbar(self.run_tab,maximum=100,length=500)
        self.bar.pack(fill="x",pady=10)
        ttk.Label(self.run_tab,textvariable=self.progress_text).pack(anchor="w",pady=(0,12))
        self.counter_vars={}
        self._counter_group(
            "THIS STAGE  •  resets after Round 1, 2 and 3",
            (("found","Songs / LRC found"),
             ("candidate","Songs / Candidate found"),
             ("not_found","Not found"),("skipped","Skipped / no metadata")))
        self._counter_group(
            "ALL STAGES  •  totals remain until a new search",
            (("total_found","LRC Count"),
             ("total_candidate","Candidate Count")))
        ttk.Label(self.run_tab,text="Stage numbers reset to 0 at each round; ALL-stages totals remain. "
                  "Timed-out/errored requests are not falsely counted as confirmed 'not found'.",
                  style="Hint.TLabel").pack(anchor="w",pady=(0,8))
        controls=ttk.Frame(self.run_tab)
        controls.pack(fill="x")
        self.stop_button=ttk.Button(controls,text="STOP SEARCH — keep app open",state="disabled",command=self._stop)
        self.stop_button.pack(side="left")
        ttk.Button(controls,text="Clear displayed log",command=self._clear_log).pack(side="left",padx=10)
        ttk.Button(controls,text="Resume previous search",command=self._resume_previous).pack(side="left",padx=10)
        self.log=scrolledtext.ScrolledText(self.run_tab,wrap="word",height=24,font=("Consolas",9))
        self.log.pack(fill="both",expand=True,pady=(12,0))
        self.log.configure(state="disabled")

    def _counter_group(self,title,fields):
        frame=ttk.LabelFrame(self.run_tab,text=title,padding=9)
        frame.pack(fill="x",pady=(0,8))
        for index,(key,label) in enumerate(fields):
            item=ttk.Frame(frame)
            item.grid(row=0,column=index,sticky="nsew",padx=12)
            frame.grid_columnconfigure(index,weight=1)
            value=tk.StringVar(value="0")
            self.counter_vars[key]=value
            ttk.Label(item,textvariable=value,font=("Segoe UI",21,"bold")).pack()
            ttk.Label(item,text=label,wraplength=200,justify="center").pack()

    def _build_review(self):
        top=ttk.Frame(self.review_tab)
        top.pack(fill="x")
        ttk.Label(top,text="Unverified candidate lyrics",style="Header.TLabel").pack(side="left")
        ttk.Button(top,text="Refresh candidates",command=self._refresh_review).pack(side="right")
        ttk.Button(top,text="Approve Greek alias...",command=self._approve_alias).pack(side="right",padx=10)
        ttk.Label(self.review_tab,text="Review before installing. Only explicitly selected primary candidates can become MARKED [00:00.00] candidate LRCs. This NEVER certifies lyrics as verified.",wraplength=850).pack(anchor="w",pady=10)
        columns=("track","candidate","status")
        self.review_tree=ttk.Treeview(self.review_tab,columns=columns,show="headings",height=12)
        for key,caption,width in (("track","Audio",350),("candidate","Candidate",330),("status","Status",200)):
            self.review_tree.heading(key,text=caption)
            self.review_tree.column(key,width=width,stretch=True)
        self.review_tree.pack(fill="both",expand=True)
        self.review_tree.bind("<<TreeviewSelect>>",self._candidate_selected)
        ttk.Label(self.review_tab,text="Selected synchronized lyrics (read-only)").pack(anchor="w",pady=(10,3))
        self.candidate_text=scrolledtext.ScrolledText(self.review_tab,height=9,wrap="word",font=("Consolas",10))
        self.candidate_text.pack(fill="both",expand=True)
        self.candidate_text.configure(state="disabled")
        buttons=ttk.Frame(self.review_tab)
        buttons.pack(fill="x",pady=12)
        ttk.Button(buttons,text="Play audio externally",command=self._play_selected).pack(side="left")
        ttk.Button(buttons,text="Promote selected to MARKED LRC",command=self._promote_selected).pack(side="left",padx=10)
        ttk.Label(buttons,text="Numbered alternatives are read-only until they become primary.").pack(side="right")

    def _preset_selected(self,_event=None):
        self.preset_description.set(self._tr(PRESET_DESCRIPTIONS.get(self._preset_key(self.preset_name.get()),"")))

    def _apply_preset(self):
        name=self._preset_key(self.preset_name.get())
        if name not in PRESET_TEMPLATES:return
        folder=self.folder.get()
        database=self.database.get()
        # Presets are editable templates, not silently persisted profiles.
        profile={**DEFAULT,**PRESET_TEMPLATES[name],
                 "folder":folder,"database":database}
        self._set_values(profile)
        self.name.set(name)
        self._preset_selected()

    def _launch_setup(self,script):
        path=program_folder()/script
        if sys.platform=="win32" and path.is_file() and not getattr(sys,"frozen",False):
            if self.process is not None and self.process.poll() is None:
                self._dialog("showwarning","Search running","Finish your music scan before changing the setup.")
                return
            if not self._dialog("askyesno","Run setup",f"Open {script} in a separate terminal?\n\nRead the installer prompts before confirming downloads."):
                return
            try:
                subprocess.Popen(["cmd.exe","/c",str(path)],cwd=str(program_folder()),
                    creationflags=subprocess.CREATE_NEW_CONSOLE)
            except OSError as error:
                self._dialog("showerror","Setup launcher",str(error))
        elif sys.platform=="win32" and getattr(sys,"frozen",False) and script=="SETUP_LRCLIB_DATABASE.cmd":
            if not self._dialog("askyesno","Download LRCLIB SQLite",
                "Open the official LRCLIB downloader in a separate console? "
                "You will choose the destination and confirm before large downloads."):
                return
            worker=program_folder()/"LRC_Bulk_Finder_Worker.exe"
            if not worker.is_file():
                self._dialog("showerror","Missing worker","Cannot find LRC_Bulk_Finder_Worker.exe")
                return
            subprocess.Popen([str(worker),"--setup-lrclib"],cwd=str(program_folder()),
                             creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            if self._dialog("askyesno","Python package required",
                "The optional local Greek AI requires Python and its external model. "
                "Open the official GitHub releases to obtain the complete setup ZIP?"):
                webbrowser.open("https://github.com/DimitrisLai/LRC-Bulk-Finder/releases")

    def _browse_music(self):
        selected=self._file_dialog("askdirectory",title="Select audio library folder",initialdir=self.folder.get() or str(Path.home()))
        if selected:self.folder.set(selected)

    def _browse_database(self):
        selected=self._file_dialog("askopenfilename",title="Existing LRCLIB SQLite database",
              filetypes=[("SQLite database","*.sqlite3 *.db"),("All files","*.*")])
        if selected:self.database.set(selected)

    def _values(self):
        values={
            "folder":self.folder.get(),"database":self.database.get(),
            "action":self.action.get(),"provider_mode":self.provider_mode.get(),
            "order":self.provider_order.get(),"custom_order":self.custom_order.get(),
            "limit":self.limit.get(),
        }
        values.update({key:v.get() for key,v in self.boolvars.items()})
        return validate_profile(values)

    def _set_values(self,profile):
        for name,var in (("folder",self.folder),("database",self.database),
                         ("action",self.action),("provider_mode",self.provider_mode),
                         ("order",self.provider_order),("custom_order",self.custom_order),
                         ("limit",self.limit)):
            var.set(profile.get(name,DEFAULT[name]))
        for key,var in self.boolvars.items():
            var.set(profile.get(key,DEFAULT[key]))

    def _refresh_profiles(self):
        try:self.loaded_profiles=load_profiles()
        except ValueError as error:
            self._dialog("showerror","Profiles",str(error))
            self.loaded_profiles={}
        self.name_choice.configure(values=list(sorted(self.loaded_profiles)))
        if self.name.get() in self.loaded_profiles:
            self._set_values(self.loaded_profiles[self.name.get()])

    def _load_selected(self,_event=None):
        if self.name.get() in self.loaded_profiles:
            self._set_values(self.loaded_profiles[self.name.get()])

    def _save(self):
        name=self.name.get().strip()
        if not name:
            self._dialog("showerror","Profile","Choose a profile name")
            return False
        try:
            profile=self._values()
            profiles=load_profiles()
            profiles[name]=profile
            save_profiles(profiles)
            self.name.set(name)
            self._refresh_profiles()
            return True
        except (OSError,ValueError) as error:
            self._dialog("showerror","Save profile",str(error))
            return False

    def _delete(self):
        name=self.name.get().strip()
        if name not in self.loaded_profiles:return
        if not self._dialog("askyesno","Delete profile","Delete saved settings for "+name+"? No music files are affected."):
            return
        try:
            profiles=load_profiles()
            del profiles[name]
            save_profiles(profiles)
            self.name.set("")
            self._refresh_profiles()
        except (OSError,ValueError) as error:
            self._dialog("showerror","Delete profile",str(error))

    def _run_profile(self):
        if self.process is not None and self.process.poll() is None:
            self._dialog("showwarning","Search running","Stop the current search before starting another.")
            return
        if not self._save():return
        profile=self.loaded_profiles[self.name.get()]
        if not Path(profile["folder"]).is_dir():
            self._dialog("showerror","Missing folder","Selected MP3 folder does not exist.")
            return
        if getattr(sys,"frozen",False) and profile["local_ai"]:
            self._dialog("showerror","Optional local AI requires Python build",
                "The standalone EXE does not contain the external G2G transformer "
                "model or its Python dependencies. For local AI, run "
                "OPEN_CONTROL_CENTER.cmd from the complete Python Windows ZIP.")
            return
        if profile["action"] in ("4","5") and not profile["database"].strip():
            # If already configured by the standard application, this is OK.
            configured=program_folder()/"LRCLIB_LOCAL_DB.txt"
            if not configured.is_file():
                self._dialog("showerror","Missing database","Option 4/5 requires your existing LRCLIB SQLite database. Choose it above.")
                return
        if getattr(sys,"frozen",False):
            worker=program_folder()/"LRC_Bulk_Finder_Worker.exe"
            if not worker.is_file():
                self._dialog("showerror","Missing worker",
                    "The standalone GUI requires LRC_Bulk_Finder_Worker.exe "
                    "in the same folder. Extract the complete EXE ZIP.")
                return
            cmd=[str(worker),"--profile",self.name.get()]
        else:
            cmd=[sys.executable,"-u",str(Path(__file__).with_name("run_saved_profile.py")),
                 "--profile",self.name.get()]
        try:
            self._cleanup_stop_marker()
            self.stop_directory=Path(tempfile.mkdtemp(prefix="LRC_Stop_"))
            self.stop_path=self.stop_directory/"stop.request"
            environment=dict(os.environ)
            environment["LRC_STOP_FILE"]=str(self.stop_path)
            # All GUI searches get a new creation-only journal under APPDATA.
            # The worker logs a file only AFTER creating it exclusively.
            self._manager_session_id=start_session(profile['folder'],label=self.name.get())
            environment['LRC_SESSION_ID']=self._manager_session_id
            selection=getattr(self,'_manager_selection_manifest',None)
            if selection:
                environment['LRC_SELECTED_TRACKS_FILE']=str(selection)
            else:
                environment.pop('LRC_SELECTED_TRACKS_FILE',None)
            creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name=="nt" else 0)
            self.process=subprocess.Popen(cmd,stdout=subprocess.PIPE,
               stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,
               encoding="utf-8",errors="replace",bufsize=1,
               cwd=str(program_folder()),creationflags=creationflags,env=environment,
               start_new_session=(os.name!="nt"))
        except (OSError,ValueError) as error:
            self._cleanup_stop_marker()
            if hasattr(self,'_manager_cleanup_selection'):self._manager_cleanup_selection()
            self._dialog("showerror","Cannot start search",str(error))
            return
        self._clear_log()
        self.active_profile=self.name.get()
        self.active_folder=profile["folder"]
        self.active_action=profile["action"]
        try:mark_run(self.active_profile,self.active_folder,"running")
        except OSError:pass
        self.provider_health=ProviderHealth(tuple(dict.fromkeys(PROVIDER_FULL+("SimpMusic",))))
        self._refresh_health()
        self.stop_requested=False
        self.stop_button.configure(text="STOP SEARCH — keep app open")
        for value in self.counter_vars.values():value.set("0")
        self.notebook.select(self.run_tab)
        self.stop_button.configure(state="normal")
        self.phase.set("Starting "+self.name.get()+"...")
        self.progress_text.set("Waiting for first completed song; ETA appears after 3 timed samples.")
        self.bar["value"]=0
        self.reader=threading.Thread(target=self._read_process,daemon=True)
        self.reader.start()

    def _read_process(self):
        process=self.process
        try:
            for line in process.stdout:
                self.messages.put(("line",line.rstrip("\r\n")))
            self.messages.put(("ended",process.wait()))
        except Exception as error:
            self.messages.put(("error",str(error)))

    def _poll(self):
        try:
            for _ in range(200):
                kind,data=self.messages.get_nowait()
                if kind=="line":self._line(data)
                elif kind=="ended":
                    if self.active_profile and self.active_folder:
                        try:mark_run(self.active_profile,self.active_folder, "stopped" if self.stop_requested or data!=0 else "finished")
                        except OSError:pass
                    if data==0 and not self.stop_requested and self.active_folder and self.active_action in ("1","5"):
                        try:
                            report=export_contribution(self.active_folder)
                            if report:self._line("PROVIDER CONTRIBUTION REPORT: "+str(report))
                        except (OSError,ValueError) as error:self._line("Contribution report unavailable: "+str(error))
                    self.phase.set(("Stopped by user; completed checkpoints preserved"
                                    if self.stop_requested else
                                    f"Search finished. Exit code: {data}"))
                    self.stop_button.configure(state="disabled")
                    self.process=None
                    self._cleanup_stop_marker()
                    if hasattr(self,'_manager_cleanup_selection'):self._manager_cleanup_selection()
                    self._refresh_review()
                elif kind=="hardstop_result":
                    success,detail=data
                    if not success:
                        alive=self.process is not None and self.process.poll() is None
                        self.stop_requested=not alive
                        self.stop_button.configure(state="normal" if alive else "disabled")
                        self.phase.set("STOP NOT FULLY VERIFIED: "+detail)
                    else:
                        self._line("STOP: "+detail+" Completed checkpoints remain available.")
                elif kind=="error":
                    self._line("Control Center reader error: "+data)
        except queue.Empty:pass
        self.after(110,self._poll)

    def _line(self,line):
        if self.provider_health.observe(line):self._refresh_health()
        status=re.fullmatch(
            r"STAGE COUNTERS: stage=(\w+) found=(\d+) candidate=(\d+) "
            r"not_found=(\d+) total_found=(\d+) total_candidate=(\d+)(?: skipped=(\d+))?",
            line.strip())
        if status:
            stage,found,candidate,not_found,total_found,total_candidate,skipped=status.groups()
            for key,number in (
                ("found",found),("candidate",candidate),("not_found",not_found),
                ("total_found",total_found),("total_candidate",total_candidate),("skipped",skipped or "0")):
                self.counter_vars[key].set(number)
        self.log.configure(state="normal")
        self.log.insert("end",line+"\n")
        # Bound memory for multi-day searches.
        if int(self.log.index("end-1c").split(".")[0])>6000:
            self.log.delete("1.0","2000.0")
        self.log.see("end")
        self.log.configure(state="disabled")
        match=re.search(r"PROGRESS ROUND (\w+): (\d+)/(\d+) \(([\d.]+)%\) \| elapsed (.*?) \| THIS ROUND ETA: (.*?)(?: \||$)",line)
        if match:
            stage,done,total,pct,elapsed,eta=match.groups()
            self.phase.set(f"Round {stage} — {done} / {total} completed")
            self.progress_text.set(f"Elapsed this round: {elapsed}    Estimated remaining this round: {eta}")
            self.bar["value"]=min(100,float(pct))
        elif line.startswith("===== ROUND"):
            self.phase.set(line.strip("= ").strip())
            self.bar["value"]=0
            self.progress_text.set("New round: ETA starts after 3 completed uncached songs")

    def _stop(self):
        process=self.process
        if process is None or process.poll() is not None or self.stop_requested:
            return
        if not self._dialog("askyesno",
                "Stop search now?",
                "Immediately KILL the running lyrics-search worker?\n\n"
                "The CONTROL CENTER will stay open. Finished-song checkpoints "
                "are retained, but the in-progress song and final reports "
                "might not have been written. Restarting can retry that song."):
            return
        self.stop_requested=True
        self.stop_button.configure(state="disabled",text="Stopping worker...")
        self.phase.set("Stopping search worker — app remains open...")
        self.progress_text.set("Previously saved checkpoints remain; unfinished song may be retried.")
        threading.Thread(target=self._hard_stop_worker,
                         args=(process,),daemon=True).start()

    def _hard_stop_worker(self,process):
        self.messages.put(("hardstop_result",kill_search_process(process)))

    def _cleanup_stop_marker(self):
        directory=self.stop_directory
        self.stop_directory=None
        self.stop_path=None
        if directory:
            try:shutil.rmtree(directory)
            except OSError:pass

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0","end")
        self.log.configure(state="disabled")

    def _refresh_review(self):
        self.review_rows={}
        self.review_tree.delete(*self.review_tree.get_children())
        folder=self.folder.get()
        if not folder or not Path(folder).is_dir():return
        try:
            for i,item in enumerate(list_review_candidates(folder,self.boolvars["recursive"].get())):
                path=item["path"]
                status=("Missing / ambiguous audio" if not item["has_mp3"] else
                        "Already has LRC" if item["has_lrc"] else
                        "Primary — review" if item["index"]==1 else "Alternative — read-only")
                key=str(i)
                self.review_rows[key]=item
                self.review_tree.insert("","end",iid=key,
                    values=(item["mp3"].name,path.name,self._tr(status)))
        except (OSError,ValueError) as error:
            self._dialog("showerror","Candidate scan",str(error))

    def _selection(self):
        items=self.review_tree.selection()
        return self.review_rows.get(items[0]) if items else None

    def _candidate_selected(self,_event=None):
        item=self._selection()
        value=""
        if item:
            try:value=preview_candidate(item["path"])
            except (OSError,ValueError) as error:value="Preview unavailable: "+str(error)
        self.candidate_text.configure(state="normal")
        self.candidate_text.delete("1.0","end")
        self.candidate_text.insert("1.0",value)
        self.candidate_text.configure(state="disabled")

    def _play_selected(self):
        item=self._selection()
        if not item or not item["has_mp3"]:return
        path=item["mp3"]
        try:
            if sys.platform=="win32":os.startfile(path)
            elif sys.platform=="darwin":subprocess.Popen(["open",str(path)])
            else:subprocess.Popen(["xdg-open",str(path)])
        except (OSError,AttributeError) as error:
            self._dialog("showerror","Open audio",str(error))

    def _promote_selected(self):
        if self.process is not None and self.process.poll() is None:
            self._dialog("showwarning","Search running","Finish the search before reviewing files.")
            return
        item=self._selection()
        if not item:return
        if item["index"]!=1 or not item["has_mp3"] or item["has_lrc"]:
            self._dialog("showinfo","Not eligible","Only a primary candidate with exactly one matching audio file and no existing LRC can be promoted.")
            return
        if not self._dialog("askyesno","Install UNVERIFIED candidate?",
            f"Install {item['path'].name} as a MARKED .lrc?\n\n"
            "It will contain [00:00.00] candidate and remain UNVERIFIED.\n"
            "Original audio/metadata will NOT change. Numbered alternatives shift forward."):
            return
        try:
            status,detail=explicitly_promote(item["path"],approved=True)
            self._dialog("showinfo","Candidate result",status+": "+detail)
        except (ValueError,PermissionError,OSError) as error:
            self._dialog("showerror","Candidate result",str(error))
        self._refresh_review()

    def _build_sync_lab(self):
        area=self.sync_tab
        ttk.Label(area,text="Experimental Sync Lab — untimed lyrics",style="Header.TLabel").pack(anchor="w")
        ttk.Label(area,text="Import or paste plain lyric text. Estimate rough timings or tap along while you listen. "
                  "This cannot confirm alignment and only saves MARKED .candidate.lrc sidecars.",
                  wraplength=900).pack(anchor="w",pady=(4,10))
        top=ttk.Frame(area);top.pack(fill="x")
        self.sync_audio=tk.StringVar()
        ttk.Entry(top,textvariable=self.sync_audio).pack(side="left",fill="x",expand=True)
        ttk.Button(top,text="Choose audio...",command=self._sync_choose_audio).pack(side="left",padx=5)
        ttk.Button(top,text="Open audio player",command=self._sync_play).pack(side="left",padx=5)
        ttk.Label(area,text="Plain lyrics (paste your own text, or import a .txt / plain .lrc)").pack(anchor="w",pady=(8,2))
        self.sync_source=scrolledtext.ScrolledText(area,height=9,wrap="word",font=("Consolas",10))
        self.sync_source.pack(fill="both",expand=True)
        top=ttk.Frame(area);top.pack(fill="x",pady=7)
        ttk.Button(top,text="Import plain text...",command=self._sync_import).pack(side="left",padx=2)
        ttk.Button(top,text="Generate ESTIMATED timestamps",command=self._sync_estimate).pack(side="left",padx=4)
        ttk.Button(top,text="Start tap timing",command=self._sync_start_tap).pack(side="left",padx=4)
        ttk.Button(top,text="Tap NEXT line",command=self._sync_tap).pack(side="left",padx=4)
        self.sync_status=tk.StringVar(value="No timings generated. All results are unverified.")
        ttk.Label(area,textvariable=self.sync_status,wraplength=930).pack(anchor="w")
        ttk.Label(area,text="Editable LRC draft — candidate marker must remain the first line").pack(anchor="w",pady=(10,2))
        self.sync_draft=scrolledtext.ScrolledText(area,height=10,wrap="word",font=("Consolas",10))
        self.sync_draft.pack(fill="both",expand=True)
        ttk.Button(area,text="Save as UNVERIFIED .candidate.lrc (never overwrite)",
                   command=self._sync_save).pack(fill="x",pady=10)
        self.sync_lines=[]
        self.sync_times=[]
        self.sync_start=None
        self.sync_position=0

    def _sync_choose_audio(self):
        path=self._file_dialog("askopenfilename",title="Choose an audio track",
            filetypes=[("Supported audio","*.mp3 *.flac *.m4a *.mp4 *.ogg *.opus *.wav"),("All files","*.*")])
        if path:
            self.sync_audio.set(path)
            self.sync_status.set("Selected "+Path(path).name+". Original audio will never be modified.")

    def _sync_play(self):
        path=Path(self.sync_audio.get())
        if not path.is_file():
            self._dialog("showerror","Sync Lab","Choose an existing audio track first.")
            return
        try:
            if sys.platform=="win32":os.startfile(path)
            elif sys.platform=="darwin":subprocess.Popen(["open",str(path)])
            else:subprocess.Popen(["xdg-open",str(path)])
        except (OSError,AttributeError) as error:self._dialog("showerror","Audio player",str(error))

    def _sync_import(self):
        path=self._file_dialog("askopenfilename",title="Open untimed lyrics",
            filetypes=[("Text or LRC","*.txt *.lrc"),("Text files","*.txt"),("All files","*.*")])
        if not path:return
        try:
            file=Path(path)
            if file.stat().st_size>150000:raise ValueError("Text file exceeds 150 KB preview limit")
            source=file.read_text(encoding="utf-8-sig",errors="replace")
            self.sync_source.delete("1.0","end")
            self.sync_source.insert("1.0",source)
            self.sync_status.set("Imported text. Generate estimates or start tapping.")
        except (OSError,ValueError) as error:self._dialog("showerror","Import",str(error))

    def _sync_estimate(self):
        try:
            from mutagen import File as MutagenFile
            track=Path(self.sync_audio.get())
            if not track.is_file():raise FileNotFoundError("Choose an existing audio track")
            audio=MutagenFile(track,easy=True)
            if audio is None or audio.info is None:raise ValueError("Cannot read duration")
            duration=float(audio.info.length)
            lines=plain_lines(self.sync_source.get("1.0","end"))
            times=estimate_timestamps(lines,duration)
            draft=draft_lrc(lines,times)
            self.sync_lines=lines;self.sync_times=times;self.sync_start=None
            self.sync_draft.delete("1.0","end")
            self.sync_draft.insert("1.0",draft)
            self.sync_status.set(f"ESTIMATE ONLY: {len(lines)} lines across {duration:.1f}s. "
                 "Review and edit timestamps; not aligned to speech.")
        except (OSError,ValueError,TypeError) as error:self._dialog("showerror","Timing estimate",str(error))

    def _sync_start_tap(self):
        try:
            self.sync_lines=plain_lines(self.sync_source.get("1.0","end"))
        except ValueError as error:
            self._dialog("showerror","Tap timing",str(error))
            return
        self.sync_times=[]
        self.sync_position=0
        self.sync_start=time.monotonic()
        self.sync_status.set("Tap started! Press Tap NEXT line when you hear the next lyric begin. "
                             "Align the audio player's playback yourself; this does not control the player.")
        self.sync_draft.delete("1.0","end")
        self.sync_draft.insert("1.0","[00:00.00] candidate\n")

    def _sync_tap(self):
        if self.sync_start is None or self.sync_position>=len(self.sync_lines):
            self.sync_status.set("Start tap timing, or all lyric lines have already been marked.")
            return
        current=round(max(0,time.monotonic()-self.sync_start),2)
        if self.sync_times and current<=self.sync_times[-1]:
            current=self.sync_times[-1]+0.01
        self.sync_times.append(current)
        self.sync_position+=1
        self.sync_draft.insert("end",f"{self._sync_stamp(current)} {self.sync_lines[self.sync_position-1]}\n")
        self.sync_status.set(f"Tapped {self.sync_position}/{len(self.sync_lines)} lines. "
            "Manual taps remain UNVERIFIED until reviewed against the recording.")

    @staticmethod
    def _sync_stamp(value):
        from lyric_sync_lab import stamp
        return stamp(value)

    def _sync_save(self):
        if self.process is not None and self.process.poll() is None:
            self._dialog("showwarning","Search running","Finish your search before writing candidate files.")
            return
        if not self.sync_lines or len(self.sync_times)!=len(self.sync_lines):
            self._dialog("showerror","Incomplete timings","Generate estimates or tap ALL lyric lines first.")
            return
        track=Path(self.sync_audio.get())
        if not track.is_file():
            self._dialog("showerror","Missing audio","Choose an existing audio file first.")
            return
        if not self._dialog("askyesno","SAVE UNVERIFIED candidate",
            "Create an additional .candidate.lrc next to this audio file?\n\n"
            "These timings are EXPERIMENTAL and have NOT been aligned or verified. "
            "The candidate marker will stay. Existing lyrics and audio are protected."):
            return
        try:
            target=save_unverified_draft(track,self.sync_draft.get("1.0","end"),
                                        self.sync_lines,self.sync_times)
            self.sync_status.set("Saved UNVERIFIED candidate: "+str(target))
            self._dialog("showinfo","Candidate saved",f"Saved:\n{target}\n\nUnverified timing — review before promotion.")
            self._refresh_review()
        except (OSError,ValueError,FileExistsError) as error:
            self._dialog("showerror","Cannot save candidate",str(error))

    def _close(self):
        if self.process is not None and self.process.poll() is None:
            self._dialog("showwarning","Search running",
                "Stop the current search before closing the Control Center.")
            return
        if hasattr(self,'_manager_cleanup_selection'):self._manager_cleanup_selection()
        self.destroy()


def main():
    app=ControlCenter()
    app.mainloop()


if __name__=="__main__":
    main()
