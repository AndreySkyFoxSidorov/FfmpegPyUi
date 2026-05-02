import os
import random

try:
    from .ffmpeg_paths import normalize_ffmpeg_dir, resolve_ffmpeg_executable
except ImportError:
    from logic.ffmpeg_paths import normalize_ffmpeg_dir, resolve_ffmpeg_executable


class TaskParameter:
    def __init__(self, name, label, default, param_type="entry", options=None, min_val=0, max_val=100, description=None):
        self.name = name
        self.label = label
        self.default = default
        self.type = param_type  # entry, checkbox, choice, slider
        self.options = options or []
        self.min_val = min_val
        self.max_val = max_val
        self.description = description

class BaseTask:
    name = "BaseTask"
    params = []
    _ffmpeg_dir = None

    @classmethod
    def set_ffmpeg_dir(cls, ffmpeg_dir):
        BaseTask._ffmpeg_dir = normalize_ffmpeg_dir(ffmpeg_dir)

    @classmethod
    def get_ffmpeg_path(cls, ffmpeg_dir=None):
        return resolve_ffmpeg_executable(ffmpeg_dir or BaseTask._ffmpeg_dir, "ffmpeg")

    def build_command(self, input_file, settings):
        raise NotImplementedError

    @staticmethod
    def _to_float(value, default=1.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def get_speed_multiplier(self, settings):
        speed = settings.get("speed", "1x")
        if isinstance(speed, str):
            speed = speed.strip().lower().replace("x", "")
        speed = self._to_float(speed, 1.0)
        return speed if speed > 0 else 1.0

    def wants_audio_output(self, settings, default=True):
        return bool(settings.get("include_audio", default))

    def needs_silent_audio(self, settings, default=True):
        return self.wants_audio_output(settings, default=default) and not settings.get("has_audio", True)

    def get_speed_video_filter(self, settings):
        speed = self.get_speed_multiplier(settings)
        if abs(speed - 1.0) < 1e-9:
            return None
        return f"setpts=PTS/{speed:g}"

    def get_speed_audio_filters(self, settings):
        speed = self.get_speed_multiplier(settings)
        if abs(speed - 1.0) < 1e-9:
            return []

        filters = []
        remaining = speed
        while remaining > 2.0 + 1e-9:
            filters.append("atempo=2")
            remaining /= 2.0

        if abs(remaining - 1.0) > 1e-9:
            filters.append(f"atempo={remaining:g}")

        return filters

    @staticmethod
    def combine_filters(*filters):
        parts = []
        for flt in filters:
            if not flt:
                continue
            if isinstance(flt, (list, tuple)):
                parts.extend(str(part) for part in flt if part)
            else:
                parts.append(str(flt))
        return ",".join(parts)

    def add_filter_args(self, cmd, video_filters=None, audio_filters=None):
        video_filter = self.combine_filters(video_filters)
        audio_filter = self.combine_filters(audio_filters)

        if video_filter:
            cmd.extend(["-vf", video_filter])
        if audio_filter:
            cmd.extend(["-filter:a", audio_filter])

    def add_silent_audio_input(self, cmd, settings, default=True, channel_layout="stereo", sample_rate=48000):
        if self.needs_silent_audio(settings, default=default):
            cmd.extend([
                "-f", "lavfi",
                "-i", f"anullsrc=channel_layout={channel_layout}:sample_rate={sample_rate}"
            ])

    def add_stream_maps(self, cmd, settings, default_audio=True):
        cmd.extend(["-map", "0:v:0"])
        if self.wants_audio_output(settings, default=default_audio):
            if self.needs_silent_audio(settings, default=default_audio):
                cmd.extend(["-map", "1:a:0"])
            else:
                cmd.extend(["-map", "0:a:0?"])

    def add_shortest_if_needed(self, cmd, settings, default_audio=True):
        if self.needs_silent_audio(settings, default=default_audio):
            cmd.append("-shortest")

    def decorate_output_path(self, output_path, settings):
        suffixes = []
        speed = self.get_speed_multiplier(settings)
        if abs(speed - 1.0) > 1e-9:
            suffixes.append(f"{speed:g}x")
        if "include_audio" in settings and not settings.get("include_audio", True):
            suffixes.append("mute")

        if not suffixes:
            return output_path

        base, ext = os.path.splitext(output_path)
        return f"{base}_{'_'.join(suffixes)}{ext}"

    def get_video_args(self, settings, default_codec="libx264", default_crf=23, default_preset="medium", requires_reencode=False):
        use_gpu = settings.get("use_gpu", False)
        codec = settings.get("codec_v", default_codec)
        preset = settings.get("preset", default_preset)
        crf = int(settings.get("crf", default_crf))

        args = []

        if codec == "copy" and requires_reencode:
            codec = default_codec

        if use_gpu and not settings.get("explicit_codec", False):
            if codec == "libx264":
                codec = "h264_nvenc"
            elif codec == "libx265":
                codec = "hevc_nvenc"

        args.extend(["-c:v", codec])

        if codec == "copy":
            return args

        if "nvenc" in codec:
            nv_preset = "p4"
            if preset in ["slow", "slower"]:
                nv_preset = "p6"
            elif preset == "veryslow":
                nv_preset = "p7"
            elif preset in ["fast", "faster"]:
                nv_preset = "p3"
            elif preset in ["superfast", "ultrafast"]:
                nv_preset = "p1"

            args.extend(["-preset", nv_preset])
            args.extend(["-rc", "vbr", "-cq", str(crf)])
            args.extend(["-pix_fmt", "yuv420p"])
        else:
            args.extend(["-preset", preset])
            args.extend(["-crf", str(crf)])
            args.extend(["-pix_fmt", "yuv420p"])

        return args

VIDEO_CODECS = ["libx264", "libx265", "libvpx-vp9", "copy"]
PRESETS = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]
AUDIO_BITRATES = ["64k", "128k", "160k", "192k", "256k", "320k"]
FPS_OPTIONS = ["23.976", "24", "25", "29.97", "30", "60"]
SPEED_OPTIONS = ["1x", "2x", "4x", "8x", "10x", "16x"]

