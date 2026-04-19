@echo off
set "SCRIPT_DIR=%~dp0"
python "%SCRIPT_DIR%ffmpegpyui\main.py" %*
if %ERRORLEVEL% NEQ 0 pause
