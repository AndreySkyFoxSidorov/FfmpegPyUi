import os
import re

try:
    from .tasks import BaseTask, SPEED_OPTIONS
except ImportError:
    from logic.tasks import BaseTask, SPEED_OPTIONS


DEFAULT_BUILTIN_SCHEME = "MP4 для отправки"

DEFAULT_WORKFLOW_CONFIG = {
    "output_container": "mp4",
    "gif_width": 640,
    "gif_fps": 15,
    "gif_dither": "sierra2_4a",
    "resolution_mode": "original",
    "custom_width": 1280,
    "custom_height": 720,
    "quality_profile": "balanced",
    "encoding_speed": "balanced",
    "video_codec": "libx264",
    "crop_mode": "none",
    "crop_left": 0,
    "crop_right": 0,
    "crop_top": 0,
    "crop_bottom": 0,
    "trim_mode": "none",
    "trim_start_seconds": 0.0,
    "trim_end_seconds": 0.0,
    "trim_start_frames": 0,
    "trim_end_frames": 0,
    "fps_mode": "source",
    "speed": "1x",
    "audio_mode": "keep_or_silent",
    "audio_quality": "normal",
    "audio_volume": 1.0,
    "video_filter_1": "none",
    "video_filter_2": "none",
    "video_filter_3": "none",
    "video_eq_brightness": 0.0,
    "video_eq_contrast": 1.0,
    "video_eq_saturation": 1.0,
    "video_denoise_strength": 3.0,
    "video_sharpen_strength": 1.0,
    "video_text": "",
    "audio_filter_1": "none",
    "audio_filter_2": "none",
    "audio_filter_3": "none",
    "audio_highpass_hz": 80,
    "audio_lowpass_hz": 16000,
    "audio_fade_seconds": 1.0,
    "advanced_video_filters": "",
    "advanced_audio_filters": "",
    "output_suffix": "processed",
}

BUILTIN_SCHEMES = {
    "MP4 для отправки": {
        **DEFAULT_WORKFLOW_CONFIG,
        "output_suffix": "mp4",
    },
    "Маленький файл": {
        **DEFAULT_WORKFLOW_CONFIG,
        "quality_profile": "small",
        "encoding_speed": "smaller_file",
        "video_codec": "libx265",
        "audio_quality": "compact",
        "output_suffix": "small",
    },
    "Высокое качество": {
        **DEFAULT_WORKFLOW_CONFIG,
        "quality_profile": "high",
        "encoding_speed": "smaller_file",
        "audio_quality": "high",
        "output_suffix": "hq",
    },
    "Ускорить 4x со звуком": {
        **DEFAULT_WORKFLOW_CONFIG,
        "speed": "4x",
        "quality_profile": "balanced",
        "output_suffix": "4x",
    },
    "Ускорить 10x без звука": {
        **DEFAULT_WORKFLOW_CONFIG,
        "speed": "10x",
        "audio_mode": "mute",
        "quality_profile": "small",
        "output_suffix": "10x_mute",
    },
    "Квадрат для WebGL": {
        **DEFAULT_WORKFLOW_CONFIG,
        "resolution_mode": "square_720",
        "audio_mode": "mute",
        "quality_profile": "balanced",
        "output_suffix": "webgl",
    },
    "MOV для монтажа": {
        **DEFAULT_WORKFLOW_CONFIG,
        "output_container": "mov",
        "quality_profile": "high",
        "audio_quality": "high",
        "output_suffix": "edit",
    },
    "WebM для сайта": {
        **DEFAULT_WORKFLOW_CONFIG,
        "output_container": "webm",
        "video_codec": "libvpx-vp9",
        "quality_profile": "balanced",
        "output_suffix": "webm",
    },
    "GIF из видео": {
        **DEFAULT_WORKFLOW_CONFIG,
        "output_container": "gif",
        "gif_width": 640,
        "gif_fps": 15,
        "audio_mode": "mute",
        "output_suffix": "gif",
    },
    "MP3 аудио": {
        **DEFAULT_WORKFLOW_CONFIG,
        "output_container": "mp3",
        "audio_quality": "high",
        "output_suffix": "mp3",
    },
    "WAV аудио": {
        **DEFAULT_WORKFLOW_CONFIG,
        "output_container": "wav",
        "audio_quality": "high",
        "output_suffix": "wav",
    },
}

