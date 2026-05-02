import hashlib
import json
import os
import platform as platform_module
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

try:
    from .ffmpeg_paths import normalize_ffmpeg_dir, resolve_ffmpeg_executable
except ImportError:
    from logic.ffmpeg_paths import normalize_ffmpeg_dir, resolve_ffmpeg_executable


FFMPEG_STABLE_VERSION = "8.1"
BTBN_RELEASE_API_URL = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/tags/latest"
BTBN_RELEASE_DOWNLOAD_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest"
BTBN_CHECKSUMS_URL = f"{BTBN_RELEASE_DOWNLOAD_URL}/checksums.sha256"
MARTIN_RIEDL_DOWNLOAD_URL = "https://ffmpeg.martin-riedl.de/redirect/latest/macos/arm64/release"
CHECKSUM_NEXT_TO_ARCHIVE = "archive-url-sha256"


class FfmpegInstallError(RuntimeError):
    pass


class FfmpegDownload:
    def __init__(self, name, url, checksum_url=None):
        self.name = name
        self.url = url
        self.checksum_url = checksum_url


def local_ffmpeg_available(ffmpeg_dir=None, platform=None):
    ffmpeg = resolve_ffmpeg_executable(ffmpeg_dir, "ffmpeg", platform=platform, fallback_to_path=False)
    ffprobe = resolve_ffmpeg_executable(ffmpeg_dir, "ffprobe", platform=platform, fallback_to_path=False)
    return os.path.exists(ffmpeg) and os.path.exists(ffprobe)


def system_ffmpeg_available():
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    return _can_run_version(ffmpeg) and _can_run_version(ffprobe)


def should_download_ffmpeg(ffmpeg_dir=None, platform=None, system_checker=None):
    if local_ffmpeg_available(ffmpeg_dir, platform=platform):
        return False

    checker = system_checker or system_ffmpeg_available
    if checker():
        return False

    return True


def ensure_ffmpeg_available(ffmpeg_dir=None, log_callback=None):
    target_dir = normalize_ffmpeg_dir(ffmpeg_dir)
    if should_download_ffmpeg(target_dir):
        return install_ffmpeg(target_dir, log_callback=log_callback)
    return target_dir


def install_ffmpeg(ffmpeg_dir=None, runtime_platform=None, machine=None, log_callback=None, release_assets=None):
    target_dir = normalize_ffmpeg_dir(ffmpeg_dir)
    downloads = ffmpeg_downloads_for_platform(
        runtime_platform=runtime_platform,
        machine=machine,
        release_assets=release_assets,
    )

    temp_dir = tempfile.mkdtemp(prefix="ffmpegpyui-")
    extract_dir = os.path.join(temp_dir, "extract")
    os.makedirs(extract_dir, exist_ok=True)

    try:
        for download in downloads:
            archive_path = os.path.join(temp_dir, download.name)
            _log(log_callback, f"Downloading {download.name}\n")
            archive_url = _download_file(download.url, archive_path)
            checksum_url = download.checksum_url
            if checksum_url == CHECKSUM_NEXT_TO_ARCHIVE:
                checksum_url = f"{archive_url}.sha256"
            if checksum_url:
                _log(log_callback, f"Verifying {download.name}\n")
                _verify_checksum(archive_path, download.name, checksum_url)
            _log(log_callback, f"Extracting {download.name}\n")
            _extract_archive(archive_path, extract_dir)

        _install_extracted_files(extract_dir, target_dir, runtime_platform)
        if not local_ffmpeg_available(target_dir, platform=runtime_platform):
            raise FfmpegInstallError("The downloaded archive did not contain both ffmpeg and ffprobe.")
        return target_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def ffmpeg_downloads_for_platform(runtime_platform=None, machine=None, release_assets=None):
    runtime_platform = runtime_platform or sys.platform
    machine = (machine or platform_module.machine()).lower()

    if runtime_platform.startswith("win"):
        platform_key = _btbn_arch_key("win", machine)
        return [_btbn_download_for_platform(platform_key, ".zip", release_assets)]

    if runtime_platform.startswith("linux"):
        platform_key = _btbn_arch_key("linux", machine)
        return [_btbn_download_for_platform(platform_key, ".tar.xz", release_assets)]

    if runtime_platform == "darwin" and machine in {"arm64", "aarch64"}:
        return [
            FfmpegDownload(
                "ffmpeg.zip",
                f"{MARTIN_RIEDL_DOWNLOAD_URL}/ffmpeg.zip",
                CHECKSUM_NEXT_TO_ARCHIVE,
            ),
            FfmpegDownload(
                "ffprobe.zip",
                f"{MARTIN_RIEDL_DOWNLOAD_URL}/ffprobe.zip",
                CHECKSUM_NEXT_TO_ARCHIVE,
            ),
        ]

    raise FfmpegInstallError(
        f"Automatic FFmpeg download is not available for {runtime_platform} on {machine}."
    )