class WAVToX2(BaseTask):
    name = "WAVToX2"
    params = [
        TaskParameter("volume", "Volume", 2.0, param_type="slider", min_val=0.5, max_val=5.0, description="Volume multiplier (2.0 = 200%)"),
        TaskParameter("limiter", "Limiter", 0.98, param_type="slider", min_val=0.1, max_val=1.0, description="Ceiling for the audio limiter to prevent clipping")
    ]

    def build_command(self, input_file, settings):
        out = f"{os.path.splitext(input_file)[0]}_x2.wav"
        vol = settings.get("volume", 2.0)
        lim = settings.get("limiter", 0.98)
        filter_str = f"volume={vol},alimiter=limit={lim}"
        return [
            self.get_ffmpeg_path(), "-y", "-i", input_file,
            "-af", filter_str, "-c:a", "pcm_s16le", out
        ]

class AllToWedGLandSound(BaseTask):
    name = "AllToWedGLandSound"
    params = [
        TaskParameter("speed", "Speed", "1x", param_type="choice", options=SPEED_OPTIONS, description="Video speed multiplier"),
        TaskParameter("include_audio", "With Sound", True, param_type="checkbox", description="Keep and process the audio track"),
        TaskParameter("scale_w", "Width", 320, param_type="entry", description="Target video width"),
        TaskParameter("scale_h", "Height", 320, param_type="entry", description="Target video height"),
        TaskParameter("audio_vol", "Audio Vol", 1.0, param_type="slider", min_val=0.0, max_val=3.0, description="Audio volume adjustment"),
        TaskParameter("audio_bitrate", "Audio Bitrate", "128k", param_type="choice", options=AUDIO_BITRATES, description="Audio quality/bitrate"),
        TaskParameter("preset", "Preset", "slow", param_type="choice", options=PRESETS, description="Encoding speed vs compression. Slower = smaller file."),
        TaskParameter("crf", "CRF", 22, param_type="slider", min_val=0, max_val=51, description="Quality factor (0-51). Lower is better quality. 18-28 is standard.")
    ]

    def build_command(self, input_file, settings):
        out = self.decorate_output_path(f"{os.path.splitext(input_file)[0]}_WebGl.mp4", settings)
        video_filters = [
            f"scale={settings.get('scale_w', 320)}:{settings.get('scale_h', 320)}",
            self.get_speed_video_filter(settings)
        ]

        audio_filters = []
        if self.wants_audio_output(settings):
            audio_filters.extend(self.get_speed_audio_filters(settings))
            audio_vol = self._to_float(settings.get("audio_vol", 1.0), 1.0)
            if abs(audio_vol - 1.0) > 1e-9:
                audio_filters.append(f"volume={audio_vol:g}")

        cmd = [self.get_ffmpeg_path(), "-y", "-i", input_file]
        self.add_silent_audio_input(cmd, settings)
        self.add_filter_args(cmd, video_filters=video_filters, audio_filters=audio_filters)
        self.add_stream_maps(cmd, settings)

        cmd.extend(self.get_video_args(settings, default_crf=22, default_preset="slow", requires_reencode=True))
        cmd.extend(["-profile:v", "main", "-level:v", "4.1", "-r", "29.976"])

        if self.wants_audio_output(settings):
            cmd.extend(["-c:a", "aac", "-b:a", settings.get("audio_bitrate", "128k")])
        else:
            cmd.append("-an")

        self.add_shortest_if_needed(cmd, settings)
        cmd.append(out)
        return cmd

