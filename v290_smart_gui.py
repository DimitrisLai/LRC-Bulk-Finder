"""v2.9 Smart Library: paginated offline QC, cancellation and review queue in Sync Lab.

The UI has no provider calls and never changes user audio or lyric sidecars.
Worker performs filesystem and SQLite operations; Tk updates only on UI thread.
"""
from __future__ import annotations
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk
from v280_karaoke_gui import V280Mixin
from v290_smart_library import (scan_index, ScanCancelled, read_page,
    counts, export_issues, set_review_state, history, ALLOWED_STATUSES,
    PAGE_SIZE, canonical_root)

class V290Mixin(V280Mixin):
    def _studio_build_tabs(self):
        result=super()._studio_build_tabs()
        self.smart_library_tab=ttk.Frame(self.studio_tabs,padding=8)
        self.studio_tabs.add(self.smart_library_tab,text="Smart Library")
        self._v290_progress=queue.Queue()
        self._v290_stop=threading.Event()
        self._v290_running=False
        self._v290_token=0
        self._v290_page=0
        self._v290_records={}
        self._v290_root=""
        self._v290_filter=tk.StringVar(value="Issues only")
        self._v290_query=tk.StringVar()
        self._v290_deep=tk.BooleanVar(value=False)
        self._v290_status=tk.StringVar(value="Choose a folder and run a safe, read-only music inventory.")
        self._v290_summary=tk.StringVar(value="No scan yet")
        self._v290_build()
        self.after(150,self._v290_poll)
        return result

    def _v290_build(self):
        parent=self.smart_library_tab
        ttk.Label(parent,text="Smart Library — indexed lyrics quality control",style="Header.TLabel").pack(anchor="w")
        ttk.Label(parent,text="Find missing, questionable or mismatched LRC files. Builds a private SQLite index; your audio, tags and original lyrics stay untouched.",
                  wraplength=945).pack(anchor="w",pady=(3,9))
        first=ttk.Frame(parent);first.pack(fill="x",pady=3)
        ttk.Label(first,text="Folder:").pack(side="left")
        ttk.Entry(first,textvariable=self.folder).pack(side="left",fill="x",expand=True,padx=4)
        ttk.Button(first,text="Browse...",command=self._browse_music).pack(side="left",padx=3)
        self._v290_start_button=ttk.Button(first,text="Scan / incremental refresh",command=self._v290_scan)
        self._v290_start_button.pack(side="left",padx=3)
        ttk.Button(first,text="Cancel scan",command=self._v290_cancel).pack(side="left",padx=3)
        row=ttk.Frame(parent);row.pack(fill="x",pady=4)
        ttk.Checkbutton(row,text="Deep duration checks (slower)",variable=self._v290_deep).pack(side="left")
        ttk.Label(row,text="Cached unchanged LRCs are reused; changed songs are re-audited.").pack(side="left",padx=14)
        ttk.Label(parent,textvariable=self._v290_status,wraplength=960).pack(anchor="w",pady=(4,4))
        ttk.Label(parent,textvariable=self._v290_summary).pack(anchor="w",pady=(0,6))
        filter_row=ttk.Frame(parent);filter_row.pack(fill="x",pady=2)
        ttk.Label(filter_row,text="Show:").pack(side="left",padx=2)
        picker=ttk.Combobox(filter_row,state="readonly",values=ALLOWED_STATUSES,
                            textvariable=self._v290_filter,width=19)
        picker.pack(side="left",padx=4)
        picker.bind("<<ComboboxSelected>>",lambda e:self._v290_reset_page())
        ttk.Label(filter_row,text="Search filename/path:").pack(side="left",padx=8)
        ttk.Entry(filter_row,textvariable=self._v290_query).pack(side="left",fill="x",expand=True,padx=3)
        ttk.Button(filter_row,text="Find",command=self._v290_reset_page).pack(side="left",padx=3)
        ttk.Button(filter_row,text="Export filtered CSV...",command=self._v290_export).pack(side="left",padx=3)
        holder=ttk.Frame(parent);holder.pack(fill="both",expand=True,pady=3)
        columns=("file","status","warnings","review")
        self._v290_tree=ttk.Treeview(holder,columns=columns,show="headings",height=13,selectmode="browse")
        for key,label,width in (("file","Audio filename",310),("status","LRC status",125),
                                 ("warnings","Quality warnings (review)",440),("review","Queue",95)):
            self._v290_tree.heading(key,text=label)
            self._v290_tree.column(key,width=width,stretch=True)
        bar=ttk.Scrollbar(holder,orient="vertical",command=self._v290_tree.yview)
        self._v290_tree.configure(yscrollcommand=bar.set)
        self._v290_tree.pack(side="left",fill="both",expand=True)
        bar.pack(side="right",fill="y")
        self._v290_tree.bind("<Double-1>",lambda e:self._v290_open())
        buttons=ttk.Frame(parent);buttons.pack(fill="x",pady=5)
        for label,fn in (("Open in Lyrics Studio",self._v290_open),
                         ("Bookmark",lambda:self._v290_mark("bookmarked")),
                         ("Mark reviewed",lambda:self._v290_mark("reviewed")),
                         ("Clear mark",lambda:self._v290_mark("clear")),
                         ("Previous page",lambda:self._v290_step(-1)),
                         ("Next page",lambda:self._v290_step(1)),
                         ("Scan history",self._v290_history)):
            ttk.Button(buttons,text=label,command=fn).pack(side="left",padx=2)
        ttk.Label(parent,text="200 records per page. Issues are warnings, not proof that the lyrics are wrong. No automatic repair, overwrite or provider requests.",
                  wraplength=940).pack(anchor="w",pady=3)

    def _v290_scan(self):
        if self._v290_running:return
        try:root=canonical_root(self.folder.get().strip())
        except (OSError,ValueError) as ex:
            self._dialog("showerror","Smart Library",str(ex));return
        self._v290_token+=1
        token=self._v290_token
        self._v290_root=root
        self._v290_running=True
        self._v290_stop=threading.Event()
        self._v290_start_button.configure(state="disabled")
        self._v290_status.set("Scanning local music and LRCs safely. Cancel rolls back the unfinished scan...")
        deep=self._v290_deep.get()
        recursive=self.boolvars["recursive"].get()
        def notify(total,audited,cached):
            self._v290_progress.put((token,"progress",(total,audited,cached)))
        def worker():
            try:
                result=scan_index(root,recursive=recursive,deep=deep,
                                  cancel=self._v290_stop,progress=notify)
                self._v290_progress.put((token,"result",result))
            except (OSError,ValueError,RuntimeError) as ex:
                self._v290_progress.put((token,"error",ex))
        threading.Thread(target=worker,daemon=True,name="LRC-SmartLibrary-QC").start()

    def _v290_cancel(self):
        if self._v290_running:
            self._v290_stop.set()
            self._v290_status.set("Cancellation requested; rolling back unfinished index changes...")
        else:
            self._v290_status.set("No Smart Library scan is currently running.")

    def _v290_poll(self):
        try:
            while True:
                token,kind,data=self._v290_progress.get_nowait()
                if token!=self._v290_token:continue
                if kind=="progress":
                    n,a,c=data
                    self._v290_status.set(f"Scanning: {n:,} tracks; audited {a:,}, unchanged cached {c:,}")
                elif kind=="result":
                    self._v290_running=False
                    self._v290_start_button.configure(state="normal")
                    self._v290_status.set(f"Safe scan completed in {data.elapsed:.1f}s: {data.total:,} tracks, {data.audited:,} checked, {data.cached:,} reused.")
                    self._v290_reset_page()
                else:
                    self._v290_running=False
                    self._v290_start_button.configure(state="normal")
                    self._v290_status.set("Smart Library: "+str(data))
        except queue.Empty:pass
        try:
            if self.winfo_exists():
                self.after(150,self._v290_poll)
        except tk.TclError:pass

    def _v290_reset_page(self):
        self._v290_page=0
        self._v290_refresh()

    def _v290_refresh(self):
        root=self._v290_root
        if not root:
            self._v290_status.set("Scan a music folder to view indexed files.")
            return
        try:
            total,rows=read_page(root,status=self._v290_filter.get(),
                                 query=self._v290_query.get().strip(),
                                 page=self._v290_page)
            overview=counts(root)
        except (OSError,ValueError) as ex:
            self._v290_status.set("Unable to load index: "+str(ex))
            return
        self._v290_records={}
        self._v290_tree.delete(*self._v290_tree.get_children())
        for index,row in enumerate(rows):
            iid=str(index)
            self._v290_records[iid]=row
            warnings=", ".join(row["flags"]) or "No issues detected"
            self._v290_tree.insert("","end",iid=iid,
                values=(row["name"],row["status"],warnings,row.get("review","")))
        last=max(1,(total+PAGE_SIZE-1)//PAGE_SIZE)
        self._v290_summary.set(f"Indexed: {overview['total']:,} | QC issues: {overview['issues']:,} | Missing: {overview['missing']:,} | Filtered: {total:,} | Page {self._v290_page+1}/{last}")

    def _v290_row(self):
        selection=self._v290_tree.selection()
        return self._v290_records.get(selection[0]) if selection else None

    def _v290_open(self):
        row=self._v290_row()
        if not row:
            self._dialog("showinfo","Smart Library","Select a track in the review queue.")
            return
        audio=row["path"]
        lrc=row["lrc"]
        if lrc and Path(lrc).is_file():
            self._v270_open(audio,lrc)
        else:
            self._v270_open(audio)

    def _v290_mark(self,decision):
        row=self._v290_row()
        if not row:return
        try:
            set_review_state(self._v290_root,row["path"],decision)
            self._v290_refresh()
        except (OSError,ValueError) as ex:
            self._dialog("showerror","Smart Library",str(ex))

    def _v290_step(self,direction):
        if not self._v290_root:return
        previous=self._v290_page
        self._v290_page=max(0,self._v290_page+direction)
        self._v290_refresh()
        if not self._v290_records and direction>0:
            self._v290_page=previous
            self._v290_refresh()

    def _v290_export(self):
        root=self._v290_root
        if not root:
            self._dialog("showinfo","Smart Library","Scan a folder first.")
            return
        chosen=self._file_dialog("asksaveasfilename",title="Export Smart Library QC CSV",
                defaultextension=".csv",filetypes=[("CSV reports","*.csv")])
        if not chosen:return
        if not self._dialog("askyesno","Export quality report?",
                            "Create a new CSV of the currently filtered rows? Existing reports will never be replaced."):
            return
        try:
            n=export_issues(root,chosen,status=self._v290_filter.get(),
                            query=self._v290_query.get().strip())
            self._v290_status.set(f"Exported {n:,} rows to a new UTF-8 BOM CSV.")
        except (OSError,ValueError) as ex:
            self._dialog("showerror","Smart Library",str(ex))

    def _v290_history(self):
        if not self._v290_root:return
        try:
            records=history(self._v290_root)
            from datetime import datetime
            lines=[f"{datetime.fromtimestamp(i['scanned']).strftime('%Y-%m-%d %H:%M')} | {i['total']:,} songs | {i['issues']:,} warnings | {i['cached']:,} reused" for i in records[:12]]
            self._dialog("showinfo","Smart Library scan history",
                         "\n".join(lines) if lines else "No completed scans yet.")
        except (OSError,ValueError) as ex:
            self._dialog("showerror","Smart Library",str(ex))

    def _studio_can_close(self):
        # Stopping a scan triggers transactional rollback before the process exits.
        if self._v290_running:
            self._v290_stop.set()
            self._dialog("showinfo","Smart Library",
                  "The Smart Library scan is stopping. Please close the app again when cancellation completes.")
            return False
        return super()._studio_can_close()