def _can_run_version(path):
    if not path:
        return False

    try:
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        result = subprocess.run(
            [path, "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo,
            timeout=8,
        )
        return result.returncode == 0
    except Exception:
        return False


def _btbn_arch_key(os_name, machine):
    if machine in {"x86_64", "amd64"}:
        return f"{os_name}64"
    if machine in {"arm64", "aarch64"}:
        return f"{os_name}arm64"
    raise FfmpegInstallError(f"Unsupported FFmpeg build architecture: {machine}.")


def _btbn_download_for_platform(platform_key, extension, release_assets=None):
    asset = _find_latest_stable_btbn_asset(platform_key, extension, release_assets)
    if asset:
        return FfmpegDownload(asset["name"], asset["url"], BTBN_CHECKSUMS_URL)

    name = f"ffmpeg-n{FFMPEG_STABLE_VERSION}-latest-{platform_key}-gpl-shared-{FFMPEG_STABLE_VERSION}{extension}"
    return FfmpegDownload(name, f"{BTBN_RELEASE_DOWNLOAD_URL}/{name}", BTBN_CHECKSUMS_URL)


def _find_latest_stable_btbn_asset(platform_key, extension, release_assets=None):
    assets = release_assets
    if assets is None:
        assets = _fetch_btbn_assets()

    pattern = re.compile(
        rf"^ffmpeg-n(\d+(?:\.\d+)*)-latest-{re.escape(platform_key)}-gpl-shared-\1{re.escape(extension)}$"
    )
    best_asset = None
    best_version = ()

    for asset in assets:
        name = _asset_name(asset)
        match = pattern.match(name)
        if match:
            version = tuple(int(part) for part in match.group(1).split("."))
            if best_asset is None or version > best_version:
                best_asset = {
                    "name": name,
                    "url": _asset_url(asset, name),
                }
                best_version = version

    return best_asset


def _fetch_btbn_assets():
    request = urllib.request.Request(BTBN_RELEASE_API_URL, headers={"User-Agent": "FfmpegPyUi"})
    with urllib.request.urlopen(request, timeout=30) as response:
        release = json.loads(response.read().decode("utf-8"))
    return release.get("assets", [])


def _asset_name(asset):
    if isinstance(asset, dict):
        return str(asset.get("name") or "")
    return str(asset)


def _asset_url(asset, name):
    if isinstance(asset, dict) and asset.get("browser_download_url"):
        return str(asset["browser_download_url"])
    return f"{BTBN_RELEASE_DOWNLOAD_URL}/{name}"


def _download_file(url, destination):
    request = urllib.request.Request(url, headers={"User-Agent": "FfmpegPyUi"})
    with urllib.request.urlopen(request, timeout=60) as response:
        with open(destination, "wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        return response.geturl()


def _verify_checksum(archive_path, archive_name, checksum_url):
    expected = _expected_checksum(archive_name, checksum_url)
    if not expected:
        raise FfmpegInstallError(f"Checksum for {archive_name} was not found.")

    digest = hashlib.sha256()
    with open(archive_path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)

    if digest.hexdigest().lower() != expected.lower():
        raise FfmpegInstallError(f"Checksum verification failed for {archive_name}.")


def _expected_checksum(archive_name, checksum_url):
    request = urllib.request.Request(checksum_url, headers={"User-Agent": "FfmpegPyUi"})
    with urllib.request.urlopen(request, timeout=30) as response:
        content = response.read().decode("utf-8")

    for line in content.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[-1] == archive_name:
            return parts[0]
    return None


def _extract_archive(archive_path, destination):
    if archive_path.endswith(".zip"):
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(destination)
    elif archive_path.endswith(".tar.xz"):
        with tarfile.open(archive_path, "r:xz") as archive:
            archive.extractall(destination)
    else:
        raise FfmpegInstallError(f"Unsupported FFmpeg archive: {archive_path}.")


def _install_extracted_files(extract_dir, target_dir, runtime_platform=None):
    runtime_platform = runtime_platform or sys.platform
    ffmpeg_name = "ffmpeg.exe" if runtime_platform.startswith("win") else "ffmpeg"
    ffprobe_name = "ffprobe.exe" if runtime_platform.startswith("win") else "ffprobe"

    tree_root = _find_extracted_tree_root(extract_dir, ffmpeg_name, ffprobe_name)
    if tree_root:
        _merge_directory(tree_root, target_dir)
    else:
        bin_dir = os.path.join(target_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(_find_extracted_file(extract_dir, ffmpeg_name), os.path.join(bin_dir, ffmpeg_name))
        shutil.copy2(_find_extracted_file(extract_dir, ffprobe_name), os.path.join(bin_dir, ffprobe_name))

    if not runtime_platform.startswith("win"):
        for name in (ffmpeg_name, ffprobe_name):
            path = os.path.join(target_dir, "bin", name)
            if os.path.exists(path):
                os.chmod(path, os.stat(path).st_mode | 0o755)


def _find_extracted_tree_root(extract_dir, ffmpeg_name, ffprobe_name):
    for root, _dirs, _files in os.walk(extract_dir):
        bin_dir = os.path.join(root, "bin")
        if (
            os.path.exists(os.path.join(bin_dir, ffmpeg_name))
            and os.path.exists(os.path.join(bin_dir, ffprobe_name))
        ):
            return root
    return None


def _find_extracted_file(extract_dir, file_name):
    for root, _dirs, files in os.walk(extract_dir):
        if file_name in files:
            return os.path.join(root, file_name)
    raise FfmpegInstallError(f"{file_name} was not found in the downloaded archive.")


def _merge_directory(source_dir, target_dir):
    os.makedirs(target_dir, exist_ok=True)
    for name in os.listdir(source_dir):
        source_path = os.path.join(source_dir, name)
        target_path = os.path.join(target_dir, name)
        if os.path.isdir(source_path):
            _merge_directory(source_path, target_path)
        else:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy2(source_path, target_path)


def _log(log_callback, text):
    if log_callback:
        log_callback(text)
