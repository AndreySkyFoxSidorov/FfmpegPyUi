import csv
import os


DEFAULT_LANGUAGE = "EN"
TRANSLATIONS_FILE = os.path.join(os.path.dirname(__file__), "localization.csv")

LANGUAGE = DEFAULT_LANGUAGE
LANGUAGES = []
TRANSLATIONS = {}
LANGUAGE_DISPLAY_NAMES = {
    "EN": "English",
    "UK": "Українська",
    "RU": "Русский",
    "ES": "Español",
    "IT": "Italiano",
    "DE": "Deutsch",
    "KO": "한국어",
    "NL": "Nederlands",
    "FR": "Français",
    "PT": "Português",
    "ZH_TW": "繁體中文",
    "ZH": "简体中文",
    "PL": "Polski",
    "CS": "Čeština",
}


WORKFLOW_OPTIONS = {
    "output_container": [
        {"value": "mp4", "label_key": "option.output_container.mp4"},
        {"value": "mov", "label_key": "option.output_container.mov"},
        {"value": "mp3", "label_key": "option.output_container.mp3"},
    ],
    "resolution_mode": [
        {"value": "original", "label_key": "option.resolution_mode.original"},
        {"value": "fit_1080", "label_key": "option.resolution_mode.fit_1080"},
        {"value": "fit_720", "label_key": "option.resolution_mode.fit_720"},
        {"value": "square_720", "label_key": "option.resolution_mode.square_720"},
        {"value": "custom", "label_key": "option.resolution_mode.custom"},
    ],
    "quality_profile": [
        {"value": "draft", "label_key": "option.quality_profile.draft"},
        {"value": "small", "label_key": "option.quality_profile.small"},
        {"value": "balanced", "label_key": "option.quality_profile.balanced"},
        {"value": "high", "label_key": "option.quality_profile.high"},
        {"value": "maximum", "label_key": "option.quality_profile.maximum"},
    ],
    "encoding_speed": [
        {"value": "fast", "label_key": "option.encoding_speed.fast"},
        {"value": "balanced", "label_key": "option.encoding_speed.balanced"},
        {"value": "smaller_file", "label_key": "option.encoding_speed.smaller_file"},
    ],
    "video_codec": [
        {"value": "libx264", "label_key": "option.video_codec.libx264"},
        {"value": "libx265", "label_key": "option.video_codec.libx265"},
        {"value": "h264_nvenc", "label_key": "option.video_codec.h264_nvenc"},
        {"value": "hevc_nvenc", "label_key": "option.video_codec.hevc_nvenc"},
        {"value": "libvpx-vp9", "label_key": "option.video_codec.libvpx-vp9"},
        {"value": "copy", "label_key": "option.video_codec.copy"},
    ],
    "crop_mode": [
        {"value": "none", "label_key": "option.crop_mode.none"},
        {"value": "manual", "label_key": "option.crop_mode.manual"},
    ],
    "trim_mode": [
        {"value": "none", "label_key": "option.trim_mode.none"},
        {"value": "seconds", "label_key": "option.trim_mode.seconds"},
        {"value": "frames", "label_key": "option.trim_mode.frames"},
    ],
    "fps_mode": [
        {"value": "source", "label_key": "option.fps_mode.source"},
        {"value": "24", "label_key": "option.fps_mode.24"},
        {"value": "30", "label_key": "option.fps_mode.30"},
        {"value": "60", "label_key": "option.fps_mode.60"},
    ],
    "speed": [
        {"value": "1x", "label_key": "option.speed.1x"},
        {"value": "2x", "label_key": "option.speed.2x"},
        {"value": "4x", "label_key": "option.speed.4x"},
        {"value": "8x", "label_key": "option.speed.8x"},
        {"value": "10x", "label_key": "option.speed.10x"},
        {"value": "16x", "label_key": "option.speed.16x"},
    ],
    "audio_mode": [
        {"value": "keep_or_silent", "label_key": "option.audio_mode.keep_or_silent"},
        {"value": "mute", "label_key": "option.audio_mode.mute"},
    ],
    "audio_quality": [
        {"value": "compact", "label_key": "option.audio_quality.compact"},
        {"value": "normal", "label_key": "option.audio_quality.normal"},
        {"value": "high", "label_key": "option.audio_quality.high"},
    ],
}

