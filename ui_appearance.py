"""Built-in modern light/dark visual system; no external GUI framework.

Changes ttk presentation and Tk text colors only. Never modifies profile values,
search behavior, filenames, saved lyrics or music data.
"""
from __future__ import annotations

import json
import os
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ui_locale import settings_file

PALETTES = {
    "light": {
        "canvas":"#F2F5FA", "surface":"#FFFFFF", "raised":"#EAF0F7",
        "text":"#18283D", "subtext":"#586A80", "border":"#D6E0EC",
        "accent":"#445CE4", "accent_hover":"#354ACE",
        "accent_text":"#FFFFFF", "selection":"#E5EAFF",
        "input":"#FFFFFF", "log_bg":"#172235", "log_fg":"#E9F0FC",
        "danger":"#C13B47", "danger_hover":"#A72D39",
        "success":"#0C8B78",
    },
    "dark": {
        "canvas":"#101723", "surface":"#1C2637", "raised":"#28354A",
        "text":"#EDF3FC", "subtext":"#A7B6C9", "border":"#39485F",
        "accent":"#8395FF", "accent_hover":"#A5B1FF",
        "accent_text":"#101723", "selection":"#354466",
        "input":"#1B2638", "log_bg":"#0C1320", "log_fg":"#E0E8F7",
        "danger":"#E07885", "danger_hover":"#F0A4AD",
        "success":"#4CD6B4",
    },
}

def read_mode(path=None):
    """Safe default for a broken/missing settings file."""
    target=Path(path) if path is not None else settings_file()
    try:
        payload=json.loads(target.read_text(encoding="utf-8"))
        value=payload.get("appearance","light")
        return value if value in PALETTES else "light"
    except (OSError, ValueError, TypeError, AttributeError):
        return "light"


def save_mode(mode,path=None):
    if mode not in PALETTES:
        raise ValueError("Unsupported appearance mode")
    target=Path(path) if path is not None else settings_file()
    target.parent.mkdir(parents=True,exist_ok=True)
    try:
        existing=json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(existing,dict):
            existing={}
    except (OSError,ValueError,TypeError):
        existing={}
    # Keep interface_language and future preferences intact.
    existing.update({"schema":1,"appearance":mode})
    temporary=None
    try:
        with tempfile.NamedTemporaryFile("w",encoding="utf-8",dir=target.parent,
                                         prefix=".appearance-",suffix=".tmp",delete=False) as handle:
            temporary=Path(handle.name)
            json.dump(existing,handle,ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary,target)
    finally:
        if temporary and temporary.exists():
            try:temporary.unlink()
            except OSError:pass


