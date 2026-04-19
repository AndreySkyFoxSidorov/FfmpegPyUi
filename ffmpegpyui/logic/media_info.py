import os
import sys
import subprocess
import json
import logging

try:
    from .ffmpeg_paths import normalize_ffmpeg_dir, resolve_ffmpeg_executable
except ImportError:
    from logic.ffmpeg_paths import normalize_ffmpeg_dir, resolve_ffmpeg_executable

class MediaInfo:
    def __init__(self, duration=0, width=0, height=0, v_codec="", a_codec="", size=0, bitrate="", fps=0):
        self.duration = duration
        self.width = width
        self.height = height
        self.v_codec = v_codec
        self.a_codec = a_codec
        self.size = size # bytes
        self.bitrate = bitrate
        self.fps = fps

    def __str__(self):
        # Format: "1080p | h264 | 24MB | 5kbps | 00:02:30"
        parts = []
        if self.width and self.height:
            parts.append(f"{self.width}x{self.height}")
        if self.v_codec:
            parts.append(self.v_codec)
        if self.size:
            mb = self.size / (1024 * 1024)
            parts.append(f"{mb:.1f}MB")
        if self.bitrate:
            parts.append(f"{self.bitrate}")
        if self.duration:
            m, s = divmod(int(self.duration), 60)
            h, m = divmod(m, 60)
            parts.append(f"{h:02d}:{m:02d}:{s:02d}")
        
        return " | ".join(parts)

class MediaProber:
    _ffmpeg_dir = None

    @classmethod
    def set_ffmpeg_dir(cls, ffmpeg_dir):
        cls._ffmpeg_dir = normalize_ffmpeg_dir(ffmpeg_dir)

    @classmethod
    def get_ffprobe_path(cls, ffmpeg_dir=None):
        return resolve_ffmpeg_executable(ffmpeg_dir or cls._ffmpeg_dir, "ffprobe")

    @staticmethod
    def probe(file_path, ffmpeg_dir=None):
        """
        Runs ffprobe and returns a MediaInfo object.
        """
        ffprobe = MediaProber.get_ffprobe_path(ffmpeg_dir)
        if not os.path.exists(ffprobe) and sys.platform == "win32":
            # Fallback if not found in local dir, maybe in PATH
            ffprobe = "ffprobe"

        cmd = [
            ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]

        try:
            # On Windows, hide console
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                startupinfo=startupinfo,
                check=True
            )
            
            data = json.loads(result.stdout)
            return MediaProber._parse_json(data)

        except Exception as e:
            print(f"Error probing {file_path}: {e}")
            return MediaInfo()

    @staticmethod
    def _parse_json(data):
        info = MediaInfo()
        
        # Format (Duration, Size, Bitrate)
        try:
            if "format" in data:
                fmt = data["format"]
                info.duration = float(fmt.get("duration", 0))
                info.size = int(fmt.get("size", 0))
                br = int(fmt.get("bit_rate", 0))
                if br > 0:
                    if br > 1000000:
                        info.bitrate = f"{br/1000000:.1f}Mbps"
                    else:
                        info.bitrate = f"{br/1000:.0f}kbps"
        except:
            pass

        # Streams
        if "streams" in data:
            for stream in data["streams"]:
                codec_type = stream.get("codec_type")
                if codec_type == "video":
                    info.v_codec = stream.get("codec_name", "")
                    info.width = int(stream.get("width", 0))
                    info.height = int(stream.get("height", 0))
                    info.fps = MediaProber._parse_frame_rate(
                        stream.get("avg_frame_rate") or stream.get("r_frame_rate")
                    )
                elif codec_type == "audio" and not info.a_codec:
                    info.a_codec = stream.get("codec_name", "")
        
        return info

    @staticmethod
    def _parse_frame_rate(value):
        if not value or value in ("0/0", "N/A"):
            return 0
        try:
            if "/" in str(value):
                numerator, denominator = str(value).split("/", 1)
                denominator = float(denominator)
                if denominator == 0:
                    return 0
                return float(numerator) / denominator
            return float(value)
        except (TypeError, ValueError):
            return 0