QUALITY_PROFILES = {
    "draft": 30,
    "small": 27,
    "balanced": 23,
    "high": 18,
    "maximum": 16,
}

ENCODING_SPEEDS = {
    "fast": "veryfast",
    "balanced": "medium",
    "smaller_file": "slow",
}

VIDEO_CODECS = {
    "libx264": "libx264",
    "libx265": "libx265",
    "h264_nvenc": "h264_nvenc",
    "hevc_nvenc": "hevc_nvenc",
    "libvpx-vp9": "libvpx-vp9",
    "libaom-av1": "libaom-av1",
    "copy": "copy",
}

GIF_DITHER_MODES = {"sierra2_4a", "bayer", "none"}
RESOLUTION_MODES = {"original", "fit_1080", "fit_720", "square_720", "custom"}
CROP_MODES = {"none", "manual"}
TRIM_MODES = {"none", "seconds", "frames"}
FPS_MODES = {"source", "24", "30", "60"}
VIDEO_FILTER_MODES = {
    "none",
    "hflip",
    "vflip",
    "rotate_90",
    "grayscale",
    "eq",
    "denoise",
    "sharpen",
    "deinterlace",
    "pad_square",
    "drawtext",
}
AUDIO_FILTER_MODES = {
    "none",
    "loudnorm",
    "highpass",
    "lowpass",
    "acompressor",
    "afade",
    "silenceremove",
}

AUDIO_BITRATES = {
    "compact": "96k",
    "normal": "160k",
    "high": "256k",
}

OUTPUT_EXTENSIONS = {
    "mp4": ".mp4",
    "mov": ".mov",
    "mkv": ".mkv",
    "webm": ".webm",
    "mp3": ".mp3",
    "wav": ".wav",
    "aac": ".aac",
    "flac": ".flac",
    "ogg": ".ogg",
    "gif": ".gif",
}

AUDIO_OUTPUT_FORMATS = {"mp3", "wav", "aac", "flac", "ogg"}
AUDIO_OUTPUT_CODECS = {
    "mp3": "libmp3lame",
    "wav": "pcm_s16le",
    "aac": "aac",
    "flac": "flac",
    "ogg": "libvorbis",
}


def get_builtin_scheme(name):
    data = BUILTIN_SCHEMES.get(name, BUILTIN_SCHEMES[DEFAULT_BUILTIN_SCHEME])
    return {**DEFAULT_WORKFLOW_CONFIG, **data}


