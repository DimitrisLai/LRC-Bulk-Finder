"""Stage 1 read-only song-centered candidate comparison window.

Stage 2 adds shared Lyrics Studio playback and synchronized highlights.
Existing v2.9.9 Candidate Review and its write buttons are untouched.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, scrolledtext
from pathlib import Path

from candidate_review_v3 import group_candidates, page_groups, read_snapshot, comparison
from v260_player import duration_seconds
from v260_studio import format_time

EL = {
    "Candidate Review 3.0 — Stage 1 (read-only)":"Έλεγχος υποψήφιων στίχων 3.0 — Στάδιο 1 (μόνο ανάγνωση)",
    "Search song / folder":"Αναζήτηση τραγουδιού / φακέλου",
    "Previous page":"Προηγούμενη σελίδα",
    "Next page":"Επόμενη σελίδα",
    "Candidate A":"Υποψήφιο Α",
    "Candidate B":"Υποψήφιο Β",
    "Comparison":"Σύγκριση",
    "No candidate selected":"Δεν έχει επιλεγεί αρχείο στίχων",
    "No matching candidates":"Δεν βρέθηκαν υποψήφιοι στίχοι",
    "Source: Unknown (not stored in LRC)":"Πηγή: Άγνωστη (δεν αποθηκεύεται στο LRC)",
    "NOT VERIFIED":"ΜΗ ΕΠΑΛΗΘΕΥΜΕΝΟ",
    "Read-only: no playback in Stage 1. Synchronized playback arrives in Stage 2.":"Μόνο ανάγνωση: χωρίς αναπαραγωγή στο Στάδιο 1. Ο συγχρονισμός έρχεται στο Στάδιο 2.",
    "Existing .lrc preserved":"Το υπάρχον .lrc προστατεύεται",
    "No unambiguous audio":"Δεν υπάρχει μοναδικό αρχείο ήχου",
    "Close":"Κλείσιμο",
}


class CandidateCompareWindow(tk.Toplevel):
    def __init__(self, owner, rows):
        super().__init__(owner)
        self.owner = owner
        self.groups = group_candidates(rows)
        self.page = 0
        self.visible = []
        self.group = None
        self._options = []
        self.title(self._tr("Candidate Review 3.0 — Stage 1 (read-only)"))
        self.geometry("1190x760")
        self.minsize(770, 580)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._build()
        self._refresh()
        self.focus_set()

    def _tr(self, text):
        language = getattr(getattr(self.owner, "gui_locale", None), "language", "en")
        return EL.get(text, text) if language == "el" else text

    def _build(self):
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=self._tr("Candidate Review 3.0 — Stage 1 (read-only)"),
                  style="Header.TLabel").pack(anchor="w")
        ttk.Label(frame, text=self._tr(
            "Read-only: no playback in Stage 1. Synchronized playback arrives in Stage 2."
        ), wraplength=1000).pack(anchor="w", pady=(3, 10))

        search = ttk.Frame(frame)
        search.pack(fill="x", pady=(0, 5))
        ttk.Label(search, text=self._tr("Search song / folder")).pack(side="left", padx=(0, 8))
        self.query = tk.StringVar()
        ttk.Entry(search, textvariable=self.query).pack(side="left", expand=True, fill="x")
        self.query.trace_add("write", lambda *_: self._on_search())
        self.total_label = tk.StringVar()
        ttk.Label(search, textvariable=self.total_label).pack(side="right", padx=8)

        main = ttk.Panedwindow(frame, orient="horizontal")
        main.pack(fill="both", expand=True)
        songs = ttk.Frame(main)
        main.add(songs, weight=1)
        self.song_list = tk.Listbox(songs, height=17, exportselection=False)
        self.song_list.pack(fill="both", expand=True)
        self.song_list.bind("<<ListboxSelect>>", self._select_song)
        paging = ttk.Frame(songs)
        paging.pack(fill="x", pady=5)
        ttk.Button(paging, text=self._tr("Previous page"), command=lambda: self._move(-1)).pack(side="left")
        ttk.Button(paging, text=self._tr("Next page"), command=lambda: self._move(1)).pack(side="right")

        right = ttk.Frame(main, padding=(8, 0))
        main.add(right, weight=3)
        self.summary = tk.StringVar()
        ttk.Label(right, textvariable=self.summary, wraplength=750).pack(anchor="w", pady=(0, 8))
        selectors = ttk.Frame(right)
        selectors.pack(fill="x")
        self.choice_a = tk.StringVar()
        self.choice_b = tk.StringVar()
        for col, value in ((0, self.choice_a), (1, self.choice_b)):
            block = ttk.Frame(selectors)
            block.grid(row=0, column=col, sticky="ew", padx=(0, 7))
            ttk.Label(block, text=self._tr("Candidate A" if col == 0 else "Candidate B")).pack(anchor="w")
            picker = ttk.Combobox(block, textvariable=value, state="readonly")
            picker.pack(fill="x")
            picker.bind("<<ComboboxSelected>>", lambda _e: self._show_comparison())
            if col == 0:
                self.select_a = picker
            else:
                self.select_b = picker
        selectors.columnconfigure(0, weight=1)
        selectors.columnconfigure(1, weight=1)
        self.diff_status = tk.StringVar(value=self._tr("No candidate selected"))
        ttk.Label(right, textvariable=self.diff_status, wraplength=750).pack(anchor="w", pady=8)
        panes = ttk.Panedwindow(right, orient="horizontal")
        panes.pack(fill="both", expand=True)
        self.previews = []
        for _ in range(2):
            text = scrolledtext.ScrolledText(panes, width=38, height=24, wrap="word",
                                             font=("Consolas", 10), state="disabled")
            panes.add(text, weight=1)
            self.previews.append(text)
        ttk.Button(frame, text=self._tr("Close"), command=self.destroy).pack(anchor="e", pady=(8, 0))

    def _on_search(self):
        self.page = 0
        self._refresh()

    def _move(self, direction):
        target = self.page + direction
        if target < 0:
            return
        available, total = page_groups(self.groups, target, self.query.get())
        if available or target == 0 or total == 0:
            self.page = target
            self._refresh()

    def _refresh(self):
        self.visible, total = page_groups(self.groups, self.page, self.query.get())
        pages = max(1, (total + 199) // 200)
        self.total_label.set(f"{total} songs  ·  page {self.page+1}/{pages}")
        self.song_list.delete(0, "end")
        for group in self.visible:
            self.song_list.insert("end", f"{group.title}   [{len(group.candidates)}]")
        if self.visible:
            self.song_list.selection_set(0)
            self._select_song()
        else:
            self.group = None
            self.summary.set(self._tr("No matching candidates"))
            self._options = []
            self.choice_a.set("")
            self.choice_b.set("")
            self.select_a.configure(values=())
            self.select_b.configure(values=())
            self._clear_text()
            self.diff_status.set(self._tr("No candidate selected"))

    def _select_song(self, event=None):
        index = self.song_list.curselection()
        if not index or index[0] >= len(self.visible):
            return
        self.group = self.visible[index[0]]
        flags = []
        if self.group.audio is None:
            flags.append(self._tr("No unambiguous audio"))
        if self.group.has_lrc:
            flags.append(self._tr("Existing .lrc preserved"))
        self.summary.set(f"{self.group.title}  ·  {len(self.group.candidates)} candidates  ·  " +
                         self._tr("NOT VERIFIED") + ("  ·  " + "; ".join(flags) if flags else ""))
        self._options = [f"#{row['index']} — {Path(row['path']).name}" for row in self.group.candidates]
        self.select_a.configure(values=self._options)
        self.select_b.configure(values=self._options)
        self.choice_a.set(self._options[0])
        self.choice_b.set(self._options[1] if len(self._options) > 1 else self._options[0])
        self._show_comparison()

    def _clear_text(self):
        for widget in self.previews:
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            widget.configure(state="disabled")

    def _render_preview(self, widget, candidate):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", self._tr("NOT VERIFIED") + "\n" +
                      self._tr("Source: Unknown (not stored in LRC)") + "\n\n")
        if candidate.error:
            widget.insert("end", "Unable to parse: " + candidate.error + "\n")
        else:
            widget.insert("end", f"{candidate.line_count} timed lines\n")
            if candidate.warnings:
                widget.insert("end", "\nWarnings:\n" +
                              "\n".join(candidate.warnings[:10]) + "\n")
                if len(candidate.warnings) > 10:
                    widget.insert("end", f"... {len(candidate.warnings)-10} more warnings\n")
            widget.insert("end", "\n")
            for line in candidate.lines:
                widget.insert("end", f"{format_time(line.seconds)} {line.text}\n")
        widget.configure(state="disabled")

    def _show_comparison(self):
        if self.group is None or not self._options:
            return
        try:
            left = self._options.index(self.choice_a.get())
            right = self._options.index(self.choice_b.get())
        except ValueError:
            return
        duration = duration_seconds(self.group.audio) if self.group.audio else 0.0
        a = read_snapshot(self.group.candidates[left], duration=duration)
        b = read_snapshot(self.group.candidates[right], duration=duration)
        self._render_preview(self.previews[0], a)
        self._render_preview(self.previews[1], b)
        report = comparison(a, b)
        if not report["ready"]:
            self.diff_status.set("Cannot compare: " + report["reason"])
        else:
            self.diff_status.set(
                f"Same file: {'Yes' if report['same_file'] else 'No'}  |  "
                f"Exact duplicates: {'Yes' if report['exact_duplicate'] else 'No'}  |  "
                f"Different text (paired lines): {report['changed_text']}  |  "
                f"Different timing: {report['changed_timing']}  |  "
                f"Unpaired lines: {report['extra_lines']}")