class AllToMov(BaseTask):
    name = "AllToMov"
    params = [
        TaskParameter("speed", "Speed", "1x", param_type="choice", options=SPEED_OPTIONS, description="Video speed multiplier"),
        TaskParameter("include_audio", "With Sound", True, param_type="checkbox", description="Keep and process the audio track"),
        TaskParameter("crf", "CRF", 20, param_type="slider", min_val=0, max_val=51, description="Quality factor. Lower is better."),
        TaskParameter("audio_bitrate", "Audio Bitrate", "160k", param_type="choice", options=AUDIO_BITRATES, description="Audio bitrate"),
        TaskParameter("preset", "Preset", "slow", param_type="choice", options=PRESETS, description="Compression efficiency preset")
    ]

    def build_command(self, input_file, settings):
        base, _ = os.path.splitext(input_file)
        out = self.decorate_output_path(f"{base}_qt.mov", settings)

        video_filters = [
            "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            self.get_speed_video_filter(settings)
        ]
        audio_filters = self.get_speed_audio_filters(settings) if self.wants_audio_output(settings) else []

        cmd = [self.get_ffmpeg_path(), "-y", "-i", input_file]
        self.add_silent_audio_input(cmd, settings)
        self.add_filter_args(cmd, video_filters=video_filters, audio_filters=audio_filters)
        self.add_stream_maps(cmd, settings)
        cmd.extend(self.get_video_args(settings, default_crf=20, default_preset="slow", requires_reencode=True))

        cmd.extend([
            "-profile:v", "high", "-level:v", "4.1",
            "-r", "30", "-tag:v", "avc1"
        ])

        if self.wants_audio_output(settings):
            cmd.extend([
                "-c:a", "aac", "-b:a", settings.get("audio_bitrate", "160k"),
                "-ac", "2", "-ar", "48000"
            ])
        else:
            cmd.append("-an")

        self.add_shortest_if_needed(cmd, settings)
        cmd.extend(["-movflags", "+faststart", out])
        return cmd

