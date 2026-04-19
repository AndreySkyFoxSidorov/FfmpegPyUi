import customtkinter as ctk
from .styles import Colors, Fonts, Metrics
from tkinter import Menu
from .tooltip import CTkToolTip

class FileListItem(ctk.CTkFrame):
    def __init__(self, master, file_path, remove_callback, info=None, **kwargs):
        super().__init__(master, fg_color=Colors.bg_card, corner_radius=Metrics.radius, border_width=1, border_color=Colors.border, **kwargs)
        self.file_path = file_path
        
        # Icon/Type
        ext = file_path.split('.')[-1].upper() if '.' in file_path else "DIR"
        self.type_lbl = ctk.CTkLabel(self, text=ext, width=35, font=Fonts.subheading, text_color=Colors.accent)
        self.type_lbl.pack(side="left", padx=(Metrics.padding_m, 5), anchor="n", pady=5)
        
        # Filename & Info Container
        center_frame = ctk.CTkFrame(self, fg_color="transparent")
        center_frame.pack(side="left", fill="x", expand=True, padx=5, pady=5)

        name = file_path.split('\\')[-1].split('/')[-1]
        self.name_lbl = ctk.CTkLabel(center_frame, text=name, font=Fonts.body, text_color=Colors.text_primary, anchor="w", wraplength=180, justify="left")
        self.name_lbl.pack(side="top", fill="x", anchor="w")
        
        if info:
            meta_text = str(info)
            self.meta_lbl = ctk.CTkLabel(center_frame, text=meta_text, font=Fonts.small, text_color=Colors.text_secondary, anchor="w", wraplength=180, justify="left")
            self.meta_lbl.pack(side="bottom", fill="x", anchor="w")
        
        # Remove button
        self.del_btn = ctk.CTkButton(self, text="×", width=24, height=24, 
                                     fg_color="transparent", hover_color=Colors.error, 
                                     text_color=Colors.error, font=("Arial", 16, "bold"),
                                     command=lambda: remove_callback(file_path))
        self.del_btn.pack(side="right", padx=Metrics.padding_m, anchor="center")

        # Context Menu
        self.menu = Menu(self, tearoff=0)
        self.menu.add_command(label="Copy File Path", command=self.copy_path)
        if info:
            self.menu.add_command(label="Copy Media Info", command=lambda: self.copy_info(info))
        
        self.bind("<Button-3>", self.show_menu)
        self.type_lbl.bind("<Button-3>", self.show_menu)
        self.name_lbl.bind("<Button-3>", self.show_menu)
        if hasattr(self, 'meta_lbl'):
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
        if path in self.items: return
        item = FileListItem(self, path, self.remove_callback, info=info)
        item.pack(fill="x", pady=2)
        self.items[path] = item

    def remove_file(self, path):
        if path in self.items:
            self.items[path].destroy()
            del self.items[path]

