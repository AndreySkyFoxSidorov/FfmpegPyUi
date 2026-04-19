import sys
import os
import customtkinter as ctk
from tkinterdnd2 import TkinterDnD

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.app import FfmpegApp
from logic.input_paths import expand_input_paths

def main():
    # Set default theme
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    # Parse args (dropped files via OS shell)
    files = expand_input_paths(sys.argv[1:]) if len(sys.argv) > 1 else []

    app = FfmpegApp(files=files)
    app.mainloop()

if __name__ == "__main__":
    main()
