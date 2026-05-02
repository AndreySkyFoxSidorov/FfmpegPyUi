@echo off
set "SCRIPT_DIR=%~dp0"
start pythonw "%SCRIPT_DIR%ffmpegpyui\main.py" %*