WORKFLOW_SECTIONS = [
    {
        "title_key": "section.output.title",
        "description_key": "section.output.description",
        "fields": [
            {
                "key": "output_container",
                "type": "choice",
                "options": "output_container",
                "label_key": "field.output_container.label",
                "description_key": "field.output_container.description",
            },
            {
                "key": "output_suffix",
                "type": "entry",
                "value_type": "text",
                "label_key": "field.output_suffix.label",
                "description_key": "field.output_suffix.description",
            },
        ],
    },
    {
        "title_key": "section.size_speed.title",
        "description_key": "section.size_speed.description",
        "fields": [
            {
                "key": "resolution_mode",
                "type": "choice",
                "options": "resolution_mode",
                "label_key": "field.resolution_mode.label",
                "description_key": "field.resolution_mode.description",
            },
            {
                "key": "custom_width",
                "type": "entry",
                "value_type": "int",
                "label_key": "field.custom_width.label",
                "description_key": "field.custom_width.description",
            },
            {
                "key": "custom_height",
                "type": "entry",
                "value_type": "int",
                "label_key": "field.custom_height.label",
                "description_key": "field.custom_height.description",
            },
            {
                "key": "fps_mode",
                "type": "choice",
                "options": "fps_mode",
                "label_key": "field.fps_mode.label",
                "description_key": "field.fps_mode.description",
            },
            {
                "key": "speed",
                "type": "choice",
                "options": "speed",
                "label_key": "field.speed.label",
                "description_key": "field.speed.description",
            },
        ],
    },
    {
        "title_key": "section.crop.title",
        "description_key": "section.crop.description",
        "fields": [
            {
                "key": "crop_mode",
                "type": "choice",
                "options": "crop_mode",
                "label_key": "field.crop_mode.label",
                "description_key": "field.crop_mode.description",
            },
            {
                "key": "crop_left",
                "type": "entry",
                "value_type": "int",
                "label_key": "field.crop_left.label",
                "description_key": "field.crop_left.description",
            },
            {
                "key": "crop_right",
                "type": "entry",
                "value_type": "int",
                "label_key": "field.crop_right.label",
                "description_key": "field.crop_right.description",
            },
            {
                "key": "crop_top",
                "type": "entry",
                "value_type": "int",
                "label_key": "field.crop_top.label",
                "description_key": "field.crop_top.description",
            },
            {
                "key": "crop_bottom",
                "type": "entry",
                "value_type": "int",
                "label_key": "field.crop_bottom.label",
                "description_key": "field.crop_bottom.description",
            },
        ],
    },
    {
        "title_key": "section.trim.title",
        "description_key": "section.trim.description",
        "fields": [
            {
                "key": "trim_mode",
                "type": "choice",
                "options": "trim_mode",
                "label_key": "field.trim_mode.label",
                "description_key": "field.trim_mode.description",
            },
            {
                "key": "trim_start_seconds",
                "type": "entry",
                "value_type": "float",
                "label_key": "field.trim_start_seconds.label",
                "description_key": "field.trim_start_seconds.description",
            },
            {
                "key": "trim_end_seconds",
                "type": "entry",
                "value_type": "float",
                "label_key": "field.trim_end_seconds.label",
                "description_key": "field.trim_end_seconds.description",
            },
            {
                "key": "trim_start_frames",
                "type": "entry",
                "value_type": "int",
                "label_key": "field.trim_start_frames.label",
                "description_key": "field.trim_start_frames.description",
            },
            {
                "key": "trim_end_frames",
                "type": "entry",
                "value_type": "int",
                "label_key": "field.trim_end_frames.label",
                "description_key": "field.trim_end_frames.description",
            },
        ],
    },
    {
        "title_key": "section.quality.title",
        "description_key": "section.quality.description",
        "fields": [
            {
                "key": "quality_profile",
                "type": "choice",
                "options": "quality_profile",
                "label_key": "field.quality_profile.label",
                "description_key": "field.quality_profile.description",
            },
            {
                "key": "encoding_speed",
                "type": "choice",
                "options": "encoding_speed",
                "label_key": "field.encoding_speed.label",
                "description_key": "field.encoding_speed.description",
            },
            {
                "key": "video_codec",
                "type": "choice",
                "options": "video_codec",
                "label_key": "field.video_codec.label",
                "description_key": "field.video_codec.description",
            },
        ],
    },
    {
        "title_key": "section.audio.title",
        "description_key": "section.audio.description",
        "fields": [
            {
                "key": "audio_mode",
                "type": "choice",
                "options": "audio_mode",
                "label_key": "field.audio_mode.label",
                "description_key": "field.audio_mode.description",
            },
            {
                "key": "audio_quality",
                "type": "choice",
                "options": "audio_quality",
                "label_key": "field.audio_quality.label",
                "description_key": "field.audio_quality.description",
            },
            {
                "key": "audio_volume",
                "type": "slider",
                "min": 0.0,
                "max": 3.0,
                "steps": 30,
                "label_key": "field.audio_volume.label",
                "description_key": "field.audio_volume.description",
            },
        ],
    },
]