class AviToMp433(BaseTask):
    name = "AviToMp433"
    params = [
        TaskParameter("speed", "Speed", "1x", param_type="choice", options=SPEED_OPTIONS, description="Video speed multiplier"),
        TaskParameter("include_audio", "With Sound", True, param_type="checkbox", description="Keep and process the audio track"),
        TaskParameter("scale_w", "Width", 480, param_type="entry", description="Video Width"),
        TaskParameter("scale_h", "Height", 270, param_type="entry", description="Video Height"),
        TaskParameter("crf", "CRF", 28, param_type="slider", min_val=0, max_val=51, description="Quality (higher CRF = lower quality)"),
        TaskParameter("fps", "FPS", "24", param_type="choice", options=FPS_OPTIONS, description="Frame rate"),
        TaskParameter("preset", "Preset", "veryslow", param_type="choice", options=PRESETS, description="Encoding preset")
    ]

    def build_command(self, input_file, settings):
        out = self.decorate_output_path(f"{input_file}.mp4", settings)
        video_filters = [
            f"scale={settings.get('scale_w', 480)}:{settings.get('scale_h', 270)}",
            self.get_speed_video_filter(settings)
        ]
        audio_filters = self.get_speed_audio_filters(settings) if self.wants_audio_output(settings) else []

        cmd = [self.get_ffmpeg_path(), "-y", "-i", input_file]
        self.add_silent_audio_input(cmd, settings)
        self.add_filter_args(cmd, video_filters=video_filters, audio_filters=audio_filters)
        self.add_stream_maps(cmd, settings)
        cmd.extend(self.get_video_args(settings, default_crf=28, default_preset="veryslow", requires_reencode=True))
        cmd.extend(["-profile:v", "main", "-level:v", "4.1", "-r", str(settings.get("fps", "24"))])

        if self.wants_audio_output(settings):
            cmd.extend(["-c:a", "aac", "-b:a", "160k"])
        else:
            cmd.append("-an")

        self.add_shortest_if_needed(cmd, settings)
        cmd.append(out)
        return cmd

class AllToMp3(BaseTask):
    name = "AllToMp3"
    params = [
        TaskParameter("quality", "VBR (0=Best)", 0, param_type="slider", min_val=0, max_val=9, description="VBR Quality. 0 is best, 9 is worst."),
        TaskParameter("codec", "Codec", "libmp3lame", param_type="choice", options=["libmp3lame", "libvorbis"], description="Audio codec to use")
    ]

    def build_command(self, input_file, settings):
        out = f"{input_file}.mp3"
        return [
            self.get_ffmpeg_path(), "-i", input_file,
            "-c:a", settings.get("codec", "libmp3lame"),
            "-q:a", str(int(settings.get("quality", 0))), "-map", "a", out
        ]

