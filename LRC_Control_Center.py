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

from v296_provider_tiers import DISPLAY as PROVIDER_PACK_LABELS, DESCRIPTION as PACK_DESCRIPTIONS, LEGACY as PACK_LEGACY, PACKS as PROVIDER_PACK_SOURCES
from v297_provider_intelligence import ALL_SOURCES, available_sources
from search_profiles import (DEFAULT,PROVIDER_FAST,PROVIDER_FULL,load_profiles,
                             save_profiles,validate_profile,PRESET_TEMPLATES,
                             PRESET_DESCRIPTIONS,preset_profile)
from tooltip_help import ToolTip
from lyric_sync_lab import plain_lines,estimate_timestamps,draft_lrc,save_unverified_draft
from review_candidates_gui import (list_review_candidates,preview_candidate,
                                   explicitly_promote)
from v298_candidate_workbench import (
    STATUSES as CANDIDATE_FILTERS, summarize as candidate_summary,
    filtered as filter_candidates, sort_items as sort_candidates,
    status_for as candidate_status, can_promote as candidate_can_promote,
    primary_paths as eligible_primary_paths, alternative_breakdown,
    selected_alternative_paths, bulk_recycle_alternatives,
    bulk_promote as batch_promote)
from runtime_paths import program_folder
from worker_stop import kill_search_process
from v243_health import ProviderHealth
from v243_resume import last_run, mark_run
from v243_aliases import approve_alias
from v243_contribution import export_contribution
from ui_locale import GuiLocale, read_language, save_language
from ui_appearance import read_mode, save_mode, install_theme, refresh_native_widgets, PALETTES
from ui_translations import UI_EL
from v250_manager import start_session
from v245_features import VERSION as APP_VERSION
from v245_gui import V245Mixin
from v290_smart_gui import V290Mixin


