from dataclasses import dataclass
from pathlib import Path


BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)


# =====================================================
# PDF
# =====================================================

PDF_DPI = 150
RETRY_DPI = 200
TOP_LEFT_DPI = 420

PDF_IMAGE_FORMAT = "RGB"
PDF_RENDER_ALPHA = False


@dataclass
class PageSettings:
    width_mm: float = 20.0
    height_mm: float = 20.0
    margin_mm: float = 1.5
    code_size_mm: float = 17.0
    horizontal_shift_mm: float = -1.0
    vertical_shift_mm: float = 0.0


PAGE_SETTINGS = PageSettings()


def get_page_settings():
    return {
        "page_width_mm": (
            PAGE_SETTINGS.width_mm
        ),
        "page_height_mm": (
            PAGE_SETTINGS.height_mm
        ),
        "margin_mm": (
            PAGE_SETTINGS.margin_mm
        ),
        "code_size_mm": (
            PAGE_SETTINGS.code_size_mm
        ),
        "horizontal_shift_mm": (
            PAGE_SETTINGS.horizontal_shift_mm
        ),
        "vertical_shift_mm": (
            PAGE_SETTINGS.vertical_shift_mm
        ),
    }


def update_page_settings(
    width_mm=None,
    height_mm=None,
    margin_mm=None,
    code_size_mm=None,
    horizontal_shift_mm=None,
    vertical_shift_mm=None,
):
    if width_mm is not None:
        PAGE_SETTINGS.width_mm = float(
            width_mm
        )

    if height_mm is not None:
        PAGE_SETTINGS.height_mm = float(
            height_mm
        )

    if margin_mm is not None:
        PAGE_SETTINGS.margin_mm = float(
            margin_mm
        )

    if code_size_mm is not None:
        PAGE_SETTINGS.code_size_mm = float(
            code_size_mm
        )

    if horizontal_shift_mm is not None:
        PAGE_SETTINGS.horizontal_shift_mm = (
            float(horizontal_shift_mm)
        )

    if vertical_shift_mm is not None:
        PAGE_SETTINGS.vertical_shift_mm = (
            float(vertical_shift_mm)
        )


def reset_page_settings():
    PAGE_SETTINGS.width_mm = 20.0
    PAGE_SETTINGS.height_mm = 20.0
    PAGE_SETTINGS.margin_mm = 1.5
    PAGE_SETTINGS.code_size_mm = 17.0
    PAGE_SETTINGS.horizontal_shift_mm = -1.0
    PAGE_SETTINGS.vertical_shift_mm = 0.0


# =====================================================
# Распознавание
# =====================================================

DECODE_TIMEOUT = 250
DECODE_SHRINK = 2

USE_PYLIBDMTX = True
USE_OPENCV_FALLBACK = True
FALLBACK_ONLY_IF_EMPTY = True


# =====================================================
# Изображения
# =====================================================

MAX_IMAGE_SIZE = 1800
MAX_UPSCALED_SIZE = 2400
MIN_IMAGE_SIZE = 80

IMAGE_MODE = "RGB"


# =====================================================
# Предварительная обработка
# =====================================================

ENABLE_PREPROCESSING = True

PREPROCESS_CONTRAST = True
PREPROCESS_SHARPNESS = True
PREPROCESS_BRIGHTNESS = True
PREPROCESS_GRAYSCALE = True
PREPROCESS_THRESHOLD = True
PREPROCESS_ADAPTIVE_THRESHOLD = True
PREPROCESS_AUTO_CROP = True


# =====================================================
# Режим обработки фотографий
# =====================================================

PHOTO_VARIANTS_ENABLED = True

PHOTO_UPSCALE_FACTORS = [
    1,
    2,
    3,
]

PHOTO_ROTATIONS = [
    0,
    90,
    180,
    270,
]

PHOTO_CONTRAST_VALUES = [
    1.0,
    1.4,
    1.8,
]

PHOTO_SHARPNESS_VALUES = [
    1.0,
    1.5,
    2.0,
]


# =====================================================
# Быстрые варианты
# =====================================================

FAST_UPSCALE_FACTORS = [
    2,
    1,
]

FAST_PAD_FACTORS = [
    0,
    20,
]

FAST_CROP_SCAN_VALUES = [
    0,
]

FAST_STABLE_PASSES = 2


# =====================================================
# Точные варианты
# =====================================================

SAFE_UPSCALE_FACTORS = [
    1,
    2,
]

SAFE_PAD_FACTORS = [
    0,
    20,
    40,
]

SAFE_CROP_SCAN_VALUES = [
    0,
    6,
    12,
]


# =====================================================
# Варианты для нескольких кодов
# =====================================================

MULTI_UPSCALE_FACTORS = [
    1,
    2,
    3,
    4,
]

MULTI_PAD_FACTORS = [
    0,
    20,
    40,
]

