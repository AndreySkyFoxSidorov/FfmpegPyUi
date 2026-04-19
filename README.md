# FfmpegPyUi

FfmpegPyUi is a desktop GUI for FFmpeg that turns "I need the right command line for this video" into "drop files here, pick a scheme, press the button, pretend you always knew the flags."

It is built with Python, CustomTkinter, TkinterDnD, and a healthy respect for how many FFmpeg options a human can remember before lunch.

## What It Does

- Batch-process video and audio files from a friendly desktop interface.
- Add files one by one, add whole folders, or drag-and-drop media into the queue.
- Read media details with `ffprobe`: duration, resolution, codecs, size, bitrate, and FPS.
- Run FFmpeg in the background while showing console output and progress.
- Save local preferences without making your Git history smell like machine-specific config.
- Use a local `./ffmpeg` folder by default, or point the app at another FFmpeg installation.

## Built-In Video Schemes

The app includes practical presets for common video chores:

- **MP4 for sharing**: a sensible default when the file needs to work almost everywhere.
- **Small file**: when your upload limit is rude and your patience is limited.
- **High quality**: keeps more detail and asks your disk space to be brave.
- **Speed up 4x with sound**: useful for timelapses, reviews, and "please get to the point" footage.
- **Speed up 10x without sound**: for when the original audio is mostly fan noise and regret.
- **Square for WebGL**: crops and scales to a square output.
- **MOV for editing**: higher-quality MOV output for post-production workflows.

You can load a scheme, tweak it, and save your own version for later.

## Settings You Can Tweak

FfmpegPyUi exposes the useful FFmpeg knobs without making you write a spellbook:

- **Output container**: MP4 or MOV.
- **Resolution**: keep original, fit to 720p, fit to 1080p, square 720, or custom width and height.
- **Quality profile**: draft, small, balanced, high, or maximum.
- **Encoding speed**: faster processing or smaller files.
- **Video codec**: `libx264`, `libx265`, `h264_nvenc`, `hevc_nvenc`, `libvpx-vp9`, or `copy`.
- **NVIDIA GPU acceleration**: optional NVENC mode if your GPU and FFmpeg build support it.
- **Crop**: no crop or manual crop values for left, right, top, and bottom.
- **Trim**: trim by seconds or by frame count.
- **FPS**: keep source FPS or force 24, 30, or 60 FPS.
- **Playback speed**: common speed multipliers like 2x, 4x, 8x, 10x, and 16x.
- **Audio mode**: keep audio, create a silent track when needed, or mute output.
- **Audio quality and volume**: choose bitrate presets and adjust volume from quiet to "why is this waveform a rectangle?"
- **Output suffix**: control how processed files are named.

## Extra Tools

Alongside the main workflow, the codebase includes smaller task helpers for:

- Converting media to MP3.
- Converting stereo MP3 to mono.
- Boosting WAV volume with a limiter.
- Creating WebGL-friendly MP4 files.
- Creating MOV files for editing.
- Extracting the first video frame.
- Extracting random preview frames.

## Requirements

- Python 3.10 or newer.
- FFmpeg and FFprobe.
- Python packages from `requirements.txt`:
  - `customtkinter`
  - `packaging`
  - `tkinterdnd2`

## FFmpeg Setup

By default, the app looks for FFmpeg in:

```text
./ffmpeg
```

That folder is intentionally ignored by Git. FFmpeg binaries are big, platform-specific, and not the kind of souvenir you want in every clone.

On Windows, this layout works well:

```text
ffmpeg/
  bin/
    ffmpeg.exe
    ffprobe.exe
```

You can also install FFmpeg somewhere else and choose that folder inside the app.

On Linux and macOS, a system FFmpeg from `PATH` can be used. If needed, select the folder manually in the sidebar.

## Installation

### Windows

```bat
setup.bat
```

Or install dependencies manually:

```bat
python -m pip install -r requirements.txt
```

### Linux / macOS

```bash
chmod +x setup.sh run.sh
./setup.sh
```

Or install dependencies manually:

```bash
python3 -m pip install -r requirements.txt
```

## Running

### Windows

```bat
run.bat
```

### Linux / macOS

```bash
./run.sh
```

You can also run the app directly:

```bash
python ffmpegpyui/main.py
```

Files can be passed as command-line arguments:

```bash
python ffmpegpyui/main.py path/to/video.mp4
```

## Testing

Run the test suite with:

```bash
python -m unittest discover -s tests
```

## Git Hygiene

The repository intentionally ignores local state, generated previews, caches, and local FFmpeg binaries:

- `/.agent/`
- `/ffmpeg/`
- `/ffmpegpyui/state.json`
- `/ffmpegpyui/preview_cache/`
- Python caches, virtual environments, build artifacts, coverage files, editor settings, and OS junk.

`ffmpegpyui/state.json` stores local app preferences. It belongs to your machine, not to your repo.

## Typical Workflow

1. Install dependencies.
2. Put FFmpeg in `./ffmpeg` or select your FFmpeg folder in the app.
3. Launch FfmpegPyUi.
4. Drop in videos.
5. Pick a scheme.
6. Adjust the settings.
7. Start processing.
8. Watch FFmpeg do the loud part while you take credit for the clean output.