BUILTIN_SCHEME_LABEL_KEYS = {
    "MP4 для отправки": "scheme.mp4_send",
    "Маленький файл": "scheme.small_file",
    "Высокое качество": "scheme.high_quality",
    "Ускорить 4x со звуком": "scheme.speed_4x_sound",
    "Ускорить 10x без звука": "scheme.speed_10x_mute",
    "Квадрат для WebGL": "scheme.square_webgl",
    "MOV для монтажа": "scheme.mov_edit",
}


def read_translation_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            return [], {}

        key_column = fieldnames[0]
        languages = [column.strip() for column in fieldnames[1:] if column.strip()]
        translations = {}

        for row in reader:
            key = (row.get(key_column) or "").strip()
            if not key:
                continue
            translations[key] = {}
            for language in languages:
                value = row.get(language, "")
                translations[key][language] = value.replace("\\n", "\n") if value is not None else ""

        return languages, translations


def load_translations(path=TRANSLATIONS_FILE):
    global LANGUAGES, TRANSLATIONS, LANGUAGE
    LANGUAGES, TRANSLATIONS = read_translation_csv(path)
    if not LANGUAGES:
        LANGUAGES = [DEFAULT_LANGUAGE]
    LANGUAGE = _normalize_language(LANGUAGE)


def available_languages():
    return list(LANGUAGES)


def language_label(language):
    code = _find_language(language) or str(language or DEFAULT_LANGUAGE).strip()
    return LANGUAGE_DISPLAY_NAMES.get(code, code)


def available_language_labels():
    return [language_label(language) for language in LANGUAGES]


def get_language():
    return LANGUAGE


def set_language(language):
    global LANGUAGE
    LANGUAGE = _normalize_language(language)
    return LANGUAGE


def _normalize_language(language):
    requested = _find_language(language)
    if requested:
        return requested
    requested = str(language or DEFAULT_LANGUAGE).strip()
    for available in LANGUAGES:
        if available.lower() == requested.lower():
            return available
    for available in LANGUAGES:
        if available.lower() == DEFAULT_LANGUAGE.lower():
            return available
    return LANGUAGES[0] if LANGUAGES else DEFAULT_LANGUAGE


def _find_language(language):
    requested = str(language or DEFAULT_LANGUAGE).strip()
    requested_lower = requested.casefold()
    for available in LANGUAGES:
        if available.casefold() == requested_lower:
            return available
    for available in LANGUAGES:
        if LANGUAGE_DISPLAY_NAMES.get(available, available).casefold() == requested_lower:
            return available
    return None


def t(key, lang=None, **kwargs):
    language = _normalize_language(lang or LANGUAGE)
    values = TRANSLATIONS.get(key, {})
    text = values.get(language) or values.get(DEFAULT_LANGUAGE) or values.get("EN") or key
    return text.format(**kwargs) if kwargs else text


def section_title(section):
    return t(section.get("title_key", ""))


def section_description(section):
    return t(section.get("description_key", ""))


def field_label(field):
    return t(field.get("label_key", ""))


def field_description(field):
    return t(field.get("description_key", ""))


def option_labels(option_key):
    return [t(item["label_key"]) for item in WORKFLOW_OPTIONS[option_key]]


def option_label(option_key, value):
    for item in WORKFLOW_OPTIONS[option_key]:
        if item["value"] == value:
            return t(item["label_key"])
    return t(WORKFLOW_OPTIONS[option_key][0]["label_key"])


def option_value(option_key, label):
    label = str(label)
    for item in WORKFLOW_OPTIONS[option_key]:
        if label == item["value"]:
            return item["value"]
        for language in LANGUAGES:
            if label == t(item["label_key"], lang=language):
                return item["value"]
    return WORKFLOW_OPTIONS[option_key][0]["value"]


def scheme_label(name):
    key = BUILTIN_SCHEME_LABEL_KEYS.get(name)
    return t(key) if key else name


def scheme_value(label):
    label = str(label)
    for name, key in BUILTIN_SCHEME_LABEL_KEYS.items():
        if label == name:
            return name
        for language in LANGUAGES:
            if label == t(key, lang=language):
                return name
    return label


load_translations()