def install_theme(root,mode):
    """Apply a restrained flat visual system using only stock ttk styles."""
    if mode not in PALETTES:raise ValueError("Unknown appearance mode")
    c=PALETTES[mode]
    style=ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    root.configure(background=c["canvas"])
    style.configure(".",font=("Segoe UI",10),background=c["surface"],foreground=c["text"])
    style.configure("TFrame",background=c["surface"])
    style.configure("App.TFrame",background=c["canvas"])
    style.configure("Hero.TFrame",background=c["canvas"])
    style.configure("Card.TFrame",background=c["surface"],relief="flat")
    style.configure("TLabel",background=c["surface"],foreground=c["text"],font=("Segoe UI",10))
    style.configure("HeroTitle.TLabel",background=c["canvas"],foreground=c["text"],
                    font=("Segoe UI",22,"bold"))
    style.configure("HeroSubtitle.TLabel",background=c["canvas"],foreground=c["subtext"],
                    font=("Segoe UI",10))
    style.configure("HeroMeta.TLabel",background=c["canvas"],foreground=c["subtext"],
                    font=("Segoe UI",9))
    style.configure("Header.TLabel",background=c["surface"],foreground=c["text"],
                    font=("Segoe UI",16,"bold"))
    style.configure("Hint.TLabel",background=c["surface"],foreground=c["subtext"],
                    font=("Segoe UI",9))
    style.configure("Metric.TLabel",background=c["surface"],foreground=c["accent"],
                    font=("Segoe UI",22,"bold"))
    style.configure("Success.TLabel",background=c["surface"],foreground=c["success"])
    style.configure("TButton",font=("Segoe UI",10),padding=(14,8),
                    relief="flat",borderwidth=0,
                    background=c["raised"],foreground=c["text"])
    style.map("TButton",
              background=[("disabled",c["raised"]),("pressed",c["selection"]),("active",c["selection"])],
              foreground=[("disabled",c["subtext"]),("!disabled",c["text"])])
    style.configure("Primary.TButton",font=("Segoe UI",10,"bold"),
                    background=c["accent"],foreground=c["accent_text"],
                    borderwidth=0,relief="flat",padding=(18,11))
    style.map("Primary.TButton",
              background=[("disabled",c["raised"]),("pressed",c["accent_hover"]),("active",c["accent_hover"])],
              foreground=[("disabled",c["subtext"]),("!disabled",c["accent_text"])])
    style.configure("Danger.TButton",padding=(12,8),relief="flat",borderwidth=0,
                    background=c["danger"],foreground=c["accent_text"])
    style.map("Danger.TButton",
              background=[("active",c["danger_hover"]),("pressed",c["danger_hover"])],
              foreground=[("!disabled",c["accent_text"])])
    style.configure("TEntry",fieldbackground=c["input"],foreground=c["text"],
                    bordercolor=c["border"],lightcolor=c["border"],darkcolor=c["border"],
                    padding=(8,6),insertcolor=c["text"])
    style.map("TEntry",fieldbackground=[("readonly",c["raised"]),("disabled",c["raised"])],
              foreground=[("disabled",c["subtext"])])
    style.configure("TCombobox",fieldbackground=c["input"],background=c["raised"],
                    foreground=c["text"],arrowcolor=c["text"],
                    bordercolor=c["border"],lightcolor=c["border"],
                    darkcolor=c["border"],padding=(8,6))
    style.map("TCombobox",fieldbackground=[("readonly",c["input"]),("disabled",c["raised"])],
              selectbackground=[("readonly",c["input"])],
              selectforeground=[("readonly",c["text"])],
              foreground=[("readonly",c["text"]),("disabled",c["subtext"])])
    style.configure("TCheckbutton",background=c["surface"],foreground=c["text"],
                    font=("Segoe UI",10),padding=(4,5))
    style.map("TCheckbutton",
              background=[("active",c["surface"])],
              foreground=[("disabled",c["subtext"]),("!disabled",c["text"])])
    style.configure("TRadiobutton",background=c["surface"],foreground=c["text"],
                    font=("Segoe UI",10),padding=(4,5))
    style.map("TRadiobutton",background=[("active",c["surface"])])
    style.configure("TLabelframe",background=c["surface"],bordercolor=c["border"],
                    lightcolor=c["border"],darkcolor=c["border"],borderwidth=1,relief="solid")
    style.configure("TLabelframe.Label",background=c["surface"],foreground=c["text"],
                    font=("Segoe UI",10,"bold"))
    style.configure("TNotebook",background=c["canvas"],borderwidth=0,tabmargins=(0,0,0,0))
    style.configure("TNotebook.Tab",font=("Segoe UI",10),
                    padding=(13,11),borderwidth=0,
                    background=c["raised"],foreground=c["subtext"])
    style.map("TNotebook.Tab",
              background=[("selected",c["surface"]),("active",c["selection"])],
              foreground=[("selected",c["accent"]),("active",c["text"])],
              expand=[("selected",(0,0,0,0))])
    style.configure("Treeview",background=c["surface"],fieldbackground=c["surface"],
                    foreground=c["text"],borderwidth=0,relief="flat",
                    rowheight=30,font=("Segoe UI",10))
    style.map("Treeview",
              background=[("selected",c["selection"])],
              foreground=[("selected",c["text"])])
    style.configure("Treeview.Heading",background=c["raised"],foreground=c["text"],
                    font=("Segoe UI",10,"bold"),relief="flat",padding=(8,8),
                    borderwidth=0)
    style.map("Treeview.Heading",background=[("active",c["selection"])])
    style.configure("Horizontal.TProgressbar",background=c["accent"],
                    troughcolor=c["raised"],borderwidth=0,lightcolor=c["accent"],
                    darkcolor=c["accent"])
    style.configure("Vertical.TScrollbar",background=c["raised"],troughcolor=c["surface"],
                    borderwidth=0,arrowcolor=c["text"])
    style.configure("Horizontal.TScrollbar",background=c["raised"],troughcolor=c["surface"],
                    borderwidth=0,arrowcolor=c["text"])
    style.configure("TSeparator",background=c["border"])
    try:
        # Native dropdown list is a Tk listbox, not part of ttk Style.
        root.option_add("*TCombobox*Listbox.background",c["input"])
        root.option_add("*TCombobox*Listbox.foreground",c["text"])
        root.option_add("*TCombobox*Listbox.selectBackground",c["selection"])
        root.option_add("*TCombobox*Listbox.selectForeground",c["text"])
    except tk.TclError:
        pass
    return c


def refresh_native_widgets(root,mode):
    """Recolor ONLY generic Tk text/list widgets; keep contents and semantics."""
    c=PALETTES[mode]
    def walk(widget):
        for child in widget.winfo_children():
            if isinstance(child,tk.Text):
                is_log=(getattr(root,"log",None) is child)
                try:
                    child.configure(background=c["log_bg"] if is_log else c["input"],
                                    foreground=c["log_fg"] if is_log else c["text"],
                                    insertbackground=c["log_fg"] if is_log else c["text"],
                                    selectbackground=c["accent"],selectforeground=c["accent_text"],
                                    highlightthickness=1,highlightbackground=c["border"],
                                    relief="flat",borderwidth=0)
                except tk.TclError:pass
            elif isinstance(child,tk.Listbox):
                try:
                    child.configure(background=c["input"],foreground=c["text"],
                                    selectbackground=c["selection"],selectforeground=c["text"])
                except tk.TclError:pass
            walk(child)
    walk(root)
