import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES
import os
import json
import random
import subprocess
import sys
import threading
import webbrowser
from tkinter import Canvas, PhotoImage, filedialog, messagebox, simpledialog
from .styles import Colors, Fonts, Metrics
from .components import ScrollableFileList
from .localization import (
    WORKFLOW_SECTIONS,
    available_language_labels,
    field_description,
    field_label,
    get_language,
    language_label,
    option_label,
    option_labels,
    option_value,
    scheme_label,
    scheme_value,
    section_description,
    section_title,
    set_language,
    t,
)
from logic.scanner import scan_path
from logic.ffmpeg_runner import FfmpegRunner
from logic.ffmpeg_installer import ensure_ffmpeg_available, should_download_ffmpeg
from logic.ffmpeg_paths import normalize_ffmpeg_dir
from logic.input_paths import expand_input_paths
from logic.media_info import MediaProber
from logic.workflow import (
    BUILTIN_SCHEMES,
    DEFAULT_BUILTIN_SCHEME,
    DEFAULT_WORKFLOW_CONFIG,
    WorkflowVideoTask,
    get_builtin_scheme,
    is_audio_output_format,
    is_gif_output_format,
    normalize_workflow_config,
    selected_audio_filters,
    selected_video_filters,
)

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state.json")
APP_ICON_ICO = os.path.join(os.path.dirname(__file__), "favicon.ico")
APP_ICON_PNG = os.path.join(os.path.dirname(__file__), "favicon.png")
DEFAULT_FFMPEG_PATH = "./ffmpeg"
FFMPEG_DOWNLOAD_URL = "https://ffmpeg.org/download.html"
AUDIO_OUTPUT_HIDDEN_WORKFLOW_FIELDS = {
    "gif_width",
    "gif_fps",
    "gif_dither",
    "resolution_mode",
    "custom_width",
    "custom_height",
    "quality_profile",
    "encoding_speed",
    "video_codec",
    "crop_mode",
    "crop_left",
    "crop_right",
    "crop_top",
    "crop_bottom",
    "fps_mode",
    "audio_mode",
    "video_filter_1",
    "video_filter_2",
    "video_filter_3",
    "video_eq_brightness",
    "video_eq_contrast",
    "video_eq_saturation",
    "video_denoise_strength",
    "video_sharpen_strength",
    "video_text",
    "advanced_video_filters",
}
GIF_ONLY_FIELDS = {"gif_width", "gif_fps", "gif_dither"}
CROP_PARAMETER_FIELDS = {"crop_left", "crop_right", "crop_top", "crop_bottom"}
RESOLUTION_PARAMETER_FIELDS = {"custom_width", "custom_height"}
TRIM_SECONDS_FIELDS = {"trim_start_seconds", "trim_end_seconds"}
TRIM_FRAME_FIELDS = {"trim_start_frames", "trim_end_frames"}
VIDEO_EQ_FIELDS = {"video_eq_brightness", "video_eq_contrast", "video_eq_saturation"}
VIDEO_DENOISE_FIELDS = {"video_denoise_strength"}
VIDEO_SHARPEN_FIELDS = {"video_sharpen_strength"}
VIDEO_TEXT_FIELDS = {"video_text"}
VIDEO_FILTER_FIELDS = {
    "resolution_mode",
    "custom_width",
    "custom_height",
    "quality_profile",
    "encoding_speed",
    "video_codec",
    "crop_mode",
    "crop_left",
    "crop_right",
    "crop_top",
    "crop_bottom",
    "fps_mode",
    "video_filter_1",
    "video_filter_2",
    "video_filter_3",
    "video_eq_brightness",
    "video_eq_contrast",
    "video_eq_saturation",
    "video_denoise_strength",
    "video_sharpen_strength",
    "video_text",
    "advanced_video_filters",
}
AUDIO_HIGHPASS_FIELDS = {"audio_highpass_hz"}
AUDIO_LOWPASS_FIELDS = {"audio_lowpass_hz"}
AUDIO_FADE_FIELDS = {"audio_fade_seconds"}
AUDIO_FILTER_FIELDS = {
    "audio_volume",
    "audio_filter_1",
    "audio_filter_2",
    "audio_filter_3",
    "audio_highpass_hz",
    "audio_lowpass_hz",
    "audio_fade_seconds",
    "advanced_audio_filters",
}

class FfmpegApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, files=None):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        self.files = []
        self.files_info = {}
        self.app_state = {}
        self.workflow_inputs = {}
        self.workflow_specs = {}
        self.workflow_value_labels = {}
        self.workflow_visibility_state = None
        self.workflow_config_snapshot = {}
        self.crop_canvas = None
        self.crop_preview_label = None
        self.crop_preview_image = None
        self.crop_preview_source_path = None
        self.crop_preview_request_id = 0
        self.crop_preview_loading = False
        self.crop_preview_error_path = None
        self.crop_preview_geometry = None
        self.crop_drag_handle = None
        self.time_trim_canvas = None
        self.time_trim_start_canvas = None
        self.time_trim_end_canvas = None
        self.time_trim_label = None
        self.time_trim_start_image = None
        self.time_trim_end_image = None
        self.time_trim_start_key = None
        self.time_trim_end_key = None
        self.time_trim_start_error_key = None
        self.time_trim_end_error_key = None
        self.time_trim_start_request_id = 0
        self.time_trim_end_request_id = 0
        self.time_trim_start_after_id = None
        self.time_trim_end_after_id = None
        self.time_trim_start_loading = False
        self.time_trim_end_loading = False
        self.time_trim_geometry = None
        self.time_trim_drag_handle = None
        self.ffmpeg_installing = False

        self.load_state()
        self.apply_ffmpeg_path_setting(self.get_ffmpeg_path_setting())
        set_language(self.app_state.get("language", get_language()))

        self.title(t("app.title"))
        self.app_icon_image = None
        if os.path.exists(APP_ICON_PNG):
            try:
                self.app_icon_image = PhotoImage(file=APP_ICON_PNG)
                self.iconphoto(True, self.app_icon_image)
            except Exception:
                self.app_icon_image = None
        if os.path.exists(APP_ICON_ICO):
            try:
                self.iconbitmap(default=APP_ICON_ICO)
            except Exception:
                pass
        self.geometry("1420x940")
        self.minsize(1280, 860)
        self.configure(fg_color=Colors.bg_dark)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.create_sidebar()
        self.create_main_area()
        self.create_console_overlay()

        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.drop)

        self.runner = FfmpegRunner(self.update_console, self.on_task_complete, self.update_progress)
        self.clear_preview_cache_files()

        if files:
            self.process_input_paths(files)
        self.start_ffmpeg_startup_check()

    def drop(self, event):
        if event.data:
            self.process_input_paths(event.data)

    def get_ffmpeg_path_setting(self):
        if hasattr(self, "ffmpeg_path_var"):
            return self.ffmpeg_path_var.get().strip() or DEFAULT_FFMPEG_PATH
        return str(self.app_state.get("ffmpeg_path") or DEFAULT_FFMPEG_PATH).strip() or DEFAULT_FFMPEG_PATH

    def apply_ffmpeg_path_setting(self, ffmpeg_path):
        normalized = normalize_ffmpeg_dir(ffmpeg_path)
        WorkflowVideoTask.set_ffmpeg_dir(normalized)
        MediaProber.set_ffmpeg_dir(normalized)
        return normalized

    def save_ffmpeg_path(self):
        if not hasattr(self, "ffmpeg_path_var"):
            return

        value = self.ffmpeg_path_var.get().strip().strip('"') or DEFAULT_FFMPEG_PATH
        self.ffmpeg_path_var.set(value)
        self.app_state["ffmpeg_path"] = value
        self.apply_ffmpeg_path_setting(value)
        self.save_state()
        self.update_command_preview()

    def choose_ffmpeg_path(self):
        initial_dir = self.apply_ffmpeg_path_setting(self.get_ffmpeg_path_setting())
        selected = filedialog.askdirectory(
            parent=self,
            title=t("sidebar.ffmpeg_browse_title"),
            initialdir=initial_dir if os.path.isdir(initial_dir) else os.getcwd(),
        )
        if selected:
            self.ffmpeg_path_var.set(selected)
            self.save_ffmpeg_path()

    def open_ffmpeg_download(self, _event=None):
        webbrowser.open_new_tab(FFMPEG_DOWNLOAD_URL)

    def start_ffmpeg_startup_check(self):
        ffmpeg_dir = self.apply_ffmpeg_path_setting(self.get_ffmpeg_path_setting())
        if should_download_ffmpeg(ffmpeg_dir):
            self.ffmpeg_installing = True
            self.show_ffmpeg_download_console(ffmpeg_dir)
            threading.Thread(
                target=self.download_startup_ffmpeg,
                args=(ffmpeg_dir,),
                daemon=True,
            ).start()

    def show_ffmpeg_download_console(self, ffmpeg_dir):
        self.console_title.configure(text="Downloading FFmpeg")
        self.progress_bar.set(0)
        self.console_text.delete("1.0", "end")
        self.console_text.insert(
            "end",
            f"FFmpeg was not found in PATH or in this folder:\n{ffmpeg_dir}\n\n",
        )
        self.btn_close_console.configure(
            text="Please wait",
            fg_color=Colors.accent,
            state="disabled",
        )
        self.console_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def download_startup_ffmpeg(self, ffmpeg_dir):
        try:
            installed_dir = ensure_ffmpeg_available(ffmpeg_dir, log_callback=self.update_console)
            self.after(0, lambda: self.finish_ffmpeg_download(installed_dir))
        except Exception as error:
            self.after(0, lambda error=error: self.fail_ffmpeg_download(error))

    def finish_ffmpeg_download(self, installed_dir):
        self.ffmpeg_installing = False
        self.apply_ffmpeg_path_setting(installed_dir)
        self.progress_bar.set(1)
        self.console_title.configure(text="FFmpeg ready")
        self.console_text.insert("end", f"\nFFmpeg is ready in:\n{installed_dir}\n")
        self.console_text.see("end")
        self.btn_close_console.configure(
            text=t("console.close_view"),
            fg_color=Colors.success,
            state="normal",
            command=lambda: self.console_frame.place_forget(),
        )
        self.update_command_preview()

    def fail_ffmpeg_download(self, error):
        self.ffmpeg_installing = False
        self.progress_bar.set(0)
        self.console_title.configure(text="FFmpeg download failed")
        self.console_text.insert("end", f"\nCould not download FFmpeg automatically:\n{error}\n")
        self.console_text.see("end")
        self.btn_close_console.configure(
            text=t("console.close_view"),
            fg_color=Colors.error,
            state="normal",
            command=lambda: self.console_frame.place_forget(),
        )

    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=320, corner_radius=0, fg_color=Colors.bg_card)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(8, weight=1)

        self.logo = ctk.CTkLabel(self.sidebar, text=t("sidebar.logo"), font=Fonts.heading, text_color=Colors.accent)
        self.logo.grid(row=0, column=0, padx=10, pady=15)

        self.btn_add_file = ctk.CTkButton(self.sidebar, text=t("sidebar.add_files"), height=30, fg_color=Colors.accent, hover_color=Colors.accent_hover, command=self.add_files_dialog)
        self.btn_add_file.grid(row=1, column=0, padx=10, pady=2, sticky="ew")

        self.btn_add_dir = ctk.CTkButton(self.sidebar, text=t("sidebar.add_directory"), height=30, fg_color=Colors.bg_card, border_color=Colors.accent, border_width=1, hover_color=Colors.accent_hover, command=self.add_dir_dialog)
        self.btn_add_dir.grid(row=2, column=0, padx=10, pady=2, sticky="ew")

        gpu_init = self.app_state.get("use_gpu", False)
        self.gpu_var = ctk.BooleanVar(value=gpu_init)
        self.chk_gpu = ctk.CTkCheckBox(self.sidebar, text=t("sidebar.gpu"), variable=self.gpu_var,
                                       text_color=Colors.text_primary, font=Fonts.body,
                                       command=self.save_state)
        self.chk_gpu.grid(row=3, column=0, padx=10, pady=(15, 2), sticky="w")

        self.gpu_help = ctk.CTkLabel(self.sidebar, text=t("sidebar.gpu_help"), font=Fonts.small,
                                     text_color=Colors.text_secondary, anchor="w", justify="left",
                                     wraplength=280)
        self.gpu_help.grid(row=4, column=0, padx=10, pady=(0, 8), sticky="ew")

        self.ffmpeg_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.ffmpeg_frame.grid(row=5, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.ffmpeg_frame.grid_columnconfigure(0, weight=1)

        self.ffmpeg_path_label = ctk.CTkLabel(
            self.ffmpeg_frame,
            text=t("sidebar.ffmpeg_path_label"),
            font=Fonts.small,
            text_color=Colors.text_secondary,
            anchor="w",
        )
        self.ffmpeg_path_label.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.ffmpeg_path_var = ctk.StringVar(value=self.get_ffmpeg_path_setting())
        self.ffmpeg_path_entry = ctk.CTkEntry(
            self.ffmpeg_frame,
            textvariable=self.ffmpeg_path_var,
            height=28,
            font=Fonts.small,
        )
        self.ffmpeg_path_entry.grid(row=1, column=0, padx=(0, 6), pady=(4, 2), sticky="ew")
        self.ffmpeg_path_entry.bind("<FocusOut>", lambda _event: self.save_ffmpeg_path())
        self.ffmpeg_path_entry.bind("<Return>", lambda _event: self.save_ffmpeg_path())

        self.btn_ffmpeg_browse = ctk.CTkButton(
            self.ffmpeg_frame,
            text=t("sidebar.ffmpeg_browse"),
            width=76,
            height=28,
            fg_color=Colors.bg_card,
            border_color=Colors.border,
            border_width=1,
            command=self.choose_ffmpeg_path,
        )
        self.btn_ffmpeg_browse.grid(row=1, column=1, pady=(4, 2), sticky="e")

        self.ffmpeg_path_help = ctk.CTkLabel(
            self.ffmpeg_frame,
            text=t("sidebar.ffmpeg_path_help"),
            font=Fonts.small,
            text_color=Colors.text_secondary,
            anchor="w",
            justify="left",
            wraplength=280,
        )
        self.ffmpeg_path_help.grid(row=2, column=0, columnspan=2, sticky="ew")

        self.ffmpeg_download_link = ctk.CTkLabel(
            self.ffmpeg_frame,
            text=t("sidebar.ffmpeg_download_link"),
            font=Fonts.small,
            text_color=Colors.accent,
            anchor="w",
            cursor="hand2",
        )
        self.ffmpeg_download_link.grid(row=3, column=0, columnspan=2, pady=(4, 0), sticky="ew")
        self.ffmpeg_download_link.bind("<Button-1>", self.open_ffmpeg_download)

        self.language_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.language_frame.grid(row=6, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.language_frame.grid_columnconfigure(1, weight=1)

        self.language_label = ctk.CTkLabel(
            self.language_frame,
            text=t("sidebar.language"),
            font=Fonts.small,
            text_color=Colors.text_secondary,
            anchor="w",
        )
        self.language_label.grid(row=0, column=0, padx=(0, 8), sticky="w")

        self.language_var = ctk.StringVar(value=language_label(get_language()))
        self.language_combo = ctk.CTkComboBox(
            self.language_frame,
            values=available_language_labels(),
            variable=self.language_var,
            width=140,
            height=28,
            command=self.on_language_changed,
        )
        self.language_combo.grid(row=0, column=1, sticky="ew")

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.lbl_files = ctk.CTkLabel(self.sidebar, text=t("sidebar.queue"), font=Fonts.subheading, text_color=Colors.text_secondary, anchor="w")
        self.lbl_files.grid(row=7, column=0, padx=10, pady=(10, 0), sticky="nw")

        self.file_list = ScrollableFileList(self.sidebar, remove_callback=self.remove_file, width=285)
        self.file_list.grid(row=8, column=0, padx=5, pady=5, sticky="nsew")

        self.lbl_hint = ctk.CTkLabel(self.sidebar, text=t("sidebar.drop_hint"), text_color=Colors.text_secondary, font=("Segoe UI", 9))
        self.lbl_hint.grid(row=9, column=0, pady=5)

    def on_language_changed(self, language):
        workflow_settings = self.get_workflow_settings() if self.workflow_inputs else None
        selected_scheme = scheme_value(self.workflow_scheme_var.get()) if hasattr(self, "workflow_scheme_var") else DEFAULT_BUILTIN_SCHEME

        set_language(language)
        self.language_var.set(language_label(get_language()))
        self.app_state["language"] = get_language()
        self.apply_localized_texts(workflow_settings=workflow_settings, selected_scheme=selected_scheme)
        self.save_state()

    def apply_localized_texts(self, workflow_settings=None, selected_scheme=None):
        self.title(t("app.title"))

        if hasattr(self, "logo"):
            self.logo.configure(text=t("sidebar.logo"))
            self.btn_add_file.configure(text=t("sidebar.add_files"))
            self.btn_add_dir.configure(text=t("sidebar.add_directory"))
            self.chk_gpu.configure(text=t("sidebar.gpu"))
            self.gpu_help.configure(text=t("sidebar.gpu_help"))
            self.ffmpeg_path_label.configure(text=t("sidebar.ffmpeg_path_label"))
            self.btn_ffmpeg_browse.configure(text=t("sidebar.ffmpeg_browse"))
            self.ffmpeg_path_help.configure(text=t("sidebar.ffmpeg_path_help"))
            self.ffmpeg_download_link.configure(text=t("sidebar.ffmpeg_download_link"))
            self.language_label.configure(text=t("sidebar.language"))
            self.language_combo.configure(values=available_language_labels())
            self.language_var.set(language_label(get_language()))
            self.lbl_files.configure(text=t("sidebar.queue"))
            self.lbl_hint.configure(text=t("sidebar.drop_hint"))

        if hasattr(self, "main_title"):
            self.main_title.configure(text=t("workflow.title"))
            self.main_subtitle.configure(text=t("workflow.subtitle"))
            self.scheme_label.configure(text=t("workflow.scheme_label"))
            self.btn_load_scheme.configure(text=t("workflow.load_scheme"))
            self.btn_save_scheme.configure(text=t("workflow.save_scheme"))
            self.btn_delete_scheme.configure(text=t("workflow.delete_scheme"))
            self.btn_reset_scheme.configure(text=t("workflow.reset_scheme"))
            self.command_preview_title.configure(text=t("workflow.command_preview_title"))
            self.btn_run_workflow.configure(text=t("workflow.run"))

            selected_scheme = selected_scheme or scheme_value(self.workflow_scheme_var.get())
            self.refresh_scheme_combo(selected=selected_scheme)

            workflow_settings = workflow_settings or self.get_workflow_settings()
            for child in self.scroll_frame.winfo_children():
                child.destroy()
            self.create_workflow_form(normalize_workflow_config(workflow_settings))

        if hasattr(self, "console_title"):
            self.console_title.configure(text=t("console.processing"))
            if not self.runner.running:
                self.btn_close_console.configure(text=t("console.close_stop"))

    def create_main_area(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=1)

        self.main_title = ctk.CTkLabel(self.main_frame, text=t("workflow.title"), font=("Segoe UI", 22, "bold"),
                                       text_color=Colors.text_primary, anchor="w")
        self.main_title.grid(row=0, column=0, sticky="ew")

        self.main_subtitle = ctk.CTkLabel(self.main_frame, text=t("workflow.subtitle"), font=Fonts.body,
                                          text_color=Colors.text_secondary, anchor="w", justify="left",
                                          wraplength=920)
        self.main_subtitle.grid(row=1, column=0, sticky="ew", pady=(4, 16))

        self.create_scheme_bar()

        self.scroll_frame = ctk.CTkScrollableFrame(self.main_frame, fg_color="transparent")
        self.scroll_frame.grid(row=3, column=0, sticky="nsew", pady=(14, 12))

        self.command_preview_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=Colors.bg_card,
            corner_radius=Metrics.radius,
            border_width=1,
            border_color=Colors.border,
        )
        self.command_preview_frame.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        self.command_preview_frame.grid_columnconfigure(0, weight=1)

        self.command_preview_title = ctk.CTkLabel(
            self.command_preview_frame,
            text=t("workflow.command_preview_title"),
            font=Fonts.subheading,
            text_color=Colors.text_primary,
            anchor="w",
        )
        self.command_preview_title.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="ew")

        self.command_preview_text = ctk.CTkTextbox(
            self.command_preview_frame,
            height=72,
            font=Fonts.mono,
            text_color=Colors.text_secondary,
            fg_color=Colors.bg_dark,
        )
        self.command_preview_text.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")

        initial_config = self.app_state.get("workflow_settings") or get_builtin_scheme(DEFAULT_BUILTIN_SCHEME)
        self.create_workflow_form(normalize_workflow_config(initial_config))

        self.btn_run_workflow = ctk.CTkButton(
            self.main_frame,
            text=t("workflow.run"),
            height=42,
            fg_color=Colors.success,
            hover_color="#89b055",
            font=("Segoe UI", 14, "bold"),
            command=self.run_workflow
        )
        self.btn_run_workflow.grid(row=5, column=0, sticky="ew")

    def create_scheme_bar(self):
        bar = ctk.CTkFrame(self.main_frame, fg_color=Colors.bg_card, corner_radius=Metrics.radius,
                           border_width=1, border_color=Colors.border)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_columnconfigure(1, weight=1)

        self.scheme_label = ctk.CTkLabel(bar, text=t("workflow.scheme_label"), font=Fonts.subheading,
                                         text_color=Colors.text_primary)
        self.scheme_label.grid(row=0, column=0, padx=(12, 8), pady=12, sticky="w")

        initial_scheme = self.app_state.get("workflow_scheme_name", DEFAULT_BUILTIN_SCHEME)
        self.workflow_scheme_var = ctk.StringVar(value=scheme_label(scheme_value(initial_scheme)))
        self.scheme_combo = ctk.CTkComboBox(
            bar,
            values=self.get_scheme_names(),
            variable=self.workflow_scheme_var,
            height=30,
            command=lambda _value: self.load_selected_scheme()
        )
        self.scheme_combo.grid(row=0, column=1, padx=8, pady=12, sticky="ew")

        self.btn_load_scheme = ctk.CTkButton(bar, text=t("workflow.load_scheme"), width=92, height=30,
                                             command=self.load_selected_scheme)
        self.btn_load_scheme.grid(row=0, column=2, padx=4, pady=12)

        self.btn_save_scheme = ctk.CTkButton(bar, text=t("workflow.save_scheme"), width=130, height=30,
                                             fg_color=Colors.accent, hover_color=Colors.accent_hover,
                                             command=self.save_current_scheme_as)
        self.btn_save_scheme.grid(row=0, column=3, padx=4, pady=12)

        self.btn_delete_scheme = ctk.CTkButton(bar, text=t("workflow.delete_scheme"), width=120, height=30,
                                               fg_color=Colors.bg_card, border_color=Colors.error,
                                               border_width=1, hover_color=Colors.error,
                                               command=self.delete_selected_scheme)
        self.btn_delete_scheme.grid(row=0, column=4, padx=4, pady=12)

        self.btn_reset_scheme = ctk.CTkButton(bar, text=t("workflow.reset_scheme"), width=92, height=30,
                                              fg_color=Colors.bg_card, border_color=Colors.border,
                                              border_width=1, command=self.reset_workflow)
        self.btn_reset_scheme.grid(row=0, column=5, padx=(4, 12), pady=12)

    def create_workflow_form(self, initial_config):
        initial_config = normalize_workflow_config(initial_config)
        self.workflow_inputs.clear()
        self.workflow_specs.clear()
        self.workflow_value_labels.clear()
        self.crop_canvas = None
        self.crop_preview_label = None
        self.crop_preview_geometry = None
        self.crop_drag_handle = None
        self.time_trim_canvas = None
        self.time_trim_start_canvas = None
        self.time_trim_end_canvas = None
        self.time_trim_label = None
        self.time_trim_geometry = None
        self.time_trim_drag_handle = None
        self.workflow_visibility_state = self.get_workflow_visibility_state(initial_config)
        self.workflow_config_snapshot = initial_config

        for section in WORKFLOW_SECTIONS:
            visible_fields = [
                field for field in section["fields"]
                if self.is_workflow_field_visible(field, initial_config)
            ]
            if not visible_fields:
                continue

            section_frame = ctk.CTkFrame(self.scroll_frame, fg_color=Colors.bg_card, corner_radius=Metrics.radius,
                                         border_width=1, border_color=Colors.border)
            section_frame.pack(fill="x", pady=(0, 12))
            section_frame.grid_columnconfigure(0, weight=1)
            section_frame.grid_columnconfigure(1, weight=0)

            section_title_widget = ctk.CTkLabel(section_frame, text=section_title(section), font=("Segoe UI", 15, "bold"),
                                         text_color=Colors.accent, anchor="w")
            section_title_widget.grid(row=0, column=0, columnspan=2, padx=14, pady=(12, 2), sticky="ew")

            section_desc = ctk.CTkLabel(section_frame, text=section_description(section), font=Fonts.body,
                                        text_color=Colors.text_secondary, anchor="w", justify="left",
                                        wraplength=820)
            section_desc.grid(row=1, column=0, columnspan=2, padx=14, pady=(0, 10), sticky="ew")

            for index, spec in enumerate(visible_fields, start=2):
                self.add_workflow_field(section_frame, index, spec, initial_config.get(spec["key"], DEFAULT_WORKFLOW_CONFIG.get(spec["key"])))

            if (
                initial_config["crop_mode"] == "manual"
                and any(field["key"] == "crop_mode" for field in visible_fields)
            ):
                preview_row = len(visible_fields) + 2
                self.create_crop_preview(section_frame, preview_row)
            if (
                initial_config["trim_mode"] != "none"
                and any(field["key"] == "trim_mode" for field in visible_fields)
            ):
                preview_row = len(visible_fields) + 2
                self.create_time_trim_preview(section_frame, preview_row)

        self.update_crop_preview()
        self.update_time_trim_preview()
        self.update_command_preview()

    def get_workflow_visibility_state(self, config):
        config = normalize_workflow_config(config)
        return (
            is_audio_output_format(config["output_container"]),
            is_gif_output_format(config["output_container"]),
            config["resolution_mode"],
            config["crop_mode"],
            config["trim_mode"],
            config["audio_mode"],
            config["video_filter_1"],
            config["video_filter_2"],
            config["video_filter_3"],
            config["audio_filter_1"],
            config["audio_filter_2"],
            config["audio_filter_3"],
        )

    def is_workflow_field_visible(self, spec, config):
        config = normalize_workflow_config(config)
        key = spec["key"]
        video_filters = selected_video_filters(config)
        audio_filters = selected_audio_filters(config)
        if key in GIF_ONLY_FIELDS and not is_gif_output_format(config["output_container"]):
            return False
        if is_audio_output_format(config["output_container"]) and key in AUDIO_OUTPUT_HIDDEN_WORKFLOW_FIELDS:
            return False
        if is_gif_output_format(config["output_container"]) and key in {"quality_profile", "encoding_speed", "video_codec", "fps_mode", "audio_mode", "audio_quality"}:
            return False
        if is_gif_output_format(config["output_container"]) and key in AUDIO_FILTER_FIELDS:
            return False
        if (
            config["audio_mode"] == "mute"
            and key in AUDIO_FILTER_FIELDS
            and not is_audio_output_format(config["output_container"])
        ):
            return False
        if key in RESOLUTION_PARAMETER_FIELDS and config["resolution_mode"] != "custom":
            return False
        if key in CROP_PARAMETER_FIELDS and config["crop_mode"] != "manual":
            return False
        if key in TRIM_SECONDS_FIELDS and config["trim_mode"] != "seconds":
            return False
        if key in TRIM_FRAME_FIELDS and config["trim_mode"] != "frames":
            return False
        if key in VIDEO_EQ_FIELDS and "eq" not in video_filters:
            return False
        if key in VIDEO_DENOISE_FIELDS and "denoise" not in video_filters:
            return False
        if key in VIDEO_SHARPEN_FIELDS and "sharpen" not in video_filters:
            return False
        if key in VIDEO_TEXT_FIELDS and "drawtext" not in video_filters:
            return False
        if key in AUDIO_HIGHPASS_FIELDS and "highpass" not in audio_filters:
            return False
        if key in AUDIO_LOWPASS_FIELDS and "lowpass" not in audio_filters:
            return False
        if key in AUDIO_FADE_FIELDS and "afade" not in audio_filters:
            return False
        return True

    def add_workflow_field(self, parent, row, spec, value):
        key = spec["key"]
        self.workflow_specs[key] = spec

        text_frame = ctk.CTkFrame(parent, fg_color="transparent")
        text_frame.grid(row=row, column=0, padx=14, pady=8, sticky="ew")
        text_frame.grid_columnconfigure(0, weight=1)

        label = ctk.CTkLabel(text_frame, text=field_label(spec), font=Fonts.subheading,
                             text_color=Colors.text_primary, anchor="w")
        label.grid(row=0, column=0, sticky="ew")

        description = ctk.CTkLabel(text_frame, text=field_description(spec), font=Fonts.small,
                                   text_color=Colors.text_secondary, anchor="w", justify="left",
                                   wraplength=780)
        description.grid(row=1, column=0, sticky="ew", pady=(2, 0))

        control_frame = ctk.CTkFrame(parent, fg_color="transparent", width=300)
        control_frame.grid(row=row, column=1, padx=14, pady=8, sticky="e")

        if spec["type"] == "choice":
            labels = option_labels(spec["options"])
            combo = ctk.CTkComboBox(control_frame, values=labels, width=300, height=30,
                                    command=lambda _value: self.on_workflow_changed())
            combo.set(option_label(spec["options"], value))
            combo.pack(fill="x")
            self.workflow_inputs[key] = combo
        elif spec["type"] == "slider":
            value_row = ctk.CTkFrame(control_frame, fg_color="transparent")
            value_row.pack(fill="x")
            value_label = ctk.CTkLabel(value_row, text=self.format_slider_value(value), font=Fonts.subheading,
                                       text_color=Colors.accent, width=48, anchor="e")
            value_label.pack(side="right")
            slider = ctk.CTkSlider(
                control_frame,
                from_=spec.get("min", 0),
                to=spec.get("max", 100),
                number_of_steps=spec.get("steps", 100),
                width=300,
                command=lambda new_value, field_key=key: self.on_slider_changed(field_key, new_value)
            )
            slider.set(float(value))
            slider.pack(fill="x", pady=(4, 0))
            self.workflow_inputs[key] = slider
            self.workflow_value_labels[key] = value_label
        else:
            entry = ctk.CTkEntry(control_frame, width=300, height=30, font=Fonts.body)
            entry.insert(0, str(value))
            entry.bind("<KeyRelease>", lambda _event: self.on_workflow_changed())
            entry.pack(fill="x")
            self.workflow_inputs[key] = entry

    def on_slider_changed(self, key, value):
        if key in self.workflow_value_labels:
            self.workflow_value_labels[key].configure(text=self.format_slider_value(value))
        self.on_workflow_changed()

    def on_workflow_changed(self):
        settings = self.get_workflow_settings()
        self.workflow_config_snapshot = settings
        self.app_state["workflow_settings"] = settings
        visibility_state = self.get_workflow_visibility_state(settings)
        if visibility_state != self.workflow_visibility_state:
            for child in self.scroll_frame.winfo_children():
                child.destroy()
            self.create_workflow_form(settings)
            self.app_state["workflow_settings"] = self.get_workflow_settings()
            return
        self.update_crop_preview()
        self.update_time_trim_preview()
        self.update_command_preview()

    def format_slider_value(self, value):
        value = float(value)
        return f"{int(value)}" if value.is_integer() else f"{value:.1f}"

    def create_crop_preview(self, parent, row):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, columnspan=2, padx=14, pady=(4, 14), sticky="ew")
        frame.grid_columnconfigure(0, weight=1)

        title_row = ctk.CTkFrame(frame, fg_color="transparent")
        title_row.grid(row=0, column=0, pady=(4, 4), sticky="ew")
        title_row.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(title_row, text=t("crop.preview_title"), font=("Segoe UI", 15, "bold"),
                             text_color=Colors.accent, anchor="w")
        title.grid(row=0, column=0, sticky="ew")

        self.btn_random_crop_frame = ctk.CTkButton(
            title_row,
            text=t("crop.preview_random_frame"),
            width=110,
            height=26,
            fg_color=Colors.bg_card,
            border_color=Colors.border,
            border_width=1,
            command=self.reload_crop_preview_frame
        )
        self.btn_random_crop_frame.grid(row=0, column=1, padx=(8, 0), sticky="e")

        self.crop_canvas = Canvas(frame, width=420, height=250, bg=Colors.bg_dark,
                                  highlightthickness=1, highlightbackground=Colors.border)
        self.crop_canvas.grid(row=1, column=0, pady=(6, 8))
        self.crop_canvas.bind("<ButtonPress-1>", self.on_crop_canvas_press)
        self.crop_canvas.bind("<B1-Motion>", self.on_crop_canvas_drag)
        self.crop_canvas.bind("<ButtonRelease-1>", self.on_crop_canvas_release)

        self.crop_preview_label = ctk.CTkLabel(frame, text="", font=Fonts.small,
                                               text_color=Colors.text_secondary, anchor="w",
                                               justify="left", wraplength=820)
        self.crop_preview_label.grid(row=2, column=0, pady=(0, 4), sticky="ew")

    def create_time_trim_preview(self, parent, row):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, columnspan=2, padx=14, pady=(4, 14), sticky="ew")
        frame.grid_columnconfigure(0, weight=0)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, weight=0)

        title = ctk.CTkLabel(frame, text=t("trim.preview_title"), font=("Segoe UI", 15, "bold"),
                             text_color=Colors.accent, anchor="w")
        title.grid(row=0, column=0, columnspan=3, pady=(4, 4), sticky="ew")

        self.time_trim_start_canvas = Canvas(frame, width=190, height=120, bg=Colors.bg_dark,
                                             highlightthickness=1, highlightbackground=Colors.border)
        self.time_trim_start_canvas.grid(row=1, column=0, padx=(0, 12), pady=(6, 8), sticky="w")

        self.time_trim_canvas = Canvas(frame, width=560, height=120, bg=Colors.bg_dark,
                                       highlightthickness=1, highlightbackground=Colors.border)
        self.time_trim_canvas.grid(row=1, column=1, pady=(6, 8))
        self.time_trim_canvas.bind("<ButtonPress-1>", self.on_time_trim_canvas_press)
        self.time_trim_canvas.bind("<B1-Motion>", self.on_time_trim_canvas_drag)
        self.time_trim_canvas.bind("<ButtonRelease-1>", self.on_time_trim_canvas_release)

        self.time_trim_end_canvas = Canvas(frame, width=190, height=120, bg=Colors.bg_dark,
                                           highlightthickness=1, highlightbackground=Colors.border)
        self.time_trim_end_canvas.grid(row=1, column=2, padx=(12, 0), pady=(6, 8), sticky="e")

        self.time_trim_label = ctk.CTkLabel(frame, text="", font=Fonts.small,
                                            text_color=Colors.text_secondary, anchor="w",
                                            justify="left", wraplength=980)
        self.time_trim_label.grid(row=2, column=0, columnspan=3, pady=(0, 4), sticky="ew")

    def get_first_video_path(self):
        for path in self.files:
            info = self.files_info.get(path)
            if info and getattr(info, "width", 0) and getattr(info, "height", 0):
                return path
        return None

    def reload_crop_preview_frame(self):
        path = self.get_first_video_path()
        if path:
            self.request_crop_preview_frame(path, force=True)
        self.update_crop_preview()

    def clear_media_previews(self):
        self.request_crop_preview_frame(None)
        self.clear_time_trim_frame_previews()

    def clear_preview_cache_files(self):
        preview_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "preview_cache")
        if os.path.isdir(preview_dir):
            for name in os.listdir(preview_dir):
                if name == "crop_preview.png" or name.startswith("crop_preview_") or name.startswith("time_trim_"):
                    path = os.path.join(preview_dir, name)
                    if os.path.isfile(path):
                        try:
                            os.remove(path)
                        except OSError:
                            pass

    def request_crop_preview_frame(self, path, force=False):
        if not path:
            self.crop_preview_request_id += 1
            self.crop_preview_source_path = None
            self.crop_preview_image = None
            self.crop_preview_loading = False
            self.crop_preview_error_path = None
        else:
            if not force and path == self.crop_preview_source_path and self.crop_preview_image:
                return
            if not force and path == self.crop_preview_source_path and self.crop_preview_loading:
                return
            if not force and path == self.crop_preview_error_path:
                return

            self.crop_preview_request_id += 1
            request_id = self.crop_preview_request_id
            self.crop_preview_source_path = path
            self.crop_preview_image = None
            self.crop_preview_loading = True
            self.crop_preview_error_path = None
            thread = threading.Thread(
                target=self.extract_random_crop_frame,
                args=(request_id, path),
                daemon=True,
            )
            thread.start()

    def extract_random_crop_frame(self, request_id, path):
        info = self.files_info.get(path)
        duration = float(getattr(info, "duration", 0) or 0)
        timestamp = random.uniform(0, max(duration - 0.2, 0.0)) if duration > 0.3 else 0

        preview_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "preview_cache")
        os.makedirs(preview_dir, exist_ok=True)
        output_path = os.path.join(preview_dir, f"crop_preview_{request_id}.png")
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass

        cmd = [
            WorkflowVideoTask.get_ffmpeg_path(self.get_ffmpeg_path_setting()),
            "-y",
            "-ss", f"{timestamp:.3f}",
            "-i", path,
            "-frames:v", "1",
            "-vf", "scale=376:206:force_original_aspect_ratio=decrease",
            output_path
        ]

        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo,
                timeout=20,
                check=True
            )
            success = True
        except Exception as e:
            print(f"Failed to extract crop preview frame: {e}")
            success = False

        def apply_crop_preview_frame():
            if request_id == self.crop_preview_request_id:
                self.crop_preview_loading = False
                if success and os.path.exists(output_path):
                    try:
                        self.crop_preview_image = PhotoImage(file=output_path)
                        self.crop_preview_error_path = None
                    except Exception as e:
                        print(f"Failed to load crop preview frame: {e}")
                        self.crop_preview_image = None
                        self.crop_preview_error_path = path
                else:
                    self.crop_preview_image = None
                    self.crop_preview_error_path = path
                self.update_crop_preview()

        try:
            self.after(0, apply_crop_preview_frame)
        except Exception as e:
            print(f"Failed to schedule crop preview update: {e}")

    def update_crop_preview(self):
        if not self.crop_canvas or not self.crop_preview_label:
            return

        try:
            settings = self.get_workflow_settings()
        except Exception:
            settings = DEFAULT_WORKFLOW_CONFIG.copy()

        source_w = 1920
        source_h = 1080
        has_real_size = False
        for path in self.files:
            info = self.files_info.get(path)
            if info and getattr(info, "width", 0) and getattr(info, "height", 0):
                source_w = int(info.width)
                source_h = int(info.height)
                has_real_size = True
                break

        path = self.get_first_video_path()
        if path:
            self.request_crop_preview_frame(path)
        else:
            self.request_crop_preview_frame(None)

        if settings.get("crop_mode") != "manual":
            left = right = top = bottom = 0
        else:
            left = int(settings.get("crop_left", 0))
            right = int(settings.get("crop_right", 0))
            top = int(settings.get("crop_top", 0))
            bottom = int(settings.get("crop_bottom", 0))

        left = min(left, source_w - 1)
        right = min(right, max(source_w - left - 1, 0))
        top = min(top, source_h - 1)
        bottom = min(bottom, max(source_h - top - 1, 0))
        crop_w = max(source_w - left - right, 1)
        crop_h = max(source_h - top - bottom, 1)

        canvas_w = 420
        canvas_h = 250
        if self.crop_preview_image:
            rect_w = self.crop_preview_image.width()
            rect_h = self.crop_preview_image.height()
            x0 = (canvas_w - rect_w) / 2
            y0 = (canvas_h - rect_h) / 2
            x1 = x0 + rect_w
            y1 = y0 + rect_h
            scale = min(rect_w / source_w, rect_h / source_h)
        else:
            margin = 22
            scale = min((canvas_w - margin * 2) / source_w, (canvas_h - margin * 2) / source_h)
            rect_w = source_w * scale
            rect_h = source_h * scale
            x0 = (canvas_w - rect_w) / 2
            y0 = (canvas_h - rect_h) / 2
            x1 = x0 + rect_w
            y1 = y0 + rect_h

        crop_x0 = x0 + left * scale
        crop_y0 = y0 + top * scale
        crop_x1 = x1 - right * scale
        crop_y1 = y1 - bottom * scale

        self.crop_canvas.delete("all")
        if self.crop_preview_image:
            self.crop_canvas.create_image(x0, y0, image=self.crop_preview_image, anchor="nw")
        else:
            self.crop_canvas.create_rectangle(x0, y0, x1, y1, fill="#111318", outline="")
        self.crop_canvas.create_rectangle(x0, y0, x1, y1, outline=Colors.text_secondary, width=2)
        self.crop_canvas.create_rectangle(crop_x0, crop_y0, crop_x1, crop_y1, outline=Colors.success, width=3)
        self.draw_crop_handles(crop_x0, crop_y0, crop_x1, crop_y1)
        self.crop_canvas.create_text(x0 + 8, y0 + 10, text=f"{source_w}x{source_h}", anchor="nw",
                                     fill=Colors.text_secondary, font=("Segoe UI", 9))
        self.crop_canvas.create_text(crop_x0 + 8, crop_y0 + 10, text=f"{crop_w}x{crop_h}", anchor="nw",
                                     fill=Colors.success, font=("Segoe UI", 10, "bold"))
        self.crop_preview_geometry = {
            "source_w": source_w,
            "source_h": source_h,
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "scale": scale,
            "left": left,
            "right": right,
            "top": top,
            "bottom": bottom,
        }

        info_text = t(
            "crop.preview_info",
            source_w=source_w,
            source_h=source_h,
            crop_w=crop_w,
            crop_h=crop_h,
            left=left,
            right=right,
            top=top,
            bottom=bottom,
        )
        if not has_real_size:
            info_text = f"{t('crop.preview_no_file')}\n{info_text}"
        if self.crop_preview_loading:
            info_text = f"{t('crop.preview_loading')}\n{info_text}"
        self.crop_preview_label.configure(text=info_text)

    def update_time_trim_preview(self):
        if not self.time_trim_canvas or not self.time_trim_label:
            return

        try:
            settings = self.get_workflow_settings()
        except Exception:
            settings = DEFAULT_WORKFLOW_CONFIG.copy()

        duration = 60.0
        fps = 30.0
        has_real_duration = False
        for path in self.files:
            info = self.files_info.get(path)
            info_duration = float(getattr(info, "duration", 0) or 0)
            if info_duration > 0:
                duration = info_duration
                fps = float(getattr(info, "fps", 0) or 0) or 30.0
                has_real_duration = True
                break

        start_seconds, end_seconds = self.get_time_trim_seconds(settings, duration, fps)
        keep_seconds = max(duration - start_seconds - end_seconds, 0.0)
        frame_step = 1.0 / fps if fps > 0 else 0.033
        last_frame_seconds = max(duration - frame_step, 0.0)
        start_preview_seconds = min(max(start_seconds, 0.0), last_frame_seconds)
        end_preview_seconds = duration - end_seconds - frame_step
        end_preview_seconds = min(max(end_preview_seconds, start_preview_seconds), last_frame_seconds)

        canvas_w = 560
        canvas_h = 120
        x0 = 34
        x1 = canvas_w - 34
        y0 = 46
        y1 = 82
        scale = (x1 - x0) / duration if duration > 0 else 1
        keep_x0 = x0 + start_seconds * scale
        keep_x1 = x1 - end_seconds * scale
        keep_x1 = max(keep_x1, keep_x0 + 2)

        self.time_trim_canvas.delete("all")
        self.time_trim_canvas.create_rectangle(x0, y0, x1, y1, fill="#111318", outline=Colors.text_secondary, width=2)
        if keep_x0 > x0:
            self.time_trim_canvas.create_rectangle(x0, y0, keep_x0, y1, fill="#3a2228", outline="")
        if keep_x1 < x1:
            self.time_trim_canvas.create_rectangle(keep_x1, y0, x1, y1, fill="#3a2228", outline="")
        self.time_trim_canvas.create_rectangle(keep_x0, y0, keep_x1, y1, fill="#1f332e", outline=Colors.success, width=3)

        self.draw_time_trim_handle("start", keep_x0, (y0 + y1) / 2)
        self.draw_time_trim_handle("end", keep_x1, (y0 + y1) / 2)

        self.time_trim_canvas.create_text(x0, y1 + 16, text="0s", anchor="nw",
                                          fill=Colors.text_secondary, font=("Segoe UI", 9))
        self.time_trim_canvas.create_text(x1, y1 + 16, text=f"{self.format_seconds_value(duration)}s", anchor="ne",
                                          fill=Colors.text_secondary, font=("Segoe UI", 9))
        self.time_trim_canvas.create_text((keep_x0 + keep_x1) / 2, y0 - 14,
                                          text=f"{self.format_seconds_value(keep_seconds)}s",
                                          anchor="center", fill=Colors.success, font=("Segoe UI", 10, "bold"))

        self.time_trim_geometry = {
            "duration": duration,
            "fps": fps,
            "x0": x0,
            "x1": x1,
            "start_seconds": start_seconds,
            "end_seconds": end_seconds,
            "start_preview_seconds": start_preview_seconds,
            "end_preview_seconds": end_preview_seconds,
        }

        info_text = t(
            "trim.preview_info",
            start_seconds=self.format_seconds_value(start_seconds),
            end_seconds=self.format_seconds_value(end_seconds),
            start_frames=int(round(start_seconds * fps)),
            end_frames=int(round(end_seconds * fps)),
            keep_seconds=self.format_seconds_value(keep_seconds),
        )
        if not has_real_duration:
            info_text = f"{t('trim.preview_no_file')}\n{info_text}"
        self.time_trim_label.configure(text=info_text)

        video_path = self.get_first_video_path()
        if video_path and has_real_duration:
            self.schedule_time_trim_frame_previews(
                video_path,
                start_preview_seconds,
                end_preview_seconds,
            )
        else:
            self.clear_time_trim_frame_previews()
        self.draw_time_trim_frame_previews(start_preview_seconds, end_preview_seconds)

    def clear_time_trim_frame_previews(self):
        if self.time_trim_start_after_id:
            try:
                self.after_cancel(self.time_trim_start_after_id)
            except Exception:
                pass
            self.time_trim_start_after_id = None
        if self.time_trim_end_after_id:
            try:
                self.after_cancel(self.time_trim_end_after_id)
            except Exception:
                pass
            self.time_trim_end_after_id = None

        self.time_trim_start_request_id += 1
        self.time_trim_end_request_id += 1
        self.time_trim_start_key = None
        self.time_trim_end_key = None
        self.time_trim_start_error_key = None
        self.time_trim_end_error_key = None
        self.time_trim_start_image = None
        self.time_trim_end_image = None
        self.time_trim_start_loading = False
        self.time_trim_end_loading = False

    def schedule_time_trim_frame_previews(self, path, start_seconds, end_seconds, force=False):
        ffmpeg_path = WorkflowVideoTask.get_ffmpeg_path(self.get_ffmpeg_path_setting())
        self.schedule_time_trim_frame_preview("start", ffmpeg_path, path, start_seconds, force)
        self.schedule_time_trim_frame_preview("end", ffmpeg_path, path, end_seconds, force)
        self.draw_time_trim_frame_previews(start_seconds, end_seconds)

    def schedule_time_trim_frame_preview(self, side, ffmpeg_path, path, seconds, force=False):
        key = (path, round(seconds, 3))
        if side == "start":
            current_key = self.time_trim_start_key
            image = self.time_trim_start_image
            loading = self.time_trim_start_loading
            error_key = self.time_trim_start_error_key
            after_id = self.time_trim_start_after_id
        elif side == "end":
            current_key = self.time_trim_end_key
            image = self.time_trim_end_image
            loading = self.time_trim_end_loading
            error_key = self.time_trim_end_error_key
            after_id = self.time_trim_end_after_id
        else:
            return

        if not force and key == current_key and image:
            return
        if not force and key == current_key and loading:
            return
        if not force and key == error_key:
            return

        if key != current_key:
            if side == "start":
                self.time_trim_start_request_id += 1
                self.time_trim_start_key = key
                self.time_trim_start_image = None
                self.time_trim_start_loading = True
            elif side == "end":
                self.time_trim_end_request_id += 1
                self.time_trim_end_key = key
                self.time_trim_end_image = None
                self.time_trim_end_loading = True

        if after_id:
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
            if side == "start":
                self.time_trim_start_after_id = None
            elif side == "end":
                self.time_trim_end_after_id = None

        if force:
            self.request_time_trim_frame_preview(side, ffmpeg_path, path, seconds, key)
        else:
            after_id = self.after(
                180,
                lambda: self.request_time_trim_frame_preview(
                    side,
                    ffmpeg_path,
                    path,
                    seconds,
                    key,
                ),
            )
            if side == "start":
                self.time_trim_start_after_id = after_id
            elif side == "end":
                self.time_trim_end_after_id = after_id

    def request_time_trim_frame_preview(self, side, ffmpeg_path, path, seconds, key):
        if side == "start":
            self.time_trim_start_after_id = None
            self.time_trim_start_request_id += 1
            request_id = self.time_trim_start_request_id
            self.time_trim_start_key = key
            self.time_trim_start_loading = True
        elif side == "end":
            self.time_trim_end_after_id = None
            self.time_trim_end_request_id += 1
            request_id = self.time_trim_end_request_id
            self.time_trim_end_key = key
            self.time_trim_end_loading = True
        else:
            return

        thread = threading.Thread(
            target=self.extract_time_trim_frame_preview,
            args=(side, request_id, ffmpeg_path, path, seconds, key),
            daemon=True,
        )
        thread.start()

    def extract_time_trim_frame_preview(self, side, request_id, ffmpeg_path, path, seconds, key):
        preview_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "preview_cache")
        os.makedirs(preview_dir, exist_ok=True)
        output_path = os.path.join(preview_dir, f"time_trim_{request_id}_{side}.png")
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass

        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        timestamps = [max(seconds, 0.0)]
        if side == "end":
            for offset in (0.08, 0.2, 0.5, 1.0):
                fallback_timestamp = max(seconds - offset, 0.0)
                if fallback_timestamp not in timestamps:
                    timestamps.append(fallback_timestamp)

        success = False
        for timestamp in timestamps:
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            cmd = [
                ffmpeg_path,
                "-y",
                "-ss", f"{timestamp:.3f}",
                "-i", path,
                "-frames:v", "1",
                "-vf", "scale=188:86:force_original_aspect_ratio=decrease",
                output_path,
            ]
            try:
                subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    startupinfo=startupinfo,
                    timeout=20,
                    check=True,
                )
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    success = True
                    break
            except Exception as e:
                print(f"Failed to extract time trim preview frame: {e}")

        def apply_time_trim_frame_preview():
            if side == "start":
                if request_id == self.time_trim_start_request_id and key == self.time_trim_start_key:
                    self.time_trim_start_loading = False
                    if success and os.path.exists(output_path):
                        try:
                            self.time_trim_start_image = PhotoImage(file=output_path)
                            self.time_trim_start_error_key = None
                        except Exception as e:
                            print(f"Failed to load time trim preview frame: {e}")
                            self.time_trim_start_image = None
                            self.time_trim_start_error_key = key
                    else:
                        self.time_trim_start_image = None
                        self.time_trim_start_error_key = key
            elif side == "end":
                if request_id == self.time_trim_end_request_id and key == self.time_trim_end_key:
                    self.time_trim_end_loading = False
                    if success and os.path.exists(output_path):
                        try:
                            self.time_trim_end_image = PhotoImage(file=output_path)
                            self.time_trim_end_error_key = None
                        except Exception as e:
                            print(f"Failed to load time trim preview frame: {e}")
                            self.time_trim_end_image = None
                            self.time_trim_end_error_key = key
                    else:
                        self.time_trim_end_image = None
                        self.time_trim_end_error_key = key

            if self.time_trim_geometry:
                self.draw_time_trim_frame_previews(
                    self.time_trim_geometry["start_preview_seconds"],
                    self.time_trim_geometry["end_preview_seconds"],
                )

        try:
            self.after(0, apply_time_trim_frame_preview)
        except Exception as e:
            print(f"Failed to schedule time trim preview update: {e}")

    def draw_time_trim_frame_previews(self, start_seconds, end_seconds):
        if not self.time_trim_start_canvas or not self.time_trim_end_canvas:
            return

        self.draw_time_trim_frame_preview(
            self.time_trim_start_canvas,
            self.time_trim_start_image,
            t("trim.preview_start_frame"),
            start_seconds,
            self.time_trim_start_loading,
        )
        self.draw_time_trim_frame_preview(
            self.time_trim_end_canvas,
            self.time_trim_end_image,
            t("trim.preview_end_frame"),
            end_seconds,
            self.time_trim_end_loading,
        )

    def draw_time_trim_frame_preview(self, canvas, image, title, seconds, loading):
        canvas_w = 190
        canvas_h = 120
        canvas.delete("all")
        canvas.create_rectangle(0, 0, canvas_w, canvas_h, fill="#111318", outline=Colors.border)

        if image:
            x = (canvas_w - image.width()) / 2
            y = 24 + (72 - image.height()) / 2
            canvas.create_image(x, y, image=image, anchor="nw")
        else:
            canvas.create_rectangle(8, 26, canvas_w - 8, 96, fill=Colors.bg_dark, outline=Colors.border)
            message = t("trim.preview_frame_loading") if loading else t("trim.preview_frame_no_file")
            canvas.create_text(
                canvas_w / 2,
                61,
                text=message,
                anchor="center",
                fill=Colors.text_secondary,
                font=("Segoe UI", 9),
                width=160,
            )

        canvas.create_rectangle(0, 0, canvas_w, 22, fill=Colors.bg_card, outline="")
        canvas.create_text(8, 11, text=title, anchor="w", fill=Colors.accent, font=("Segoe UI", 9, "bold"))
        canvas.create_rectangle(0, 100, canvas_w, canvas_h, fill="#111318", outline="")
        canvas.create_text(
            canvas_w / 2,
            110,
            text=f"{self.format_seconds_value(seconds)}s",
            anchor="center",
            fill=Colors.success,
            font=("Segoe UI", 9, "bold"),
        )

    def get_time_trim_seconds(self, settings, duration, fps):
        if settings.get("trim_mode") == "frames":
            start_seconds = int(settings.get("trim_start_frames", 0) or 0) / fps if fps > 0 else 0.0
            end_seconds = int(settings.get("trim_end_frames", 0) or 0) / fps if fps > 0 else 0.0
        elif settings.get("trim_mode") == "seconds":
            start_seconds = float(settings.get("trim_start_seconds", 0) or 0)
            end_seconds = float(settings.get("trim_end_seconds", 0) or 0)
        else:
            start_seconds = 0.0
            end_seconds = 0.0

        start_seconds = min(max(start_seconds, 0.0), max(duration - 0.001, 0.0))
        end_seconds = min(max(end_seconds, 0.0), max(duration - start_seconds - 0.001, 0.0))
        return start_seconds, end_seconds

    def draw_time_trim_handle(self, handle, x, y):
        radius = 7
        self.time_trim_canvas.create_line(x, y - 24, x, y + 24, fill=Colors.success, width=3,
                                          tags=("time_trim_handle", f"handle:{handle}"))
        self.time_trim_canvas.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill=Colors.success,
            outline="#ffffff",
            width=1,
            tags=("time_trim_handle", f"handle:{handle}")
        )

    def on_time_trim_canvas_press(self, event):
        self.time_trim_drag_handle = self.find_time_trim_handle(event.x, event.y)

    def on_time_trim_canvas_drag(self, event):
        if not self.time_trim_drag_handle or not self.time_trim_geometry:
            return

        geom = self.time_trim_geometry
        duration = geom["duration"]
        x0 = geom["x0"]
        x1 = geom["x1"]
        x = min(max(event.x, x0), x1)
        span = max(x1 - x0, 1)
        min_keep = min(0.001, duration)

        start_seconds = geom["start_seconds"]
        end_seconds = geom["end_seconds"]

        if self.time_trim_drag_handle == "start":
            start_seconds = ((x - x0) / span) * duration
            start_seconds = min(max(start_seconds, 0.0), max(duration - end_seconds - min_keep, 0.0))
        elif self.time_trim_drag_handle == "end":
            end_seconds = ((x1 - x) / span) * duration
            end_seconds = min(max(end_seconds, 0.0), max(duration - start_seconds - min_keep, 0.0))

        self.set_time_trim_values(start_seconds, end_seconds, geom["fps"])

    def on_time_trim_canvas_release(self, _event):
        handle = self.time_trim_drag_handle
        self.time_trim_drag_handle = None
        if self.time_trim_geometry:
            path = self.get_first_video_path()
            if path:
                ffmpeg_path = WorkflowVideoTask.get_ffmpeg_path(self.get_ffmpeg_path_setting())
                if handle == "start":
                    self.schedule_time_trim_frame_preview(
                        "start",
                        ffmpeg_path,
                        path,
                        self.time_trim_geometry["start_preview_seconds"],
                        force=True,
                    )
                elif handle == "end":
                    self.schedule_time_trim_frame_preview(
                        "end",
                        ffmpeg_path,
                        path,
                        self.time_trim_geometry["end_preview_seconds"],
                        force=True,
                    )
                else:
                    self.schedule_time_trim_frame_previews(
                        path,
                        self.time_trim_geometry["start_preview_seconds"],
                        self.time_trim_geometry["end_preview_seconds"],
                        force=True,
                    )
                self.draw_time_trim_frame_previews(
                    self.time_trim_geometry["start_preview_seconds"],
                    self.time_trim_geometry["end_preview_seconds"],
                )

    def find_time_trim_handle(self, x, y):
        closest = self.time_trim_canvas.find_closest(x, y)
        if not closest:
            return None

        item = closest[0]
        tags = self.time_trim_canvas.gettags(item)
        if "time_trim_handle" not in tags:
            return None

        bbox = self.time_trim_canvas.bbox(item)
        if not bbox:
            return None
        x0, y0, x1, y1 = bbox
        if x < x0 - 8 or x > x1 + 8 or y < y0 - 8 or y > y1 + 8:
            return None

        for tag in tags:
            if tag.startswith("handle:"):
                return tag.split(":", 1)[1]
        return None

    def set_time_trim_values(self, start_seconds, end_seconds, fps):
        settings = self.get_workflow_settings()
        mode = settings.get("trim_mode")
        if mode not in ("seconds", "frames"):
            mode = "seconds"

        self.set_workflow_field_value("trim_mode", mode)
        self.set_workflow_field_value("trim_start_seconds", self.format_seconds_value(start_seconds))
        self.set_workflow_field_value("trim_end_seconds", self.format_seconds_value(end_seconds))
        self.set_workflow_field_value("trim_start_frames", int(round(start_seconds * fps)))
        self.set_workflow_field_value("trim_end_frames", int(round(end_seconds * fps)))
        self.on_workflow_changed()

    def format_seconds_value(self, value):
        value = max(float(value or 0), 0.0)
        if abs(value - round(value)) < 0.005:
            return str(int(round(value)))
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def draw_crop_handles(self, x0, y0, x1, y1):
        handle_points = {
            "nw": (x0, y0),
            "n": ((x0 + x1) / 2, y0),
            "ne": (x1, y0),
            "e": (x1, (y0 + y1) / 2),
            "se": (x1, y1),
            "s": ((x0 + x1) / 2, y1),
            "sw": (x0, y1),
            "w": (x0, (y0 + y1) / 2),
        }
        radius = 5
        for handle, (x, y) in handle_points.items():
            self.crop_canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill=Colors.success,
                outline="#ffffff",
                width=1,
                tags=("crop_handle", f"handle:{handle}")
            )

    def on_crop_canvas_press(self, event):
        self.crop_drag_handle = self.find_crop_handle(event.x, event.y)

    def on_crop_canvas_drag(self, event):
        if not self.crop_drag_handle or not self.crop_preview_geometry:
            return

        geom = self.crop_preview_geometry
        x = min(max(event.x, geom["x0"]), geom["x1"])
        y = min(max(event.y, geom["y0"]), geom["y1"])
        scale = geom["scale"] or 1

        left = geom["left"]
        right = geom["right"]
        top = geom["top"]
        bottom = geom["bottom"]
        source_w = geom["source_w"]
        source_h = geom["source_h"]
        handle = self.crop_drag_handle

        if "w" in handle:
            left = round((x - geom["x0"]) / scale)
            left = min(max(left, 0), source_w - right - 1)
        if "e" in handle:
            right = round((geom["x1"] - x) / scale)
            right = min(max(right, 0), source_w - left - 1)
        if "n" in handle:
            top = round((y - geom["y0"]) / scale)
            top = min(max(top, 0), source_h - bottom - 1)
        if "s" in handle:
            bottom = round((geom["y1"] - y) / scale)
            bottom = min(max(bottom, 0), source_h - top - 1)

        self.set_crop_values(left, right, top, bottom)

    def on_crop_canvas_release(self, _event):
        self.crop_drag_handle = None

    def find_crop_handle(self, x, y):
        closest = self.crop_canvas.find_closest(x, y)
        if not closest:
            return None

        item = closest[0]
        tags = self.crop_canvas.gettags(item)
        if "crop_handle" not in tags:
            return None

        bbox = self.crop_canvas.bbox(item)
        if not bbox:
            return None
        x0, y0, x1, y1 = bbox
        if x < x0 - 6 or x > x1 + 6 or y < y0 - 6 or y > y1 + 6:
            return None

        for tag in tags:
            if tag.startswith("handle:"):
                return tag.split(":", 1)[1]
        return None

    def set_crop_values(self, left, right, top, bottom):
        self.set_workflow_field_value("crop_mode", "manual")
        self.set_workflow_field_value("crop_left", left)
        self.set_workflow_field_value("crop_right", right)
        self.set_workflow_field_value("crop_top", top)
        self.set_workflow_field_value("crop_bottom", bottom)
        self.on_workflow_changed()

    def set_workflow_field_value(self, key, value):
        widget = self.workflow_inputs.get(key)
        spec = self.workflow_specs.get(key)
        if not widget or not spec:
            return

        if spec["type"] == "choice":
            widget.set(option_label(spec["options"], value))
        elif spec["type"] == "slider":
            widget.set(float(value))
            if key in self.workflow_value_labels:
                self.workflow_value_labels[key].configure(text=self.format_slider_value(value))
        else:
            widget.delete(0, "end")
            widget.insert(0, str(value))

    def get_saved_schemes(self):
        schemes = self.app_state.setdefault("workflow_schemes", {})
        return schemes if isinstance(schemes, dict) else {}

    def get_scheme_names(self):
        return [scheme_label(name) for name in BUILTIN_SCHEMES.keys()] + sorted(self.get_saved_schemes().keys())

    def refresh_scheme_combo(self, selected=None):
        names = self.get_scheme_names()
        self.scheme_combo.configure(values=names)
        if selected:
            selected_name = scheme_value(selected)
            selected_label = scheme_label(selected_name) if selected_name in BUILTIN_SCHEMES else selected_name
            if selected_label in names:
                self.workflow_scheme_var.set(selected_label)

    def load_selected_scheme(self):
        name = scheme_value(self.workflow_scheme_var.get())
        saved = self.get_saved_schemes()

        if name in saved:
            config = normalize_workflow_config(saved[name])
        else:
            name = name if name in BUILTIN_SCHEMES else DEFAULT_BUILTIN_SCHEME
            config = get_builtin_scheme(name)
            self.workflow_scheme_var.set(scheme_label(name))

        self.set_workflow_settings(config)
        self.app_state["workflow_scheme_name"] = name
        self.app_state["workflow_settings"] = self.get_workflow_settings()
        self.save_state()

    def reset_workflow(self):
        self.workflow_scheme_var.set(scheme_label(DEFAULT_BUILTIN_SCHEME))
        self.set_workflow_settings(get_builtin_scheme(DEFAULT_BUILTIN_SCHEME))
        self.app_state["workflow_scheme_name"] = DEFAULT_BUILTIN_SCHEME
        self.app_state["workflow_settings"] = self.get_workflow_settings()
        self.save_state()

    def save_current_scheme_as(self):
        name = simpledialog.askstring(t("workflow.save_prompt_title"), t("workflow.save_prompt"), parent=self)
        if not name:
            return

        name = name.strip()
        if not name:
            return

        if scheme_value(name) in BUILTIN_SCHEMES:
            messagebox.showwarning(t("workflow.save_prompt_title"), t("workflow.save_name_conflict"))
            return

        self.get_saved_schemes()[name] = self.get_workflow_settings()
        self.app_state["workflow_scheme_name"] = name
        self.save_state()
        self.refresh_scheme_combo(selected=name)

    def delete_selected_scheme(self):
        name = scheme_value(self.workflow_scheme_var.get())
        saved = self.get_saved_schemes()

        if name in BUILTIN_SCHEMES:
            messagebox.showinfo(t("workflow.delete_title"), t("workflow.delete_builtin"))
            return
        if name not in saved:
            return
        if not messagebox.askyesno(t("workflow.delete_title"), t("workflow.delete_confirm", name=name)):
            return

        del saved[name]
        self.refresh_scheme_combo(selected=DEFAULT_BUILTIN_SCHEME)
        self.reset_workflow()

    def get_workflow_settings(self):
        values = {
            **DEFAULT_WORKFLOW_CONFIG,
            **(getattr(self, "workflow_config_snapshot", None) or self.app_state.get("workflow_settings") or {}),
        }
        for key, widget in self.workflow_inputs.items():
            spec = self.workflow_specs[key]
            if spec["type"] == "choice":
                values[key] = option_value(spec["options"], widget.get())
            elif spec["type"] == "slider":
                values[key] = float(widget.get())
            else:
                raw = widget.get().strip()
                if spec.get("value_type") == "int":
                    try:
                        values[key] = int(float(raw.replace(",", ".")))
                    except ValueError:
                        values[key] = DEFAULT_WORKFLOW_CONFIG.get(key)
                elif spec.get("value_type") == "float":
                    try:
                        values[key] = float(raw.replace(",", "."))
                    except ValueError:
                        values[key] = DEFAULT_WORKFLOW_CONFIG.get(key)
                else:
                    values[key] = raw
        return normalize_workflow_config(values)

    def set_workflow_settings(self, settings):
        config = normalize_workflow_config(settings)
        if self.get_workflow_visibility_state(config) != self.workflow_visibility_state:
            for child in self.scroll_frame.winfo_children():
                child.destroy()
            self.create_workflow_form(config)
            self.app_state["workflow_settings"] = self.get_workflow_settings()
            return

        for key, widget in self.workflow_inputs.items():
            spec = self.workflow_specs[key]
            value = config.get(key, DEFAULT_WORKFLOW_CONFIG.get(key))

            if spec["type"] == "choice":
                widget.set(option_label(spec["options"], value))
            elif spec["type"] == "slider":
                widget.set(float(value))
                if key in self.workflow_value_labels:
                    self.workflow_value_labels[key].configure(text=self.format_slider_value(value))
            else:
                widget.delete(0, "end")
                widget.insert(0, str(value))
        self.workflow_config_snapshot = config
        self.update_crop_preview()
        self.update_time_trim_preview()
        self.update_command_preview()

    def build_file_context(self, path):
        duration = 0
        has_audio = True
        width = 0
        height = 0
        fps = 0
        if path in self.files_info:
            info = self.files_info[path]
            duration = info.duration
            width = int(getattr(info, "width", 0) or 0)
            height = int(getattr(info, "height", 0) or 0)
            fps = float(getattr(info, "fps", 0) or 0)
            probe_has_data = any([
                getattr(info, "duration", 0),
                getattr(info, "width", 0),
                getattr(info, "height", 0),
                getattr(info, "fps", 0),
                getattr(info, "v_codec", ""),
                getattr(info, "a_codec", ""),
                getattr(info, "size", 0),
                getattr(info, "bitrate", "")
            ])
            if probe_has_data:
                has_audio = bool(getattr(info, "a_codec", ""))
        return duration, has_audio, width, height, fps

    def update_command_preview(self):
        if not hasattr(self, "command_preview_text"):
            return

        try:
            settings = self.get_workflow_settings()
            run_settings = settings.copy()
            run_settings["use_gpu"] = self.gpu_var.get() if hasattr(self, "gpu_var") else False
            run_settings["ffmpeg_path"] = self.get_ffmpeg_path_setting()

            input_file = self.files[0] if self.files else "input.ext"
            if self.files:
                duration, has_audio, width, height, fps = self.build_file_context(input_file)
            else:
                duration = 10
                has_audio = True
                width = 1920
                height = 1080
                fps = 30

            run_settings["duration"] = duration
            run_settings["has_audio"] = has_audio
            run_settings["source_width"] = width
            run_settings["source_height"] = height
            run_settings["source_fps"] = fps
            cmd = WorkflowVideoTask().build_command(input_file, run_settings)
            text = subprocess.list2cmdline(cmd)
        except Exception as e:
            text = t("workflow.command_preview_error", error=e)

        self.command_preview_text.delete("1.0", "end")
        self.command_preview_text.insert("1.0", text)

    def create_console_overlay(self):
        self.console_frame = ctk.CTkFrame(self, fg_color=Colors.bg_dark)

        self.console_title = ctk.CTkLabel(self.console_frame, text=t("console.processing"), font=Fonts.heading, text_color=Colors.text_primary)
        self.console_title.pack(pady=(20, 10))

        self.progress_bar = ctk.CTkProgressBar(self.console_frame, width=400, height=10, progress_color=Colors.success)
        self.progress_bar.pack(pady=(0, 20))
        self.progress_bar.set(0)

        self.console_text = ctk.CTkTextbox(self.console_frame, font=Fonts.mono, text_color="#eeeeee", fg_color="#000000")
        self.console_text.pack(fill="both", expand=True, padx=20, pady=10)

        self.btn_close_console = ctk.CTkButton(self.console_frame, text=t("console.close_stop"), fg_color=Colors.error, command=self.stop_or_close_task)
        self.btn_close_console.pack(pady=20)

    def process_input_paths(self, paths):
        previous_preview_path = self.get_first_video_path()
        added = 0
        for path in expand_input_paths(paths):
            added += self.process_input_path(path, update_previews=False)
        if added:
            if previous_preview_path != self.get_first_video_path():
                self.clear_media_previews()
            self.update_crop_preview()
            self.update_time_trim_preview()
            self.update_command_preview()
        return added

    def process_input_path(self, path, update_previews=True):
        previous_preview_path = self.get_first_video_path()
        self.apply_ffmpeg_path_setting(self.get_ffmpeg_path_setting())
        path = str(path or "").strip()
        if not path:
            return 0

        found = scan_path(path)
        added = 0
        for f in found:
            if f not in self.files:
                self.files.append(f)
                info = MediaProber.probe(f, self.get_ffmpeg_path_setting())
                self.files_info[f] = info
                self.file_list.add_file(f, info=info)
                added += 1
        if update_previews and added:
            if previous_preview_path != self.get_first_video_path():
                self.clear_media_previews()
            self.update_crop_preview()
            self.update_time_trim_preview()
            self.update_command_preview()
        return added

    def add_files_dialog(self):
        filepaths = filedialog.askopenfilenames()
        self.process_input_paths(filepaths)

    def add_dir_dialog(self):
        dirpath = filedialog.askdirectory()
        if dirpath:
            self.process_input_paths(dirpath)

    def remove_file(self, path):
        if path in self.files:
            previous_preview_path = self.get_first_video_path()
            self.files.remove(path)
            if path in self.files_info:
                del self.files_info[path]
            self.file_list.remove_file(path)
            if previous_preview_path != self.get_first_video_path():
                self.clear_media_previews()
            self.update_crop_preview()
            self.update_time_trim_preview()
            self.update_command_preview()

    def run_workflow(self):
        if self.ffmpeg_installing:
            messagebox.showwarning("FFmpeg download", "FFmpeg is downloading. Please wait until it finishes.")
            return

        if not self.files:
            messagebox.showwarning(t("workflow.no_files_title"), t("workflow.no_files"))
            return

        settings = self.get_workflow_settings()
        self.app_state["workflow_settings"] = settings
        self.app_state["workflow_scheme_name"] = scheme_value(self.workflow_scheme_var.get())
        self.save_state()

        task_instance = WorkflowVideoTask()
        run_settings = settings.copy()
        run_settings["use_gpu"] = self.gpu_var.get()
        run_settings["ffmpeg_path"] = self.get_ffmpeg_path_setting()

        commands = []
        durations = []
        for f in self.files:
            try:
                duration, has_audio, width, height, fps = self.build_file_context(f)

                file_settings = run_settings.copy()
                file_settings["duration"] = duration
                file_settings["has_audio"] = has_audio
                file_settings["source_width"] = width
                file_settings["source_height"] = height
                file_settings["source_fps"] = fps

                print(f"Building command for {f} with settings: {file_settings}")
                cmd = task_instance.build_command(f, file_settings)
                print(f"Built command: {cmd}")

                commands.append(cmd)
                durations.append(task_instance.get_output_duration(file_settings))

            except Exception as e:
                print(f"Error building command for {f}: {e}")
                import traceback
                traceback.print_exc()

        if not commands:
            messagebox.showerror(t("workflow.no_commands_title"), t("workflow.no_commands"))
            return

        self.console_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.console_text.delete("1.0", "end")
        self.btn_close_console.configure(text=t("console.stop"), fg_color=Colors.error)

        self.runner.run_commands(commands, durations)

    def update_progress(self, percent):
        def _update():
            self.progress_bar.set(percent)
        self.after(0, _update)

    def update_console(self, text):
        def _update():
            self.console_text.insert("end", text)
            self.console_text.see("end")
        self.after(0, _update)

    def stop_or_close_task(self):
        if self.runner.running:
            self.runner.stop()
            self.console_text.insert("end", t("console.stopped"))
            self.btn_close_console.configure(text=t("console.close_view"), fg_color=Colors.accent)
        else:
            self.console_frame.place_forget()
            if self.runner.stopped or not self.runner.running:
                 self.quit()

    def on_task_complete(self, success):
        def _finish():
            if success:
                self.console_text.insert("end", t("console.done"))
                self.btn_close_console.configure(text=t("console.close_app"), fg_color=Colors.success, command=self.quit)
                self.after(2000, self.quit)
            else:
                self.console_text.insert("end", t("console.finished"))
                self.btn_close_console.configure(text=t("console.close_view"), fg_color=Colors.accent, command=lambda: self.console_frame.place_forget())

        self.after(0, _finish)

    def load_state(self):
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    self.app_state = json.load(f)
            else:
                self.app_state = {}
        except Exception:
            self.app_state = {}

    def save_state(self):
        try:
            self.app_state["language"] = get_language()
            if hasattr(self, "ffmpeg_path_var"):
                ffmpeg_path = self.ffmpeg_path_var.get().strip().strip('"') or DEFAULT_FFMPEG_PATH
                self.ffmpeg_path_var.set(ffmpeg_path)
                self.app_state["ffmpeg_path"] = ffmpeg_path
                self.apply_ffmpeg_path_setting(ffmpeg_path)
            if hasattr(self, 'gpu_var'):
                self.app_state["use_gpu"] = self.gpu_var.get()
            if getattr(self, "workflow_inputs", None):
                self.app_state["workflow_settings"] = self.get_workflow_settings()
                if hasattr(self, "workflow_scheme_var"):
                    self.app_state["workflow_scheme_name"] = scheme_value(self.workflow_scheme_var.get())
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.app_state, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save state: {e}")

    def on_closing(self):
        self.save_state()
        self.destroy()
