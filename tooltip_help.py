"""Mouseover help for Tkinter widgets (no dependencies)."""
import tkinter as tk

class ToolTip:
    def __init__(self,widget,text,delay=500):
        self.widget=widget
        self.message=str(text)
        self.delay=delay
        self._after=None
        self.tip=None
        widget.bind("<Enter>",self._enter,add="+")
        widget.bind("<Leave>",self._leave,add="+")
        widget.bind("<ButtonPress>",self._leave,add="+")

    def _enter(self,_=None):
        self._cancel()
        self._after=self.widget.after(self.delay,self._show)

    def _cancel(self):
        if self._after is not None:
            self.widget.after_cancel(self._after)
            self._after=None

    def _leave(self,_=None):
        self._cancel()
        if self.tip:
            self.tip.destroy()
            self.tip=None

    def _show(self):
        self._after=None
        if self.tip or not self.widget.winfo_exists():
            return
        x=self.widget.winfo_rootx()+20
        y=self.widget.winfo_rooty()+self.widget.winfo_height()+6
        self.tip=tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        label=tk.Label(self.tip,text=self.message,justify="left",wraplength=390,
                       background="#fffbe9",foreground="#1b2734",
                       borderwidth=1,relief="solid",padx=10,pady=8,
                       font=("Segoe UI",9))
        label.pack()