class AviToMp4(BaseTask):
    name = "AviToMp4"
    params = [
        TaskParameter("speed", "Speed", "1x", param_type="choice", options=SPEED_OPTIONS, description="Video speed multiplier"),
        TaskParameter("include_audio", "With Sound", True, param_type="checkbox", description="Keep and process the audio track"),
        TaskParameter("crf", "CRF", 22, param_type="slider", min_val=0, max_val=51, description="Constant Rate Factor. Lower value = better quality."),
        TaskParameter("preset", "Preset", "slow", param_type="choice", options=PRESETS, description="Encoding speed. Slow = better compression."),
        TaskParameter("codec_v", "Video Codec", "libx264", param_type="choice", options=VIDEO_CODECS, description="Video codec (H.264/H.265)"),
        TaskParameter("volume", "Volume", 1.0, param_type="slider", min_val=0.0, max_val=3.0, description="Volume multiplier")
    ]

    def build_command(self, input_file, settings):
        out = self.decorate_output_path(f"{input_file}.mp4", settings)
        speed = self.get_speed_multiplier(settings)
        requires_reencode = abs(speed - 1.0) > 1e-9

        audio_filters = []
        if self.wants_audio_output(settings):
            audio_filters.extend(self.get_speed_audio_filters(settings))
            volume = self._to_float(settings.get("volume", 1.0), 1.0)
            if abs(volume - 1.0) > 1e-9:
                audio_filters.append(f"volume={volume:g}")

        cmd = [self.get_ffmpeg_path(), "-y", "-i", input_file]
        self.add_silent_audio_input(cmd, settings)
        self.add_filter_args(cmd, video_filters=[self.get_speed_video_filter(settings)], audio_filters=audio_filters)
        self.add_stream_maps(cmd, settings)

        video_args = self.get_video_args(
            settings,
            default_codec="libx264",
            default_crf=22,
            default_preset="slow",
            requires_reencode=requires_reencode
        )
        cmd.extend(video_args)

        if "copy" not in video_args:
            cmd.extend(["-profile:v", "main", "-level:v", "4.1", "-r", "29.976"])

        if self.wants_audio_output(settings):
            cmd.extend(["-c:a", "aac", "-b:a", "160k"])
        else:
            cmd.append("-an")

        self.add_shortest_if_needed(cmd, settings)
        cmd.append(out)
        return cmd

class AllToBox(BaseTask):
    name = "AllToBox"
    params = [
        TaskParameter("speed", "Speed", "1x", param_type="choice", options=SPEED_OPTIONS, description="Video speed multiplier"),
        TaskParameter("include_audio", "With Sound", True, param_type="checkbox", description="Keep and process the audio track"),
        TaskParameter("crop_w", "Crop Width", 900, param_type="entry", description="Width of the cropped area in center"),
        TaskParameter("crop_h", "Crop Height", 900, param_type="entry", description="Height of the cropped area in center")
    ]

    def build_command(self, input_file, settings):
        out = self.decorate_output_path(f"{input_file}_box.mp4", settings)
        w = settings.get("crop_w", 900)
        h = settings.get("crop_h", 900)
        crop_filter = f"crop={w}:{h}:(iw-{w})/2:(ih-{h})/2"
        audio_filters = self.get_speed_audio_filters(settings) if self.wants_audio_output(settings) else []

        cmd = [self.get_ffmpeg_path(), "-y", "-i", input_file]
        self.add_silent_audio_input(cmd, settings)
        self.add_filter_args(
            cmd,
            video_filters=[crop_filter, self.get_speed_video_filter(settings)],
            audio_filters=audio_filters
        )
        self.add_stream_maps(cmd, settings)
        cmd.extend(self.get_video_args(settings, default_crf=22, default_preset="slow", requires_reencode=True))

        if self.wants_audio_output(settings):
            if audio_filters or self.needs_silent_audio(settings):
                cmd.extend(["-c:a", "aac", "-b:a", "160k"])
            else:
                cmd.extend(["-c:a", "copy"])
        else:
            cmd.append("-an")

        self.add_shortest_if_needed(cmd, settings)
        cmd.append(out)
        return cmd

class StereoMp3ToMono(BaseTask):
    name = "StereoMp3ToMono"
    params = [
        TaskParameter("bitrate", "Bitrate", "64k", param_type="choice", options=AUDIO_BITRATES, description="Target bitrate for mono audio")
    ]

    def build_command(self, input_file, settings):
        out = f"{input_file}Mono.mp3"
        return [
            self.get_ffmpeg_path(), "-i", input_file,
            "-ac", "1", "-b:a", settings.get("bitrate", "64k"), out
        ]

