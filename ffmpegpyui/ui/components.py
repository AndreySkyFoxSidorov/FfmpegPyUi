import os
from tkinter import Menu

import customtkinter as ctk

from .styles import Colors, Fonts, Metrics


class FileListItem(ctk.CTkFrame):
    def __init__(self, master, file_path, remove_callback, info=None, **kwargs):
        super().__init__(
            master,
            fg_color=Colors.bg_card,
            corner_radius=Metrics.radius,
            border_width=1,
            border_color=Colors.border,
            **kwargs,
        )
        self.file_path = file_path

        ext = os.path.splitext(file_path)[1].lstrip(".").upper() or "DIR"
        self.type_lbl = ctk.CTkLabel(
            self,
            text=ext,
            width=35,
            font=Fonts.subheading,
            text_color=Colors.accent,
        )
        self.type_lbl.pack(side="left", padx=(Metrics.padding_m, 5), anchor="n", pady=5)

        center_frame = ctk.CTkFrame(self, fg_color="transparent")
        center_frame.pack(side="left", fill="x", expand=True, padx=5, pady=5)

        self.name_lbl = ctk.CTkLabel(
            center_frame,
            text=os.path.basename(file_path),
            font=Fonts.body,
            text_color=Colors.text_primary,
            anchor="w",
            wraplength=180,
            justify="left",
        )
        self.name_lbl.pack(side="top", fill="x", anchor="w")

        if info:
            self.meta_lbl = ctk.CTkLabel(
                center_frame,
                text=str(info),
                font=Fonts.small,
                text_color=Colors.text_secondary,
                anchor="w",
                wraplength=180,
                justify="left",
            )
            self.meta_lbl.pack(side="bottom", fill="x", anchor="w")

        self.del_btn = ctk.CTkButton(
            self,
            text="X",
            width=24,
            height=24,
            fg_color="transparent",
            hover_color=Colors.error,
            text_color=Colors.error,
            font=("Arial", 16, "bold"),
            command=lambda: remove_callback(file_path),
        )
        self.del_btn.pack(side="right", padx=Metrics.padding_m, anchor="center")

        self.menu = Menu(self, tearoff=0)
        self.menu.add_command(label="Copy File Path", command=self.copy_path)
        if info:
            self.menu.add_command(label="Copy Media Info", command=lambda: self.copy_info(info))

        self.bind("<Button-3>", self.show_menu)
        self.type_lbl.bind("<Button-3>", self.show_menu)
        self.name_lbl.bind("<Button-3>", self.show_menu)
        if hasattr(self, "meta_lbl"):
            self.meta_lbl.bind("<Button-3>", self.show_menu)
        center_frame.bind("<Button-3>", self.show_menu)

    def show_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def copy_path(self):
        self.clipboard_clear()
        self.clipboard_append(self.file_path)

    def copy_info(self, info):
        self.clipboard_clear()
        self.clipboard_append(str(info))


class ScrollableFileList(ctk.CTkScrollableFrame):
    def __init__(self, master, remove_callback, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.remove_callback = remove_callback
        self.items = {}

    def add_file(self, path, info=None):
        if path not in self.items:
            item = FileListItem(self, path, self.remove_callback, info=info)
            item.pack(fill="x", pady=2)
            self.items[path] = item

    def remove_file(self, path):
        if path in self.items:
            self.items[path].destroy()
            del self.items[path]