MULTI_CROP_SCAN_VALUES = [
    0,
    6,
    12,
]

MULTI_GRID_ROWS = 3
MULTI_GRID_COLUMNS = 3
MULTI_GRID_OVERLAP = 0.35

MULTI_MIN_CODES_TO_FINISH = 2


# =====================================================
# Повторная обработка
# =====================================================

RETRY_ENABLED = True
MAX_RETRY_PASSES = 1

RETRY_ON_EMPTY_RESULT = True
RETRY_ON_DECODE_ERROR = True

RETRY_USE_HIGHER_DPI = True
RETRY_USE_GRID = True
RETRY_USE_TOP_LEFT = True

RETRY_ONLY_FAILED_PAGES = True


# =====================================================
# Остановка
# =====================================================

STOP_ENABLED = True
STOP_CHECK_ENABLED = True


# =====================================================
# Прогресс
# =====================================================

PROGRESS_ENABLED = True
PROGRESS_UPDATE_INTERVAL = 0.1

SHOW_CURRENT_FILE = True
SHOW_CURRENT_PAGE = True
SHOW_CURRENT_VARIANT = True
SHOW_CURRENT_STAGE = True


# =====================================================
# Кэширование
# =====================================================

CACHE_ENABLED = True
CACHE_RENDERED_PAGES = True
CACHE_DECODED_VARIANTS = True

CACHE_MAX_PAGES = 20


# =====================================================
# Отчёты
# =====================================================

REPORTS_DIR = (
    BASE_DIR
    / "reports"
)

REPORTS_OUTPUT_DIR = (
    REPORTS_DIR
    / "output"
)

JSON_REPORT_ENABLED = True
CSV_REPORT_ENABLED = True

SAVE_FAILED_PAGES = True
SAVE_MARKED_IMAGES = True
SAVE_DECODE_DEBUG_IMAGES = False

FAILED_PAGES_DIR = (
    REPORTS_OUTPUT_DIR
    / "failed_pages"
)

MARKED_IMAGES_DIR = (
    REPORTS_OUTPUT_DIR
    / "marked_images"
)

DEBUG_IMAGES_DIR = (
    REPORTS_OUTPUT_DIR
    / "debug"
)

REPORT_JSON_NAME = (
    "scan_report.json"
)

REPORT_CSV_NAME = (
    "scan_report.csv"
)


# =====================================================
# Результаты распознавания
# =====================================================

SAVE_RAW_CODES = True
SAVE_UNIQUE_CODES = True
SAVE_DUPLICATES = True

SAVE_DECODER_METHOD = True
SAVE_VARIANT_NAME = True
SAVE_PAGE_NUMBER = True
SAVE_PROCESSING_TIME = True
SAVE_ERROR_TEXT = True

SHOW_GROUP_SEPARATOR_AS = "<GS>"


# =====================================================
# GS1 DataMatrix
# =====================================================

GS1_ENABLED = True

GS1_GROUP_SEPARATOR = "\x1d"

GS1_SAVE_PARSED_FIELDS = True
GS1_VALIDATE_GTIN = True
GS1_VALIDATE_APPLICATION_IDENTIFIERS = True


# =====================================================
# Разметка найденных кодов
# =====================================================

MARK_CODE_BOXES = True
MARK_CODE_LABELS = True
MARK_CODE_METHOD = True

MARK_COLOR = (
    0,
    200,
    0,
)

MARK_WIDTH = 3


# =====================================================
# Поддерживаемые файлы
# =====================================================

IMAGE_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tif",
    ".tiff",
    ".gif",
}

PDF_EXTS = {
    ".pdf",
}


# =====================================================
# Режимы обработки
# =====================================================

DEFAULT_MODE = "fast"

SUPPORTED_MODES = {
    "auto",
    "fast",
    "multi",
    "safe",
    "photo",
}


# =====================================================
# Память успешных вариантов
# =====================================================

MEMORY_FILE = (
    BASE_DIR
    / "dmx_memory.json"
)


# =====================================================
# Настройки интерфейса
# =====================================================

SETTINGS_FILE = (
    BASE_DIR
    / "dmx_settings.json"
)


# =====================================================
# Итоговый PDF
# =====================================================

OUTPUT_PDF_SUFFIX = (
    " (все коды).pdf"
)

PDF_PAGE_SIZE = "CUSTOM"
PDF_CODE_FONT_SIZE = 8
PDF_CODE_MARGIN = 20
PDF_CODE_WRAP_LENGTH = 90


# =====================================================
# Служебные функции
# =====================================================

def ensure_directories():
    directories = [
        REPORTS_DIR,
        REPORTS_OUTPUT_DIR,
        FAILED_PAGES_DIR,
        MARKED_IMAGES_DIR,
        DEBUG_IMAGES_DIR,
    ]

    for directory in directories:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )


ensure_directories()