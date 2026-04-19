import os

SUPPORTED_EXTENSIONS = {
    '.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.mpeg', '.mpg', 
    '.wav', '.mp3', '.aac', '.m4a', '.flac', '.ogg'
}

def scan_path(path):
    """
    Returns a list of file paths.
    If path is a file, returns [path].
    If path is a directory, recursively finds all supported files.
    """
    if os.path.isfile(path):
        return [path]
    
    found_files = []
    for root, dirs, files in os.walk(path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                found_files.append(os.path.join(root, file))
    return found_files