def normalize_workflow_config(config):
    normalized = {**DEFAULT_WORKFLOW_CONFIG, **(config or {})}
    normalized.pop("gif_source_mode", None)

    if normalized.get("speed") not in SPEED_OPTIONS:
        normalized["speed"] = DEFAULT_WORKFLOW_CONFIG["speed"]
    if normalized.get("output_container") not in OUTPUT_EXTENSIONS:
        normalized["output_container"] = DEFAULT_WORKFLOW_CONFIG["output_container"]
    if normalized.get("gif_dither") not in GIF_DITHER_MODES:
        normalized["gif_dither"] = DEFAULT_WORKFLOW_CONFIG["gif_dither"]
    if normalized.get("quality_profile") not in QUALITY_PROFILES:
        normalized["quality_profile"] = DEFAULT_WORKFLOW_CONFIG["quality_profile"]
    if normalized.get("encoding_speed") not in ENCODING_SPEEDS:
        normalized["encoding_speed"] = DEFAULT_WORKFLOW_CONFIG["encoding_speed"]

    raw_config = config or {}
    if "video_codec" not in raw_config and raw_config.get("encoder_profile") == "smaller_file":
        normalized["video_codec"] = "libx265"
    elif "video_codec" not in raw_config and raw_config.get("encoder_profile") == "copy_when_possible":
        normalized["video_codec"] = "copy"
    if normalized.get("video_codec") not in VIDEO_CODECS:
        normalized["video_codec"] = DEFAULT_WORKFLOW_CONFIG["video_codec"]
    if normalized["output_container"] == "webm" and normalized["video_codec"] in {"libx264", "libx265", "h264_nvenc", "hevc_nvenc"}:
        normalized["video_codec"] = "libvpx-vp9"
    if normalized["output_container"] == "gif":
        normalized["audio_mode"] = "mute"

    if normalized.get("audio_quality") not in AUDIO_BITRATES:
        normalized["audio_quality"] = DEFAULT_WORKFLOW_CONFIG["audio_quality"]
    if normalized.get("audio_mode") not in ("keep_or_silent", "mute"):
        normalized["audio_mode"] = DEFAULT_WORKFLOW_CONFIG["audio_mode"]
    if normalized.get("resolution_mode") not in RESOLUTION_MODES:
        normalized["resolution_mode"] = DEFAULT_WORKFLOW_CONFIG["resolution_mode"]
    if normalized.get("crop_mode") not in CROP_MODES:
        normalized["crop_mode"] = DEFAULT_WORKFLOW_CONFIG["crop_mode"]
    if normalized.get("trim_mode") not in TRIM_MODES:
        normalized["trim_mode"] = DEFAULT_WORKFLOW_CONFIG["trim_mode"]

    normalized["fps_mode"] = str(normalized.get("fps_mode", DEFAULT_WORKFLOW_CONFIG["fps_mode"]))
    if normalized["fps_mode"] not in FPS_MODES:
        normalized["fps_mode"] = DEFAULT_WORKFLOW_CONFIG["fps_mode"]
    for key in ("video_filter_1", "video_filter_2", "video_filter_3"):
        if normalized.get(key) not in VIDEO_FILTER_MODES:
            normalized[key] = DEFAULT_WORKFLOW_CONFIG[key]
    for key in ("audio_filter_1", "audio_filter_2", "audio_filter_3"):
        if normalized.get(key) not in AUDIO_FILTER_MODES:
            normalized[key] = DEFAULT_WORKFLOW_CONFIG[key]

    normalized["gif_width"] = _positive_int(normalized.get("gif_width"), DEFAULT_WORKFLOW_CONFIG["gif_width"])
    normalized["gif_fps"] = _positive_int(normalized.get("gif_fps"), DEFAULT_WORKFLOW_CONFIG["gif_fps"])
    normalized["custom_width"] = _positive_int(normalized.get("custom_width"), DEFAULT_WORKFLOW_CONFIG["custom_width"])
    normalized["custom_height"] = _positive_int(normalized.get("custom_height"), DEFAULT_WORKFLOW_CONFIG["custom_height"])
    normalized["crop_left"] = _non_negative_int(normalized.get("crop_left"), DEFAULT_WORKFLOW_CONFIG["crop_left"])
    normalized["crop_right"] = _non_negative_int(normalized.get("crop_right"), DEFAULT_WORKFLOW_CONFIG["crop_right"])
    normalized["crop_top"] = _non_negative_int(normalized.get("crop_top"), DEFAULT_WORKFLOW_CONFIG["crop_top"])
    normalized["crop_bottom"] = _non_negative_int(normalized.get("crop_bottom"), DEFAULT_WORKFLOW_CONFIG["crop_bottom"])
    normalized["trim_start_seconds"] = _non_negative_float(normalized.get("trim_start_seconds"), DEFAULT_WORKFLOW_CONFIG["trim_start_seconds"])
    normalized["trim_end_seconds"] = _non_negative_float(normalized.get("trim_end_seconds"), DEFAULT_WORKFLOW_CONFIG["trim_end_seconds"])
    normalized["trim_start_frames"] = _non_negative_int(normalized.get("trim_start_frames"), DEFAULT_WORKFLOW_CONFIG["trim_start_frames"])
    normalized["trim_end_frames"] = _non_negative_int(normalized.get("trim_end_frames"), DEFAULT_WORKFLOW_CONFIG["trim_end_frames"])
    if "duration" in normalized:
        normalized["duration"] = _non_negative_float(normalized.get("duration"), 0.0)
    if "source_fps" in normalized:
        normalized["source_fps"] = _non_negative_float(normalized.get("source_fps"), 0.0)

    normalized["audio_volume"] = _bounded_float(normalized.get("audio_volume"), 1.0, 0.0, 3.0)
    normalized["video_eq_brightness"] = _bounded_float(normalized.get("video_eq_brightness"), 0.0, -1.0, 1.0)
    normalized["video_eq_contrast"] = _bounded_float(normalized.get("video_eq_contrast"), 1.0, 0.0, 3.0)
    normalized["video_eq_saturation"] = _bounded_float(normalized.get("video_eq_saturation"), 1.0, 0.0, 3.0)
    normalized["video_denoise_strength"] = _bounded_float(normalized.get("video_denoise_strength"), 3.0, 0.0, 10.0)
    normalized["video_sharpen_strength"] = _bounded_float(normalized.get("video_sharpen_strength"), 1.0, 0.0, 5.0)
    normalized["audio_highpass_hz"] = _positive_int(normalized.get("audio_highpass_hz"), DEFAULT_WORKFLOW_CONFIG["audio_highpass_hz"])
    normalized["audio_lowpass_hz"] = _positive_int(normalized.get("audio_lowpass_hz"), DEFAULT_WORKFLOW_CONFIG["audio_lowpass_hz"])
    normalized["audio_fade_seconds"] = _non_negative_float(normalized.get("audio_fade_seconds"), DEFAULT_WORKFLOW_CONFIG["audio_fade_seconds"])
    normalized["video_text"] = str(normalized.get("video_text") or "").strip()
    normalized["advanced_video_filters"] = _safe_filter_chain(normalized.get("advanced_video_filters"))
    normalized["advanced_audio_filters"] = _safe_filter_chain(normalized.get("advanced_audio_filters"))
    normalized["output_suffix"] = _safe_suffix(normalized.get("output_suffix", "processed"))
    return normalized


