import unittest
import sys
import os
import tempfile

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ffmpegpyui.logic.media_info import MediaProber, MediaInfo
from ffmpegpyui.logic.ffmpeg_runner import FfmpegRunner
from ffmpegpyui.logic.ffmpeg_installer import (
    FFMPEG_STABLE_VERSION,
    ffmpeg_downloads_for_platform,
    local_ffmpeg_available,
    should_download_ffmpeg,
)
from ffmpegpyui.logic.input_paths import expand_input_paths
from ffmpegpyui.logic.ffmpeg_paths import resolve_ffmpeg_executable
from ffmpegpyui.logic.tasks import BaseTask, AviToMp4, AllToWedGL
from ffmpegpyui.logic.workflow import WorkflowVideoTask, get_builtin_scheme, normalize_workflow_config
from ffmpegpyui.ui.localization import (
    WORKFLOW_OPTIONS,
    WORKFLOW_SECTIONS,
    TRANSLATIONS,
    available_language_labels,
    available_languages,
    get_language,
    language_label,
    option_label,
    option_value,
    read_translation_csv,
    set_language,
    t,
)

class TestLogic(unittest.TestCase):
    def test_localization_reads_csv_languages(self):
        previous_language = get_language()
        try:
            self.assertEqual(
                available_languages(),
                ["EN", "UK", "RU", "ES", "IT", "DE", "KO", "NL", "FR", "PT", "ZH_TW", "ZH", "PL", "CS"],
            )
            self.assertEqual(
                available_language_labels(),
                [
                    "English",
                    "Українська",
                    "Русский",
                    "Español",
                    "Italiano",
                    "Deutsch",
                    "한국어",
                    "Nederlands",
                    "Français",
                    "Português",
                    "繁體中文",
                    "简体中文",
                    "Polski",
                    "Čeština",
                ],
            )
            self.assertEqual(language_label("RU"), "Русский")
            self.assertEqual(set_language("Українська"), "UK")
            set_language("EN")
            self.assertEqual(t("sidebar.add_files"), "Add files")
            self.assertEqual(option_value("speed", option_label("speed", "4x")), "4x")
            set_language("RU")
            self.assertEqual(t("sidebar.add_files"), "Добавить файлы")
        finally:
            set_language(previous_language)

    def test_translation_csv_accepts_new_language_column(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "localization.csv")
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write("key,EN,XX\nsample,Hello,New language\n")

            languages, translations = read_translation_csv(path)

        self.assertEqual(languages, ["EN", "XX"])
        self.assertEqual(translations["sample"]["XX"], "New language")

    def test_input_paths_accepts_multiple_argv_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            first = os.path.join(tmpdir, "one.mp4")
            second = os.path.join(tmpdir, "two.mp4")
            open(first, "w").close()
            open(second, "w").close()

            self.assertEqual(expand_input_paths([first, second]), [first, second])

    def test_input_paths_splits_quoted_argument_bundle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            first = os.path.join(tmpdir, "one file.mp4")
            second = os.path.join(tmpdir, "two file.mp4")
            open(first, "w").close()
            open(second, "w").close()

            self.assertEqual(expand_input_paths([f'"{first}" "{second}"']), [first, second])

    def test_input_paths_splits_braced_drop_bundle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            first = os.path.join(tmpdir, "one file.mp4")
            second = os.path.join(tmpdir, "two file.mp4")
            open(first, "w").close()
            open(second, "w").close()

            self.assertEqual(expand_input_paths([f"{{{first}}} {{{second}}}"]), [first, second])

    def test_workflow_localization_keys_exist(self):
        expected_keys = {
            "sidebar.language",
            "sidebar.ffmpeg_path_label",
            "sidebar.ffmpeg_path_help",
            "sidebar.ffmpeg_download_link",
            "sidebar.ffmpeg_browse",
            "sidebar.ffmpeg_browse_title",
            "workflow.run",
            "workflow.command_preview_title",
            "workflow.command_preview_error",
            "crop.preview_title",
            "crop.preview_loading",
            "trim.preview_title",
            "trim.preview_start_frame",
            "trim.preview_end_frame",
            "trim.preview_frame_loading",
            "trim.preview_frame_no_file",
            "trim.preview_no_file",
            "trim.preview_info",
        }
        for section in WORKFLOW_SECTIONS:
            expected_keys.add(section["title_key"])
            expected_keys.add(section["description_key"])
            for field in section["fields"]:
                expected_keys.add(field["label_key"])
                expected_keys.add(field["description_key"])

        for options in WORKFLOW_OPTIONS.values():
            for option in options:
                expected_keys.add(option["label_key"])

        missing = sorted(key for key in expected_keys if key not in TRANSLATIONS)
        self.assertEqual(missing, [])

    def test_media_info_parse(self):
        data = {
            "format": {"duration": "120.5"},
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "avg_frame_rate": "30000/1001"},
                {"codec_type": "audio", "codec_name": "aac"}
            ]
        }
        info = MediaProber._parse_json(data)
        self.assertEqual(info.duration, 120.5)
        self.assertEqual(info.width, 1920)
        self.assertEqual(info.height, 1080)
        self.assertEqual(info.v_codec, "h264")
        self.assertEqual(info.a_codec, "aac")
        self.assertAlmostEqual(info.fps, 29.97002997)
        # New format check (size/bitrate are 0 in this test data so they won't show up, but duration will be formatted)
        # Duration 120.5 -> 00:02:00
        self.assertEqual(str(info), "1920x1080 | h264 | 00:02:00")

    def test_ffmpeg_runner_time_parse(self):
        runner = FfmpegRunner(None, None)
        line = "frame=  234 fps=0.0 q=-1.0 size=    1024kB time=00:00:09.60 bitrate= 873.8kbits/s"
        t = runner._parse_time(line)
        self.assertAlmostEqual(t, 9.60)
        
        line2 = "time=01:02:03.50"
        t2 = runner._parse_time(line2)
        self.assertAlmostEqual(t2, 3600 + 120 + 3.5)

    def test_gpu_args(self):
        task = BaseTask()
        
        # Test 1: No GPU
        settings = {"use_gpu": False, "codec_v": "libx264", "preset": "slow", "crf": 23}
        args = task.get_video_args(settings)
        self.assertIn("-c:v", args)
        self.assertIn("libx264", args)
        self.assertIn("-preset", args)
        self.assertIn("slow", args)
        self.assertIn("-crf", args)
        
        # Test 2: GPU Enabled
        settings_gpu = {"use_gpu": True, "codec_v": "libx264", "preset": "slow", "crf": 23}
        args_gpu = task.get_video_args(settings_gpu)
        self.assertIn("-c:v", args_gpu)
        self.assertIn("h264_nvenc", args_gpu) # Implementation maps libx264 -> h264_nvenc
        self.assertIn("-preset", args_gpu)
        self.assertIn("p6", args_gpu) # slow -> p6
        self.assertIn("-rc", args_gpu)
        self.assertIn("vbr", args_gpu)
        self.assertIn("-cq", args_gpu)

        settings_explicit = {"use_gpu": True, "explicit_codec": True, "codec_v": "libx264", "preset": "slow", "crf": 23}
        args_explicit = task.get_video_args(settings_explicit)
        self.assertEqual(args_explicit[args_explicit.index("-c:v") + 1], "libx264")

    def test_speed_audio_filter_chain(self):
        task = BaseTask()
        filters = task.get_speed_audio_filters({"speed": "10x"})
        self.assertEqual(filters, ["atempo=2", "atempo=2", "atempo=2", "atempo=1.25"])

    def test_avi_to_mp4_speed_reencodes_copy_codec(self):
        task = AviToMp4()
        cmd = task.build_command(
            "sample.avi",
            {
                "speed": "4x",
                "include_audio": True,
                "has_audio": True,
                "codec_v": "copy",
                "preset": "slow",
                "crf": 22,
                "volume": 1.0
            }
        )

        self.assertIn("-vf", cmd)
        self.assertIn("setpts=PTS/4", cmd)
        self.assertIn("-filter:a", cmd)
        self.assertIn("atempo=2,atempo=2", cmd)
        self.assertEqual(cmd[cmd.index("-c:v") + 1], "libx264")
        self.assertTrue(cmd[-1].endswith("_4x.mp4"))

    def test_avi_to_mp4_adds_silent_audio_when_missing(self):
        task = AviToMp4()
        cmd = task.build_command(
            "silent.avi",
            {
                "speed": "1x",
                "include_audio": True,
                "has_audio": False,
                "codec_v": "libx264",
                "preset": "slow",
                "crf": 22,
                "volume": 1.0
            }
        )

        self.assertIn("-f", cmd)
        self.assertIn("lavfi", cmd)
        self.assertIn("anullsrc=channel_layout=stereo:sample_rate=48000", cmd)
        self.assertIn("-map", cmd)
        self.assertIn("1:a:0", cmd)
        self.assertIn("-shortest", cmd)
        self.assertNotIn("-an", cmd)

    def test_webgl_mute_output(self):
        task = AllToWedGL()
        cmd = task.build_command(
            "clip.mov",
            {
                "speed": "16x",
                "include_audio": False,
                "codec_v": "libx264",
                "preset": "slow",
                "crf": 22
            }
        )

        self.assertIn("-an", cmd)
        self.assertTrue(cmd[-1].endswith("_WebGl_16x_mute.mp4"))

    def test_workflow_adds_silent_audio_for_video_without_audio(self):
        task = WorkflowVideoTask()
        settings = get_builtin_scheme("MP4 для отправки")
        settings["has_audio"] = False
        cmd = task.build_command("clip.mov", settings)

        self.assertIn("-f", cmd)
        self.assertIn("lavfi", cmd)
        self.assertIn("anullsrc=channel_layout=stereo:sample_rate=48000", cmd)
        self.assertIn("1:a:0", cmd)
        self.assertIn("-shortest", cmd)
        self.assertNotIn("-an", cmd)
        self.assertTrue(cmd[-1].endswith("_mp4.mp4"))

    def test_workflow_mute_does_not_add_silent_audio(self):
        task = WorkflowVideoTask()
        settings = get_builtin_scheme("Ускорить 10x без звука")
        settings["has_audio"] = False
        cmd = task.build_command("clip.mov", settings)

        self.assertIn("-an", cmd)
        self.assertNotIn("anullsrc=channel_layout=stereo:sample_rate=48000", cmd)
        self.assertTrue(cmd[-1].endswith("_10x_mute.mp4"))

    def test_workflow_uses_explicit_codec_name(self):
        task = WorkflowVideoTask()
        settings = {
            "video_codec": "libx264",
            "use_gpu": True,
            "has_audio": True,
        }
        cmd = task.build_command("clip.mov", settings)

        self.assertEqual(cmd[cmd.index("-c:v") + 1], "libx264")
        self.assertNotIn("h264_nvenc", cmd)

    def test_workflow_uses_configured_ffmpeg_path(self):
        task = WorkflowVideoTask()
        ffmpeg_path = os.path.join("custom-tools", "ffmpeg")
        cmd = task.build_command("clip.mov", {"ffmpeg_path": ffmpeg_path, "has_audio": True})

        self.assertEqual(cmd[0], resolve_ffmpeg_executable(ffmpeg_path, "ffmpeg"))

    def test_workflow_mp3_extracts_audio_only(self):
        task = WorkflowVideoTask()
        cmd = task.build_command(
            "clip.mov",
            {
                "output_container": "mp3",
                "audio_quality": "high",
                "trim_mode": "seconds",
                "trim_start_seconds": 2,
                "trim_end_seconds": 3,
                "duration": 20,
                "has_audio": True,
            },
        )

        self.assertIn("-ss", cmd)
        self.assertLess(cmd.index("-ss"), cmd.index("-i"))
        self.assertEqual(cmd[cmd.index("-ss") + 1], "2")
        self.assertIn("-t", cmd)
        self.assertLess(cmd.index("-t"), cmd.index("-i"))
        self.assertEqual(cmd[cmd.index("-t") + 1], "15")
        self.assertIn("0:a:0?", cmd)
        self.assertIn("-vn", cmd)
        self.assertEqual(cmd[cmd.index("-c:a") + 1], "libmp3lame")
        self.assertEqual(cmd[cmd.index("-b:a") + 1], "256k")
        self.assertNotIn("0:v:0", cmd)
        self.assertNotIn("-c:v", cmd)
        self.assertNotIn("-movflags", cmd)
        self.assertTrue(cmd[-1].endswith("_processed.mp3"))

    def test_workflow_mp3_without_audio_creates_bounded_silence(self):
        task = WorkflowVideoTask()
        cmd = task.build_command(
            "silent.mov",
            {
                "output_container": "mp3",
                "duration": 12,
                "has_audio": False,
            },
        )

        self.assertIn("anullsrc=channel_layout=stereo:sample_rate=48000", cmd)
        self.assertIn("1:a:0", cmd)
        self.assertIn("-vn", cmd)
        self.assertEqual(cmd[cmd.index("-c:a") + 1], "libmp3lame")
        t_indexes = [index for index, value in enumerate(cmd) if value == "-t"]
        self.assertEqual(cmd[t_indexes[-1] + 1], "12")
        self.assertGreater(t_indexes[-1], cmd.index("-i"))
        self.assertTrue(cmd[-1].endswith("_processed.mp3"))

    def test_workflow_webm_uses_web_codecs(self):
        task = WorkflowVideoTask()
        cmd = task.build_command(
            "clip.mov",
            {
                "output_container": "webm",
                "video_codec": "libx264",
                "has_audio": True,
            },
        )

        self.assertEqual(cmd[cmd.index("-c:v") + 1], "libvpx-vp9")
        self.assertIn("-b:v", cmd)
        self.assertEqual(cmd[cmd.index("-c:a") + 1], "libopus")
        self.assertTrue(cmd[-1].endswith("_processed.webm"))

    def test_workflow_wav_extracts_audio_without_bitrate(self):
        task = WorkflowVideoTask()
        cmd = task.build_command(
            "clip.mov",
            {
                "output_container": "wav",
                "audio_quality": "high",
                "has_audio": True,
            },
        )

        self.assertIn("-vn", cmd)
        self.assertEqual(cmd[cmd.index("-c:a") + 1], "pcm_s16le")
        self.assertNotIn("-b:a", cmd)
        self.assertTrue(cmd[-1].endswith("_processed.wav"))

    def test_workflow_gif_from_video_uses_palette_filtergraph(self):
        task = WorkflowVideoTask()
        cmd = task.build_command(
            "clip.mov",
            {
                "output_container": "gif",
                "gif_width": 480,
                "gif_fps": 12,
                "source_width": 1920,
                "source_height": 1080,
                "has_audio": True,
            },
        )

        filtergraph = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("[0:v]", filtergraph)
        self.assertIn("fps=12", filtergraph)
        self.assertIn("scale=480:-1:flags=lanczos", filtergraph)
        self.assertIn("palettegen", filtergraph)
        self.assertIn("paletteuse", filtergraph)
        self.assertTrue(cmd[-1].endswith("_processed.gif"))

    def test_workflow_gif_requires_video_input(self):
        task = WorkflowVideoTask()

        with self.assertRaises(ValueError):
            task.build_command(
                "sound.mp3",
                {
                    "output_container": "gif",
                    "gif_width": 640,
                    "gif_fps": 15,
                    "has_audio": True,
                    "source_width": 0,
                    "source_height": 0,
                },
            )

    def test_workflow_normalize_removes_legacy_gif_audio_mode(self):
        config = normalize_workflow_config({
            "output_container": "gif",
            "gif_source_mode": "audio_waveform",
        })

        self.assertNotIn("gif_source_mode", config)

    def test_workflow_grouped_filters_append_ffmpeg_filters(self):
        task = WorkflowVideoTask()
        cmd = task.build_command(
            "clip.mov",
            {
                "video_filter_1": "eq",
                "video_eq_brightness": 0.2,
                "video_eq_contrast": 1.4,
                "video_eq_saturation": 1.2,
                "video_filter_2": "denoise",
                "video_denoise_strength": 4,
                "audio_filter_1": "loudnorm",
                "audio_filter_2": "highpass",
                "audio_highpass_hz": 120,
                "advanced_video_filters": "curves=preset=medium_contrast",
                "advanced_audio_filters": "equalizer=f=1000:t=q:w=1:g=3",
                "has_audio": True,
            },
        )

        video_filters = cmd[cmd.index("-vf") + 1]
        audio_filters = cmd[cmd.index("-filter:a") + 1]
        self.assertIn("eq=brightness=0.2:contrast=1.4:saturation=1.2", video_filters)
        self.assertIn("hqdn3d=4:4:4:4", video_filters)
        self.assertIn("curves=preset=medium_contrast", video_filters)
        self.assertIn("loudnorm=I=-16:TP=-1.5:LRA=11", audio_filters)
        self.assertIn("highpass=f=120", audio_filters)
        self.assertIn("equalizer=f=1000:t=q:w=1:g=3", audio_filters)

    def test_ffmpeg_path_resolver_uses_platform_binary_names(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = os.path.join(tmpdir, "bin")
            os.makedirs(bin_dir)
            linux_ffmpeg = os.path.join(bin_dir, "ffmpeg")
            windows_ffmpeg = os.path.join(bin_dir, "ffmpeg.exe")
            open(linux_ffmpeg, "w").close()
            open(windows_ffmpeg, "w").close()

            self.assertEqual(
                resolve_ffmpeg_executable(tmpdir, "ffmpeg", platform="linux"),
                linux_ffmpeg,
            )
            self.assertEqual(
                resolve_ffmpeg_executable(tmpdir, "ffmpeg", platform="darwin"),
                linux_ffmpeg,
            )
            self.assertEqual(
                resolve_ffmpeg_executable(tmpdir, "ffmpeg", platform="win32"),
                windows_ffmpeg,
            )

    def test_ffmpeg_path_resolver_falls_back_to_path_when_local_binary_is_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(
                resolve_ffmpeg_executable(tmpdir, "ffmpeg", platform="linux"),
                "ffmpeg",
            )
            self.assertEqual(
                resolve_ffmpeg_executable(tmpdir, "ffprobe", platform="darwin"),
                "ffprobe",
            )

    def test_ffprobe_path_can_be_inferred_from_direct_ffmpeg_executable_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ffmpeg_path = os.path.join(tmpdir, "ffmpeg.exe")
            ffprobe_path = os.path.join(tmpdir, "ffprobe.exe")
            open(ffmpeg_path, "w").close()
            open(ffprobe_path, "w").close()

            self.assertEqual(
                resolve_ffmpeg_executable(ffmpeg_path, "ffprobe", platform="win32"),
                ffprobe_path,
            )

    def test_local_ffmpeg_available_requires_ffmpeg_and_ffprobe(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = os.path.join(tmpdir, "bin")
            os.makedirs(bin_dir)
            ffmpeg_path = os.path.join(bin_dir, "ffmpeg.exe")
            ffprobe_path = os.path.join(bin_dir, "ffprobe.exe")
            open(ffmpeg_path, "w").close()
            open(ffprobe_path, "w").close()

            self.assertTrue(local_ffmpeg_available(tmpdir, platform="win32"))

            os.remove(ffprobe_path)
            self.assertFalse(local_ffmpeg_available(tmpdir, platform="win32"))

    def test_ffmpeg_download_is_needed_only_without_local_or_system_pair(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertTrue(
                should_download_ffmpeg(
                    tmpdir,
                    platform="linux",
                    system_checker=lambda: False,
                )
            )
            self.assertFalse(
                should_download_ffmpeg(
                    tmpdir,
                    platform="linux",
                    system_checker=lambda: True,
                )
            )

            bin_dir = os.path.join(tmpdir, "bin")
            os.makedirs(bin_dir)
            open(os.path.join(bin_dir, "ffmpeg"), "w").close()
            open(os.path.join(bin_dir, "ffprobe"), "w").close()

            self.assertFalse(
                should_download_ffmpeg(
                    tmpdir,
                    platform="linux",
                    system_checker=lambda: False,
                )
            )

    def test_ffmpeg_download_selects_latest_stable_btbn_asset(self):
        assets = [
            {
                "name": "ffmpeg-master-latest-win64-gpl-shared.zip",
                "browser_download_url": "https://example.com/master.zip",
            },
            {
                "name": "ffmpeg-n7.1-latest-win64-gpl-shared-7.1.zip",
                "browser_download_url": "https://example.com/7.1.zip",
            },
            {
                "name": "ffmpeg-n8.1-latest-win64-gpl-shared-8.1.zip",
                "browser_download_url": "https://example.com/8.1.zip",
            },
        ]

        download = ffmpeg_downloads_for_platform(
            runtime_platform="win32",
            machine="AMD64",
            release_assets=assets,
        )[0]

        self.assertEqual(download.name, "ffmpeg-n8.1-latest-win64-gpl-shared-8.1.zip")
        self.assertEqual(download.url, "https://example.com/8.1.zip")

    def test_ffmpeg_download_falls_back_to_configured_stable_version(self):
        download = ffmpeg_downloads_for_platform(
            runtime_platform="linux",
            machine="x86_64",
            release_assets=[],
        )[0]

        self.assertEqual(
            download.name,
            f"ffmpeg-n{FFMPEG_STABLE_VERSION}-latest-linux64-gpl-shared-{FFMPEG_STABLE_VERSION}.tar.xz",
        )

    def test_ffmpeg_download_uses_apple_silicon_macos_builds(self):
        downloads = ffmpeg_downloads_for_platform(
            runtime_platform="darwin",
            machine="arm64",
            release_assets=[],
        )

        self.assertEqual([download.name for download in downloads], ["ffmpeg.zip", "ffprobe.zip"])
        self.assertEqual(
            [download.url for download in downloads],
            [
                "https://ffmpeg.martin-riedl.de/redirect/latest/macos/arm64/release/ffmpeg.zip",
                "https://ffmpeg.martin-riedl.de/redirect/latest/macos/arm64/release/ffprobe.zip",
            ],
        )

    def test_workflow_manual_crop_left(self):
        task = WorkflowVideoTask()
        settings = {
            "crop_mode": "manual",
            "crop_left": 100,
            "has_audio": True,
        }
        cmd = task.build_command("clip.mov", settings)

        self.assertIn("-vf", cmd)
        self.assertIn("crop=iw-100:ih:100:0", cmd)

    def test_workflow_trim_seconds(self):
        task = WorkflowVideoTask()
        settings = {
            "trim_mode": "seconds",
            "trim_start_seconds": 2,
            "trim_end_seconds": 3,
            "duration": 20,
            "has_audio": True,
        }
        cmd = task.build_command("clip.mov", settings)

        self.assertIn("-ss", cmd)
        self.assertLess(cmd.index("-ss"), cmd.index("-i"))
        self.assertEqual(cmd[cmd.index("-ss") + 1], "2")
        self.assertIn("-t", cmd)
        self.assertLess(cmd.index("-t"), cmd.index("-i"))
        self.assertEqual(cmd[cmd.index("-t") + 1], "15")

    def test_workflow_trim_frames_uses_source_fps(self):
        task = WorkflowVideoTask()
        settings = {
            "trim_mode": "frames",
            "trim_start_frames": 30,
            "trim_end_frames": 60,
            "source_fps": 30,
            "duration": 10,
            "has_audio": True,
        }
        cmd = task.build_command("clip.mov", settings)

        self.assertEqual(cmd[cmd.index("-ss") + 1], "1")
        self.assertEqual(cmd[cmd.index("-t") + 1], "7")

    def test_workflow_output_duration_uses_trim_and_speed(self):
        task = WorkflowVideoTask()
        settings = {
            "trim_mode": "seconds",
            "trim_start_seconds": 2,
            "trim_end_seconds": 2,
            "duration": 20,
            "speed": "2x",
        }

        self.assertAlmostEqual(task.get_output_duration(settings), 8)

if __name__ == '__main__':
    unittest.main()
