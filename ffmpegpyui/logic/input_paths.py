import os
import re
import shlex


def expand_input_paths(raw_paths):
    paths = []
    if raw_paths is None:
        return paths

    if isinstance(raw_paths, str):
        items = [raw_paths]
    else:
        items = list(raw_paths)

    for item in items:
        paths.extend(_split_input_item(item))

    result = []
    seen = set()
    for path in paths:
        normalized = _clean_path(path)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _split_input_item(item):
    text = str(item or "").strip()
    if not text:
        return []

    cleaned = _clean_path(text)
    if os.path.exists(cleaned):
        return [cleaned]

    if "{" in text and "}" in text:
        matches = re.findall(r"\{([^}]*)\}|(\S+)", text)
        parsed = [braced or plain for braced, plain in matches]
        if parsed:
            return parsed

    if "\n" in text or "\r" in text:
        return [line for line in re.split(r"[\r\n]+", text) if line.strip()]

    try:
        parsed = shlex.split(text, posix=False)
    except ValueError:
        parsed = []

    if len(parsed) > 1:
        return parsed
    return [text]


def _clean_path(path):
    path = str(path or "").strip()
    pairs = {'"': '"', "'": "'", "{": "}"}
    while len(path) >= 2 and path[0] in pairs and path[-1] == pairs[path[0]]:
        path = path[1:-1].strip()
    return os.path.expandvars(os.path.expanduser(path))
