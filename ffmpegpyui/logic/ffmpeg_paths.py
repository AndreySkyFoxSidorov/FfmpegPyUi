import os
import sys


def project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def default_ffmpeg_dir():
    return os.path.join(project_root(), "ffmpeg")


def normalize_ffmpeg_dir(path):
    value = str(path or "").strip().strip('"')
    if not value:
        return default_ffmpeg_dir()

    value = os.path.expandvars(os.path.expanduser(value))
    if not os.path.isabs(value):
        value = os.path.join(project_root(), value)
    return os.path.normpath(value)


def _executable_name(executable, platform=None):
    name = executable[:-4] if executable.lower().endswith(".exe") else executable
    if (platform or sys.platform).startswith("win"):
        return f"{name}.exe"
    return name


def _executable_stem(path):
    name = os.path.basename(path).lower()
    return name[:-4] if name.endswith(".exe") else name


def _resolve_from_file(file_path, executable, platform=None):
    requested_name = _executable_name(executable, platform)
    requested_stem = _executable_stem(requested_name)
    current_stem = _executable_stem(file_path)

    if current_stem == requested_stem:
        return file_path

    if current_stem in {"ffmpeg", "ffprobe"} and requested_stem in {"ffmpeg", "ffprobe"}:
        sibling = os.path.join(os.path.dirname(file_path), requested_name)
        if os.path.exists(sibling):
            return sibling

    return executable[:-4] if executable.lower().endswith(".exe") else executable


def resolve_ffmpeg_executable(ffmpeg_dir=None, executable="ffmpeg", platform=None, fallback_to_path=True):
    platform = platform or sys.platform

    base_path = normalize_ffmpeg_dir(ffmpeg_dir)
    exe_name = _executable_name(executable, platform)

    if os.path.isfile(base_path):
        return _resolve_from_file(base_path, executable, platform)

    candidates = [
        os.path.join(base_path, "bin", exe_name),
        os.path.join(base_path, exe_name),
    ]

    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    if fallback_to_path:
        return executable[:-4] if executable.lower().endswith(".exe") else executable
    return candidates[0]
