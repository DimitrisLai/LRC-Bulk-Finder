"""LRC Bulk Finder v2.3 Control Center (standard-library Tkinter).

Search runs execute in a separate Python process using the unchanged strict
matching engine; GUI never writes MP3/audio/ID3 or unmarked 'verified' lyrics.
"""
from __future__ import annotations
import os
import queue
import re
import signal
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog,messagebox,scrolledtext,ttk

from search_profiles import (DEFAULT,PROVIDER_FAST,PROVIDER_FULL,load_profiles,
                             save_profiles,validate_profile)
from review_candidates_gui import (list_review_candidates,preview_candidate,
                                   explicitly_promote)
from runtime_paths import program_folder


class ControlCenter(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LRC Bulk Finder v2.3 — Control Center")
        self.geometry("1050x780")
        self.minsize(870,670)
        self.process=None
        self.reader=None
        self.messages=queue.Queue()
        self.review_rows={}
        self.loaded_profiles={}
        self._build()
        self._refresh_profiles()
        self.after(110,self._poll)
        self.protocol("WM_DELETE_WINDOW",self._close)

    def _build(self):
        style=ttk.Style(self)
        if "clam" in style.theme_names():style.theme_use("clam")
        style.configure("Header.TLabel",font=("Segoe UI",16,"bold"))
        style.configure("Hint.TLabel",font=("Segoe UI",9))
        style.configure("TButton",padding=5)
        header=ttk.Frame(self,padding=(18,16,18,8))
        header.pack(fill="x")
        ttk.Label(header,text="LRC Bulk Finder",style="Header.TLabel").pack(anchor="w")
        ttk.Label(header,text="Search profiles · honest per-round ETA · safe review of unverified lyrics",style="Hint.TLabel").pack(anchor="w")
        self.notebook=ttk.Notebook(self)
        self.notebook.pack(fill="both",expand=True,padx=15,pady=(0,15))
        self.search_tab=ttk.Frame(self.notebook,padding=12)
        self.run_tab=ttk.Frame(self.notebook,padding=12)
        self.review_tab=ttk.Frame(self.notebook,padding=12)
        self.notebook.add(self.search_tab,text="  Saved searches  ")
        self.notebook.add(self.run_tab,text="  Live progress  ")
        self.notebook.add(self.review_tab,text="  Candidate review  ")
        self._build_profiles()
        self._build_progress()
        self._build_review()

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
        for field in ("greek","local_ai","musicbrainz","recovery_wait","recursive","history","exact_fallback","auto_search"):
            self.boolvars[field]=tk.BooleanVar(value=DEFAULT[field])
        row=0
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
        ]
        for i,(key,label) in enumerate(toggles):
            ttk.Checkbutton(frame,text=label,variable=self.boolvars[key]).grid(
                row=i//2,column=i%2,sticky="w",padx=12,pady=4)
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
        controls=ttk.Frame(self.run_tab)
        controls.pack(fill="x")
        self.stop_button=ttk.Button(controls,text="Stop / save finished checkpoints",state="disabled",command=self._stop)
        self.stop_button.pack(side="left")
        ttk.Button(controls,text="Clear displayed log",command=self._clear_log).pack(side="left",padx=10)
        self.log=scrolledtext.ScrolledText(self.run_tab,wrap="word",height=24,font=("Consolas",9))
        self.log.pack(fill="both",expand=True,pady=(12,0))
        self.log.configure(state="disabled")

    def _build_review(self):
        top=ttk.Frame(self.review_tab)
        top.pack(fill="x")
        ttk.Label(top,text="Unverified candidate lyrics",style="Header.TLabel").pack(side="left")
        ttk.Button(top,text="Refresh candidates",command=self._refresh_review).pack(side="right")
        ttk.Label(self.review_tab,text="Review before installing. Only explicitly selected primary candidates can become MARKED [00:00.00] candidate LRCs. This NEVER certifies lyrics as verified.",wraplength=850).pack(anchor="w",pady=10)
        columns=("track","candidate","status")
        self.review_tree=ttk.Treeview(self.review_tab,columns=columns,show="headings",height=12)
        for key,caption,width in (("track","MP3",350),("candidate","Candidate",330),("status","Status",200)):
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
        ttk.Button(buttons,text="Play MP3 externally",command=self._play_selected).pack(side="left")
        ttk.Button(buttons,text="Promote selected to MARKED LRC",command=self._promote_selected).pack(side="left",padx=10)
        ttk.Label(buttons,text="Numbered alternatives are read-only until they become primary.").pack(side="right")

    def _browse_music(self):
        selected=filedialog.askdirectory(title="Select MP3 folder",initialdir=self.folder.get() or str(Path.home()))
        if selected:self.folder.set(selected)

    def _browse_database(self):
        selected=filedialog.askopenfilename(title="Existing LRCLIB SQLite database",
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
            messagebox.showerror("Profiles",str(error))
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
            messagebox.showerror("Profile","Choose a profile name")
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
            messagebox.showerror("Save profile",str(error))
            return False

    def _delete(self):
        name=self.name.get().strip()
        if name not in self.loaded_profiles:return
        if not messagebox.askyesno("Delete profile","Delete saved settings for "+name+"? No music files are affected."):
            return
        try:
            profiles=load_profiles()
            del profiles[name]
            save_profiles(profiles)
            self.name.set("")
            self._refresh_profiles()
        except (OSError,ValueError) as error:
            messagebox.showerror("Delete profile",str(error))

    def _run_profile(self):
        if self.process is not None and self.process.poll() is None:
            messagebox.showwarning("Search running","Stop the current search before starting another.")
            return
        if not self._save():return
        profile=self.loaded_profiles[self.name.get()]
        if not Path(profile["folder"]).is_dir():
            messagebox.showerror("Missing folder","Selected MP3 folder does not exist.")
            return
        if getattr(sys,"frozen",False) and profile["local_ai"]:
            messagebox.showerror("Optional local AI requires Python build",
                "The standalone EXE does not contain the external G2G transformer "
                "model or its Python dependencies. For local AI, run "
                "OPEN_CONTROL_CENTER.cmd from the complete Python Windows ZIP.")
            return
        if profile["action"] in ("4","5") and not profile["database"].strip():
            # If already configured by the standard application, this is OK.
            configured=program_folder()/"LRCLIB_LOCAL_DB.txt"
            if not configured.is_file():
                messagebox.showerror("Missing database","Option 4/5 requires your existing LRCLIB SQLite database. Choose it above.")
                return
        if getattr(sys,"frozen",False):
            worker=program_folder()/"LRC_Bulk_Finder_Worker.exe"
            if not worker.is_file():
                messagebox.showerror("Missing worker",
                    "The standalone GUI requires LRC_Bulk_Finder_Worker.exe "
                    "in the same folder. Extract the complete EXE ZIP.")
                return
            cmd=[str(worker),"--profile",self.name.get()]
        else:
            cmd=[sys.executable,"-u",str(Path(__file__).with_name("run_saved_profile.py")),
                 "--profile",self.name.get()]
        try:
            creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name=="nt" else 0)
            self.process=subprocess.Popen(cmd,stdout=subprocess.PIPE,
               stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,
               encoding="utf-8",errors="replace",bufsize=1,
               cwd=str(Path(__file__).resolve().parent),creationflags=creationflags)
        except OSError as error:
            messagebox.showerror("Cannot start search",str(error))
            return
        self._clear_log()
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
                    self.phase.set(f"Search finished. Exit code: {data}")
                    self.stop_button.configure(state="disabled")
                    self.process=None
                    self._refresh_review()
                elif kind=="error":
                    self._line("Control Center reader error: "+data)
        except queue.Empty:pass
        self.after(110,self._poll)

    def _line(self,line):
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
        if process is None or process.poll() is not None:return
        if not messagebox.askyesno("Stop current search",
            "Stop the search? Completed tracks have durable checkpoints.\n"
            "The current in-flight request may be repeated when resuming."):
            return
        try:
            if os.name=="nt":
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                process.send_signal(signal.SIGINT)
            self.phase.set("Stopping; requesting safe checkpoint/report finalization...")
        except (OSError,ValueError):
            self.phase.set("Stop request could not be delivered; see log")

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
                status=("Missing MP3" if not item["has_mp3"] else
                        "Already has LRC" if item["has_lrc"] else
                        "Primary — review" if item["index"]==1 else "Alternative — read-only")
                key=str(i)
                self.review_rows[key]=item
                self.review_tree.insert("","end",iid=key,
                    values=(item["mp3"].name,path.name,status))
        except (OSError,ValueError) as error:
            messagebox.showerror("Candidate scan",str(error))

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
            messagebox.showerror("Open audio",str(error))

    def _promote_selected(self):
        if self.process is not None and self.process.poll() is None:
            messagebox.showwarning("Search running","Finish the search before reviewing files.")
            return
        item=self._selection()
        if not item:return
        if item["index"]!=1 or not item["has_mp3"] or item["has_lrc"]:
            messagebox.showinfo("Not eligible","Only a primary candidate with MP3 and no existing LRC can be promoted.")
            return
        if not messagebox.askyesno("Install UNVERIFIED candidate?",
            f"Install {item['path'].name} as a MARKED .lrc?\n\n"
            "It will contain [00:00.00] candidate and remain UNVERIFIED.\n"
            "Original MP3/ID3 will NOT change. Numbered alternatives shift forward."):
            return
        try:
            status,detail=explicitly_promote(item["path"],approved=True)
            messagebox.showinfo("Candidate result",status+": "+detail)
        except (ValueError,PermissionError,OSError) as error:
            messagebox.showerror("Candidate result",str(error))
        self._refresh_review()

    def _close(self):
        if self.process is not None and self.process.poll() is None:
            messagebox.showwarning("Search running",
                "Stop the current search before closing the Control Center.")
            return
        self.destroy()


def main():
    app=ControlCenter()
    app.mainloop()


if __name__=="__main__":
    main()
