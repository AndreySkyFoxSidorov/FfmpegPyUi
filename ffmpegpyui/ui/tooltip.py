import customtkinter as ctk
from tkinter import Toplevel, Label

class CTkToolTip:
    """
    Creates a ToolTip for a given widget
    """
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.id = None
        self.widget.bind("<Enter>", self.schedule)
        self.widget.bind("<Leave>", self.hide)
        self.widget.bind("<ButtonPress>", self.hide)

    def schedule(self, event=None):
        self.unschedule()
        self.id = self.widget.after(self.delay, self.show)

    def unschedule(self, event=None):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def show(self):
        if self.tooltip_window:
            return
            
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
        
        # Use the root window as master to avoid issues with CTk wrappers
        root = self.widget.winfo_toplevel()
        self.tooltip_window = Toplevel(root)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        self.tooltip_window.attributes("-topmost", True) # Ensure it's on top

        label = Label(self.tooltip_window, text=self.text, justify='left',
                      background="#333333", relief='solid', borderwidth=1,
                      foreground="#ffffff", font=("Segoe UI", 10), padx=8, pady=4, wraplength=300)
        label.pack(ipadx=1)

    def hide(self, event=None):
        self.unschedule()
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