class ControlCenter(V290Mixin,V245Mixin,tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"LRC Bulk Finder v{APP_VERSION} — Control Center")
        self.gui_locale=GuiLocale(read_language())
        self.appearance_mode=read_mode()
        self._locale_widgets={}
        self._status_vars={}
        self._locale_is_refreshing=False
        self.geometry("1250x940")
        self.minsize(980,760)
        self.process=None
        self.reader=None
        self.stop_directory=None
        self.stop_path=None
        self.stop_requested=False
        self.g2g_setup_process=None
        self.g2g_setup_window=None
        self.active_profile=None
        self.active_folder=None
        self.active_action=None
        self.benchmark_process=None
        self.benchmark_stop_requested=False
        self.messages=queue.Queue()
        self.review_rows={}
        self.review_all_rows=[]
        self.review_sort_column="track"
        self.review_sort_descending=False
        self.review_bulk_running=False
        self.review_bulk_stop=False
        self.review_bulk_kind=None
        self.loaded_profiles={}
        self._build()
        refresh_native_widgets(self,self.appearance_mode)
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

    def _g2g_available(self):
        if not getattr(sys,"frozen",False):
            return True  # Python edition can use its own installed toolkit.
        from g2g_auto import installed
        return installed() is not None

    def _available_preset_names(self):
        ready=self._g2g_available()
        return [name for name in PRESET_TEMPLATES
                if ready or not PRESET_TEMPLATES[name].get("local_ai",False)]

    def _preset_key(self,display):
        if display in PRESET_TEMPLATES:return display
        # Display text is independent of the persisted/internal preset key.
        for original in PRESET_TEMPLATES:
            if GuiLocale('el').tr(original)==display:return original
        return display

    def _appearance_options(self):
        return ("Φωτεινό", "Σκοτεινό") if self.gui_locale.language=="el" else ("Light","Dark")

    def _appearance_selected(self,_event=None):
        selected=self.appearance_choice.get()
        mode="dark" if selected in ("Dark","Σκοτεινό") else "light"
        if mode==self.appearance_mode:return
        self.appearance_mode=mode
        self.palette=install_theme(self,mode)
        refresh_native_widgets(self,mode)
        try:save_mode(mode)
        except OSError as error:
            self._dialog("showwarning","Appearance","Could not save appearance preference: "+str(error))

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
            self.title(f'LRC Bulk Finder v{APP_VERSION} — Control Center')
            if hasattr(self,"appearance_control"):
                self.appearance_control.configure(values=self._appearance_options())
                self.appearance_choice.set(self._appearance_options()[1 if self.appearance_mode=="dark" else 0])
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
            if hasattr(self, "studio_tabs"):
                for tab in self.studio_tabs.tabs():
                    original = self._locale_widgets.get(("studio_tab", tab))
                    if original is None:
                        original = self.studio_tabs.tab(tab, "text")
                        self._locale_widgets[("studio_tab", tab)] = original
                    self.studio_tabs.tab(tab, text=self._tr(original))
            for tree in (getattr(self,'health_tree',None),getattr(self,'review_tree',None),
                         getattr(self,'dashboard_tree',None),getattr(self,'studio_tree',None)):
                if tree is None:continue
                for key in tree['columns']:
                    original=self._locale_widgets.get(('heading',str(tree),key))
                    if original is None:
                        original=tree.heading(key,'text')
                        self._locale_widgets[('heading',str(tree),key)]=original
                    tree.heading(key,text=self._tr(original))
            if hasattr(self,"pack_picker"):
                current_pack=self._pack_key(self.provider_pack.get())
                self.pack_picker.configure(values=[self._tr(value) for value in PROVIDER_PACK_LABELS.values()])
                self.provider_pack.set(self._tr(PROVIDER_PACK_LABELS[current_pack]))
                self.provider_pack_help.set(self._tr(PACK_DESCRIPTIONS[current_pack]))
            if hasattr(self,'preset_choice'):
                current=self._preset_key(self.preset_name.get())
                self.preset_choice.configure(values=[self._tr(k) for k in self._available_preset_names()])
                if current in PRESET_TEMPLATES:self.preset_name.set(self._tr(current))
            for var,raw in self._status_vars.values():
                localized=self._tr(raw)
                if var.get()!=localized:var.set(localized)
            if hasattr(self,"review_filter_picker"):
                current=self._review_filter_key()
                self.review_filter_picker.configure(
                    values=[self._tr(k) for k in CANDIDATE_FILTERS])
                self.review_filter.set(self._tr(current))
                self._render_review()
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
        # Pure presentation: all old search widgets, states and callbacks survive.
        self.palette=install_theme(self,self.appearance_mode)
        header=ttk.Frame(self,style="Hero.TFrame",padding=(22,16,22,14))
        header.pack(fill="x")
        header.columnconfigure(1,weight=1)
        ttk.Label(header,text="♫",style="HeroAccent.TLabel").grid(row=0,column=0,rowspan=2,
            sticky="nw",padx=(0,12))
        ttk.Label(header,text="LRC Bulk Finder",style="HeroTitle.TLabel").grid(
            row=0,column=1,sticky="sw")
        ttk.Label(header,text="Search profiles · trusted progress · careful lyric review",
                  style="HeroSubtitle.TLabel").grid(row=1,column=1,sticky="nw",pady=(1,0))
        ttk.Label(header,text=f"v{APP_VERSION}",style="HeroMeta.TLabel").grid(
            row=0,column=2,sticky="e",padx=(6,24))
        self.appearance_choice=tk.StringVar(
            value=("Σκοτεινό" if self.gui_locale.language=="el" else "Dark")
                  if self.appearance_mode=="dark" else
                  ("Φωτεινό" if self.gui_locale.language=="el" else "Light"))
        self.appearance_control=ttk.Combobox(header,textvariable=self.appearance_choice,
                                            values=self._appearance_options(),
                                            state="readonly",width=12)
        self.appearance_control.grid(row=0,column=3,sticky="e",padx=(0,14))
        self.appearance_control.bind("<<ComboboxSelected>>",self._appearance_selected)
        ttk.Label(header,text="Appearance",style="HeroMeta.TLabel").grid(
            row=1,column=3,sticky="e",padx=(0,14))
        self.language_choice=tk.StringVar(value="Ελληνικά" if self.gui_locale.language=='el' else "English")
        self.language_control=ttk.Combobox(header,textvariable=self.language_choice,
                                           values=("English","Ελληνικά"),state="readonly",width=13)
        self.language_control.grid(row=0,column=4,sticky="e")
        self.language_control.bind("<<ComboboxSelected>>",self._language_selected)
        ttk.Label(header,text="Interface language",style="HeroMeta.TLabel").grid(
            row=1,column=4,sticky="e")
        self.notebook=ttk.Notebook(self)
        self.notebook.pack(fill="both",expand=True,padx=18,pady=(0,18))
        self.quick_tab=ttk.Frame(self.notebook,padding=18)
        self.search_tab=ttk.Frame(self.notebook,padding=(10,12))
        self.run_tab=ttk.Frame(self.notebook,padding=18)
        self.review_tab=ttk.Frame(self.notebook,padding=18)
        self.sync_tab=ttk.Frame(self.notebook,padding=18)
        self.health_tab=ttk.Frame(self.notebook,padding=18)
        self.dashboard_tab=ttk.Frame(self.notebook,padding=18)
        self.repair_tab=ttk.Frame(self.notebook,padding=18)
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
        # Accent the existing primary actions, without touching their commands.
        if hasattr(self,"search_start_button"):
            self.search_start_button.configure(style="Primary.TButton")
        if hasattr(self,"stop_button"):
            self.stop_button.configure(style="Danger.TButton")

    def _build_health(self):
        """States are derived from this run's actual provider output."""
        names=tuple(dict.fromkeys(PROVIDER_FULL+("BetterQQ","SimpMusic")))
        self.provider_health=ProviderHealth(names)
        bench=ttk.LabelFrame(self.health_tab,text="Provider Benchmark — read-only music test",padding=10)
        bench.pack(fill="x",pady=(0,12))
        buttons=ttk.Frame(bench)
        buttons.pack(fill="x")
        ttk.Label(buttons,text="Sample size").pack(side="left",padx=(0,6))
        self.benchmark_sample=tk.StringVar(value="10")
        self.benchmark_sample_picker=ttk.Combobox(buttons,textvariable=self.benchmark_sample,
                                                   values=("5","10","20"),state="readonly",width=6)
        self.benchmark_sample_picker.pack(side="left",padx=(0,12))
        self.benchmark_start_button=ttk.Button(buttons,text="Test My Providers",
                                              command=self._start_provider_benchmark,
                                              style="Primary.TButton")
        self.benchmark_start_button.pack(side="left",padx=(0,10))
        self.benchmark_stop_button=ttk.Button(buttons,text="Stop benchmark",
                                             command=self._stop_provider_benchmark,state="disabled")
        self.benchmark_stop_button.pack(side="left")
        self.benchmark_status=tk.StringVar(value="No benchmark running. Select a music folder, tier and sources in Saved searches.")
        ttk.Label(bench,textvariable=self.benchmark_status,style="Hint.TLabel",
                  wraplength=1000).pack(fill="x",pady=(8,5))
        cols=("provider","tested","verified","unique","review","timeouts","errors","avg")
        self.benchmark_tree=ttk.Treeview(bench,columns=cols,show="headings",height=5)
        for key,title,width in (("provider","Source",130),("tested","Tested",65),
                                ("verified","Verified",70),("unique","Unique",65),
                                ("review","Review",65),("timeouts","Timeout",70),
                                ("errors","Errors",65),("avg","Avg sec",65)):
            self.benchmark_tree.heading(key,text=title)
            self.benchmark_tree.column(key,width=width,stretch=True)
        self.benchmark_tree.pack(fill="x",pady=(2,5))
        ttk.Label(self.health_tab,text="Provider health — current run",style="Header.TLabel").pack(anchor="w")
        ttk.Label(self.health_tab,text="The health table is passive; only Test My Providers makes live requests. HTTP 200 does not verify a lyric.",wraplength=900).pack(anchor="w",pady=8)
        fields=("provider","status","last_http_success","last_verified","verified_count","detail")
        self.health_tree=ttk.Treeview(self.health_tab,columns=fields,show="headings",height=10)
        for key,label,width in (("provider","Provider",120),("status","Latest state",170),("last_http_success","Latest HTTP 2xx",145),("last_verified","Last verified hit",155),("verified_count","Verified hits",100),("detail","Latest response",340)):
            self.health_tree.heading(key,text=label)
            self.health_tree.column(key,width=width,stretch=True)
        self.health_tree.pack(fill="both",expand=True,pady=8)
        self._refresh_health()

    def _refresh_health(self):
        self.health_tree.delete(*self.health_tree.get_children())
        for provider,data in self.provider_health.rows.items():
            self.health_tree.insert("","end",values=(provider,self._tr(data["status"]),data["last_http_success"],data["last_verified"],data["verified_count"],data["detail"]))

    def _start_provider_benchmark(self):
        if self.review_bulk_running:
            self._dialog("showwarning","Candidate promotion running",
                         "Finish or stop candidate promotion before benchmarking.")
            return
        # Unlike a real search, this does not save a profile, open a creation
        # journal or install any lyrics. It only creates a CSV of aggregate data.
        if self.process is not None and self.process.poll() is None:
            self._dialog("showwarning","Search running",
                         "Finish the current search before benchmarking providers.")
            return
        if self.benchmark_process is not None and self.benchmark_process.poll() is None:
            return
        if self.g2g_setup_process is not None and self.g2g_setup_process.poll() is None:
            self._dialog("showwarning","Installation running",
                         "Finish Greek AI installation before testing providers.")
            return
        try:
            profile=self._values()
            folder=Path(profile["folder"])
            if not folder.is_dir():raise ValueError("Selected music folder does not exist.")
            selected=int(self.benchmark_sample.get())
            if selected not in (5,10,20):raise ValueError("Choose 5, 10 or 20 test songs")
        except (ValueError,OSError) as error:
            self._dialog("showerror","Benchmark configuration",str(error))
            return
        # A source benchmark is intentionally live, even if the selected search
        # action is OFFLINE ONLY. State this explicitly and require confirmation.
        note=("Perform a LIVE online test of "+str(selected)+" songs using "
              +str(len(self._base_pack_sources())-len(profile["provider_exclusions"]))+
              " enabled sources?\n\n"
              "No LRC, candidates, MP3s or tags will be created or edited. "
              "Only an aggregate CSV is written to your personal application-data folder. "
              "This makes REAL provider network requests, which may take minutes "
              "and must respect rate limits, provider cooldowns and server restrictions.")
        if not self._dialog("askyesno","Test My Providers",note):
            return
        if getattr(sys,"frozen",False):
            executable=program_folder()/"LRC_Bulk_Finder_Worker.exe"
            if not executable.is_file():
                self._dialog("showerror","Missing worker","Extract both EXEs in the same folder.")
                return
            cmd=[str(executable)]
        else:
            cmd=[sys.executable,"-u",str(Path(__file__).with_name("run_saved_profile.py"))]
        cmd+=["--benchmark","--benchmark-folder",str(folder),
              "--benchmark-pack",profile["provider_pack"],
              "--benchmark-mode",profile["provider_mode"],
              "--benchmark-excluded",",".join(profile["provider_exclusions"]),
              "--benchmark-sample",str(selected)]
        if not profile["recursive"]:cmd.append("--benchmark-nonrecursive")
        if profile["provider_pack"]==PACK_LEGACY and profile.get("experimental_simpmusic"):
            cmd.append("--benchmark-experimental-simpmusic")
        env=dict(os.environ)
        env["PYTHONIOENCODING"]="utf-8:backslashreplace"
        # Benchmark must not inherit any search-only selection or user stop marker.
        env.pop("LRC_SESSION_ID",None)
        env.pop("LRC_SELECTED_TRACKS_FILE",None)
        env.pop("LRC_STOP_FILE",None)
        try:
            self.benchmark_process=subprocess.Popen(
                cmd,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,encoding="utf-8",errors="replace",bufsize=1,
                cwd=str(program_folder()),env=env,
                creationflags=(getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0)
                               if os.name=="nt" else 0),
                start_new_session=(os.name!="nt"))
        except (OSError,ValueError) as error:
            self.benchmark_process=None
            self._dialog("showerror","Benchmark cannot start",str(error))
            return
        self.benchmark_stop_requested=False
        self.benchmark_start_button.configure(state="disabled")
        self.benchmark_stop_button.configure(state="normal")
        self.benchmark_status.set("Provider test running (read-only). Reports will remain in app data.")
        self.benchmark_tree.delete(*self.benchmark_tree.get_children())
        threading.Thread(target=self._read_benchmark_process,
                         args=(self.benchmark_process,),daemon=True).start()

    def _read_benchmark_process(self,process):
        try:
            for line in process.stdout:
                self.messages.put(("benchmark_line",line.rstrip("\r\n")))
            self.messages.put(("benchmark_done",process.wait()))
        except (OSError,ValueError) as error:
            self.messages.put(("benchmark_line","Reader error: "+str(error)))
            self.messages.put(("benchmark_done",process.poll() or 2))

    def _stop_provider_benchmark(self):
        process=self.benchmark_process
        if process is None or process.poll() is not None:
            return
        if not self._dialog("askyesno","Stop provider benchmark",
                            "Immediately stop the live provider test? "
                            "No music files have been modified; a partial CSV "
                            "may not be available if the worker is killed."):
            return
        self.benchmark_stop_requested=True
        self.benchmark_stop_button.configure(state="disabled")
        self.benchmark_status.set("Stopping provider benchmark...")
        threading.Thread(target=lambda:self.messages.put(
            ("benchmark_stop",kill_search_process(process))),daemon=True).start()

    def _load_benchmark_report(self,path):
        import csv
        self.benchmark_tree.delete(*self.benchmark_tree.get_children())
        with Path(path).open(encoding="utf-8-sig",newline="") as f:
            rows=list(csv.DictReader(f))
        for row in rows:
            self.benchmark_tree.insert("","end",values=(
                row["provider"],row["attempts"],row["verified_matches"],
                row["unique_verified_matches"],row["review_only"],row["timeouts"],
                row["errors"],row["average_seconds"]))
        self.benchmark_status.set(
            "Benchmark results: "+str(path)+". "
            "Unique means the first matching provider in the chosen tier order; "
            "it is not permission to install lyrics automatically.")

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
        # Only the long advanced form scrolls; 940px screens no longer cut off
        # the setup options or Start Search button. Other tabs stay unchanged.
        host=self.search_tab
        canvas=tk.Canvas(host,highlightthickness=0,borderwidth=0,
                         background=self.palette["surface"])
        scrollbar=ttk.Scrollbar(host,orient="vertical",command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right",fill="y")
        canvas.pack(side="left",fill="both",expand=True)
        outer=ttk.Frame(canvas,padding=(8,4,14,16))
        window=canvas.create_window((0,0),window=outer,anchor="nw")
        outer.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",lambda e:canvas.itemconfigure(window,width=e.width))
        canvas.bind("<MouseWheel>",lambda e:canvas.yview_scroll(int(-e.delta/120),"units"))
        self.profiles_canvas=canvas
        self.profiles_content=outer
        outer.columnconfigure(1,weight=1)
        self.name=tk.StringVar()
        self.folder=tk.StringVar()
        self.database=tk.StringVar()
        self.action=tk.StringVar(value="5")
        self.provider_mode=tk.StringVar(value="full")
        self.provider_pack=tk.StringVar(value=PROVIDER_PACK_LABELS[PACK_LEGACY])
        self.provider_pack_help=tk.StringVar(value=PACK_DESCRIPTIONS[PACK_LEGACY])
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
                                   values=self._available_preset_names(),state="readonly",width=44)
        self.preset_choice=preset_choice
        preset_choice.grid(row=row,column=1,sticky="ew",padx=5)
        preset_choice.bind("<<ComboboxSelected>>",self._preset_selected)
        ttk.Button(outer,text="Apply preset",command=self._apply_preset).grid(row=row,column=2,sticky="ew",padx=5)
        self._tool_tip(preset_choice,"15 presets, grouped Greek first and international second, broadest searches first. Offline-first/offline-only require a configured local LRCLIB SQLite database. Optional G2G model is not bundled. Applying a preset never overwrites saved profiles.")
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
        self.provider_mode_picker=ttk.Combobox(outer,textvariable=self.provider_mode,state="readonly",
                     values=("fast","full"),width=12)
        self.provider_mode_picker.grid(row=row,column=1,sticky="w",padx=5)
        self.provider_mode_picker.bind("<<ComboboxSelected>>",self._source_selection_updated)
        row+=1
        ttk.Label(outer,text="Provider pack / cumulative tier").grid(
            row=row,column=0,sticky="w",padx=5,pady=5)
        self.pack_picker=ttk.Combobox(
            outer,textvariable=self.provider_pack,state="readonly",width=43,
            values=[self._tr(name) for name in PROVIDER_PACK_LABELS.values()])
        self.pack_picker.grid(row=row,column=1,sticky="ew",padx=5)
        self.pack_picker.bind("<<ComboboxSelected>>",self._pack_changed)
        ttk.Label(outer,text="Tier 1 ⊂ 2 ⊂ 3 ⊂ 4 ⊂ 5 ⊂ 6",style="Hint.TLabel").grid(
            row=row,column=2,sticky="w",padx=5)
        row+=1
        ttk.Label(outer,textvariable=self.provider_pack_help,wraplength=850,
                  style="Hint.TLabel").grid(row=row,column=0,columnspan=3,sticky="w",padx=5,pady=(0,6))
        row+=1
        excluded=ttk.LabelFrame(outer,text="Individual provider exclusions (optional)",padding=9)
        excluded.grid(row=row,column=0,columnspan=3,sticky="ew",padx=5,pady=(6,8))
        self.source_enabled={}
        self.source_checkboxes={}
        for index,source in enumerate(ALL_SOURCES):
            self.source_enabled[source]=tk.BooleanVar(value=True)
            widget=ttk.Checkbutton(excluded,text=source,variable=self.source_enabled[source])
            widget.grid(row=index//4,column=index%4,sticky="w",padx=10,pady=4)
            self.source_checkboxes[source]=widget
        self.exclusions_hint=tk.StringVar()
        ttk.Label(excluded,textvariable=self.exclusions_hint,style="Hint.TLabel",
                  wraplength=950).grid(row=4,column=0,columnspan=4,sticky="w",padx=7,pady=(8,0))
        self._source_selection_updated()
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
            if key=="experimental_simpmusic":
                widget.configure(command=self._source_selection_updated)
            if key=="local_ai":
                self.g2g_checkbox=widget
                if not self._g2g_available():
                    widget.configure(state="disabled")
                    self.boolvars["local_ai"].set(False)
            self._tool_tip(widget,descriptions[key])
        row+=1
        setup=ttk.LabelFrame(outer,text="Downloads & local setup",padding=8)
        setup.grid(row=row,column=0,columnspan=3,sticky="ew",pady=5)
        lrclib_button=ttk.Button(setup,text="Download / set up LRCLIB database",
                                 command=lambda:self._launch_setup("SETUP_LRCLIB_DATABASE.cmd"))
        lrclib_button.pack(side="left",padx=5)
        self.g2g_button=ttk.Button(setup,text="Install / verify Greek G2G AI (one click)",
                                   command=self._install_g2g)
        self.g2g_button.pack(side="left",padx=5)
        self.g2g_status=tk.StringVar(value="Greek AI ready" if self._g2g_available() else
                                     "Optional model not installed")
        ttk.Label(setup,textvariable=self.g2g_status,style="Hint.TLabel").pack(side="left",padx=8)
        self._tool_tip(lrclib_button,"Starts the bundled LRCLIB setup script in a separate Windows terminal, with its own prompts. Already downloaded? Use Choose database instead.")
        self._tool_tip(self.g2g_button,"One-click optional AUEB G2G setup: isolated Python environment, downloads, verification and progress. Requires approval, internet and significant free disk space.")
        row+=1
        self.search_start_button=ttk.Button(outer,text="Save profile and START SEARCH",
                   command=self._run_profile,style="Primary.TButton")
        self.search_start_button.grid(row=row,column=0,columnspan=3,sticky="ew",padx=5,pady=(12,10))
        ttk.Label(outer,text="The GUI stores profiles in your local user settings. Original MP3s/ID3 files are never modified.",
                  style="Hint.TLabel").grid(row=row+1,column=0,columnspan=3,sticky="w",padx=5)
        # Native wheel scrolling reaches child controls, without a global mouse
        # binding that could unexpectedly scroll tabs or editable lyric text.
        def wheel(event):
            if self.notebook.select()!=str(self.search_tab):
                return None
            amount=int(-event.delta/120) if getattr(event,"delta",0) else (
                -1 if getattr(event,"num",0)==4 else 1)
            if amount:
                self.profiles_canvas.yview_scroll(amount,"units")
            return "break"
        for widget in (canvas,outer,*tuple(self._iter_ui_children(outer))):
            if isinstance(widget,ttk.Combobox):
                continue  # Wheel within a focused combo retains native selection.
            widget.bind("<MouseWheel>",wheel,add="+")
            widget.bind("<Button-4>",wheel,add="+")
            widget.bind("<Button-5>",wheel,add="+")

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
        self.stop_button=ttk.Button(controls,text="STOP SEARCH — keep app open",state="disabled",command=self._stop,style="Danger.TButton")
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
            ttk.Label(item,textvariable=value,style="Metric.TLabel").pack()
            ttk.Label(item,text=label,wraplength=200,justify="center").pack()

    def _build_review(self):
        header=ttk.Frame(self.review_tab)
        header.pack(fill="x",pady=(0,9))
        ttk.Label(header,text="Candidate Review Workbench",style="Header.TLabel").pack(side="left")
        ttk.Button(header,text="Refresh candidates",command=self._refresh_review).pack(side="right")
        ttk.Button(header,text="Approve Greek alias...",command=self._approve_alias).pack(side="right",padx=(0,8))
        ttk.Label(self.review_tab,
                  text="Batch promotion installs MARKED [00:00.00] candidate LRCs only. "
                       "These remain UNVERIFIED. Existing .lrc and audio/ID3 files are never overwritten.",
                  style="Hint.TLabel",wraplength=1050).pack(anchor="w",pady=(0,10))
        self.review_counter=tk.StringVar(value="Total: 0  |  Primary: 0  |  Alternatives: 0  |  Eligible: 0")
        ttk.Label(self.review_tab,textvariable=self.review_counter,style="Header.TLabel").pack(anchor="w",pady=(0,2))
        self.review_alt_levels=tk.StringVar(value="Alternative levels: none")
        ttk.Label(self.review_tab,textvariable=self.review_alt_levels,style="Hint.TLabel").pack(anchor="w",pady=(0,8))
        controls=ttk.Frame(self.review_tab)
        controls.pack(fill="x",pady=(0,8))
        ttk.Label(controls,text="Status").pack(side="left",padx=(0,6))
        self.review_filter=tk.StringVar(value="All statuses")
        self.review_filter_picker=ttk.Combobox(controls,textvariable=self.review_filter,
                         values=[self._tr(k) for k in CANDIDATE_FILTERS],
                         state="readonly",width=26)
        self.review_filter_picker.pack(side="left",padx=(0,12))
        self.review_filter_picker.bind("<<ComboboxSelected>>",lambda e:self._render_review())
        ttk.Label(controls,text="Filter text").pack(side="left",padx=(0,6))
        self.review_query=tk.StringVar()
        self.review_search=ttk.Entry(controls,textvariable=self.review_query,width=38)
        self.review_search.pack(side="left",fill="x",expand=True)
        self.review_query.trace_add("write",lambda *_:self._render_review())
        self.review_visible_count=tk.StringVar(value="Visible: 0  |  Selected: 0")
        ttk.Label(controls,textvariable=self.review_visible_count,style="Hint.TLabel").pack(side="right",padx=(12,0))
        columns=("track","candidate","kind","status","number","folder")
        grid=ttk.Frame(self.review_tab)
        grid.pack(fill="both",expand=True)
        self.review_tree=ttk.Treeview(grid,columns=columns,show="headings",
                                      height=8,selectmode="extended")
        labels=(("track","Audio",230),("candidate","Candidate",265),
                ("kind","Kind",100),("status","Status",185),
                ("number","#",55),("folder","Folder",230))
        for key,caption,width in labels:
            self.review_tree.heading(key,text=caption,
                 command=lambda col=key:self._sort_review(col))
            self.review_tree.column(key,width=width,stretch=(key!="number"))
        scroll=ttk.Scrollbar(grid,orient="vertical",command=self.review_tree.yview)
        self.review_tree.configure(yscrollcommand=scroll.set)
        self.review_tree.pack(side="left",fill="both",expand=True)
        scroll.pack(side="right",fill="y")
        self.review_tree.bind("<<TreeviewSelect>>",self._candidate_selected)
        select_actions=ttk.Frame(self.review_tab)
        select_actions.pack(fill="x",pady=(8,7))
        ttk.Button(select_actions,text="Select visible",command=self._review_select_visible).pack(side="left",padx=(0,6))
        ttk.Button(select_actions,text="Select eligible primaries",command=self._review_select_eligible).pack(side="left",padx=(0,6))
        ttk.Button(select_actions,text="Select visible alternatives",
                   command=self._review_select_alternatives).pack(side="left",padx=(0,6))
        ttk.Button(select_actions,text="Clear selection",command=lambda:self.review_tree.selection_remove(*self.review_tree.selection())).pack(side="left",padx=(0,8))
        ttk.Label(self.review_tab,text="Preview of focused candidate (read-only)").pack(anchor="w")
        self.candidate_text=scrolledtext.ScrolledText(self.review_tab,height=5,wrap="word",font=("Consolas",10))
        self.candidate_text.pack(fill="both",expand=True,pady=(3,8))
        self.candidate_text.configure(state="disabled")
        buttons=ttk.Frame(self.review_tab)
        buttons.pack(fill="x",pady=(0,8))
        ttk.Button(buttons,text="Play audio externally",command=self._play_selected).pack(side="left")
        self.review_promote_button=ttk.Button(buttons,text="Promote selected primaries",
                  command=self._promote_selected,style="Primary.TButton")
        self.review_promote_button.pack(side="left",padx=8)
        self.review_promote_all_button=ttk.Button(buttons,text="Promote ALL eligible primaries",
                  command=self._promote_all_primary)
        self.review_promote_all_button.pack(side="left",padx=8)
        recycle_actions=ttk.Frame(self.review_tab)
        recycle_actions.pack(fill="x",pady=(0,5))
        self.review_recycle_button=ttk.Button(recycle_actions,
                  text="Delete selected alternatives (Recycle Bin)",
                  command=self._recycle_selected_alternatives,style="Danger.TButton")
        self.review_recycle_button.pack(side="left")
        ttk.Label(recycle_actions,text="Only numbered alternatives go to your system Recycle Bin.",
                  style="Hint.TLabel").pack(side="left",padx=12)
        self.review_stop_button=ttk.Button(buttons,text="Stop batch",state="disabled",
                  command=self._stop_review_batch)
        self.review_stop_button.pack(side="left",padx=8)
        self.review_progress=tk.IntVar(value=0)
        self.review_progress_bar=ttk.Progressbar(
            self.review_tab,orient="horizontal",mode="determinate",maximum=100,
            variable=self.review_progress)
        self.review_progress_bar.pack(fill="x",pady=(6,4))
        self.review_progress_label=tk.StringVar(value="0 / 0 (0%)")
        ttk.Label(self.review_tab,textvariable=self.review_progress_label,
                  style="Hint.TLabel").pack(anchor="w",pady=(0,3))
        self.review_batch_status=tk.StringVar(
            value="Ready. Deleted alternatives go to the Recycle Bin. Promotions remain UNVERIFIED.")
        ttk.Label(self.review_tab,textvariable=self.review_batch_status,
                  style="Hint.TLabel",wraplength=1040).pack(fill="x")

    def _pack_key(self,label):
        for key,value in PROVIDER_PACK_LABELS.items():
            if label in (value,self._tr(value),UI_EL.get(value,value)):
                return key
        # Locale may have changed since the combobox was populated. Never guess
        # the tier; reject instead of silently running a different source set.
        from v296_provider_tiers import pack_from_display
        return pack_from_display(label)

    def _base_pack_sources(self):
        tier=self._pack_key(self.provider_pack.get())
        if tier!=PACK_LEGACY:
            return PROVIDER_PACK_SOURCES[tier]
        base=PROVIDER_FULL if self.provider_mode.get()=="full" else PROVIDER_FAST
        if (self.provider_mode.get()=="full" and
                self.boolvars["experimental_simpmusic"].get()):
            base=base+("SimpMusic",)
        return base

    def _source_selection_updated(self,_event=None):
        selected=set(self._base_pack_sources())
        for source,widget in self.source_checkboxes.items():
            if source in selected:
                widget.grid()
            else:
                widget.grid_remove()
                self.source_enabled[source].set(True)
        self.exclusions_hint.set(
            "Unchecked sources are omitted only for this profile. All built-in tiers remain unchanged. "
            "Disabled providers never receive requests. CUSTOM order still lists the full tier.")

    def _pack_changed(self,_event=None):
        tier=self._pack_key(self.provider_pack.get())
        self.provider_pack_help.set(self._tr(PACK_DESCRIPTIONS[tier]))
        self._source_selection_updated()

    def _preset_selected(self,_event=None):
        self.preset_description.set(self._tr(PRESET_DESCRIPTIONS.get(self._preset_key(self.preset_name.get()),"")))

    def _apply_preset(self):
        name=self._preset_key(self.preset_name.get())
        if not self._g2g_available() and name in PRESET_TEMPLATES and PRESET_TEMPLATES[name]["local_ai"]:
            # A name retained in settings or selected programmatically must
            # still be usable without a modal error on standalone Windows.
            name="Greek FULL — Offline First"
            self.preset_name.set(self._tr(name))
        if name not in self._available_preset_names():return
        folder=self.folder.get()
        database=self.database.get()
        # Presets are editable templates, not silently persisted profiles.
        profile={**DEFAULT,**PRESET_TEMPLATES[name],
                 "folder":folder,"database":database}
        self._set_values(profile)
        self.name.set(name)
        self._preset_selected()

    def _refresh_g2g_capability(self):
        ready=self._g2g_available()
        if hasattr(self,"g2g_checkbox"):
            self.g2g_checkbox.configure(state="normal" if ready else "disabled")
        if not ready:self.boolvars["local_ai"].set(False)
        if hasattr(self,"preset_choice"):
            self.preset_choice.configure(values=[self._tr(k) for k in self._available_preset_names()])

    def _install_g2g(self):
        if self.review_bulk_running:
            self._dialog("showwarning","Candidate promotion running",
                         "Finish or stop candidate promotion before installing Greek AI.")
            return
        if self.benchmark_process is not None and self.benchmark_process.poll() is None:
            self._dialog("showwarning","Benchmark running",
                         "Stop the provider benchmark before installing Greek AI.")
            return
        if self.process is not None and self.process.poll() is None:
            self._dialog("showwarning","Search running","Finish the search before installing AI.")
            return
        if self.g2g_setup_process is not None and self.g2g_setup_process.poll() is None:
            return
        from g2g_auto import installed
        status=installed()
        message=(
            "Install and verify the optional AUEB Greek G2G model automatically?\n\n"
            "The full model is about 1.2 GB, with additional large Python/PyTorch downloads. "
            "The installation uses your own user folder and internet connection. "
            "If compatible Python is missing on Windows, the installer may run the official "
            "winget Python 3.11 installer. It will not edit any music files.\n\n"
            "The model runs on CPU to avoid requiring a large GPU. "
            "Accept only if you have enough disk space and trust the upstream packages."
        )
        if status:
            message=("Greek AI is already verified. Reinstall/verify the full model?\n\n"
                     "This can download additional software and may take considerable time.")
        if not self._dialog("askyesno","Install Greek AI",message):
            return
        if getattr(sys,"frozen",False):
            worker=program_folder()/"LRC_Bulk_Finder_Worker.exe"
            if not worker.is_file():
                self._dialog("showerror","Missing worker",
                             "Extract the complete Windows ZIP, including the worker.")
                return
            cmd=[str(worker),"--setup-g2g","--g2g-model","g2g","--allow-python-install"]
        else:
            cmd=[sys.executable,"-u",str(Path(__file__).with_name("g2g_auto.py")),
                 "--install","--model","g2g","--allow-python-install"]
        window=tk.Toplevel(self)
        window.title(self._tr("Greek AI installation"))
        window.geometry("700x395")
        window.transient(self)
        ttk.Label(window,text=self._tr("Installing Greek G2G AI in a separate user environment"),
                  wraplength=650).pack(anchor="w",padx=10,pady=10)
        progress=ttk.Progressbar(window,mode="indeterminate")
        progress.pack(fill="x",padx=10,pady=5)
        log=tk.Text(window,height=14,wrap="word")
        log.pack(fill="both",expand=True,padx=10,pady=10)
        log.configure(state="disabled")
        close=ttk.Button(window,text=self._tr("Close"),state="disabled",
                         command=window.destroy)
        close.pack(side="right",padx=12,pady=8)
        cancel=ttk.Button(window,text=self._tr("Cancel installation"),
                          command=self._cancel_g2g_setup)
        cancel.pack(side="right",padx=6,pady=8)
        window.protocol("WM_DELETE_WINDOW",lambda:None if self.g2g_setup_process is not None
                        else window.destroy())
        try:
            env=dict(os.environ)
            env["PYTHONIOENCODING"]="utf-8:backslashreplace"
            self.g2g_setup_process=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,cwd=str(program_folder()),
                text=True,encoding="utf-8",errors="replace",bufsize=1,env=env,
                creationflags=((getattr(subprocess,"CREATE_NO_WINDOW",0) |
                                getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0))
                               if os.name=="nt" else 0),
                start_new_session=(os.name!="nt"))
        except (OSError,ValueError) as error:
            window.destroy()
            self._dialog("showerror","Cannot start Greek AI installer",str(error))
            return
        self.g2g_setup_window=window
        self.g2g_setup_log=log
        self.g2g_setup_progress=progress
        self.g2g_setup_close=close
        self.g2g_setup_cancel=cancel
        self.g2g_status.set("Greek AI installation running...")
        progress.start(12)
        threading.Thread(target=self._read_g2g_install,daemon=True).start()

    def _cancel_g2g_setup(self):
        process=self.g2g_setup_process
        if process is None or process.poll() is not None:
            return
        if not self._dialog("askyesno","Cancel Greek AI installation",
                            "Stop this optional model setup now? Partial downloads may "
                            "remain in the local model cache and can be retried later. "
                            "Music files are never touched."):
            return
        self.g2g_setup_cancel.configure(state="disabled")
        self.g2g_status.set("Stopping optional AI installer...")
        from worker_stop import kill_search_process
        def stop_in_background():
            success,detail=kill_search_process(process)
            self.messages.put(("g2g_line","STOP: "+detail))
            if not success:
                self.messages.put(("g2g_line","Please inspect remaining installer child processes."))
        threading.Thread(target=stop_in_background,daemon=True).start()

    def _read_g2g_install(self):
        process=self.g2g_setup_process
        try:
            for line in process.stdout:
                self.messages.put(("g2g_line",line.rstrip("\r\n")))
            self.messages.put(("g2g_done",process.wait()))
        except (OSError,ValueError) as error:
            self.messages.put(("g2g_line","Installer output interrupted: "+str(error)))
            self.messages.put(("g2g_done",process.poll() or 2))

    def _launch_setup(self,script):
        if self.review_bulk_running:
            self._dialog("showwarning","Candidate promotion running",
                         "Finish or stop candidate promotion before starting a download.")
            return
        if self.benchmark_process is not None and self.benchmark_process.poll() is None:
            self._dialog("showwarning","Benchmark running",
                         "Stop the provider benchmark before starting another download.")
            return
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
            "provider_pack":self._pack_key(self.provider_pack.get()),
            "provider_exclusions":[p for p in self._base_pack_sources() if not self.source_enabled[p].get()],
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
        pack=profile.get("provider_pack",PACK_LEGACY)
        self.provider_pack.set(self._tr(PROVIDER_PACK_LABELS[pack]))
        self.provider_pack_help.set(self._tr(PACK_DESCRIPTIONS[pack]))
        for key,var in self.boolvars.items():
            value=profile.get(key,DEFAULT[key])
            if key=="local_ai" and not self._g2g_available():
                value=False  # Never enable AI until a real model is ready.
            var.set(value)
        self._source_selection_updated()
        excluded=set(profile.get("provider_exclusions",[]))
        for source in self._base_pack_sources():
            self.source_enabled[source].set(source not in excluded)
        if not self._g2g_available() and profile.get("local_ai",False):
            self.preset_description.set(
                "Greek AI setup has not finished. Dictionary matching is available; "
                "click Install / verify Greek G2G AI to enable this option.")

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
        if self.review_bulk_running:
            self._dialog("showwarning","Candidate promotion running",
                         "Finish or stop the candidate batch before starting a search.")
            return
        if self.g2g_setup_process is not None and self.g2g_setup_process.poll() is None:
            self._dialog("showwarning","Greek AI setup in progress",
                         "Finish optional Greek AI setup before starting a search.")
            return
        if self.process is not None and self.process.poll() is None:
            self._dialog("showwarning","Search running","Stop the current search before starting another.")
            return
        if self.benchmark_process is not None and self.benchmark_process.poll() is None:
            self._dialog("showwarning","Benchmark running","Stop or finish the provider benchmark before starting a music search.")
            return
        chosen=self.name.get().strip()
        if not self._g2g_available() and chosen=="Greek Local AI — FULL":
            # Keep the unavailable user's old named profile untouched; create
            # the supported equivalent as a separate normal profile.
            chosen="Greek FULL — Offline First"
            self.name.set(chosen)
            self.preset_name.set(self._tr(chosen))
            self._set_values({**DEFAULT,**PRESET_TEMPLATES[chosen],
                              "folder":self.folder.get(),"database":self.database.get()})
            self.preset_description.set(
                "Greek AI is not installed; running Greek FULL dictionary search.")
        if chosen in PRESET_TEMPLATES:
            # Saved profiles are editable, so a familiar preset *name* can
            # otherwise silently run a completely different action/scope.
            current=self._values()
            critical=("action","limit","greek","provider_mode","provider_pack")
            mismatches=[key for key in critical
                        if current[key]!=PRESET_TEMPLATES[chosen].get(key,DEFAULT[key])]
            if mismatches:
                details=", ".join(mismatches)
                if not self._dialog(
                    "askyesno","Preset settings differ",
                    "The displayed preset name does not match its current saved settings "
                    f"({details}).\n\nRestore the built-in {chosen} settings "
                    "before starting?\n\nChoose No to cancel; save a different "
                    "profile name to keep custom settings."):
                    return
                self._set_values({**DEFAULT,**PRESET_TEMPLATES[chosen],
                                  "folder":self.folder.get(),"database":self.database.get()})
        if not self._save():return
        profile=self.loaded_profiles[self.name.get()]
        if not Path(profile["folder"]).is_dir():
            self._dialog("showerror","Missing folder","Selected MP3 folder does not exist.")
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
            # Windows PyInstaller workers can default to cp1252. A filename
            # with a Unicode hyphen previously killed the whole worker. The
            # GUI's pipe is always decoded as UTF-8 below.
            environment["PYTHONIOENCODING"]="utf-8:backslashreplace"
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
        self.provider_health=ProviderHealth(tuple(dict.fromkeys(PROVIDER_FULL+("BetterQQ","SimpMusic"))))
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
                    self.phase.set(
                        "Stopped by user; completed checkpoints preserved"
                        if self.stop_requested else
                        "Search completed successfully"
                        if data==0 else
                        f"Worker stopped unexpectedly (exit {data}); see log. "
                        "Completed tracks are retained; unfinished songs can be retried.")
                    self.stop_button.configure(state="disabled")
                    self.process=None
                    self._cleanup_stop_marker()
                    if hasattr(self,'_manager_cleanup_selection'):self._manager_cleanup_selection()
                    self._refresh_review()
                elif kind=="benchmark_line":
                    if data.startswith("BENCHMARK REPORT: "):
                        report_path=data.split("BENCHMARK REPORT: ",1)[1]
                        try:self._load_benchmark_report(report_path)
                        except (OSError,ValueError,KeyError) as error:
                            self.benchmark_status.set("Report could not be opened: "+str(error))
                    elif data.startswith("BENCHMARK PROGRESS: "):
                        self.benchmark_status.set(data)
                    elif data.startswith("BENCHMARK ERROR: "):
                        self.benchmark_status.set(data)
                elif kind=="benchmark_done":
                    self.benchmark_process=None
                    self.benchmark_start_button.configure(state="normal")
                    self.benchmark_stop_button.configure(state="disabled")
                    if data!=0:
                        self.benchmark_status.set("Benchmark stopped (exit "+str(data)+
                                                  "). See details in worker log/report.")
                    elif not self.benchmark_status.get().startswith("Benchmark results:"):
                        self.benchmark_status.set("Benchmark completed; no aggregate report was received.")
                elif kind=="benchmark_stop":
                    success,detail=data
                    if not success:self.benchmark_status.set("Benchmark stop not verified: "+detail)
                elif kind=="review_batch_progress":
                    done,total,name,status=data
                    percent=round(done*100/total) if total else 0
                    self.review_progress.set(percent)
                    self.review_progress_label.set(f"{done} / {total} ({percent}%)")
                    prefix="Recycling" if self.review_bulk_kind=="recycle" else "Promoting"
                    suffix="" if self.review_bulk_kind=="recycle" else " (UNVERIFIED)"
                    self.review_batch_status.set(
                        f"{prefix} {done}/{total}: {status} — {name}{suffix}")
                elif kind=="review_batch_done":
                    counts,done,total=data
                    operation=self.review_bulk_kind
                    self.review_bulk_running=False
                    self.review_bulk_kind=None
                    self.review_promote_button.configure(state="normal")
                    self.review_promote_all_button.configure(state="normal")
                    self.review_recycle_button.configure(state="normal")
                    self.review_stop_button.configure(state="disabled")
                    percent=round(done*100/total) if total else 0
                    self.review_progress.set(percent)
                    self.review_progress_label.set(f"{done} / {total} ({percent}%)")
                    self._refresh_review()
                    outcome=", ".join(f"{key}: {n}" for key,n in sorted(counts.items()))
                    warning=(". Files were moved to the system Recycle Bin / Trash."
                             if operation=="recycle" else
                             ". Any installed LRC remains marked UNVERIFIED.")
                    self.review_batch_status.set(
                        f"Batch complete: {done}/{total} processed. {outcome}{warning}")
                elif kind=="review_batch_error":
                    self._dialog("showerror","Candidate batch error",data)
                elif kind=="g2g_line":
                    if self.g2g_setup_window is not None and self.g2g_setup_window.winfo_exists():
                        self.g2g_setup_log.configure(state="normal")
                        self.g2g_setup_log.insert("end",data+"\n")
                        self.g2g_setup_log.see("end")
                        self.g2g_setup_log.configure(state="disabled")
                elif kind=="g2g_done":
                    self.g2g_setup_process=None
                    if self.g2g_setup_window is not None and self.g2g_setup_window.winfo_exists():
                        self.g2g_setup_progress.stop()
                        self.g2g_setup_close.configure(state="normal")
                        self.g2g_setup_cancel.configure(state="disabled")
                    ready=self._g2g_available()
                    self._refresh_g2g_capability()
                    self.g2g_status.set("Greek AI ready — checkbox enabled" if ready else
                                        "Greek AI setup incomplete — see installation log")
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
        if line.startswith("PREFLIGHT DISCOVERY:"):
            self.phase.set("Preflight: scanning filenames and existing lyrics")
            self.progress_text.set(line)
        elif line.startswith("PREFLIGHT METADATA:"):
            self.phase.set("Preflight: reading selected music metadata")
            self.progress_text.set(line)
        elif line.startswith("PREFLIGHT COMPLETE:"):
            self.phase.set("Preflight complete — preparing search")
            self.progress_text.set(line)
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

    def _review_filter_key(self):
        value=self.review_filter.get()
        from ui_translations import UI_EL
        return next((x for x in CANDIDATE_FILTERS
                     if value in (x,self._tr(x),UI_EL.get(x,x))),"All statuses")

    def _refresh_review(self):
        if self.review_bulk_running:
            return
        folder=self.folder.get()
        self.review_all_rows=[]
        self.review_rows={}
        if folder and Path(folder).is_dir():
            try:self.review_all_rows=list_review_candidates(folder,self.boolvars["recursive"].get())
            except (OSError,ValueError) as error:
                self._dialog("showerror","Candidate scan",str(error))
        self._render_review()

    def _render_review(self):
        if not hasattr(self,"review_tree"):return
        selected_paths={str(self.review_rows[k]["path"]) for k in self.review_tree.selection()
                        if k in self.review_rows}
        focus=self.review_tree.focus()
        focus_path=str(self.review_rows[focus]["path"]) if focus in self.review_rows else None
        self.review_rows={}
        self.review_tree.delete(*self.review_tree.get_children())
        counts=candidate_summary(self.review_all_rows)
        self.review_counter.set(
            f"Total: {counts['total']}   |   Primary: {counts['primary']}   |   "
            f"Alternatives: {counts['alternative']}   |   Eligible: {counts['eligible']}   |   "
            f"Blocked primary: {counts['blocked_primary']}")
        alternative_levels=alternative_breakdown(self.review_all_rows)
        breakdown=[f"#{index}: {count}" for index,count in alternative_levels.items()]
        self.review_alt_levels.set("Alternative levels: "+(
             "  |  ".join(breakdown[:8])+
             (f"  |  +{len(breakdown)-8} further levels" if len(breakdown)>8 else "")
             if breakdown else "none"))
        shown=sort_candidates(filter_candidates(self.review_all_rows,self._review_filter_key(),
                                               self.review_query.get()),
                             self.review_sort_column,self.review_sort_descending)
        restore=[]
        for index,item in enumerate(shown):
            key=str(index)
            self.review_rows[key]=item
            kind="Primary" if item["index"]==1 else "Alternative"
            status=candidate_status(item)
            self.review_tree.insert("","end",iid=key,
                     values=(item["mp3"].name,item["path"].name,self._tr(kind),
                             self._tr(status),item["index"],str(item["path"].parent)))
            if str(item["path"]) in selected_paths:
                restore.append(key)
            if str(item["path"])==focus_path:
                self.review_tree.focus(key)
        if restore:self.review_tree.selection_set(restore)
        self.review_visible_count.set(
            f"Visible: {len(shown)}  |  Selected: {len(self.review_tree.selection())}")
        self._candidate_selected()

    def _sort_review(self,column):
        if column==self.review_sort_column:
            self.review_sort_descending=not self.review_sort_descending
        else:
            self.review_sort_column=column
            self.review_sort_descending=False
        self._render_review()

    def _review_select_visible(self):
        if self.review_bulk_running:return
        self.review_tree.selection_set(self.review_tree.get_children())

    def _review_select_eligible(self):
        if self.review_bulk_running:return
        ids=[key for key,item in self.review_rows.items() if candidate_can_promote(item)]
        self.review_tree.selection_set(ids)

    def _review_select_alternatives(self):
        if self.review_bulk_running:return
        ids=[key for key,item in self.review_rows.items() if item["index"]>=2]
        self.review_tree.selection_set(ids)

    def _selection(self):
        ids=self.review_tree.selection()
        focus=self.review_tree.focus()
        return self.review_rows.get(focus) if focus in ids and focus in self.review_rows else (
               self.review_rows.get(ids[0]) if ids else None)

    def _candidate_selected(self,_event=None):
        count=len(self.review_tree.selection())
        self.review_visible_count.set(f"Visible: {len(self.review_rows)}  |  Selected: {count}")
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
        self._promote_review_items(
            [self.review_rows[key] for key in self.review_tree.selection()
             if key in self.review_rows],"selected rows")

    def _promote_all_primary(self):
        # User explicitly requested ALL primaries, not just the filtered rows.
        self._promote_review_items(self.review_all_rows,"ALL eligible primaries")

    def _promote_review_items(self,items,scope):
        if self.review_bulk_running:return
        if self.process is not None and self.process.poll() is None:
            self._dialog("showwarning","Search running",
                         "Finish the search before promoting candidates.");return
        if self.benchmark_process is not None and self.benchmark_process.poll() is None:
            self._dialog("showwarning","Benchmark running",
                         "Finish the provider benchmark before promoting candidates.");return
        if self.g2g_setup_process is not None and self.g2g_setup_process.poll() is None:
            self._dialog("showwarning","Greek AI installation running",
                         "Finish the model installation before promoting candidates.");return
        eligible=eligible_primary_paths(items)
        blocked=sum(row["index"]==1 and not candidate_can_promote(row) for row in items)
        ignored_alternatives=sum(row["index"]>1 for row in items)
        if not eligible:
            self._dialog("showinfo","No eligible primaries",
                         "No selected primary candidates are eligible. "
                         "Numbered alternatives, missing audio and existing LRC files cannot be promoted.");return
        total=len(eligible)
        preview="\n".join(" • "+p.name for p in eligible[:7])
        if total>7:preview+=f"\n ... and {total-7} more"
        extra=("This includes ALL eligible primaries in the chosen folder, "
               "even those hidden by current filters or not selected.\n\n"
               if scope=="ALL eligible primaries" else "")
        message=(f"Promote {total} {scope} to MARKED .lrc files?\n\n"
                 +extra+
                 "This is a batch WRITE operation, NOT lyrics verification.\n"
                 "Each new .lrc receives [00:00.00] candidate and stays UNVERIFIED.\n"
                 "Existing .lrc, audio and ID3 are never overwritten.\n"
                 "Numbered alternatives are moved forward, never promoted directly.\n\n"
                 f"Blocked primaries: {blocked}; numbered alternatives excluded: {ignored_alternatives}\n\n"+preview)
        if not self._dialog("askyesno","Confirm batch of UNVERIFIED lyrics",message):
            return
        self._begin_review_batch("promote",total)
        self.review_batch_status.set(f"Promoting 0/{total} primaries... All results remain UNVERIFIED.")
        folder=self.folder.get()
        recursive=self.boolvars["recursive"].get()
        def on_progress(done,total,path,status,detail):
            self.messages.put(("review_batch_progress",(done,total,path.name,status)))
        def worker():
            try:
                results,details=batch_promote(
                    eligible,folder,recursive,approved=True,
                    report=on_progress,stop=lambda:self.review_bulk_stop)
                self.messages.put(("review_batch_done",(results,len(details),total)))
            except (OSError,ValueError,PermissionError) as error:
                self.messages.put(("review_batch_done",({"ERROR":1},0,total)))
                self.messages.put(("review_batch_error",str(error)))
        threading.Thread(target=worker,daemon=True).start()

    def _begin_review_batch(self,kind,total):
        self.review_bulk_running=True
        self.review_bulk_stop=False
        self.review_bulk_kind=kind
        self.review_progress.set(0)
        self.review_progress_label.set(f"0 / {total} (0%)")
        self.review_promote_button.configure(state="disabled")
        self.review_promote_all_button.configure(state="disabled")
        self.review_recycle_button.configure(state="disabled")
        self.review_stop_button.configure(state="normal")

    def _recycle_selected_alternatives(self):
        if self.review_bulk_running:return
        if self.process is not None and self.process.poll() is None:
            self._dialog("showwarning","Search running",
                         "Finish the music search before deleting alternatives.");return
        if self.benchmark_process is not None and self.benchmark_process.poll() is None:
            self._dialog("showwarning","Benchmark running",
                         "Finish the benchmark before deleting alternatives.");return
        if self.g2g_setup_process is not None and self.g2g_setup_process.poll() is None:
            self._dialog("showwarning","Greek AI installation running",
                         "Finish installation before deleting alternatives.");return
        rows=[self.review_rows[key] for key in self.review_tree.selection()
              if key in self.review_rows]
        alternatives=selected_alternative_paths(rows)
        excluded=len(rows)-len(alternatives)
        if not alternatives:
            self._dialog("showinfo","No alternatives selected",
                         "Select one or more numbered alternatives (#2, #3, #4, etc.). "
                         "Primary candidates and ordinary LRCs cannot be deleted here.")
            return
        sample="\n".join(" • "+path.name for path in alternatives[:7])
        if len(alternatives)>7:
            sample+=f"\n ... and {len(alternatives)-7} more"
        prompt=(f"Move {len(alternatives)} selected numbered candidates to the "
                "system Recycle Bin / Trash?\n\n"
                "Only the selected .candidate.2.lrc, .candidate.3.lrc, etc. "
                "sidecar files will be affected. Primary candidates, normal .lrc, "
                "audio and ID3 are preserved.\n"
                f"Other selected rows skipped: {excluded}.\n\n"
                "This can be reversed using your system Recycle Bin / Trash. "
                "No permanent-delete fallback is used.\n\n"+sample)
        if not self._dialog("askyesno","Confirm deleting selected alternatives",prompt):
            return
        self._begin_review_batch("recycle",len(alternatives))
        self.review_batch_status.set(
            f"Moving 0/{len(alternatives)} numbered alternatives to Recycle Bin...")
        folder=self.folder.get()
        recursive=self.boolvars["recursive"].get()
        def on_progress(done,total,path,status,detail):
            self.messages.put(("review_batch_progress",(done,total,path.name,status)))
        def worker():
            try:
                result,detail=bulk_recycle_alternatives(
                    alternatives,folder,recursive,approved=True,
                    report=on_progress,stop=lambda:self.review_bulk_stop)
                self.messages.put(("review_batch_done",(result,len(detail),len(alternatives))))
            except (OSError,RuntimeError,ValueError,ImportError,PermissionError) as error:
                self.messages.put(("review_batch_done",({"ERROR":1},0,len(alternatives))))
                self.messages.put(("review_batch_error",str(error)))
        threading.Thread(target=worker,daemon=True).start()

    def _stop_review_batch(self):
        if self.review_bulk_running:
            self.review_bulk_stop=True
            self.review_stop_button.configure(state="disabled")
            self.review_batch_status.set("Stopping after the current candidate file is processed...")

    def _build_sync_lab(self):
        area=self._studio_build_tabs()
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
        if self.review_bulk_running:
            self._dialog("showwarning","Candidate promotion running",
                         "Stop the candidate batch before closing the Control Center.")
            return
        if self.g2g_setup_process is not None and self.g2g_setup_process.poll() is None:
            self._dialog("showwarning","Greek AI installation",
                         "Finish or stop the installation before closing the Control Center.")
            return
        if self.benchmark_process is not None and self.benchmark_process.poll() is None:
            self._dialog("showwarning","Provider benchmark running",
                         "Stop the benchmark before closing the Control Center.")
            return
        if self.process is not None and self.process.poll() is None:
            self._dialog("showwarning","Search running",
                "Stop the current search before closing the Control Center.")
            return
        if not self._studio_can_close():return
        if hasattr(self,'_manager_cleanup_selection'):self._manager_cleanup_selection()
        self.destroy()


def main():
    app=ControlCenter()
    app.mainloop()


if __name__=="__main__":
    main()