class AllToWedGL(BaseTask):
    name = "AllToWedGL"
    params = [
        TaskParameter("speed", "Speed", "1x", param_type="choice", options=SPEED_OPTIONS, description="Video speed multiplier"),
        TaskParameter("include_audio", "With Sound", False, param_type="checkbox", description="Keep and process the audio track"),
        TaskParameter("crf", "CRF", 22, param_type="slider", min_val=0, max_val=51, description="Quality factor (0-51)"),
        TaskParameter("preset", "Preset", "slow", param_type="choice", options=PRESETS, description="Encoding efficiency"),
        TaskParameter("codec_v", "Video Codec", "libx264", param_type="choice", options=VIDEO_CODECS, description="Video codec")
    ]

    def build_command(self, input_file, settings):
        out = self.decorate_output_path(f"{os.path.splitext(input_file)[0]}_WebGl.mp4", settings)
        speed = self.get_speed_multiplier(settings)
        requires_reencode = abs(speed - 1.0) > 1e-9
        audio_filters = self.get_speed_audio_filters(settings) if self.wants_audio_output(settings, default=False) else []

        cmd = [self.get_ffmpeg_path(), "-y", "-i", input_file]
        self.add_silent_audio_input(cmd, settings, default=False)
        self.add_filter_args(cmd, video_filters=[self.get_speed_video_filter(settings)], audio_filters=audio_filters)
        self.add_stream_maps(cmd, settings, default_audio=False)

        video_args = self.get_video_args(
            settings,
            default_crf=22,
            default_preset="slow",
            requires_reencode=requires_reencode
        )
        cmd.extend(video_args)

        if "copy" not in video_args:
            cmd.extend(["-profile:v", "main", "-level:v", "4.1"])

        if self.wants_audio_output(settings, default=False):
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])
        else:
            cmd.append("-an")

        self.add_shortest_if_needed(cmd, settings, default_audio=False)
        cmd.append(out)
        return cmd

class FirstFrame(BaseTask):
    name = "FirstFrame"
    params = [
        TaskParameter("quality", "JPG Quality", 2, param_type="slider", min_val=1, max_val=31, description="Q-scale (2=High, 31=Low)")
    ]

    def build_command(self, input_file, settings):
        out = f"{input_file}_first_frame.jpg"
        return [
            self.get_ffmpeg_path(), "-i", input_file,
            "-vf", r"select=eq(n\,0)", "-vsync", "vfr",
            "-q:v", str(int(settings.get("quality", 2))), out
        ]

class RandomFrames(BaseTask):
    name = "RandomFrames"
    params = [
        TaskParameter("count", "Frame Count", 5, param_type="slider", min_val=1, max_val=20, description="Number of random frames to extract from the video."),
        TaskParameter("quality", "JPG Quality", 2, param_type="slider", min_val=1, max_val=31, description="Image quality scale. 2 is Best, 31 is Worst.")
    ]

    def build_command(self, input_file, settings):
        count = int(settings.get("count", 5))
        duration = settings.get("duration", 60.0)
        if duration <= 1.0:
            duration = 10.0

        timestamps = sorted([random.uniform(0, duration) for _ in range(count)])

        commands = []
        base_name = os.path.splitext(input_file)[0]

        for i, t in enumerate(timestamps):
            out_file = f"{base_name}_rnd_{i+1:03d}.jpg"
            cmd = [
                self.get_ffmpeg_path(),
                "-ss", f"{t:.3f}",
                "-i", input_file,
                "-vframes", "1",
                "-q:v", str(int(settings.get("quality", 2))),
                "-y",
                out_file
            ]
            commands.append(cmd)

        return commands

TASKS = {
    "WAVToX2": WAVToX2,
    "AllToWedGLandSound": AllToWedGLandSound,
    "AllToMov": AllToMov,
    "AviToMp433": AviToMp433,
    "AllToMp3": AllToMp3,
    "AviToMp4": AviToMp4,
    "FirstFrame": FirstFrame,
    "RandomFrames": RandomFrames,
    "AllToBox": AllToBox,
    "StereoMp3ToMono": StereoMp3ToMono,
    "AllToWedGL": AllToWedGL
}