def is_audio_output_format(output_container):
    return output_container in AUDIO_OUTPUT_FORMATS


def is_gif_output_format(output_container):
    return output_container == "gif"


def selected_video_filters(config):
    config = normalize_workflow_config(config)
    return {config["video_filter_1"], config["video_filter_2"], config["video_filter_3"]}


def selected_audio_filters(config):
    config = normalize_workflow_config(config)
    return {config["audio_filter_1"], config["audio_filter_2"], config["audio_filter_3"]}


def _positive_int(value, default):
    try:
        value = int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _non_negative_int(value, default):
    try:
        value = int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return default
    return max(value, 0)


def _non_negative_float(value, default):
    try:
        value = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default
    return max(value, 0.0)


def _bounded_float(value, default, min_value, max_value):
    try:
        value = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default
    return min(max(value, min_value), max_value)


def _format_seconds(value):
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text or "0"


def _safe_suffix(value):
    suffix = str(value or "processed").strip()
    suffix = re.sub(r"[^A-Za-z0-9А-Яа-яЁё._-]+", "_", suffix)
    suffix = suffix.strip("._-")
    return suffix or "processed"


def _safe_filter_chain(value):
    text = str(value or "").strip()
    if "\n" in text or "\r" in text:
        text = ",".join(part.strip() for part in re.split(r"[\r\n]+", text) if part.strip())
    return text


def _escape_drawtext_text(value):
    text = str(value or "").replace("\\", "\\\\")
    text = text.replace(":", r"\:")
    text = text.replace("'", r"\'")
    text = text.replace(",", r"\,")
    return text


