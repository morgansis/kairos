"""Canonical constants namespace for Kairos.

This module centralizes static values so they can be imported by other modules
without changing runtime behavior.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# ===================== Theme =====================
THEMES = {
    "晨霧灰藍 (沈穩)": {
        "MAIN": "#7D8C94",
        "HOVER": "#66747A",
        "BG": "#F4F6F7",
        "SUB": "#97A9B3",
        "STOP": "#A88B87",
        "TEXT": "#4A4F54",
        "LABEL": "#777777",
        "BORDER": "#E0E4E6",
        "PROGRESS": "#B0BDC4",
    },
    "乾燥玫瑰 (溫暖)": {
        "MAIN": "#A68B87",
        "HOVER": "#917774",
        "BG": "#F8F5F4",
        "SUB": "#B8A3A0",
        "STOP": "#C99B96",
        "TEXT": "#4E4848",
        "LABEL": "#777777",
        "BORDER": "#EBE4E2",
        "PROGRESS": "#D4B9B5",
    },
    "鼠尾草綠 (自然)": {
        "MAIN": "#8A9A8A",
        "HOVER": "#758575",
        "BG": "#F5F6F4",
        "SUB": "#A3B3A3",
        "STOP": "#C9A696",
        "TEXT": "#4E544E",
        "LABEL": "#777777",
        "BORDER": "#E4E6E4",
        "PROGRESS": "#B8C4B8",
    },
}

DEFAULT_THEME_NAME = "晨霧灰藍 (沈穩)"
VERSION = "2026-07-18"

# ===================== UI tuning =====================
UI_FONT_FAMILY = "Calibri"
UI_TITLE_FONT_SIZE = 24
UI_APP_FONT_SIZE = 15
UI_BUTTON_FONT_SIZE = 20
UI_SUBTITLE_FONT_SIZE = 11
UI_STATUS_FONT_SIZE = 14
UI_SUBTITLE_BUILD_HEIGHT = 24
UI_SUBTITLE_LINE_HEIGHT = 17
UI_ROW_HEIGHT = 30
UI_LOG_FONT_FAMILY = "Consolas"
UI_LOG_FONT_SIZE = 12

UI_MAIN_WINDOW_GEOMETRY = "1600x900"
UI_MAIN_WINDOW_MIN_WIDTH = 1280
UI_MAIN_WINDOW_MIN_HEIGHT = 720
UI_DIALOG_FOLDER_GEOMETRY = "640x540"
UI_DIALOG_FOLDER_MIN_WIDTH = 480
UI_DIALOG_FOLDER_MIN_HEIGHT = 380
UI_DIALOG_MSGBOX_WIDTH = 420
UI_DIALOG_MSGBOX_MIN_WIDTH = 400
UI_DIALOG_MSGBOX_MIN_HEIGHT = 240
UI_DIALOG_MSGBOX_MAX_WIDTH = 600
UI_DIALOG_MSGBOX_MAX_HEIGHT = 720
UI_DIALOG_MSGBOX_BASE_HEIGHT = 280
UI_DIALOG_MSGBOX_ROW_HEIGHT = 50
UI_DIALOG_MSGBOX_DYNAMIC_MAX_HEIGHT = 560

UI_FONT_SIZE_MSGBOX_ICON = 28
UI_FONT_SIZE_MSGBOX_TITLE = 16
UI_FONT_SIZE_MSGBOX_BODY = 14
UI_FONT_SIZE_MSGBOX_MAIN_BTN = 14
UI_FONT_SIZE_MSGBOX_REPORT_BTN = 13
UI_MSGBOX_WRAP_LENGTH = 360
UI_MSGBOX_MAIN_BTN_HEIGHT = 38
UI_MSGBOX_REPORT_BTN_HEIGHT = 36
UI_MSGBOX_REPORT_SCROLL_HEIGHT = 180

UI_FONT_SIZE_FOLDER_TITLE = 15
UI_FONT_SIZE_FOLDER_CHECK = 15
UI_FONT_SIZE_FOLDER_ACTION = 14
UI_FONT_SIZE_FOLDER_BOTTOM_BTN = 16
UI_FOLDER_ACTION_BTN_WIDTH = 90
UI_FOLDER_ACTION_BTN_HEIGHT = 32
UI_FOLDER_BOTTOM_BTN_HEIGHT = 42

UI_SMALL_BTN_WIDTH = 50
UI_THEME_MENU_WIDTH = 160
UI_PROGRESS_HEIGHT = 14
UI_LOGBOX_HEIGHT = 150
UI_START_BTN_HEIGHT = 55
UI_START_MAXIMIZED = True

# ===================== Runtime paths =====================
if getattr(sys, "frozen", False):
    APPLICATION_PATH = os.path.dirname(sys.executable)
    BASE_NAME = os.path.splitext(os.path.basename(sys.executable))[0]
else:
    main_file = getattr(sys.modules.get("__main__"), "__file__", None)
    if main_file:
        APPLICATION_PATH = os.path.dirname(os.path.abspath(main_file))
        BASE_NAME = os.path.splitext(os.path.basename(main_file))[0]
    else:
        APPLICATION_PATH = str(Path(__file__).resolve().parent.parent)
        BASE_NAME = "kairos"

CONFIG_FILE = os.path.join(APPLICATION_PATH, f"{BASE_NAME}.ini")

# ===================== Media constants =====================
DATE_TIME_ORIGINAL_TAG = 36867

STANDARD_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
    ".heic",
    ".heif",
}
RAW_EXTENSIONS = {".dng", ".cr2", ".cr3", ".nef", ".arw", ".raf", ".orf", ".rw2", ".psd"}
VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".wmv",
    ".flv",
    ".m4v",
    ".3gp",
    ".mts",
    ".m2ts",
    ".mpg",
}
GEO_LOOKUP_EXTENSIONS = {".jpg", ".jpeg", ".tif", ".tiff", ".heic", ".heif"}
EXCLUDE_DIR_KEYWORDS = [
    "helper.lrdata",
    "previews.lrdata",
    "smart previews.lrdata",
    "lrcat-data",
    "System Volume Information",
    "$RECYCLE.BIN",
]
IGNORED_EXTENSIONS = [
    ".lrcat",
    ".lrdata",
    ".tmp",
    ".ds_store",
    ".db",
    ".xls",
    ".xlsx",
    ".doc",
    ".docx",
    ".pdf",
    ".html",
    ".csv",
    ".txt",
    ".json",
    ".js",
    ".css",
]
PLACEHOLDER = "-"

TIMESTAMP_STEM_RE = re.compile(
    r"^(?P<base>\d{4}-\d{2}-\d{2} \d{2}\.\d{2}\.\d{2})(?P<suffix>-(?:\d{1,6}(?:-\d+)?|u\d+|c\d+))?$"
)
EXIF_DATETIME_FORMAT = "%Y:%m:%d %H:%M:%S"
EXIF_DATETIME_TAG_KEYS = ("EXIF DateTimeOriginal", "EXIF DateTimeDigitized", "Image DateTime")
EXIF_SUBSEC_TAG_KEYS = ("EXIF SubSecTimeOriginal", "EXIF SubSecTime", "EXIF SubSecTimeDigitized")
EXIF_SERIAL_TAG_KEYS = (
    "EXIF BodySerialNumber",
    "Image BodySerialNumber",
    "MakerNote SerialNumber",
    "EXIF SerialNumber",
)

__all__ = [
    "THEMES",
    "DEFAULT_THEME_NAME",
    "VERSION",
    "UI_FONT_FAMILY",
    "UI_TITLE_FONT_SIZE",
    "UI_APP_FONT_SIZE",
    "UI_BUTTON_FONT_SIZE",
    "UI_SUBTITLE_FONT_SIZE",
    "UI_STATUS_FONT_SIZE",
    "UI_SUBTITLE_BUILD_HEIGHT",
    "UI_SUBTITLE_LINE_HEIGHT",
    "UI_ROW_HEIGHT",
    "UI_LOG_FONT_FAMILY",
    "UI_LOG_FONT_SIZE",
    "UI_MAIN_WINDOW_GEOMETRY",
    "UI_MAIN_WINDOW_MIN_WIDTH",
    "UI_MAIN_WINDOW_MIN_HEIGHT",
    "UI_DIALOG_FOLDER_GEOMETRY",
    "UI_DIALOG_FOLDER_MIN_WIDTH",
    "UI_DIALOG_FOLDER_MIN_HEIGHT",
    "UI_DIALOG_MSGBOX_WIDTH",
    "UI_DIALOG_MSGBOX_MIN_WIDTH",
    "UI_DIALOG_MSGBOX_MIN_HEIGHT",
    "UI_DIALOG_MSGBOX_MAX_WIDTH",
    "UI_DIALOG_MSGBOX_MAX_HEIGHT",
    "UI_DIALOG_MSGBOX_BASE_HEIGHT",
    "UI_DIALOG_MSGBOX_ROW_HEIGHT",
    "UI_DIALOG_MSGBOX_DYNAMIC_MAX_HEIGHT",
    "UI_FONT_SIZE_MSGBOX_ICON",
    "UI_FONT_SIZE_MSGBOX_TITLE",
    "UI_FONT_SIZE_MSGBOX_BODY",
    "UI_FONT_SIZE_MSGBOX_MAIN_BTN",
    "UI_FONT_SIZE_MSGBOX_REPORT_BTN",
    "UI_MSGBOX_WRAP_LENGTH",
    "UI_MSGBOX_MAIN_BTN_HEIGHT",
    "UI_MSGBOX_REPORT_BTN_HEIGHT",
    "UI_MSGBOX_REPORT_SCROLL_HEIGHT",
    "UI_FONT_SIZE_FOLDER_TITLE",
    "UI_FONT_SIZE_FOLDER_CHECK",
    "UI_FONT_SIZE_FOLDER_ACTION",
    "UI_FONT_SIZE_FOLDER_BOTTOM_BTN",
    "UI_FOLDER_ACTION_BTN_WIDTH",
    "UI_FOLDER_ACTION_BTN_HEIGHT",
    "UI_FOLDER_BOTTOM_BTN_HEIGHT",
    "UI_SMALL_BTN_WIDTH",
    "UI_THEME_MENU_WIDTH",
    "UI_PROGRESS_HEIGHT",
    "UI_LOGBOX_HEIGHT",
    "UI_START_BTN_HEIGHT",
    "UI_START_MAXIMIZED",
    "APPLICATION_PATH",
    "BASE_NAME",
    "CONFIG_FILE",
    "DATE_TIME_ORIGINAL_TAG",
    "STANDARD_EXTENSIONS",
    "RAW_EXTENSIONS",
    "VIDEO_EXTENSIONS",
    "GEO_LOOKUP_EXTENSIONS",
    "EXCLUDE_DIR_KEYWORDS",
    "IGNORED_EXTENSIONS",
    "PLACEHOLDER",
    "TIMESTAMP_STEM_RE",
    "EXIF_DATETIME_FORMAT",
    "EXIF_DATETIME_TAG_KEYS",
    "EXIF_SUBSEC_TAG_KEYS",
    "EXIF_SERIAL_TAG_KEYS",
]
