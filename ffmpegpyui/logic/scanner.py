import os

SUPPORTED_EXTENSIONS = {
    ".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".mpeg", ".mpg",
    ".gif",
    ".wav", ".mp3", ".aac", ".m4a", ".flac", ".ogg",
}


def scan_path(path):
    if os.path.isfile(path):
        return [path]

    found_files = []
    for root, _dirs, files in os.walk(path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                found_files.append(os.path.join(root, file))
    return found_files