class TaskRow(ctk.CTkFrame):
    """
    A row representing a specific task preset with inline settings.
    """
    def __init__(self, master, title, run_callback, schema=None, initial_values=None, **kwargs):
        super().__init__(master, fg_color=Colors.bg_card, corner_radius=Metrics.radius, border_width=1, border_color=Colors.border, **kwargs)
        self.run_callback = run_callback
        self.title = title
        self.schema = schema or []
        self.initial_values = initial_values or {}
        
        # Main Layout: Title | Settings | Run
        
        # 1. Title
        self.lbl_title = ctk.CTkLabel(self, text=title, font=Fonts.subheading, text_color=Colors.text_primary, width=130, anchor="w")
        self.lbl_title.pack(side="left", padx=Metrics.padding_l, pady=Metrics.padding_m)
        
        # 2. Settings Container (Scrollable or Flex)
        self.settings_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.settings_frame.pack(side="left", fill="x", expand=True, padx=Metrics.padding_m)
        self.inputs = {}
        self.labels = {} # Store value labels for sliders

        # Render settings
        for param in self.schema:
            val = self.initial_values.get(param.name, param.default)
            self.add_setting(param, val)

        # 3. Actions (Reset + Run)
        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_frame.pack(side="right", padx=Metrics.padding_l, pady=Metrics.padding_m)

        # Reset Button (Small icon-like)
        self.btn_reset = ctk.CTkButton(self.actions_frame, text="↺", width=24, height=Metrics.btn_height,
                                       fg_color=Colors.bg_card, border_color=Colors.border, border_width=1,
                                       hover_color=Colors.error, text_color=Colors.text_secondary,
                                       font=("Arial", 14), command=self.reset_settings)
        self.btn_reset.pack(side="left", padx=(0, 5))

        # Run Button
        self.btn_run = ctk.CTkButton(self.actions_frame, text="RUN", width=50, height=Metrics.btn_height, 
                                     fg_color=Colors.success, hover_color="#89b055", font=Fonts.subheading,
                                     command=lambda: self.run_callback(self.title, self.get_settings()))
        self.btn_run.pack(side="left")

    def add_setting(self, param, current_val):
        # A vertical stack for Label + Control
        container = ctk.CTkFrame(self.settings_frame, fg_color="transparent", width=90)
        container.pack(side="left", padx=Metrics.padding_s, fill="y")
        
        # Label Row (Label + Value if slider)
        top_row = ctk.CTkFrame(container, fg_color="transparent", height=14)
        top_row.pack(side="top", fill="x", expand=False)
        
        lbl = ctk.CTkLabel(top_row, text=param.label, font=Fonts.small, text_color=Colors.text_secondary, anchor="w")
        lbl.pack(side="left")
        
        if param.description:
            lbl.tooltip = CTkToolTip(lbl, param.description, delay=300)

        widget = None

        if param.type == "choice":
            # Combobox
            var = ctk.StringVar(value=str(current_val))
            widget = ctk.CTkComboBox(container, values=param.options, variable=var, 
                                     width=100, height=Metrics.input_height, font=Fonts.body,
                                     dropdown_font=Fonts.body)
            self.inputs[param.name] = widget
            
        elif param.type == "slider":
            # Slider
            var = ctk.DoubleVar(value=float(current_val))
            
            # Value Label (Live update)
            val_lbl = ctk.CTkLabel(top_row, text=str(val_check(current_val)), font=Fonts.small, text_color=Colors.accent, width=30, anchor="e")
            val_lbl.pack(side="right")
            self.labels[param.name] = val_lbl
            
            # Determine if this slider should be integer-based
            is_int = isinstance(param.min_val, int) and isinstance(param.max_val, int)
            steps = 100
            if is_int:
                steps = param.max_val - param.min_val # 1 step per int
                if steps == 0: steps = 1

            def update_slider(val):
                # Update label text
                v = float(val)
                if is_int:
                    txt = f"{int(v)}"
                else:
                    txt = f"{int(v)}" if v.is_integer() else f"{v:.1f}"
                val_lbl.configure(text=txt)

            widget = ctk.CTkSlider(container, from_=param.min_val, to=param.max_val, variable=var,
                                   width=100, height=14, command=update_slider, number_of_steps=steps)
            self.inputs[param.name] = widget
            # Trigger initial label set
            update_slider(float(current_val))

        elif param.type == "checkbox" or isinstance(current_val, bool):
             # Checkbox
            var = ctk.BooleanVar(value=current_val)
            widget = ctk.CTkCheckBox(container, text="", variable=var, width=20, height=20, border_width=2)
            self.inputs[param.name] = var
            
        else:
            # Entry
            widget = ctk.CTkEntry(container, width=70, height=Metrics.input_height, font=Fonts.body)
            widget.insert(0, str(current_val))
            self.inputs[param.name] = widget

        if widget and not isinstance(widget, ctk.BooleanVar):
            widget.pack(side="bottom", fill="x", pady=(2, 0))
        elif isinstance(widget, ctk.BooleanVar):
            # Checkbox specific packing
             ctk.CTkCheckBox(container, text="", variable=widget, width=20, height=20).pack(side="bottom", anchor="w", pady=(2,0))


    def reset_settings(self):
        for param in self.schema:
            default_val = param.default
            
            # Update Widget
            if param.name in self.inputs:
                widget = self.inputs[param.name]
                
                if isinstance(widget, ctk.CTkComboBox):
                    widget.set(str(default_val))
                elif isinstance(widget, ctk.CTkSlider):
                    widget.set(float(default_val))
                    # Manually update label since .set() doesn't trigger command
                    if param.name in self.labels:
                        v = float(default_val)
                        txt = f"{int(v)}" if v.is_integer() else f"{v:.1f}"
                        self.labels[param.name].configure(text=txt)
                elif isinstance(widget, ctk.BooleanVar):
                    widget.set(default_val)
                elif isinstance(widget, ctk.CTkEntry):
                    widget.delete(0, "end")
                    widget.insert(0, str(default_val))

    def get_settings(self):
        vals = {}
        for k, w in self.inputs.items():
            if isinstance(w, ctk.BooleanVar):
                 vals[k] = w.get()
            elif isinstance(w, ctk.CTkSlider):
                 vals[k] = w.get()
            else:
                 val = w.get()
                 # Try convert to number
                 try:
                     if "." in val and not val.lower().endswith("k"): # Avoid converting "128k" to float
                        vals[k] = float(val)
                     elif val.isdigit():
                        vals[k] = int(val)
                     else:
                        vals[k] = val
                 except:
                     vals[k] = val
        return vals

def val_check(v):
    if isinstance(v, float) and v.is_integer(): return int(v)
    return v

class TaskGroup(ctk.CTkFrame):
    """
    Collapsible or simple group frame.
    """
    def __init__(self, master, title, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.lbl = ctk.CTkLabel(self, text=title, font=Fonts.heading, text_color=Colors.accent, anchor="w")
        self.lbl.pack(fill="x", pady=(Metrics.padding_l, Metrics.padding_s))
        
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="x", expand=True)