class WorkflowVideoTask(BaseTask):
    name = "WorkflowVideoTask"

    def build_command(self, input_file, settings):
        config = normalize_workflow_config(settings)

        if is_gif_output_format(config["output_container"]):
            return self._build_gif_output_command(input_file, settings, config)
        if is_audio_output_format(config["output_container"]):
            return self._build_audio_output_command(input_file, settings, config)

        include_audio = config["audio_mode"] != "mute"
        ff_settings = {
            "speed": config["speed"],
            "include_audio": include_audio,
            "has_audio": settings.get("has_audio", True),
            "use_gpu": settings.get("use_gpu", False),
            "explicit_codec": True,
            "codec_v": VIDEO_CODECS[config["video_codec"]],
            "preset": ENCODING_SPEEDS[config["encoding_speed"]],
            "crf": QUALITY_PROFILES[config["quality_profile"]],
        }

        output_path = self._output_path(input_file, config)
        video_filters = self._video_filters(config, ff_settings)
        audio_filters = self._audio_filters(config, ff_settings) if include_audio else []
        trim_start, trim_duration = self._trim_window(config)

        cmd = [self.get_ffmpeg_path(settings.get("ffmpeg_path")), "-y"]
        if trim_start > 0:
            cmd.extend(["-ss", _format_seconds(trim_start)])
        if trim_duration is not None:
            cmd.extend(["-t", _format_seconds(trim_duration)])
        cmd.extend(["-i", input_file])
        self.add_silent_audio_input(cmd, ff_settings)
        self.add_filter_args(cmd, video_filters=video_filters, audio_filters=audio_filters)
        self.add_stream_maps(cmd, ff_settings)

        requires_reencode = bool(video_filters) or config["fps_mode"] != "source"
        video_args = self.get_video_args(
            ff_settings,
            default_codec="libx264",
            default_crf=QUALITY_PROFILES[config["quality_profile"]],
            default_preset=ENCODING_SPEEDS[config["encoding_speed"]],
            requires_reencode=requires_reencode,
        )
        cmd.extend(video_args)

        video_codec = video_args[video_args.index("-c:v") + 1] if "-c:v" in video_args else ""
        if video_codec == "libvpx-vp9":
            cmd.extend(["-b:v", "0"])
        if video_codec == "libaom-av1":
            cmd.extend(["-b:v", "0", "-cpu-used", "4"])
        if video_codec not in ("", "copy", "libvpx-vp9", "libaom-av1"):
            cmd.extend(["-profile:v", "main", "-level:v", "4.1"])

        if config["fps_mode"] != "source":
            cmd.extend(["-r", str(config["fps_mode"])])

        if include_audio:
            if config["output_container"] == "webm":
                cmd.extend(["-c:a", "libopus", "-b:a", AUDIO_BITRATES[config["audio_quality"]]])
            else:
                cmd.extend([
                    "-c:a", "aac",
                    "-b:a", AUDIO_BITRATES[config["audio_quality"]],
                    "-ac", "2",
                    "-ar", "48000",
                ])
        else:
            cmd.append("-an")

        if config["output_container"] == "mov":
            cmd.extend(["-tag:v", "avc1"])

        self.add_shortest_if_needed(cmd, ff_settings)
        if config["output_container"] in ("mp4", "mov"):
            cmd.extend(["-movflags", "+faststart"])
        cmd.append(output_path)
        return cmd

    def _build_audio_output_command(self, input_file, settings, config):
        ff_settings = {
            "speed": config["speed"],
            "include_audio": True,
            "has_audio": settings.get("has_audio", True),
        }
        output_path = self._output_path(input_file, config)
        audio_filters = self._audio_filters(config, ff_settings)
        trim_start, trim_duration = self._trim_window(config)

        cmd = [self.get_ffmpeg_path(settings.get("ffmpeg_path")), "-y"]
        if trim_start > 0:
            cmd.extend(["-ss", _format_seconds(trim_start)])
        if trim_duration is not None:
            cmd.extend(["-t", _format_seconds(trim_duration)])
        cmd.extend(["-i", input_file])

        self.add_silent_audio_input(cmd, ff_settings)
        self.add_filter_args(cmd, audio_filters=audio_filters)

        if self.needs_silent_audio(ff_settings):
            cmd.extend(["-map", "1:a:0"])
        else:
            cmd.extend(["-map", "0:a:0?"])

        cmd.append("-vn")
        codec = AUDIO_OUTPUT_CODECS.get(config["output_container"], "aac")
        cmd.extend(["-c:a", codec])
        if config["output_container"] not in ("wav", "flac"):
            cmd.extend(["-b:a", AUDIO_BITRATES[config["audio_quality"]]])
        cmd.extend(["-ac", "2", "-ar", "48000"])

        if self.needs_silent_audio(ff_settings):
            silent_duration = self.get_output_duration({**settings, **config})
            cmd.extend(["-t", _format_seconds(silent_duration if silent_duration > 0 else 1.0)])

        cmd.append(output_path)
        return cmd

    def _build_gif_output_command(self, input_file, settings, config):
        output_path = self._output_path(input_file, config)
        trim_start, trim_duration = self._trim_window(config)
        has_video = bool(settings.get("source_width", 0) and settings.get("source_height", 0))
        if not has_video:
            raise ValueError("GIF output requires a video input")

        cmd = [self.get_ffmpeg_path(settings.get("ffmpeg_path")), "-y"]
        if trim_start > 0:
            cmd.extend(["-ss", _format_seconds(trim_start)])
        if trim_duration is not None:
            cmd.extend(["-t", _format_seconds(trim_duration)])
        cmd.extend(["-i", input_file])

        ff_settings = {
            "speed": config["speed"],
            "include_audio": False,
            "has_audio": False,
            "use_gpu": False,
        }
        filters = self._video_filters(config, ff_settings)
        filters.append(f"fps={config['gif_fps']}")
        filters.append(f"scale={config['gif_width']}:-1:flags=lanczos")
        source = "[0:v]"

        chain = self.combine_filters(filters)
        dither = f"=dither={config['gif_dither']}" if config["gif_dither"] != "none" else "=dither=none"
        filter_complex = f"{source}{chain},split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse{dither}"
        cmd.extend(["-filter_complex", filter_complex, "-loop", "0", output_path])
        return cmd

    def get_output_duration(self, settings):
        config = normalize_workflow_config(settings)
        trim_start, trim_duration = self._trim_window(config)
        duration = config.get("duration", 0)

        if trim_duration is not None:
            duration = trim_duration
        elif trim_start > 0 and duration > 0:
            duration = max(duration - trim_start, 0.001)

        speed = self.get_speed_multiplier(config)
        return duration / speed if speed else duration

    def _output_path(self, input_file, config):
        base, _ = os.path.splitext(input_file)
        ext = OUTPUT_EXTENSIONS[config["output_container"]]
        return f"{base}_{config['output_suffix']}{ext}"

    def _video_filters(self, config, ff_settings):
        filters = []

        if config["crop_mode"] == "manual":
            crop_filter = self._manual_crop_filter(config)
            if crop_filter:
                filters.append(crop_filter)

        if config["resolution_mode"] == "fit_720":
            filters.append("scale=-2:720")
        elif config["resolution_mode"] == "fit_1080":
            filters.append("scale=-2:1080")
        elif config["resolution_mode"] == "square_720":
            filters.append(r"crop=min(iw\,ih):min(iw\,ih):(iw-min(iw\,ih))/2:(ih-min(iw\,ih))/2")
            filters.append("scale=720:720")
        elif config["resolution_mode"] == "custom":
            filters.append(f"scale={config['custom_width']}:{config['custom_height']}")

        speed_filter = self.get_speed_video_filter(ff_settings)
        if speed_filter:
            filters.append(speed_filter)

        for key in ("video_filter_1", "video_filter_2", "video_filter_3"):
            extra_filter = self._extra_video_filter(config, config[key])
            if extra_filter:
                filters.append(extra_filter)

        if config["advanced_video_filters"]:
            filters.append(config["advanced_video_filters"])
        return filters

    def _extra_video_filter(self, config, mode):
        if mode == "hflip":
            return "hflip"
        if mode == "vflip":
            return "vflip"
        if mode == "rotate_90":
            return "transpose=1"
        if mode == "grayscale":
            return "format=gray"
        if mode == "eq":
            return (
                f"eq=brightness={config['video_eq_brightness']:g}:"
                f"contrast={config['video_eq_contrast']:g}:"
                f"saturation={config['video_eq_saturation']:g}"
            )
        if mode == "denoise":
            strength = config["video_denoise_strength"]
            return f"hqdn3d={strength:g}:{strength:g}:{strength:g}:{strength:g}"
        if mode == "sharpen":
            return f"unsharp=5:5:{config['video_sharpen_strength']:g}:5:5:0.0"
        if mode == "deinterlace":
            return "yadif"
        if mode == "pad_square":
            return r"pad=max(iw\,ih):max(iw\,ih):(ow-iw)/2:(oh-ih)/2"
        if mode == "drawtext" and config["video_text"]:
            text = _escape_drawtext_text(config["video_text"])
            return f"drawtext=text='{text}':x=(w-text_w)/2:y=h-th-24:fontsize=32:fontcolor=white:box=1:boxcolor=black@0.45"
        return None

    def _manual_crop_filter(self, config):
        left = config["crop_left"]
        right = config["crop_right"]
        top = config["crop_top"]
        bottom = config["crop_bottom"]

        source_w = _non_negative_int(config.get("source_width"), 0)
        source_h = _non_negative_int(config.get("source_height"), 0)
        if source_w:
            left = min(left, source_w - 1)
            right = min(right, max(source_w - left - 1, 0))
        if source_h:
            top = min(top, source_h - 1)
            bottom = min(bottom, max(source_h - top - 1, 0))

        if not any([left, right, top, bottom]):
            return None

        width_expr = f"iw-{left + right}" if left + right else "iw"
        height_expr = f"ih-{top + bottom}" if top + bottom else "ih"
        return f"crop={width_expr}:{height_expr}:{left}:{top}"

    def _audio_filters(self, config, ff_settings):
        filters = self.get_speed_audio_filters(ff_settings)
        volume = config["audio_volume"]
        if abs(volume - 1.0) > 1e-9:
            filters.append(f"volume={volume:g}")

        for key in ("audio_filter_1", "audio_filter_2", "audio_filter_3"):
            extra_filter = self._extra_audio_filter(config, config[key])
            if extra_filter:
                filters.append(extra_filter)

        if config["advanced_audio_filters"]:
            filters.append(config["advanced_audio_filters"])
        return filters

    def _extra_audio_filter(self, config, mode):
        if mode == "loudnorm":
            return "loudnorm=I=-16:TP=-1.5:LRA=11"
        if mode == "highpass":
            return f"highpass=f={config['audio_highpass_hz']}"
        if mode == "lowpass":
            return f"lowpass=f={config['audio_lowpass_hz']}"
        if mode == "acompressor":
            return "acompressor=threshold=-18dB:ratio=3:attack=20:release=250"
        if mode == "afade":
            return f"afade=t=in:st=0:d={config['audio_fade_seconds']:g}"
        if mode == "silenceremove":
            return "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.1"
        return None

    def _trim_window(self, config):
        start = 0.0
        end = 0.0

        if config["trim_mode"] == "seconds":
            start = config["trim_start_seconds"]
            end = config["trim_end_seconds"]
        elif config["trim_mode"] == "frames":
            fps = config.get("source_fps", 0)
            if fps <= 0:
                fps = 30.0
            start = config["trim_start_frames"] / fps
            end = config["trim_end_frames"] / fps

        duration = config.get("duration", 0)
        if duration <= 0:
            return start, None

        start = min(start, max(duration - 0.001, 0.0))
        output_duration = max(duration - start - end, 0.001)
        if start <= 0 and end <= 0:
            return 0.0, None
        return start, output_duration
