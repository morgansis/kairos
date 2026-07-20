"""
================================================================================
媒體檔案自動化整理與劇院級檢視工具 (Media Organizer Pro) - v2026-07-20
================================================================================
Designed for creators, this tool provides safe, lossless media archiving
with millisecond burst protection, intelligent deduplication, and a full-screen
interactive lightbox experience.

【軟體功能與特色說明書】
本軟體專為攝影師、工程師與內容創作者設計，用於將散落各處、命名雜亂的相片（含 RAW 檔）
與動態影片進行無損自動化分類、重新命名、去重複過濾，並產出高互動性的視覺化檢視報告。
程式執行全程採取「安全複製」模式，絕不更動、破壞或刪除使用者的原始來源檔案。

一、 核心自動化與整理機制：
  1. 智慧多目錄彈窗選取：
     點擊瀏覽來源目錄時，系統自動展開彈窗，列出該母目錄底下的所有子資料夾，使用者可勾選
     多個子資料夾進行批次順序處理，省去重複操作的繁瑣流程。
  2. 毫秒級連拍保護與物理去重 (Smart Burst & Duplicate Protection)：
     - 第一層物理實體過濾：在處理前自動進行檔案大小 (Bytes) 與完整 SHA-256 內容對比，
       若確認為完全相同的實體檔案則直接優雅略過，杜絕重複執行時產生冗餘的 `-1` 檔案。
     - 第二層毫秒連拍辨識：透過 EXIF 亞秒/毫秒 (SubSecTimeOriginal) + 相機序號 + 小於 1 秒間隔，
       區分連拍序列與同秒衝突；同秒連拍衝突優先掛上三位毫秒後綴，避免前後秒邊界被誤判。
     - 第三層修改時間裁決：非連拍同名衝突則依修改時間 (mtime) 保留較新修圖版本在前台。
  3. 彈性時間分類與更新取代機制：
     - 支援將檔名正規化為「YYYY-MM-DD HH.MM.SS」標準格式，並自動依年份與月份建立資料夾。
     - 支援彈性「地理位置解析開關」，關閉時極速掃描；開啟時將地圖資訊整合進月份視覺報表。
     - 若勾選「強制覆蓋」，同毫秒重複只保留一張在上層（名稱正規化），其餘移至 `candidate`
       並以 `-1/-2...` 尾綴保留。
  4. 外掛異常精準攔截與報表整合：
     - 自動捕捉 exifread、Pillow、hachoir 等第三方解析外掛所產生的警告與錯誤，
       直接關聯至當前處理檔案並同步整合進 CSV/HTML 報表中的「插件訊息」欄位，不再繁雜刷屏。

二、 雙流空間快取與批量解析 (Dual-Stream Spatial Cache & Batch Geocoding)：
  1. 智能快取繼承機制 (Snowball Inheritance)：
     - 執行前自動向「來源目錄」、「來源上一層母目錄」及「輸出目錄」搜尋並繼承 `_manifest_geo.json`，
       多源歸檔或二次整理時可於毫秒內重用歷史反查成果，達成零運算極速重用。
  2. 非對稱雙流座標設計：
     - 行政地名反查 (Key) 採用小數點後 3 位精度 (約 100 米)，同景點千張照片僅需反查一次。
     - 導航地圖網址 (URL) 現場直接由 EXIF 生成小數點後 4 位精度 (約 10 米)，導航準確毫無耗損。
  3. 極速 C++ 批量矩陣查詢：
     - 廢除單筆查詢迴圈，將所有未命中的座標打包為 List，一次送入 reverse_geocoder 的 C++
       多執行緒 K-D Tree 進行批量反查，效能提升數十倍。
  4. 全域處理數據看板 (Performance Dashboard)：
     - 總報表與各月份 HTML 報告頂端均內嵌精美戰情看板，即時展示處理耗時、複製去重統計、
       地理快取命中率 (%) 與 C++ 批量查詢次數。

三、 劇院級互動 HTML 報告與懸浮燈箱 (Interactive Report & Overlay Lightbox)：
  1. 根目錄集中式報告與免外掛總報表
     - 各月份處理結果會直接於「輸出根目錄」生成單一 HTML 視覺化報告（如 2026_04_media_report.html），
       內嵌 Intersection Observer 延遲載入 (Lazy Load) 技術與地圖跳轉按鈕，萬張照片也順暢不卡頓。
     - 同時產出 `_index.html` 免外掛互動式總報表，支援關鍵字搜尋與分類過濾。
  2. 究極滿版懸浮燈箱 (100vw / 100vh Overlay Lightbox)：
     - 點擊照片或影片即進入全螢幕燈箱，畫面直接擴展至瀏覽器視窗的 100% 極限滿版，絕不浪費螢幕空間。
     - 控制資訊採取「半透明漸層懸浮列 (Overlay)」設計，優雅重疊於影像上下兩端，不干擾主體視覺。
     - 影片直接串流：內嵌 <video> 播放器，支援 MP4、MOV 等格式在燈箱中直接高畫質播放。
  3. 跨平台沙盒突破與安全清理機制：
     - 瀏覽器端提供「🗑️ 標記為待刪除」功能。為突破瀏覽器本地沙盒安全限制，報告上方提供
       「📋 複製 Windows 刪除指令」與「📋 複製 macOS/Linux 刪除指令」一鍵按鈕。
     - 點擊後即可將對應的 `del /f /q` 或 `rm -f` 終端機語法複製到剪貼簿，直接打開終端機
       貼上即可一鍵清除所有標記的廢片。

四、 現代化介面與安全中斷機制：
  1. 莫蘭迪美學 UI：全系列視窗與彈窗皆完美整合晨霧灰藍、乾燥玫瑰、鼠尾草綠等專業配色，
     字體間距嚴格調校對齊，提供視覺舒適的深層體驗。
  2. 精巧計數器與報告啟動器：處理完畢後，系統會彈出視覺俐落的精緻通知視窗，底端自動產出
     「🌐 開啟 [月份] 報告」動態按鈕，點擊立刻調用系統預設瀏覽器開啟檢視。
  3. 安全中斷 (Graceful Exit)：支援終端機 Ctrl+C 或介面按鈕隨時安全停止，會等待當前檔案
     完整寫入後再退出，確保輸出檔案不破損。
================================================================================
"""

import os
import io
import re
import sys
import csv
import html
import time
import json
import queue
import ctypes
import shutil
import signal
import hashlib
import logging
import threading
import subprocess
import webbrowser
import urllib.parse
import configparser
import tkinter as tk
import customtkinter as ctk
from pathlib import Path
from datetime import datetime
from tkinter import filedialog, messagebox
from collections import Counter, defaultdict

def format_display_path(path_value):
    """Format a path for display without changing the path used for file I/O."""
    path_str = str(path_value)
    if os.name == 'nt':
        return path_str.replace('/', '\\')
    return path_str.replace('\\', '/')

def parse_saved_source_paths(saved_value):
    """Read new and legacy multi-folder settings without treating UI text as a path."""
    paths = [path.strip() for path in saved_value.split(';') if path.strip()]
    if paths and paths[0].startswith('[') and '] ' in paths[0]:
        paths[0] = paths[0].split('] ', 1)[1].strip()
    return [path for path in paths if os.path.exists(path)]

# 1. EXIF 讀取套件 (處理照片)
try:
    import exifread
    EXIFREAD_AVAILABLE = True
except ImportError:
    EXIFREAD_AVAILABLE = False

# 2. PIL/Pillow (處理照片)
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# 3. Hachoir (處理影片)
try:
    from hachoir.parser import createParser
    from hachoir.metadata import extractMetadata
    HACHOIR_AVAILABLE = True
except ImportError:
    HACHOIR_AVAILABLE = False

# 4. Reverse Geocoder (離線地理解析)
try:
    import reverse_geocoder as rg
    RG_AVAILABLE = True
except ImportError:
    RG_AVAILABLE = False

# 5. Pillow-heif (處理照片)
try:
    import pillow_heif
    PILLOW_HEIF_AVAILABLE = True
except ImportError:
    PILLOW_HEIF_AVAILABLE = False

# 6. Exiftool (處理照片)
EXIFTOOL_AVAILABLE = shutil.which("exiftool") is not None

# ===================== 莫蘭迪配色設定 =====================
THEMES = {
    "晨霧灰藍 (沈穩)": {
        "MAIN": "#7D8C94", "HOVER": "#66747A", "BG": "#F4F6F7",
        "SUB": "#97A9B3", "STOP": "#A88B87", "TEXT": "#4A4F54",
        "LABEL": "#777777", "BORDER": "#E0E4E6", "PROGRESS": "#B0BDC4"
    },
    "乾燥玫瑰 (溫暖)": {
        "MAIN": "#A68B87", "HOVER": "#917774", "BG": "#F8F5F4",
        "SUB": "#B8A3A0", "STOP": "#C99B96", "TEXT": "#4E4848",
        "LABEL": "#777777", "BORDER": "#EBE4E2", "PROGRESS": "#D4B9B5"
    },
    "鼠尾草綠 (自然)": {
        "MAIN": "#8A9A8A", "HOVER": "#758575", "BG": "#F5F6F4",
        "SUB": "#A3B3A3", "STOP": "#C9A696", "TEXT": "#4E544E",
        "LABEL": "#777777", "BORDER": "#E4E6E4", "PROGRESS": "#B8C4B8"
    }
}

# 預設啟動色系
DEFAULT_THEME_NAME = "晨霧灰藍 (沈穩)"
# ===================== 程式設定 =====================
VERSION = "2026-07-20"

# ===================== UI tuning constants =====================
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

# 1. 判斷是否為打包後的執行檔
if getattr(sys, 'frozen', False):
    # 執行檔的絕對路徑
    APPLICATION_PATH = os.path.dirname(sys.executable)
    # 取得執行檔本身的名稱 (例如 "Kairos.exe")
    BASE_NAME = os.path.splitext(os.path.basename(sys.executable))[0]
else:
    # Python 腳本的絕對路徑
    APPLICATION_PATH = os.path.dirname(os.path.abspath(__file__))
    # 取得腳本本身的名稱 (例如 "image_organizer")
    BASE_NAME = os.path.splitext(os.path.basename(__file__))[0]

# 2. 自動結合產出路徑與檔名
CONFIG_FILE = os.path.join(APPLICATION_PATH, f"{BASE_NAME}.ini")

DATE_TIME_ORIGINAL_TAG = 36867

STANDARD_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.heic', '.heif'}
RAW_EXTENSIONS = {'.dng', '.cr2', '.cr3', '.nef', '.arw', '.raf', '.orf', '.rw2', '.psd'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.m4v', '.3gp', '.mts', '.m2ts', '.mpg'}
GEO_LOOKUP_EXTENSIONS = {'.jpg', '.jpeg', '.tif', '.tiff', '.heic', '.heif'}
EXCLUDE_DIR_KEYWORDS = ['helper.lrdata', 'previews.lrdata', 'smart previews.lrdata', 'lrcat-data', 'System Volume Information', '$RECYCLE.BIN']
IGNORED_EXTENSIONS = ['.lrcat', '.lrdata', '.tmp', '.ds_store', '.db', '.xls', '.xlsx', '.doc', '.docx', '.pdf', '.html', '.csv', '.txt', '.json', '.js', '.css']
PLACEHOLDER = "-"

TIMESTAMP_STEM_RE = re.compile(r'^(?P<base>\d{4}-\d{2}-\d{2} \d{2}\.\d{2}\.\d{2})(?P<suffix>-(?:\d{1,6}(?:-\d+)?|u\d+|c\d+))?$')
EXIF_DATETIME_FORMAT = '%Y:%m:%d %H:%M:%S'
EXIF_DATETIME_TAG_KEYS = ('EXIF DateTimeOriginal', 'EXIF DateTimeDigitized', 'Image DateTime')
EXIF_SUBSEC_TAG_KEYS = ('EXIF SubSecTimeOriginal', 'EXIF SubSecTime', 'EXIF SubSecTimeDigitized')
EXIF_SERIAL_TAG_KEYS = (
    'EXIF BodySerialNumber',
    'Image BodySerialNumber',
    'MakerNote SerialNumber',
    'EXIF SerialNumber',
)
CAPTURE_META_CACHE = {}

# ==================== 全域空間快取與戰情計數器 ====================
GEO_COORD_CACHE = {}
GEO_PERF_STATS = {
    'queries': 0,
    'cache_hits': 0,
    'new_lookups': 0,
    'copied': 0,
    'skipped': 0,
    'total_time': 0.0
}
# =================================================================

# Stage 2 (non-behavioral extraction): centralize constants in config module.
try:
    from .config.constants import *  # noqa: F401,F403
except ImportError:
    from config.constants import *  # noqa: F401,F403

class PluginWarningCapturer:
    """專門用來攔截第三方外掛 (exifread, hachoir, PIL) 輸出警告與錯誤的攔截器"""
    def __init__(self):
        self.output = io.StringIO()
        self.handler = logging.StreamHandler(self.output)
        self.handler.setFormatter(logging.Formatter('%(message)s'))
        self.old_stderr = sys.stderr
        self.old_hachoir_handler = None

    def __enter__(self):
        sys.stderr = self.output
        exifread_logger = logging.getLogger('exifread')
        exifread_logger.addHandler(self.handler)
        exifread_logger.setLevel(logging.WARNING)
        try:
            import hachoir.core.warning as h_warn
            self.old_hachoir_handler = h_warn.logWarning
            h_warn.logWarning = self._hachoir_warn_callback
        except Exception:
            pass
        return self

    def _hachoir_warn_callback(self, msg, *args, **kwargs):
        self.output.write(f"[hachoir] {msg}\n")

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stderr = self.old_stderr
        logging.getLogger('exifread').removeHandler(self.handler)
        try:
            import hachoir.core.warning as h_warn
            if self.old_hachoir_handler:
                h_warn.logWarning = self.old_hachoir_handler
        except Exception:
            pass

    def get_messages(self):
        content = self.output.getvalue().strip()
        if not content:
            return []
        return [line.strip() for line in content.split('\n') if line.strip()]

def resource_path(relative_path):
    # 取得資源的絕對路徑，兼容開發模式與 PyInstaller 打包模式
    try:
        # PyInstaller 打包模式：指到 _MEIPASS 底下的 resources 資料夾
        base_path = os.path.join(sys._MEIPASS, "resources")

    except Exception:
        # 開發模式：Path(__file__).resolve().parent 直接定位到 src/kairos/
        base_path = str(Path(__file__).resolve().parent / "resources")

    return os.path.join(base_path, relative_path)

def format_size(size_bytes):
    if size_bytes == 0: return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {units[i]}"

def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def _hex_to_colorref(hex_color):
    color = str(hex_color).lstrip('#')
    if len(color) != 6:
        return None
    r = int(color[0:2], 16)
    g = int(color[2:4], 16)
    b = int(color[4:6], 16)
    return (b << 16) | (g << 8) | r

def _titlebar_text_hex_for_bg(hex_color):
    color = str(hex_color).lstrip('#')
    if len(color) != 6:
        return "#FFFFFF"
    r = int(color[0:2], 16)
    g = int(color[2:4], 16)
    b = int(color[4:6], 16)
    # Relative luminance heuristic
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#000000" if luminance > 170 else "#FFFFFF"

def apply_windows_titlebar_theme(window, caption_hex):
    """Apply Windows title-bar caption/text color (best effort; no-op on non-Windows)."""
    if sys.platform != "win32":
        return
    try:
        window.update_idletasks()
        hwnd = window.winfo_id()
        caption_color = _hex_to_colorref(caption_hex)
        text_color = _hex_to_colorref(_titlebar_text_hex_for_bg(caption_hex))
        if caption_color is None or text_color is None:
            return
        DWMWA_BORDER_COLOR = 34
        DWMWA_CAPTION_COLOR = 35
        DWMWA_TEXT_COLOR = 36
        value_caption = ctypes.c_int(caption_color)
        value_text = ctypes.c_int(text_color)
        value_border = ctypes.c_int(caption_color)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(value_caption), ctypes.sizeof(value_caption))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR, ctypes.byref(value_text), ctypes.sizeof(value_text))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_BORDER_COLOR, ctypes.byref(value_border), ctypes.sizeof(value_border))
    except Exception:
        pass

def _copy_windows_icon_from_parent(window, parent_window):
    """Copy title-bar icons from parent window handle (Windows only)."""
    if sys.platform != "win32" or parent_window is None:
        return False
    try:
        user32 = ctypes.windll.user32
        WM_GETICON = 0x007F
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        GCLP_HICONSM = -34
        GCLP_HICON = -14

        get_class_long_ptr = getattr(user32, "GetClassLongPtrW", None)
        if get_class_long_ptr is None:
            get_class_long_ptr = user32.GetClassLongW

        parent_hwnd = parent_window.winfo_id()
        child_hwnd = window.winfo_id()

        hicon_small = user32.SendMessageW(parent_hwnd, WM_GETICON, ICON_SMALL, 0)
        hicon_big = user32.SendMessageW(parent_hwnd, WM_GETICON, ICON_BIG, 0)
        if not hicon_small:
            hicon_small = get_class_long_ptr(parent_hwnd, GCLP_HICONSM)
        if not hicon_big:
            hicon_big = get_class_long_ptr(parent_hwnd, GCLP_HICON)

        if hicon_small:
            user32.SendMessageW(child_hwnd, WM_SETICON, ICON_SMALL, hicon_small)
        if hicon_big:
            user32.SendMessageW(child_hwnd, WM_SETICON, ICON_BIG, hicon_big)
        return bool(hicon_small or hicon_big)
    except Exception:
        return False

def apply_window_icon(window, icon_path=None, inherit_from=None):
    """Best-effort icon apply for Tk/CTk windows with delayed retries."""
    if icon_path is None:
        icon_path = resource_path("icon.ico")

    def _set_once(path=icon_path):
        has_path_icon = bool(path and os.path.exists(path))
        try:
            if has_path_icon:
                window.iconbitmap(path)
                return True
        except Exception:
            pass
        try:
            if has_path_icon:
                window.wm_iconbitmap(path)
                return True
        except Exception:
            pass
        if _copy_windows_icon_from_parent(window, inherit_from):
            return True
        try:
            if inherit_from is not None:
                parent_icon = inherit_from.iconbitmap()
                if parent_icon:
                    window.iconbitmap(parent_icon)
                    return True
        except Exception:
            pass
        return False

    applied = _set_once()
    if not applied:
        for delay in (80, 220, 480):
            try:
                window.after(delay, lambda p=icon_path: _set_once(p))
            except Exception:
                pass
    return applied

def is_identical_file(src_path, target_path):
    """先快速比對，再以完整 SHA-256 確認內容相同；絕不以片段比對作為略過依據。"""
    try:
        if os.path.getsize(src_path) != os.path.getsize(target_path):
            return False
        with open(src_path, 'rb') as f1, open(target_path, 'rb') as f2:
            chunk1 = f1.read(65536)
            chunk2 = f2.read(65536)
            if chunk1 != chunk2:
                return False
            file_size = os.path.getsize(src_path)
            if file_size > 65536:
                f1.seek(-min(65536, file_size), os.SEEK_END)
                f2.seek(-min(65536, file_size), os.SEEK_END)
                if f1.read() != f2.read():
                    return False
        return file_sha256(src_path) == file_sha256(target_path)
    except Exception:
        return False

def find_identical_in_target(src_path, target_dir, stem, ext):
    """
    在目標目錄中搜尋主檔名相同及其帶有序號後綴 (-1, -2, -c1 等) 的所有檔案，
    進行完整 SHA-256 實體比對，若存在相同檔案則直接回傳該目標檔案路徑。
    """
    # 1. 優先比對主檔名本身 (如 filename.jpg)
    base_file = target_dir / f"{stem}{ext}"
    if base_file.exists() and is_identical_file(src_path, base_file):
        return base_file

    # 2. 掃描帶有序號或連拍後綴的變體檔案 (如 filename-1.jpg, filename-2.jpg, filename-c1.jpg)
    # 使用 glob 尋找同一 stem 開頭且相同副檔名的所有候選者
    for candidate in target_dir.glob(f"{stem}-*{ext}"):
        if candidate.is_file() and is_identical_file(src_path, candidate):
            return candidate

    return None

def file_sha256(file_path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            digest.update(chunk)
    return digest.hexdigest()

def timestamp_parts(stem):
    """只解析本程式的時間戳命名，避免把 IMG-001 之類原始檔名誤當衝突後綴。"""
    match = TIMESTAMP_STEM_RE.fullmatch(stem)
    if not match:
        return None, None
    return match.group('base'), match.group('suffix')

def unique_path(directory, stem, ext):
    candidate = directory / f"{stem}{ext}"
    counter = 1
    while candidate.exists():
        candidate = directory / f"{stem}-{counter}{ext}"
        counter += 1
    return candidate

def unique_indexed_path(directory, stem, ext, start=1):
    """Always add numeric suffix starting from `start` (e.g. -1, -2, ...)."""
    counter = max(int(start), 1)
    candidate = directory / f"{stem}-{counter}{ext}"
    while candidate.exists():
        counter += 1
        candidate = directory / f"{stem}-{counter}{ext}"
    return candidate

def candidate_path_for(month_dir, stem, ext):
    candidate_dir = month_dir / 'candidate'
    candidate_dir.mkdir(parents=True, exist_ok=True)
    return unique_indexed_path(candidate_dir, stem, ext, start=1)


# Stage 2 (non-behavioral extraction): bind runtime utility calls to extracted modules.
try:
    from .utils.file_ops import (
        candidate_path_for as _candidate_path_for,
        file_sha256 as _file_sha256,
        find_identical_in_target as _find_identical_in_target,
        is_identical_file as _is_identical_file,
        timestamp_parts as _timestamp_parts,
        unique_indexed_path as _unique_indexed_path,
        unique_path as _unique_path,
    )
    from .utils.logger import PluginWarningCapturer as _PluginWarningCapturer
    from .utils.sys_helpers import (
        apply_window_icon as _apply_window_icon,
        apply_windows_titlebar_theme as _apply_windows_titlebar_theme,
        format_display_path as _format_display_path,
        format_size as _format_size,
        format_time as _format_time,
        parse_saved_source_paths as _parse_saved_source_paths,
        resource_path as _resource_path,
    )
except ImportError:
    from utils.file_ops import (
        candidate_path_for as _candidate_path_for,
        file_sha256 as _file_sha256,
        find_identical_in_target as _find_identical_in_target,
        is_identical_file as _is_identical_file,
        timestamp_parts as _timestamp_parts,
        unique_indexed_path as _unique_indexed_path,
        unique_path as _unique_path,
    )
    from utils.logger import PluginWarningCapturer as _PluginWarningCapturer
    from utils.sys_helpers import (
        apply_window_icon as _apply_window_icon,
        apply_windows_titlebar_theme as _apply_windows_titlebar_theme,
        format_display_path as _format_display_path,
        format_size as _format_size,
        format_time as _format_time,
        parse_saved_source_paths as _parse_saved_source_paths,
        resource_path as _resource_path,
    )

format_display_path = _format_display_path
parse_saved_source_paths = _parse_saved_source_paths
resource_path = _resource_path
format_size = _format_size
format_time = _format_time
apply_windows_titlebar_theme = _apply_windows_titlebar_theme
apply_window_icon = _apply_window_icon
is_identical_file = _is_identical_file
find_identical_in_target = _find_identical_in_target
file_sha256 = _file_sha256
timestamp_parts = _timestamp_parts
unique_path = _unique_path
unique_indexed_path = _unique_indexed_path
candidate_path_for = _candidate_path_for
PluginWarningCapturer = _PluginWarningCapturer

def get_media_date(file_path):
    ext = Path(file_path).suffix.lower()

    if ext in VIDEO_EXTENSIONS:
        if HACHOIR_AVAILABLE:
            try:
                parser = createParser(str(file_path))
                if parser:
                    with parser:
                        metadata = extractMetadata(parser)
                        if metadata and metadata.has("creation_date"):
                            return metadata.get("creation_date")
            except Exception:
                pass

    else:
        if EXIFREAD_AVAILABLE:
            try:
                with open(file_path, 'rb') as f:
                    tags = exifread.process_file(f, stop_tag='EXIF DateTimeOriginal', details=False)
                    if 'EXIF DateTimeOriginal' in tags:
                        return datetime.strptime(str(tags['EXIF DateTimeOriginal']), '%Y:%m:%d %H:%M:%S')
            except Exception: pass

        if PIL_AVAILABLE:
            try:
                with Image.open(file_path) as img:
                    exif = img._getexif()
                    if exif and DATE_TIME_ORIGINAL_TAG in exif:
                        return datetime.strptime(exif[DATE_TIME_ORIGINAL_TAG], '%Y:%m:%d %H:%M:%S')
            except Exception: pass

    return datetime.fromtimestamp(os.path.getmtime(file_path))

def get_camera_model(file_path):
    """讀取相機型號與品牌，若無則回傳 '-' """
    ext = Path(file_path).suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        if HACHOIR_AVAILABLE:
            try:
                parser = createParser(str(file_path))
                if parser:
                    with parser:
                        metadata = extractMetadata(parser)
                        if metadata and metadata.has("camera_model"):
                            val = str(metadata.get("camera_model")).strip()
                            if val: return val
            except Exception:
                pass
    else:
        if EXIFREAD_AVAILABLE:
            try:
                with open(file_path, 'rb') as f:
                    tags = exifread.process_file(f, stop_tag='Image Model', details=False)
                    model = str(tags.get('Image Model', '')).strip()
                    make = str(tags.get('Image Make', '')).strip()
                    if model and make:
                        if make.lower() in model.lower():
                            return model
                        return f"{make} {model}"
                    elif model:
                        return model
                    elif make:
                        return make
            except Exception:
                pass
    return "-"

# ==================== 智能快取繼承與封存模組 ====================
def load_and_merge_geo_caches(source_folders, dest_dir, log_callback=None):
    """從所有來源與目的目錄 (及其上一層母目錄) 中尋找並繼承舊的地理快取"""
    cache_files_found = set()

    # 1. 檢查目標輸出目錄
    dest_cache = Path(dest_dir) / "_manifest_geo.json"
    if dest_cache.exists():
        cache_files_found.add(dest_cache)

    # 2. 檢查所有勾選的來源目錄 (及其上一層母目錄，防止勾選子資料夾時遺漏)
    for src in source_folders:
        src_path = Path(src)
        for check_dir in [src_path, src_path.parent]:
            src_cache = check_dir / "_manifest_geo.json"
            if src_cache.exists():
                cache_files_found.add(src_cache)

    # 3. 載入並聯集合併到全域的 GEO_COORD_CACHE
    loaded_count = 0
    for c_file in cache_files_found:
        try:
            with open(c_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for key_str, loc_name in data.items():
                    if ',' in key_str:
                        lat_str, lon_str = key_str.split(',', 1)
                        coord_key = (round(float(lat_str), 3), round(float(lon_str), 3))
                        if coord_key not in GEO_COORD_CACHE:
                            GEO_COORD_CACHE[coord_key] = loc_name
                            loaded_count += 1
            if log_callback:
                log_callback(f"[GEO_CACHE] 成功繼承歷史地理快取: {c_file.name} (+{loaded_count} 筆空間座標)")
        except Exception as e:
            if log_callback:
                log_callback(f"[GEO_CACHE] 讀取快取失敗 ({c_file.name}): {e}")

def save_geo_cache_to_dest(dest_dir, log_callback=None):
    """處理完畢後，將全域地理快取封存至目標輸出根目錄"""
    if not GEO_COORD_CACHE:
        return
    dest_cache = Path(dest_dir) / "_manifest_geo.json"
    try:
        # 將 Tuple key (lat, lon) 轉為 "lat,lon" 字串格式以符合標準 JSON 規範
        export_data = {f"{lat},{lon}": name for (lat, lon), name in GEO_COORD_CACHE.items()}
        with open(dest_cache, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        if log_callback:
            log_callback(f"[GEO_CACHE] 空間位置字典已成功封存至: {dest_cache.name} (共 {len(export_data)} 筆)")
    except Exception as e:
        if log_callback:
            log_callback(f"[GEO_CACHE] 封存快取失敗: {e}")

def get_stats_banner_html():
    """產生整合至 HTML 報告頂端的戰情統計看板 HTML"""
    t_time = format_time(GEO_PERF_STATS.get('total_time', 0))
    copied = GEO_PERF_STATS.get('copied', 0)
    skipped = GEO_PERF_STATS.get('skipped', 0)
    queries = GEO_PERF_STATS.get('queries', 0)
    hits = GEO_PERF_STATS.get('cache_hits', 0)
    new_l = GEO_PERF_STATS.get('new_lookups', 0)
    hit_rate = (hits / queries * 100) if queries > 0 else 0.0

    return f"""
    <div style="background: #EAF2F8; border-left: 4px solid #2980B9; padding: 12px 18px; margin: 15px 0; border-radius: 6px; font-size: 13px; display: flex; flex-wrap: wrap; gap: 20px; color: #2C3E50; box-shadow: 0 1px 3px rgba(0,0,0,0.05); line-height: 1.6;">
        <span>⏱️ <b>總處理耗時:</b> {t_time}</span>
        <span>📁 <b>實體複製與歸檔:</b> {copied:,} 張 <small style="color:#7F8C8D;">(物理去重略過 {skipped:,} 張)</small></span>
        <span>🌏 <b>地理座標查詢:</b> 共 {queries:,} 次</span>
        <span>⚡ <b>快取命中與重用:</b> {hits:,} 次 (<span style="color:#27AE60; font-weight:bold;">{hit_rate:.1f}% 繼承或重用</span>)</span>
        <span>🔍 <b>新增空間反查:</b> {new_l:,} 次 <small style="color:#2980B9;">(極速批量 C++ KD-Tree)</small></span>
    </div>
    """
# =================================================================

def _geo_ratio_to_float(value):
    try:
        if hasattr(value, 'num') and hasattr(value, 'den'):
            den = float(value.den) if float(value.den) != 0 else 1.0
            return float(value.num) / den
        if isinstance(value, tuple) and len(value) == 2:
            den = float(value[1]) if float(value[1]) != 0 else 1.0
            return float(value[0]) / den
        return float(value)
    except Exception:
        return None

def _geo_dms_to_decimal(dms_values, ref_tag):
    try:
        if len(dms_values) < 3:
            return None
        d = _geo_ratio_to_float(dms_values[0])
        m = _geo_ratio_to_float(dms_values[1])
        s = _geo_ratio_to_float(dms_values[2])
        if d is None or m is None or s is None:
            return None
        dec = d + (m / 60.0) + (s / 3600.0)
        if str(ref_tag).upper() in ['S', 'W']:
            dec = -dec
        return dec
    except Exception:
        return None

def _geo_extract_with_exifread(file_path):
    if not EXIFREAD_AVAILABLE:
        return None, None, "FAIL: exifread unavailable"
    try:
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
        if 'GPS GPSLatitude' not in tags or 'GPS GPSLongitude' not in tags:
            return None, None, "FAIL: missing GPS EXIF (GPSLatitude/GPSLongitude)"
        lat_ref = str(tags.get('GPS GPSLatitudeRef', 'N'))
        lon_ref = str(tags.get('GPS GPSLongitudeRef', 'E'))
        lat = _geo_dms_to_decimal(tags['GPS GPSLatitude'].values, lat_ref)
        lon = _geo_dms_to_decimal(tags['GPS GPSLongitude'].values, lon_ref)
        if lat is None or lon is None:
            return None, None, "FAIL: invalid GPS EXIF DMS values"
        return lat, lon, None
    except Exception as e:
        return None, None, f"ERROR: EXIF parse exception | {repr(e)}"

def _geo_extract_with_exiftool(file_path):
    exiftool_path = shutil.which("exiftool")
    if not exiftool_path:
        return None, None, "FAIL: exiftool unavailable"
    try:
        cp = subprocess.run(
            [exiftool_path, "-j", "-n", "-GPSLatitude", "-GPSLongitude", str(file_path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10
        )
        if cp.returncode != 0:
            return None, None, f"ERROR: exiftool failed | {cp.stderr.strip()}"
        payload = json.loads(cp.stdout or "[]")
        if not payload or not isinstance(payload, list):
            return None, None, "FAIL: exiftool returned empty payload"
        row = payload[0]
        lat = row.get("GPSLatitude")
        lon = row.get("GPSLongitude")
        if lat is None or lon is None:
            return None, None, "FAIL: exiftool returned no GPS fields"
        return float(lat), float(lon), None
    except Exception as e:
        return None, None, f"ERROR: exiftool exception | {repr(e)}"

def _geo_extract_with_pillow_heif(file_path):
    if not PIL_AVAILABLE:
        return None, None, "FAIL: Pillow unavailable"
    try:
        import pillow_heif
    except Exception:
        return None, None, "FAIL: pillow-heif unavailable"

    try:
        pillow_heif.register_heif_opener()
        with Image.open(file_path) as img:
            exif = img.getexif()
            gps_ifd = exif.get_ifd(0x8825) if hasattr(exif, "get_ifd") else None
            if gps_ifd is None:
                gps_ifd = exif.get(34853) if exif else None
            if not gps_ifd:
                return None, None, "FAIL: missing GPS EXIF in pillow-heif metadata"
            lat_values = gps_ifd.get(2)
            lon_values = gps_ifd.get(4)
            lat_ref = gps_ifd.get(1, 'N')
            lon_ref = gps_ifd.get(3, 'E')
            if not lat_values or not lon_values:
                return None, None, "FAIL: missing GPS EXIF (GPSLatitude/GPSLongitude)"
            lat = _geo_dms_to_decimal(lat_values, lat_ref)
            lon = _geo_dms_to_decimal(lon_values, lon_ref)
            if lat is None or lon is None:
                return None, None, "FAIL: invalid GPS EXIF DMS values"
            return lat, lon, None
    except Exception as e:
        return None, None, f"ERROR: pillow-heif parse exception | {repr(e)}"

def extract_raw_coords(file_path):
    """提取未經四捨五入的原始高精度浮點數經緯度 (lat, lon, error_reason)"""
    ext = Path(file_path).suffix.lower()
    if ext not in STANDARD_EXTENSIONS:
        return None, None, "SKIP: EXIF GPS not supported for this file type"

    lat, lon, reason = _geo_extract_with_exifread(file_path)
    if (lat is None or lon is None) and ext in {'.heic', '.heif'}:
        lat, lon, reason_pillow = _geo_extract_with_pillow_heif(file_path)
        if lat is None or lon is None:
            lat, lon, reason_exiftool = _geo_extract_with_exiftool(file_path)
            reason = reason_exiftool or reason_pillow or reason
        else:
            reason = None

    if lat is None or lon is None:
        reason = reason or "FAIL: missing GPS EXIF (GPSLatitude/GPSLongitude)"
        return None, None, reason

    return lat, lon, None

def get_exif_subsec(file_path):
    return get_capture_meta(file_path).get('subsec_raw')

def _read_exif_capture_fields(file_path):
    result = {
        'capture_dt': None,
        'subsec_raw': None,
        'subsec_ms': None,
        'serial': PLACEHOLDER,
        'capture_epoch': None,
        'has_precise_ms': False,
    }
    ext = Path(file_path).suffix.lower()
    if not (EXIFREAD_AVAILABLE and ext in STANDARD_EXTENSIONS):
        return result

    try:
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
    except Exception:
        return result

    dt_text = None
    for key in EXIF_DATETIME_TAG_KEYS:
        if key in tags:
            value = str(tags[key]).strip()
            if value:
                dt_text = value
                break
    if dt_text:
        try:
            result['capture_dt'] = datetime.strptime(dt_text, EXIF_DATETIME_FORMAT)
        except Exception:
            result['capture_dt'] = None

    for key in EXIF_SUBSEC_TAG_KEYS:
        if key in tags:
            value = str(tags[key]).strip()
            if value:
                result['subsec_raw'] = value
                result['subsec_ms'] = normalized_subsec(value)
                break

    for key in EXIF_SERIAL_TAG_KEYS:
        if key in tags:
            value = str(tags[key]).strip()
            if value:
                result['serial'] = value
                break

    return result

def get_capture_meta(file_path):
    cache_key = os.path.normcase(os.path.abspath(str(file_path)))
    if cache_key in CAPTURE_META_CACHE:
        return CAPTURE_META_CACHE[cache_key]

    meta = _read_exif_capture_fields(file_path)
    if meta['capture_dt'] is None:
        try:
            meta['capture_dt'] = datetime.fromtimestamp(os.path.getmtime(file_path))
        except Exception:
            meta['capture_dt'] = None

    if meta['capture_dt'] is not None:
        epoch = meta['capture_dt'].timestamp()
        if meta['subsec_ms'] is not None:
            epoch += (int(meta['subsec_ms']) / 1000.0)
            meta['has_precise_ms'] = True
        meta['capture_epoch'] = epoch

    CAPTURE_META_CACHE[cache_key] = meta
    return meta

def invalidate_capture_meta(file_path):
    cache_key = os.path.normcase(os.path.abspath(str(file_path)))
    CAPTURE_META_CACHE.pop(cache_key, None)

def is_same_millisecond_capture(src_path, target_path):
    src_meta = get_capture_meta(src_path)
    tgt_meta = get_capture_meta(target_path)
    if not (src_meta.get('has_precise_ms') and tgt_meta.get('has_precise_ms')):
        return False
    src_serial = src_meta.get('serial', PLACEHOLDER)
    tgt_serial = tgt_meta.get('serial', PLACEHOLDER)
    if src_serial != PLACEHOLDER and tgt_serial != PLACEHOLDER and src_serial != tgt_serial:
        return False
    src_ms = int(round(src_meta['capture_epoch'] * 1000))
    tgt_ms = int(round(tgt_meta['capture_epoch'] * 1000))
    return src_ms == tgt_ms

def is_burst_shot(src_path, target_path):
    src_meta = get_capture_meta(src_path)
    tgt_meta = get_capture_meta(target_path)
    src_serial = src_meta.get('serial', PLACEHOLDER)
    tgt_serial = tgt_meta.get('serial', PLACEHOLDER)
    if src_serial == PLACEHOLDER or tgt_serial == PLACEHOLDER or src_serial != tgt_serial:
        return False
    src_epoch = src_meta.get('capture_epoch')
    tgt_epoch = tgt_meta.get('capture_epoch')
    if src_epoch is None or tgt_epoch is None:
        return False
    delta = abs(src_epoch - tgt_epoch)
    return 0 < delta < 1.0

# 定義自己產出的檔案特徵，避免誤殺使用者原始檔
def is_kairos_self_file(filename):
    # 1. 報表檔案 (如 _index.html, 2026_04_media_report.html)
    if filename.endswith('_media_report.html') or filename == '_index.html':
        return True
    # 2. 清單與日誌檔案 (如 _manifest_geo.json, _manifest_audit.csv, _manifest_skiplist.txt, _process_log.txt)
    system_prefixes = ('_manifest_', '_process_log.txt', '_kairos_')

    if filename.startswith(system_prefixes):
        return True
    return False

# Stage 15 (non-behavioral extraction): bind self-file rule to config.rules module.
try:
    from .config.rules import is_kairos_self_file as _rule_is_kairos_self_file
except ImportError:
    from config.rules import is_kairos_self_file as _rule_is_kairos_self_file

is_kairos_self_file = _rule_is_kairos_self_file

def compare_and_decide(src_path, target_path):
    """Priority: IDENTICAL -> SAME_MS -> BURST -> REPLACE/KEEP by mtime."""
    if is_identical_file(src_path, target_path):
        return "IDENTICAL"

    if is_same_millisecond_capture(src_path, target_path):
        return "SAME_MS"

    if is_burst_shot(src_path, target_path):
        return "BURST"

    try:
        src_mtime = os.path.getmtime(src_path)
        tgt_mtime = os.path.getmtime(target_path)
        return "REPLACE" if src_mtime > tgt_mtime else "KEEP"
    except OSError:
        return "KEEP"

def normalized_subsec(value):
    """將 EXIF 亞秒標準化為毫秒字串；不足三位補零，超過三位取毫秒。"""
    digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
    return (digits + '000')[:3] if digits else None

def safe_rename_batch(rename_map):
    """先改為唯一暫存名，再改為最終名，避免群組內名稱互換時覆蓋。"""
    targets = list(rename_map.values())
    if len(targets) != len(set(targets)):
        raise ValueError("第二輪命名計畫有重複目標；未進行任何改名")
    unmanaged_targets = [target for target in targets if target.exists() and target not in rename_map]
    if unmanaged_targets:
        raise FileExistsError(f"第二輪目標已存在且不屬於目前群組：{unmanaged_targets[0]}")
    staged = []
    for index, (source, target) in enumerate(rename_map.items()):
        if source == target:
            continue
        temp = source.with_name(f".__kairos_stage_{index}_{source.name}")
        while temp.exists():
            temp = temp.with_name(f".__kairos_stage_{index}_{time.time_ns()}_{source.name}")
        source.rename(temp)
        staged.append((temp, target))
    for temp, target in staged:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(f"第二輪目標已存在：{target}")
        temp.rename(target)

def second_pass_month(month_dir, stop_event):
    """以同秒、同副檔名的圖片群組進行無刪除的連拍／候選整理。"""
    groups = defaultdict(list)
    for path in month_dir.iterdir():
        if stop_event.is_set():
            return
        if not path.is_file() or path.suffix.lower() not in STANDARD_EXTENSIONS:
            continue
        base, _ = timestamp_parts(path.stem)
        if base:
            groups[(base, path.suffix.lower())].append(path)

    for (base, ext), members in groups.items():
        if stop_event.is_set() or len(members) < 2:
            continue
        known, unknown = defaultdict(list), []
        for member in members:
            subsec = normalized_subsec(get_exif_subsec(member))
            (known[subsec] if subsec else unknown).append(member)

        rename_map = {}
        # 相同亞秒是同一張照片的版本；修改時間最新者留前台，其餘放到 candidate。
        for subsec, variants in known.items():
            winner = max(variants, key=lambda p: p.stat().st_mtime)
            if len(known) == 1:
                winner_name = f"{base}{ext}"
            else:
                winner_name = f"{base}-{subsec}{ext}"
            rename_map[winner] = month_dir / winner_name
            candidate_index = 1
            for variant in variants:
                if variant == winner:
                    continue
                # 亞秒值納入候選檔名，避免多個連拍瞬間各自產生 -c1 而撞名。
                target = unique_path(month_dir / 'candidate', f"{base}-{subsec}-c{candidate_index}", ext)
                rename_map[variant] = target
                candidate_index += 1

        # 缺少亞秒的檔案不做版本推論，強制保留在前台。
        for index, member in enumerate(sorted(unknown, key=lambda p: p.name), start=1):
            rename_map[member] = month_dir / f"{base}-u{index}{ext}"

        safe_rename_batch(rename_map)


# Stage 3 (non-behavioral extraction): bind arbitration logic to metadata module.
try:
    from .metadata.arbiter import (
        CAPTURE_META_CACHE as _ARB_CAPTURE_META_CACHE,
        _read_exif_capture_fields as _arb_read_exif_capture_fields,
        compare_and_decide as _arb_compare_and_decide,
        get_capture_meta as _arb_get_capture_meta,
        get_exif_subsec as _arb_get_exif_subsec,
        invalidate_capture_meta as _arb_invalidate_capture_meta,
        is_burst_shot as _arb_is_burst_shot,
        is_same_millisecond_capture as _arb_is_same_millisecond_capture,
        normalized_subsec as _arb_normalized_subsec,
        safe_rename_batch as _arb_safe_rename_batch,
        second_pass_month as _arb_second_pass_month,
    )
except ImportError:
    from metadata.arbiter import (
        CAPTURE_META_CACHE as _ARB_CAPTURE_META_CACHE,
        _read_exif_capture_fields as _arb_read_exif_capture_fields,
        compare_and_decide as _arb_compare_and_decide,
        get_capture_meta as _arb_get_capture_meta,
        get_exif_subsec as _arb_get_exif_subsec,
        invalidate_capture_meta as _arb_invalidate_capture_meta,
        is_burst_shot as _arb_is_burst_shot,
        is_same_millisecond_capture as _arb_is_same_millisecond_capture,
        normalized_subsec as _arb_normalized_subsec,
        safe_rename_batch as _arb_safe_rename_batch,
        second_pass_month as _arb_second_pass_month,
    )

CAPTURE_META_CACHE = _ARB_CAPTURE_META_CACHE
normalized_subsec = _arb_normalized_subsec
_read_exif_capture_fields = _arb_read_exif_capture_fields
get_capture_meta = _arb_get_capture_meta
invalidate_capture_meta = _arb_invalidate_capture_meta
get_exif_subsec = _arb_get_exif_subsec
is_same_millisecond_capture = _arb_is_same_millisecond_capture
is_burst_shot = _arb_is_burst_shot
compare_and_decide = _arb_compare_and_decide
safe_rename_batch = _arb_safe_rename_batch
second_pass_month = _arb_second_pass_month

# Stage 4 (non-behavioral extraction): bind metadata parser and geo extract helpers.
try:
    from .metadata.exif_parser import (
        get_camera_model as _meta_get_camera_model,
        get_media_date as _meta_get_media_date,
    )
    from .metadata.geo_engine import (
        GEO_COORD_CACHE as _meta_geo_coord_cache,
        GEO_PERF_STATS as _meta_geo_perf_stats,
        _geo_dms_to_decimal as _meta_geo_dms_to_decimal,
        _geo_extract_with_exifread as _meta_geo_extract_with_exifread,
        _geo_extract_with_exiftool as _meta_geo_extract_with_exiftool,
        _geo_extract_with_pillow_heif as _meta_geo_extract_with_pillow_heif,
        _geo_ratio_to_float as _meta_geo_ratio_to_float,
        collect_media_records as _meta_collect_media_records,
        extract_raw_coords as _meta_extract_raw_coords,
        get_stats_banner_html as _meta_get_stats_banner_html,
        load_and_merge_geo_caches as _meta_load_and_merge_geo_caches,
        save_geo_cache_to_dest as _meta_save_geo_cache_to_dest,
    )
except ImportError:
    from metadata.exif_parser import (
        get_camera_model as _meta_get_camera_model,
        get_media_date as _meta_get_media_date,
    )
    from metadata.geo_engine import (
        GEO_COORD_CACHE as _meta_geo_coord_cache,
        GEO_PERF_STATS as _meta_geo_perf_stats,
        _geo_dms_to_decimal as _meta_geo_dms_to_decimal,
        _geo_extract_with_exifread as _meta_geo_extract_with_exifread,
        _geo_extract_with_exiftool as _meta_geo_extract_with_exiftool,
        _geo_extract_with_pillow_heif as _meta_geo_extract_with_pillow_heif,
        _geo_ratio_to_float as _meta_geo_ratio_to_float,
        collect_media_records as _meta_collect_media_records,
        extract_raw_coords as _meta_extract_raw_coords,
        get_stats_banner_html as _meta_get_stats_banner_html,
        load_and_merge_geo_caches as _meta_load_and_merge_geo_caches,
        save_geo_cache_to_dest as _meta_save_geo_cache_to_dest,
    )

GEO_COORD_CACHE = _meta_geo_coord_cache
GEO_PERF_STATS = _meta_geo_perf_stats
get_media_date = _meta_get_media_date
get_camera_model = _meta_get_camera_model
load_and_merge_geo_caches = _meta_load_and_merge_geo_caches
save_geo_cache_to_dest = _meta_save_geo_cache_to_dest
get_stats_banner_html = _meta_get_stats_banner_html
_geo_ratio_to_float = _meta_geo_ratio_to_float
_geo_dms_to_decimal = _meta_geo_dms_to_decimal
_geo_extract_with_exifread = _meta_geo_extract_with_exifread
_geo_extract_with_exiftool = _meta_geo_extract_with_exiftool
_geo_extract_with_pillow_heif = _meta_geo_extract_with_pillow_heif
extract_raw_coords = _meta_extract_raw_coords

def collect_media_records(dest_path, organize_by_time, enable_geo_lookup=False, q=None, stop_event=None, start_time=0, processed_size=0, performance_mode=False):
    """第二輪後由實際目的地重建 HTML 索引，若開啟地理解析則進行批量極速反查，並同步更新 UI 進度與計時狀態"""
    records_by_group = defaultdict(list)
    geo_log_callback = (lambda message: q.put(('log', message))) if (q and not performance_mode) else None
    geo_stats = {'pass': 0, 'fail': 0, 'skip': 0}
    geo_fail_by_abs_path = {}
    geo_map_by_abs_path = {}
    geo_fail_reason_counter = Counter()
    roots = [p for p in dest_path.iterdir() if p.is_dir()] if organize_by_time else [dest_path]

    all_files = []
    for root in roots:
        for path in root.rglob('*'):
            if path.is_file() and not path.name.startswith('_'):
                ext = path.suffix.lower()
                if ext in STANDARD_EXTENSIONS or ext in VIDEO_EXTENSIONS:
                    all_files.append((root.name if organize_by_time else 'ALL_MEDIA', path))

    total_count = len(all_files)
    file_geo_tasks = []
    unique_keys_to_query = set()

    for idx, (month_key, path) in enumerate(all_files, start=1):
        if stop_event and stop_event.is_set():
            break

        if q and idx % 15 == 0:
            q.put(('status', f"Building HTML report and extracting GPS data... ({idx} / {total_count})"))
            q.put(('progress', idx / max(total_count, 1)))
            if start_time > 0:
                q.put(('metrics', (time.time() - start_time, processed_size)))

        ext = path.suffix.lower()
        base, _ = timestamp_parts(path.stem)
        category = 'candidate' if 'candidate' in path.parts else ('video' if ext in VIDEO_EXTENSIONS else 'standard')

        loc_name, map_url = "-", "-"
        needs_geo_lookup = category in ("standard", "candidate") and ext in GEO_LOOKUP_EXTENSIONS

        rec_dict = {
            'name': path.name, 'rel_path': path.relative_to(dest_path).as_posix(),
            'size': path.stat().st_size, 'category': category,
            'group_key': base or path.stem, 'group_order': 1 if category == 'candidate' else 0,
            'loc_name': loc_name, 'map_url': map_url
        }
        records_by_group[month_key].append(rec_dict)

        if enable_geo_lookup and needs_geo_lookup:
            lat, lon, reason = extract_raw_coords(path)
            if lat is None or lon is None:
                geo_stats['fail'] += 1
                abs_p = os.path.normcase(os.path.abspath(str(path)))
                geo_fail_by_abs_path[abs_p] = reason or "FAIL: missing GPS EXIF"
                geo_fail_reason_counter[reason or "FAIL: missing GPS EXIF"] += 1
                if geo_log_callback:
                    geo_log_callback(f"[GEO] {format_display_path(path)} | {reason}")
            else:
                geo_stats['pass'] += 1
                # 雙流設計 1：導航網址保留小數點後 4 位高精度 (現場生成)
                map_url = f"https://www.google.com/maps?q={lat:.4f},{lon:.4f}"
                # 雙流設計 2：地名查詢 Key 降至小數點後 3 位 (百米快取)
                coord_key = (round(lat, 3), round(lon, 3))

                abs_p = os.path.normcase(os.path.abspath(str(path)))
                geo_map_by_abs_path[abs_p] = map_url
                rec_dict['map_url'] = map_url

                GEO_PERF_STATS['queries'] += 1
                if coord_key in GEO_COORD_CACHE:
                    GEO_PERF_STATS['cache_hits'] += 1
                    rec_dict['loc_name'] = GEO_COORD_CACHE[coord_key]
                else:
                    unique_keys_to_query.add(coord_key)
                    file_geo_tasks.append((rec_dict, coord_key))
        elif enable_geo_lookup and not needs_geo_lookup:
            geo_stats['skip'] += 1

    # 🚀 執行 C++ 批量矩陣查詢 (Batch Geocoding)
    if unique_keys_to_query and RG_AVAILABLE:
        query_list = list(unique_keys_to_query)
        if q:
            q.put(('status', f"🚀 正在調用 reverse_geocoder 批量解析 ({len(query_list)} 組全新空間座標)..."))
        try:
            res_list = rg.search(query_list)
            for idx, coord_key in enumerate(query_list):
                info = res_list[idx]
                c = info.get('cc', '')
                a1 = info.get('admin1', '')
                a2 = info.get('name', '')
                parts = [p for p in [c, a1] if p]
                loc_str = " - ".join(parts)
                loc_name = f"{loc_str} ({a2})" if (loc_str and a2) else (loc_str or a2 or "-")
                GEO_COORD_CACHE[coord_key] = loc_name
            GEO_PERF_STATS['new_lookups'] += len(query_list)
            if geo_log_callback:
                geo_log_callback(f"[GEO_BATCH] 成功批量反查並寫入 {len(query_list)} 筆全新空間地名字典！")
        except Exception as e:
            if geo_log_callback:
                geo_log_callback(f"[GEO_ERROR] 批量反查例外失敗: {e}")

    # 為未命中快取的檔案填入批量反查到的地名
    for rec_dict, coord_key in file_geo_tasks:
        rec_dict['loc_name'] = GEO_COORD_CACHE.get(coord_key, "-")

    if q:
        q.put(('progress', 1.0))
        if start_time > 0:
            q.put(('metrics', (time.time() - start_time, processed_size)))

    return records_by_group, geo_stats, geo_fail_by_abs_path, geo_map_by_abs_path, geo_fail_reason_counter

# Bind post-definition to ensure runtime uses extracted module implementation.
collect_media_records = _meta_collect_media_records

def destination_extension_counts(dest_path):
    excluded = {'_index.html', '_manifest_audit.csv', '_manifest_skiplist.txt', '_manifest_filetype.html'}
    return Counter(p.suffix.lower() or '[無副檔名]' for p in dest_path.rglob('*') if p.is_file() and p.name not in excluded and not p.name.startswith('_process_log') and not p.name.endswith('_media_report.html'))

def generate_html_report(output_root_dir, month_key, media_records):
    if not media_records:
        return

    html_path = Path(output_root_dir) / f"{month_key}_media_report.html"
    generated_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    month_title = f"{month_key} 媒體處理報告"
    if re.fullmatch(r"\d{4}_\d{2}", str(month_key)):
        month_title = f"{month_key[:4]}年{month_key[5:7]}月的照片與影片"

    cards_html = []
    for rec in media_records:
        rel_path = rec['rel_path']
        display_rel_path = format_display_path(rel_path)
        # 關鍵修復：針對帶有空格或特殊字元的檔名進行 URL '%20' 轉碼，防止瀏覽器讀取本地檔案失敗
        rel_path_encoded = urllib.parse.quote(rel_path.replace('\\', '/'))

        fname = rec['name']
        escaped_fname = html.escape(fname, quote=True)
        fsize = format_size(rec['size'])
        category = rec['category']
        group_key = rec.get('group_key', Path(fname).stem)
        group_order = rec.get('group_order', 0)

        display_label = "IMAGE" if category == "standard" else category.upper()
        if category == "candidate": display_label = "備選"

        badge_style = "background: #7D8C94; color: white;"
        if category == "raw": badge_style = "background: #A88B87; color: white;"
        elif category == "video": badge_style = "background: #66747A; color: white;"
        elif category == "candidate": badge_style = "background: #E67E22; color: white;"

        error_div = '<div class="error-msg">檔案已刪除</div>'
        error_script = "this.closest('.media-card').classList.add('broken');"

        if category in ("standard", "candidate"):
            img_tag = f'<img data-src="{rel_path_encoded}" class="lazy-image" alt="{escaped_fname}" onerror="{error_script}">{error_div}'
        else:
            if category == "video":
                detector = f'<video src="{rel_path_encoded}" style="display:none;" onerror="{error_script}"></video>'
                img_tag = f'<div class="video-placeholder">🎬 影片檔案<br><small>{escaped_fname}</small><br><span style="font-size:11px; color:#3498DB;">[點擊播放]</span></div>{detector}{error_div}'
            elif category == "raw":
                img_tag = f'<div class="raw-placeholder">📸 RAW 原檔<br><small>{escaped_fname}</small></div>{error_div}'
            else:
                img_tag = f'<div class="raw-placeholder">{escaped_fname}</div>{error_div}'

        # 新增：將地理位置整合進月份卡片中
        loc_name = rec.get('loc_name', '-')
        map_url = rec.get('map_url', '-')
        geo_html = ""
        if loc_name != "-" or map_url != "-":
            loc_display = html.escape(loc_name, quote=True) if loc_name != "-" else "未知位置"
            map_link_html = f'<a href="{map_url}" target="_blank" class="geo-map-btn" onclick="event.stopPropagation();" title="View on Google Maps">🌏️</a>' if map_url != "-" else ""
            geo_html = f'<div class="geo-bar"><span class="geo-text" title="{loc_display}">📍 {loc_display}</span>{map_link_html}</div>'

        # data-filepath 嚴格保留未轉碼之原始相對路徑，供 Windows/macOS 終端機刪除語法使用
        card = f"""
        <div class="media-card" data-category="{category}" data-name="{html.escape(fname.lower(), quote=True)}" data-group="{html.escape(group_key.lower(), quote=True)}" data-group-order="{group_order}" data-size="{rec['size']}" data-url="{rel_path_encoded}" data-filepath="{html.escape(str(Path(output_root_dir) / rel_path), quote=True)}" data-display-name="{escaped_fname}">
            <div class="img-container" onclick="openLightbox(this)" style="cursor: pointer;" title="點擊開啟全螢幕極限滿版瀏覽 / 影片串流">
                {img_tag}
            </div>
            <div class="info">
                <div class="filename" title="{escaped_fname}">{escaped_fname}</div>
                {geo_html}
                <div class="details">
                    <span class="badge" style="{badge_style}">{display_label}</span>
                    <span class="size">{fsize}</span>
                </div>
                <button class="card-del-btn" onclick="toggleCardDelete(this); event.stopPropagation();" title="標記/取消標記為待刪除">🗑️ 標記刪除</button>
            </div>
        </div>
        """
        cards_html.append(card)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{month_title}</title>
    <style>
        :root {{ --bg: #F4F6F7; --card-bg: #FFFFFF; --text: #4A4F54; --border: #E0E4E6; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }}
        header {{ background: var(--card-bg); padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 20px; }}
        h1 {{ margin: 0 0 10px 0; font-size: 24px; color: #2C3E50; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; }}
        .generated-time {{ color: #95A5A6; font-size: 13px; font-weight: normal; }}
        .controls {{ display: flex; flex-wrap: wrap; gap: 15px; align-items: center; margin-top: 15px; padding-top: 15px; border-top: 1px solid var(--border); }}
        .btn-group {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        button {{ background: #7D8C94; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; transition: 0.2s; font-weight: bold; }}
        button:hover, button.active {{ background: #4A4F54; }}
        select {{ padding: 8px; border-radius: 5px; border: 1px solid var(--border); outline: none; font-size: 14px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; }}
        .media-card {{ background: var(--card-bg); border-radius: 8px; overflow: hidden; border: 1px solid var(--border); box-shadow: 0 2px 4px rgba(0,0,0,0.03); transition: transform 0.2s, border-color 0.2s; display: flex; flex-direction: column; }}
        .media-card:hover {{ transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
        .media-card.marked-delete {{ border: 2px solid #e74c3c; background: #FFF8F8; opacity: 0.75; }}
        .img-container {{ width: 100%; height: 180px; background: #EAECEE; display: flex; align-items: center; justify-content: center; overflow: hidden; position: relative; }}
        .lazy-image {{ width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity 0.3s ease; }}
        .lazy-image.loaded {{ opacity: 1; }}
        .video-placeholder, .raw-placeholder {{ text-align: center; color: #7F8C8D; font-weight: bold; padding: 10px; }}
        .info {{ padding: 12px; display: flex; flex-direction: column; flex-grow: 1; justify-content: space-between; gap: 8px; }}
        .filename {{ font-size: 13px; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .geo-bar {{ display: flex; justify-content: space-between; align-items: center; font-size: 11px; background: #F8F9F9; padding: 4px 6px; border-radius: 4px; border: 1px solid var(--border); gap: 4px; }}
        .geo-text {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #5D6D7E; flex-grow: 1; }}
        .geo-map-btn {{ color: #2980B9; text-decoration: none; font-weight: bold; flex-shrink: 0; background: #EAF2F8; padding: 2px 6px; border-radius: 3px; transition: 0.2s; }}
        .geo-map-btn:hover {{ background: #D4E6F1; text-decoration: underline; }}
        .details {{ display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #7F8C8D; }}
        .badge {{ padding: 3px 8px; border-radius: 12px; font-size: 10px; font-weight: bold; }}
        .card-del-btn {{ background: #EAECEE; color: #7F8C8D; font-size: 11px; padding: 5px; width: 100%; border-radius: 4px; margin-top: 5px; }}
        .media-card.marked-delete .card-del-btn {{ background: #e74c3c; color: white; }}
        .error-msg {{ display: none; padding: 20px; font-size: 12px; color: #999; text-align: center; }}
        .media-card.broken .lazy-image, .media-card.broken .video-placeholder, .media-card.broken .raw-placeholder {{ display: none !important; }}
        .media-card.broken .error-msg {{ display: block !important; }}
        .delete-bar {{ background: #FFF3CD; border: 1px solid #FFEEBA; color: #856404; padding: 15px; border-radius: 8px; margin-bottom: 20px; display: none; align-items: center; gap: 20px; font-weight: bold; }}
        .delete-btns {{ display: flex; flex-direction: row; gap: 8px; flex-wrap: wrap; }}
        .btn-copy {{ background: #27AE60; color: white; width: 250px; text-align: left; }}
        .btn-copy:hover {{ background: #1E8449; }}
        .lightbox {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100vw; height: 100vh; background-color: #000000; align-items: center; justify-content: center; overflow: hidden; }}
        .lightbox-content {{ width: 100vw; height: 100vh; max-width: 100vw; max-height: 100vh; object-fit: contain; }}
        .lightbox-top-bar {{ position: absolute; top: 0; left: 0; width: 100%; padding: 20px 30px; background: linear-gradient(to bottom, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0) 100%); display: flex; justify-content: space-between; align-items: center; z-index: 1002; box-sizing: border-box; pointer-events: none; }}
        .lightbox-top-bar * {{ pointer-events: auto; }}
        .lightbox-caption {{ color: #F4F6F7; font-size: 16px; text-shadow: 0 1px 3px rgba(0,0,0,0.8); }}
        .lightbox-close {{ color: #FFF; font-size: 42px; font-weight: bold; cursor: pointer; transition: 0.2s; user-select: none; line-height: 1; }}
        .lightbox-close:hover {{ color: #e74c3c; }}
        .nav-arrow {{ position: absolute; top: 50%; transform: translateY(-50%); color: rgba(255,255,255,0.7); font-size: 60px; font-weight: bold; cursor: pointer; padding: 20px 15px; user-select: none; transition: 0.2s; z-index: 1002; }}
        .nav-arrow:hover {{ color: #FFF; background-color: rgba(255,255,255,0.15); border-radius: 8px; }}
        .prev-arrow {{ left: 15px; }}
        .next-arrow {{ right: 15px; }}
        .lightbox-bottom-bar {{ position: absolute; bottom: 0; left: 0; width: 100%; padding: 25px 30px; background: linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0) 100%); display: flex; justify-content: center; align-items: center; z-index: 1002; box-sizing: border-box; pointer-events: none; }}
        .lightbox-bottom-bar * {{ pointer-events: auto; }}
        .lightbox-del-btn {{ background: rgba(125,140,148,0.9); color: white; padding: 12px 30px; border-radius: 30px; font-size: 15px; font-weight: bold; cursor: pointer; border: 2px solid white; transition: 0.2s; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }}
        .lightbox-del-btn:hover {{ background: #4A4F54; transform: scale(1.05); }}
        .lightbox-del-btn.marked {{ background: #e74c3c; border-color: #ffd700; }}
        .lightbox-msg {{ color: #FFF; font-size: 18px; text-align: center; padding: 40px; background: #2C3E50; border-radius: 8px; z-index: 1001; }}
    </style>
</head>
<body>
    <header>
        <h1>
            <span>📁 {month_title} <span class="generated-time">(Generated : {generated_ts})</span></span>
            <span style="font-size: 15px; font-weight: normal; color:#7F8C8D;">總共收錄: <strong>{len(media_records)}</strong> 個檔案</span>
        </h1>
        <div class="delete-bar" id="deleteBar">
            <span id="deleteCountText">🗑️ 已標記 0 個待刪除檔案</span>
            <div class="delete-btns">
                <button class="btn-copy" onclick="copyDeleteCommands('win')" title="直接複製 del /f /q 指令，於 CMD 貼上即可刪除">📋 Windows CMD 刪除指令</button>
                <button class="btn-copy" style="background:#5B4B8A;" onclick="copyDeleteCommands('powershell')" title="直接複製 Remove-Item 指令，於 Windows PowerShell 貼上即可刪除">📋 Windows PowerShell 刪除指令</button>
                <button class="btn-copy" style="background:#2980B9;" onclick="copyDeleteCommands('mac')" title="直接複製 rm -f 指令，於 macOS 終端機貼上即可刪除">📋 複製 macOS/Linux 刪除指令</button>
            </div>
        </div>
        <div class="controls">
            <span>過濾篩選:</span>
            <div class="btn-group">
                <button class="filter-btn active" onclick="filterSelection('all')">全部</button>
                <button class="filter-btn" onclick="filterSelection('standard')">照片</button>
                <button class="filter-btn" onclick="filterSelection('video')">影片</button>
            </div>
            <span style="margin-left:auto;">排序方式:</span>
            <select id="sortSelect" onchange="sortGrid()">
                <option value="name-asc">檔名 (A ➔ Z)</option>
                <option value="name-desc">檔名 (Z ➔ A)</option>
                <option value="size-desc">大小 (大 ➔ 小)</option>
                <option value="size-asc">大小 (小 ➔ 大)</option>
            </select>
        </div>
    </header>

    <div class="grid" id="mediaGrid">
        {"".join(cards_html)}
    </div>

    <!-- 100vw/100vh 究極滿版懸浮燈箱 -->
    <div id="lightbox" class="lightbox" onclick="if(event.target === this) closeLightbox();">
        <div class="lightbox-top-bar">
            <div id="lightbox-caption" class="lightbox-caption"></div>
            <span class="lightbox-close" onclick="closeLightbox()" title="關閉燈箱 (Esc)">&times;</span>
        </div>
        <a class="nav-arrow prev-arrow" onclick="changeSlide(-1, event)" title="上一張 (方向鍵左)">&#10094;</a>
        <a class="nav-arrow next-arrow" onclick="changeSlide(1, event)" title="下一張 (方向鍵右 / 空白鍵)">&#10095;</a>
        <img id="lightbox-img" class="lightbox-content" src="" alt="" style="display:none;">
        <video id="lightbox-video" class="lightbox-content" controls style="display:none; background:#000;" onclick="event.stopPropagation();"></video>
        <div id="lightbox-msg" class="lightbox-msg" style="display:none;"></div>
        <div class="lightbox-bottom-bar">
            <button id="lightbox-del-btn" class="lightbox-del-btn" onclick="toggleLightboxDelete(event)" title="快速鍵: Delete / Backspace">🗑️ 標記為刪除</button>
        </div>
    </div>

    <script>
        let currentVisibleCards = [];
        let currentIndex = 0;

        document.addEventListener("DOMContentLoaded", function() {{
            initLazyLoad();
            sortGrid();
        }});

        function initLazyLoad() {{
            let lazyImages = [].slice.call(document.querySelectorAll("img.lazy-image"));
            if ("IntersectionObserver" in window) {{
                let lazyImageObserver = new IntersectionObserver(function(entries, observer) {{
                    entries.forEach(function(entry) {{
                        if (entry.isIntersecting) {{
                            let lazyImage = entry.target;
                            lazyImage.src = lazyImage.dataset.src;
                            lazyImage.onload = () => lazyImage.classList.add("loaded");
                            lazyImageObserver.unobserve(lazyImage);
                        }}
                    }});
                }});
                lazyImages.forEach(function(lazyImage) {{ lazyImageObserver.observe(lazyImage); }});
            }} else {{
                lazyImages.forEach(function(lazyImage) {{
                    lazyImage.src = lazyImage.dataset.src;
                    lazyImage.classList.add("loaded");
                }});
            }}
        }}

        function filterSelection(category) {{
            let cards = document.getElementsByClassName("media-card");
            let btns = document.getElementsByClassName("filter-btn");
            for (let btn of btns) {{ btn.classList.remove("active"); }}
            event.target.classList.add("active");

            for (let card of cards) {{
                if (category === "all" || card.getAttribute("data-category") === category) {{
                    card.style.display = "flex";
                }} else {{
                    card.style.display = "none";
                }}
            }}
            updateVisibleCardsList();
        }}

        function sortGrid() {{
            let grid = document.getElementById("mediaGrid");
            let cards = Array.from(grid.getElementsByClassName("media-card"));
            let sortValue = document.getElementById("sortSelect").value;

            cards.sort(function(a, b) {{
                if (sortValue === "name-asc") {{ let groupCompare = a.dataset.group.localeCompare(b.dataset.group); return groupCompare || (parseInt(a.dataset.groupOrder) - parseInt(b.dataset.groupOrder)) || a.dataset.name.localeCompare(b.dataset.name); }}
                if (sortValue === "name-desc") return b.dataset.name.localeCompare(a.dataset.name);
                if (sortValue === "size-desc") return parseInt(b.dataset.size) - parseInt(a.dataset.size);
                if (sortValue === "size-asc") return parseInt(a.dataset.size) - parseInt(b.dataset.size);
            }});

            for (let card of cards) {{ grid.appendChild(card); }}
            updateVisibleCardsList();
        }}

        function updateVisibleCardsList() {{
            let grid = document.getElementById("mediaGrid");
            currentVisibleCards = Array.from(grid.getElementsByClassName("media-card")).filter(c => c.style.display !== "none");
        }}

        // --- 標記刪除與一鍵剪貼簿功能 ---
        function toggleCardDelete(btn) {{
            let card = btn.closest(".media-card");
            card.classList.toggle("marked-delete");
            btn.innerText = card.classList.contains("marked-delete") ? "✓ 已標記刪除" : "🗑️ 標記刪除";
            updateDeleteUI();
        }}

        function toggleLightboxDelete(e) {{
            if (e) e.stopPropagation();
            let card = currentVisibleCards[currentIndex];
            if (!card) return;
            card.classList.toggle("marked-delete");
            let btn = card.querySelector(".card-del-btn");
            if (btn) btn.innerText = card.classList.contains("marked-delete") ? "✓ 已標記刪除" : "🗑️ 標記刪除";
            updateDeleteUI();
            updateLightboxDeleteBtn();
        }}

        function updateLightboxDeleteBtn() {{
            let lbDelBtn = document.getElementById("lightbox-del-btn");
            let card = currentVisibleCards[currentIndex];
            if (card && card.classList.contains("marked-delete")) {{
                lbDelBtn.classList.add("marked");
                lbDelBtn.innerText = "✓ 已標記為刪除 (點此或按 Delete 取消)";
            }} else {{
                lbDelBtn.classList.remove("marked");
                lbDelBtn.innerText = "🗑️ 標記為刪除 (點此或按 Delete)";
            }}
        }}

        function updateDeleteUI() {{
            let markedCards = document.querySelectorAll(".media-card.marked-delete");
            let bar = document.getElementById("deleteBar");
            let txt = document.getElementById("deleteCountText");
            if (markedCards.length > 0) {{
                bar.style.display = "flex";
                txt.innerText = `🗑️ 已標記 ${{markedCards.length}} 個待刪除檔案`;
            }} else {{
                bar.style.display = "none";
            }}
        }}

        function quotePosixShell(path) {{
            return "'" + path.replace(/'/g, "'\\"'\\"'") + "'";
        }}

        function copyDeleteCommands(type) {{
            let markedCards = document.querySelectorAll(".media-card.marked-delete");
            if (markedCards.length === 0) return;

            let content = "";
            if (type === 'win') {{
                markedCards.forEach(c => {{
                    let relPath = (c.dataset.filepath || c.dataset.url).replace(/\\//g, '\\\\');
                    content += `del /f /q "${{relPath}}"\\r\\n`;
                }});
            }} else if (type === 'powershell') {{
                markedCards.forEach(c => {{
                    let relPath = (c.dataset.filepath || c.dataset.url).replace(/\\//g, '\\\\');
                    let literalPath = relPath.replace(/'/g, "''");
                    content += `Remove-Item -LiteralPath '${{literalPath}}' -Force\\r\\n`;
                }});
            }} else {{
                markedCards.forEach(c => {{
                    let relPath = c.dataset.filepath || c.dataset.url;
                    content += `rm -f ${{quotePosixShell(relPath)}}\\n`;
                }});
            }}

            navigator.clipboard.writeText(content).then(() => {{
                alert(`✅ 已成功複製 ${{markedCards.length}} 筆刪除指令到剪貼簿！\\n\\n請在輸出根目錄開啟對應的 CMD、Windows PowerShell 或 macOS/Linux 終端機，再貼上執行。`);
            }}).catch(err => {{
                alert("無法自動寫入剪貼簿，請改為點擊右方下載按鈕保存腳本。");
            }});
        }}

        function openLightbox(element) {{
            document.body.style.overflow = 'hidden';
            updateVisibleCardsList();
            let card = element.closest(".media-card");
            currentIndex = currentVisibleCards.indexOf(card);
            showSlide(currentIndex);
            document.getElementById("lightbox").style.display = "flex";
        }}

        function closeLightbox() {{
            document.body.style.overflow = '';
            let lbVid = document.getElementById("lightbox-video");
            lbVid.pause();
            lbVid.src = "";
            document.getElementById("lightbox").style.display = "none";
        }}

        function changeSlide(step, e) {{
            if (e) e.stopPropagation();
            currentIndex += step;
            if (currentIndex >= currentVisibleCards.length) currentIndex = 0;
            if (currentIndex < 0) currentIndex = currentVisibleCards.length - 1;
            showSlide(currentIndex);
        }}

        function showSlide(index) {{
            let card = currentVisibleCards[index];
            if (!card) return;
            let imgUrl = card.dataset.url;
            let name = card.dataset.displayName;
            let category = card.dataset.category;
            let displayCategory = (category === 'standard') ? 'IMAGE' : category.toUpperCase();

            let lbImg = document.getElementById("lightbox-img");
            let lbVid = document.getElementById("lightbox-video");
            let lbMsg = document.getElementById("lightbox-msg");
            let lbCaption = document.getElementById("lightbox-caption");

            lbVid.pause();
            lbCaption.innerHTML = `<strong>${{name}}</strong> <span style="background:#A88B87; color:white; padding:2px 8px; border-radius:10px; font-size:12px; margin-left:8px;">${{displayCategory}}</span> <span style="color:#BDC3C7; font-size:14px; margin-left:12px;">第 ${{index + 1}} / ${{currentVisibleCards.length}} 張</span>`;

            if (category === "video") {{
                lbImg.style.display = "none";
                lbMsg.style.display = "none";
                lbVid.style.display = "block";
                lbVid.src = imgUrl;
                lbVid.play().catch(() => console.log("瀏覽器阻擋自動播放，需手動點擊"));
            }} else if (category === "raw") {{
                lbImg.style.display = "none";
                lbVid.style.display = "none";
                lbMsg.style.display = "block";
                lbMsg.innerHTML = `📸 RAW 原檔不支援瀏覽器線上大圖預覽<br><br><a href="${{imgUrl}}" target="_blank" style="color: #F39C12; text-decoration: underline; font-weight:bold;">點此下載 / 新分頁開啟原始檔 (${{name}})</a>`;
            }} else {{
                lbVid.style.display = "none";
                lbMsg.style.display = "none";
                lbImg.style.display = "block";
                lbImg.src = imgUrl;
            }}
            updateLightboxDeleteBtn();
        }}

        document.addEventListener("keydown", function(e) {{
            let lb = document.getElementById("lightbox");
            if (lb.style.display === "flex") {{
                if (e.key === "ArrowRight" || e.key === " ") {{
                    e.preventDefault();
                    changeSlide(1);
                }} else if (e.key === "ArrowLeft") {{
                    e.preventDefault();
                    changeSlide(-1);
                }} else if (e.key === "Escape") {{
                    closeLightbox();
                }} else if (e.key === "Delete" || e.key === "Backspace") {{
                    e.preventDefault();
                    toggleLightboxDelete();
                }}
            }}
        }});
    </script>
</body>
</html>"""

    try:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception:
        pass

def generate_file_type_summary(output_root_dir, audit_manifest):
    """產生獨立的副檔名統計頁；目的地數量以本次最終實體檔為準。"""
    source = Counter(row[4].lower() or '[無副檔名]' for row in audit_manifest)
    copied = Counter(row[4].lower() or '[no_ext]' for row in audit_manifest if row[6] == 'PASS')
    skipped = Counter(row[4].lower() or '[no_ext]' for row in audit_manifest if row[6] == 'SKIP')
    failed = Counter(row[4].lower() or '[no_ext]' for row in audit_manifest if row[6] == 'FAIL')
    destination = destination_extension_counts(Path(output_root_dir))
    extensions = sorted(set(source) | set(destination))
    rows = ''.join(
        f"<tr><td>{html.escape(ext)}</td><td>{source[ext]:,}</td><td>{copied[ext]:,}</td><td>{skipped[ext]:,}</td><td>{failed[ext]:,}</td><td>{destination[ext]:,}</td></tr>"
        for ext in extensions
    )
    generated_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    content = f'''<!doctype html><html lang="zh-TW"><meta charset="utf-8"><title>檔案類型統計</title>
    <style>body{{font-family:Segoe UI,sans-serif;margin:24px;color:#2c3e50}}table{{border-collapse:collapse;width:100%;max-width:900px}}th,td{{padding:9px 12px;border:1px solid #dfe6e9;text-align:right}}th:first-child,td:first-child{{text-align:left}}th{{background:#eef2f3}}</style>
    <h1>檔案類型統計 <span style="color:#95A5A6;font-size:13px;font-weight:normal;">(Generated : {generated_ts})</span></h1><p>來源掃描數包含本次掃描範圍內所有副檔名；目的地實際數不含程式產生的報表與日誌。</p>
    <table><tr><th>Ext</th><th>Scanned</th><th>PASS</th><th>SKIP</th><th>FAIL</th><th>Dest Count</th></tr>{rows}</table></html>'''
    with open(Path(output_root_dir) / '_manifest_filetype.html', 'w', encoding='utf-8') as f:
        f.write(content)

# --- 產生免外掛、完全獨立可執行的 HTML 總報表 ---
def generate_manifest_html(output_root_dir, audit_manifest):
    if not audit_manifest:
        return
    import json
    html_path = Path(output_root_dir) / "_index.html"
    generated_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    has_geo_column = any(len(row) > 9 for row in audit_manifest)
    geo_filter_btn_html = '<button onclick="setFilter(\'status\', \'GEO\', this)">🌏 GEO</button>' if has_geo_column else ''
    geo_header_html = '<th>地圖</th>' if has_geo_column else ''

    clean_data = []
    for row in audit_manifest:
        normalized = [
            str(row[0]),
            # Normalize non-path placeholders to "-"
            format_display_path(row[1]) if (row[1] and row[1] != PLACEHOLDER) else PLACEHOLDER,
            format_display_path(row[2]) if (row[2] and row[2] != PLACEHOLDER) else PLACEHOLDER,
            str(row[3]),
            str(row[4]),
            str(row[5]),
            str(row[6]),
            str(row[7]),
            str(row[8])
        ]
        if has_geo_column:
            normalized.append(str(row[9]) if len(row) > 9 else PLACEHOLDER)
        clean_data.append(normalized)

    # 2. 將 Python List 轉為壓縮版 JSON 字串 (去除多餘空白，體積縮小 80%)
    json_data_str = json.dumps(clean_data, ensure_ascii=False, separators=(',', ':'))

    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>照片影片處理總報表</title>
    <style>
        :root {{ --bg: #F4F6F7; --card-bg: #FFFFFF; --text: #4A4F54; --border: #E0E4E6; --main: #7D8C94; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }}
        header {{ background: var(--card-bg); padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 15px; }}
        h1 {{ margin: 0 0 15px 0; font-size: 22px; color: #2C3E50; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }}
        .generated-time {{ color: #95A5A6; font-size: 13px; font-weight: normal; }}
        .filter-bar {{ display: flex; flex-wrap: wrap; gap: 15px; align-items: center; border-top: 1px solid var(--border); padding-top: 15px; }}
        .btn-group {{ display: flex; gap: 6px; flex-wrap: wrap; }}
        button {{ background: var(--main); color: white; border: none; padding: 6px 14px; border-radius: 5px; cursor: pointer; transition: 0.2s; font-size: 13px; font-weight: bold; }}
        button:hover, button.active {{ background: #2C3E50; }}
        button:disabled {{ background: #BDC3C7; cursor: not-allowed; }}
        input[type="text"] {{ padding: 8px 12px; border-radius: 5px; border: 1px solid var(--border); outline: none; font-size: 14px; width: 280px; }}

        /* 分頁控制器 */
        .pagination-bar {{ display: flex; justify-content: space-between; align-items: center; background: var(--card-bg); padding: 12px 20px; border-radius: 8px; margin-bottom: 15px; border: 1px solid var(--border); flex-wrap: wrap; gap: 10px; }}
        .page-info {{ font-weight: bold; color: #2C3E50; font-size: 14px; }}
        select {{ padding: 6px 10px; border-radius: 5px; border: 1px solid var(--border); font-size: 13px; outline: none; }}

        .table-container {{ background: var(--card-bg); border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); overflow-x: auto; border: 1px solid var(--border); min-height: 500px; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; white-space: nowrap; }}
        th {{ background: #EAECEE; color: #2C3E50; padding: 12px 15px; font-weight: bold; border-bottom: 2px solid var(--border); position: sticky; top: 0; z-index: 10; }}
        td {{ padding: 10px 15px; border-bottom: 1px solid var(--border); vertical-align: middle; }}
        tr:hover {{ background-color: #F8F9F9; }}
        tr.has-plugin-warn {{ background-color: #FFFDF0; }}
        tr.has-plugin-warn:hover {{ background-color: #FFF9D6; }}

        .font-bold {{ font-weight: bold; color: #2C3E50; }}
        .path-cell {{ max-width: 250px; overflow: hidden; text-overflow: ellipsis; color: #7F8C8D; }}
        .reason-cell {{ max-width: 200px; overflow: hidden; text-overflow: ellipsis; }}
        .plugin-cell {{ max-width: 250px; overflow: hidden; text-overflow: ellipsis; color: #D68910; font-weight: 500; }}
        .cam-badge {{ background: #EAEDED; color: #5D6D7E; padding: 3px 8px; border-radius: 4px; font-size: 12px; }}
        .status-badge {{ padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; }}
        .status-success {{ background: #D4EFDF; color: #196F3D; }}
        .status-skip {{ background: #FCF3CF; color: #B7950B; }}
        .status-fail {{ background: #FADBD8; color: #943126; }}
    </style>
</head>
<body>
    <header>
        <h1>
            <span>📋 照片影片處理總報表 <span class="generated-time">(Generated : {generated_ts})</span></span>
            <span style="font-size: 14px; color: #7F8C8D; font-weight: normal;">總收錄: <strong id="totalCount" style="color:#2C3E50;">0</strong> 筆資料</span>
        </h1>
        {get_stats_banner_html()}
        <div class="filter-bar">
            <button onclick="window.open('_manifest_filetype.html','fileTypeSummary','width=980,height=720')">檔案類型統計</button>
            <span>🔍 搜尋過濾:</span>
            <input type="text" id="searchInput" oninput="debounceFilter()" placeholder="關鍵字 (檔名、相機、插件訊息)...">

            <span style="margin-left: 10px;">狀態篩選:</span>
            <div class="btn-group" id="statusBtns">
                <button class="active" onclick="setFilter('status', 'all', this)">全部</button>
                {geo_filter_btn_html}
                <button onclick="setFilter('status', 'PASS', this)">✅ PASS</button>
                <button onclick="setFilter('status', 'SKIP', this)">⏭️ SKIP</button>
                <button onclick="setFilter('status', 'FAIL', this)">❌ FAIL</button>
            </div>

            <span style="margin-left: 10px;">類別:</span>
            <div class="btn-group" id="catBtns">
                <button class="active" onclick="setFilter('cat', 'all', this)">全部</button>
                <button onclick="setFilter('cat', 'standard', this)">照片</button>
                <button onclick="setFilter('cat', 'video', this)">影片</button>
                <button onclick="setFilter('cat', 'raw', this)">RAW</button>
            </div>
        </div>
    </header>

    <!-- 分頁控制列 -->
    <div class="pagination-bar">
        <div class="btn-group">
            <button id="btnFirst" onclick="changePage(1)">⏪ 第一頁</button>
            <button id="btnPrev" onclick="changePage(currentPage - 1)">◀ 上一頁</button>
            <button id="btnNext" onclick="changePage(currentPage + 1)">下一頁 ▶</button>
            <button id="btnLast" onclick="changePage(totalPages)">最末頁 ⏩</button>
        </div>
        <div class="page-info">
            第 <span id="pageSpan" style="color:#E74C3C; font-size:16px;">1</span> / <span id="totalPageSpan">1</span> 頁
            (目前顯示：<span id="showingRangeSpan">0 - 0</span> 筆)
        </div>
        <div>
            每頁顯示:
            <select id="pageSizeSelect" onchange="changePageSize()">
                <option value="100">100 筆</option>
                <option value="250" selected>250 筆</option>
                <option value="500">500 筆</option>
                <option value="1000">1000 筆</option>
            </select>
        </div>
    </div>

    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>檔案名稱</th>
                    <th>來源完整路徑</th>
                    <th>輸出目標路徑</th>
                    <th>相機型號</th>
                    <th>副檔名</th>
                    {geo_header_html}
                    <th>處理類別</th>
                    <th>最終狀態</th>
                    <th>詳細說明/略過原因</th>
                    <th>插件訊息</th>
                </tr>
            </thead>
            <tbody id="tableBody">
                <!-- 資料會透過 JS 記憶體分頁極速渲染 -->
            </tbody>
        </table>
    </div>

    <script>
        // 1. 載入原始 JSON 大數據陣列
        const RAW_DATA = {json_data_str};
        const HAS_GEO_COL = {"true" if has_geo_column else "false"};

        let filteredData = RAW_DATA;
        let currentPage = 1;
        let pageSize = 250;
        let totalPages = 1;

        let filterState = {{ status: 'all', cat: 'all', keyword: '' }};
        let filterTimeout = null;

        document.addEventListener("DOMContentLoaded", function() {{
            document.getElementById("totalCount").innerText = RAW_DATA.length.toLocaleString();
            applyFilters();
        }});

        function setFilter(type, value, btn) {{
            filterState[type] = value;
            let container = (type === 'status') ? document.getElementById("statusBtns") : document.getElementById("catBtns");
            let btns = container.getElementsByTagName("button");
            for (let b of btns) b.classList.remove("active");
            btn.classList.add("active");
            applyFilters();
        }}

        // 使用 Debounce 避免連續敲打鍵盤時重複運算
        function debounceFilter() {{
            clearTimeout(filterTimeout);
            filterTimeout = setTimeout(() => {{
                filterState.keyword = document.getElementById("searchInput").value.trim().toLowerCase();
                applyFilters();
            }}, 150);
        }}

        // 記憶體極速過濾核心 (26 萬筆僅耗時幾毫秒)
        function applyFilters() {{
            let kw = filterState.keyword;
            filteredData = RAW_DATA.filter(row => {{
                if (filterState.status === 'GEO') {{
                    if (!(HAS_GEO_COL && String(row[9] || "-") !== "-")) return false;
                }} else if (filterState.status !== 'all' && row[6] !== filterState.status) {{
                    return false;
                }}
                if (filterState.cat !== 'all' && row[5] !== filterState.cat) return false;
                if (kw !== "") {{
                    let searchStr = (row[0] + " " + row[3] + " " + row[8] + " " + (HAS_GEO_COL ? (row[9] || "") : "")).toLowerCase();
                    if (searchStr.indexOf(kw) === -1) return false;
                }}
                return true;
            }});

            currentPage = 1;
            updatePagination();
            renderTable();
        }}

        function changePageSize() {{
            pageSize = parseInt(document.getElementById("pageSizeSelect").value);
            currentPage = 1;
            updatePagination();
            renderTable();
        }}

        function changePage(targetPage) {{
            if (targetPage < 1 || targetPage > totalPages || targetPage === currentPage) return;
            currentPage = targetPage;
            updatePagination();
            renderTable();
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}

        function updatePagination() {{
            let totalRecords = filteredData.length;
            totalPages = Math.max(1, Math.ceil(totalRecords / pageSize));
            if (currentPage > totalPages) currentPage = totalPages;

            document.getElementById("pageSpan").innerText = currentPage.toLocaleString();
            document.getElementById("totalPageSpan").innerText = totalPages.toLocaleString();

            let startIdx = (totalRecords === 0) ? 0 : (currentPage - 1) * pageSize + 1;
            let endIdx = Math.min(currentPage * pageSize, totalRecords);
            document.getElementById("showingRangeSpan").innerText = `${{startIdx.toLocaleString()}} - ${{endIdx.toLocaleString()}}`;

            document.getElementById("btnFirst").disabled = (currentPage === 1);
            document.getElementById("btnPrev").disabled = (currentPage === 1);
            document.getElementById("btnNext").disabled = (currentPage === totalPages || totalRecords === 0);
            document.getElementById("btnLast").disabled = (currentPage === totalPages || totalRecords === 0);
        }}

        // 僅渲染當前頁面的 250 筆 HTML 節點，徹底解決記憶體與卡死問題
        function renderTable() {{
            let tbody = document.getElementById("tableBody");
            if (filteredData.length === 0) {{
                tbody.innerHTML = `<tr><td colspan="${{HAS_GEO_COL ? 10 : 9}}" style="text-align:center; padding:30px; color:#999;">找不到符合條件的資料</td></tr>`;
                return;
            }}

            let startIdx = (currentPage - 1) * pageSize;
            let endIdx = Math.min(startIdx + pageSize, filteredData.length);
            let pageData = filteredData.slice(startIdx, endIdx);

            let htmlRows = pageData.map(row => {{
                let fname = escapeHtml(row[0]);
                let srcP = escapeHtml(row[1]);
                let dstP = escapeHtml(row[2]);
                let cam = escapeHtml(row[3]);
                let ext = escapeHtml(row[4]);
                let cat = escapeHtml(row[5]);
                let status = escapeHtml(row[6]);
                let reason = escapeHtml(row[7]);
                let plugin = escapeHtml(row[8]);
                let geoMap = HAS_GEO_COL ? String(row[9] || "-") : "-";

                let dstCellHtml = dstP;
                if ((status === "PASS" || reason.indexOf("IDENTICAL") !== -1) && dstP !== "-" && dstP.indexOf("ALL_MEDIA") === -1) {{
                    let match = dstP.match(/(\\d{{4}}_\\d{{2}})/);
                    if (match) {{
                        let monthReportUrl = `./${{match[1]}}_media_report.html`;
                        dstCellHtml = `<a href="${{monthReportUrl}}" target="_blank" style="color:#2980B9; text-decoration:underline; font-weight:bold;">${{dstP}}</a>`;
                    }}
                }}

                let statusClass = "status-success";
                if (status === "SKIP") statusClass = "status-skip";
                else if (status === "FAIL") statusClass = "status-fail";

                let geoCellHtml = (HAS_GEO_COL && geoMap !== "-")
                    ? `<a href="${{escapeHtml(geoMap)}}" target="_blank" title="View on Google Maps">&#127757;</a>`
                    : "-";

                let rowClass = (plugin !== "-") ? "has-plugin-warn" : "";

                return `<tr class="${{rowClass}}">
                    <td class="font-bold">${{fname}}</td>
                    <td class="path-cell" title="${{srcP}}">${{srcP}}</td>
                    <td class="path-cell" title="${{dstP}}">${{dstCellHtml}}</td>
                    <td><span class="cam-badge">${{cam}}</span></td>
                    <td>${{ext}}</td>
                    ${{HAS_GEO_COL ? `<td>${{geoCellHtml}}</td>` : ``}}
                    <td>${{cat}}</td>
                    <td><span class="status-badge ${{statusClass}}">${{status}}</span></td>
                    <td class="reason-cell" title="${{reason}}">${{reason}}</td>
                    <td class="plugin-cell" title="${{plugin}}">${{plugin}}</td>
                </tr>`;
            }});

            tbody.innerHTML = htmlRows.join('');
        }}

        function escapeHtml(str) {{
            return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
        }}
    </script>
</body>
</html>"""
    try:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception:
        pass

# Stage 7 (non-behavioral extraction): bind reporting builders to reporting modules.
try:
    from .reporting.html_builder import generate_html_report as _report_generate_html_report
    from .reporting.index_builder import (
        destination_extension_counts as _report_destination_extension_counts,
        generate_file_type_summary as _report_generate_file_type_summary,
        generate_manifest_html as _report_generate_manifest_html,
    )
except ImportError:
    from reporting.html_builder import generate_html_report as _report_generate_html_report
    from reporting.index_builder import (
        destination_extension_counts as _report_destination_extension_counts,
        generate_file_type_summary as _report_generate_file_type_summary,
        generate_manifest_html as _report_generate_manifest_html,
    )

destination_extension_counts = _report_destination_extension_counts
generate_html_report = _report_generate_html_report
generate_file_type_summary = _report_generate_file_type_summary
generate_manifest_html = _report_generate_manifest_html

# --- 背景執行緒函式 ---
def threaded_process_images(selected_folders, dest_dir, organize_by_time, normalize_name, enable_geo_lookup, copy_video, copy_raw, overwrite, performance_mode, q, stop_event):
    dest_path = Path(dest_dir)
    report_lines = []
    audit_manifest = []
    CAPTURE_META_CACHE.clear()

    # 歸零全域戰情數據
    GEO_PERF_STATS['queries'] = 0
    GEO_PERF_STATS['cache_hits'] = 0
    GEO_PERF_STATS['new_lookups'] = 0
    GEO_PERF_STATS['copied'] = 0
    GEO_PERF_STATS['skipped'] = 0
    GEO_PERF_STATS['total_time'] = 0.0

    if performance_mode:
        q.put(('log', "[PERF] Performance mode enabled: less log / fast scan / GEO fail summary"))

    if not organize_by_time and len(selected_folders) != 1:
        q.put(('msgbox', ("設定錯誤", "未啟用依年月整理時，來源與目的資料夾為 1:1，無法處理多個來源資料夾。"), 'warning', None))
        q.put(('reset', None))
        return

    # 🚀 執行前：搜尋原本來源目錄 (及父目錄) 與目的目錄，聯集載入歷史 _manifest_geo.json
    if enable_geo_lookup:
        load_and_merge_geo_caches(selected_folders, dest_dir, log_callback=lambda m: q.put(('log', m)))

    if enable_geo_lookup and not RG_AVAILABLE:
        q.put(('log', "[GEO] FAIL: reverse_geocoder unavailable; only EXIF GPS and map URL will be used."))

    if enable_geo_lookup and RG_AVAILABLE:
        q.put(('status', "⏳ Loading global offline geo database (first load may take a few seconds)..."))
        try:
            _ = rg.search((24.989, 121.313))
            q.put(('log', "✅ Global offline geo database loaded and index warmed up."))
        except Exception as e:
            q.put(('log', f"⚠️ [GEO] ERROR: database preload failed: {e}"))
            enable_geo_lookup = False

    files = []
    valid_extensions = set(STANDARD_EXTENSIONS)
    if copy_raw: valid_extensions.update(RAW_EXTENSIONS)
    if copy_video: valid_extensions.update(VIDEO_EXTENSIONS)

    # 走訪所有被選目錄
    for folder in selected_folders:
        if stop_event.is_set(): break
        for dirpath, dirnames, filenames in os.walk(folder):
            if stop_event.is_set(): break

            # 關鍵修復：針對被 EXCLUDE_DIR_KEYWORDS 排除的目錄，強制攔截並輸出日誌理由
            removed_dirs = [d for d in dirnames if any(keyword in d.lower() for keyword in EXCLUDE_DIR_KEYWORDS)]
            for d in removed_dirs:
                skip_path = format_display_path(os.path.join(dirpath, d))
                skip_msg = f"[SKIP_DIR] {skip_path} | REASON: ignored directory ({d})"
                report_lines.append(skip_msg + "\n")
                if not performance_mode:
                    q.put(('log', skip_msg))
            dirnames[:] = [d for d in dirnames if d not in removed_dirs]

            display_path = format_display_path(dirpath)
            display_path = display_path if len(display_path) <= 65 else "..." + display_path[-62:]
            q.put(('status', f"🔍 Scanning directory: {display_path}"))

            # 走訪所有檔案
            for filename in filenames:
                # 精確過濾：只有符合 Kairos 系統特徵的檔案才執行「靜默忽略」
                if is_kairos_self_file(filename):
                    continue

                ext = os.path.splitext(filename)[1].lower()
                full_src_p = os.path.join(dirpath, filename)
                full_src_win_p = format_display_path(full_src_p)

                if ext in IGNORED_EXTENSIONS:
                    # 如果您希望連一般被忽略的檔案都不刷屏，這裡的 append 也可以保留現狀或改為 debug 級別
                    report_lines.append(f"[SKIP_FILE] {full_src_win_p} | REASON: ignored extension ({ext})\n")
                    audit_manifest.append([filename, full_src_win_p, "-", "-", ext, "ignored", "SKIP", f"ignored extension ({ext})", "-"])
                    continue

                if ext in valid_extensions:
                    files.append(Path(dirpath) / filename)
                else:
                    report_lines.append(f"[SKIP] {full_src_win_p} | REASON: unsupported extension ({ext})\n")
                    audit_manifest.append([filename, full_src_win_p, "-", "-", ext, "ignored", "SKIP", f"unsupported extension ({ext})", "-"])

    if stop_event.is_set():
        q.put(('status', "🛑 Processing interrupted"))
        q.put(('reset', None))
        return

    total_files = len(files)
    if total_files == 0:
        q.put(('msgbox', ("提示", "所選目錄中找不到符合的媒體檔。"), 'info', None))
        q.put(('reset', None))
        return

    success_count = 0
    skipped_count = 0
    failed_count = 0
    start_time = time.time()
    processed_size_bytes = 0
    q.put(('status', f"First Pass | safe collection and dup-skip: 0 / {total_files} (0.0%)"))

    monthly_media_map = {}

    for i, file_path in enumerate(files):
        if stop_event.is_set(): break

        full_win_path = format_display_path(file_path)

        try: file_size = os.path.getsize(file_path)
        except OSError: file_size = 0

        # 用於記錄該檔案處理過程中的外掛異常訊息
        captured_warnings = []
        camera_model = "-"
        loc_name, map_url = "-", "-"

        try:
            ext = file_path.suffix.lower()
            stem = file_path.stem

            # 讀取相機型號同時攔截插件訊息
            if performance_mode:
                camera_model = get_camera_model(file_path)
            else:
                with PluginWarningCapturer() as capturer:
                    camera_model = get_camera_model(file_path)
                captured_warnings.extend(capturer.get_messages())

            timestamp_base, _ = timestamp_parts(stem)
            clean_stem = timestamp_base or stem

            if timestamp_base:
                year, month = timestamp_base[:4], timestamp_base[5:7]
                target_name = f"{clean_stem}{ext}"
            else:
                if organize_by_time or normalize_name:
                    # 使用攔截器包覆 get_media_date
                    if performance_mode:
                        media_date = get_media_date(file_path)
                    else:
                        with PluginWarningCapturer() as capturer:
                            media_date = get_media_date(file_path)
                        captured_warnings.extend(capturer.get_messages())

                    year = media_date.strftime('%Y')
                    month = media_date.strftime('%m')
                    target_name = f"{media_date.strftime('%Y-%m-%d %H.%M.%S')}{ext}" if normalize_name else f"{clean_stem}{ext}"
                else:
                    year, month = None, None
                    target_name = f"{clean_stem}{ext}"

            if organize_by_time:
                month_key = f"{year}_{month}"
                target_dir = dest_path / month_key
                category = "standard"

                if ext in RAW_EXTENSIONS:
                    target_dir /= "raw"
                    category = "raw"
                elif ext in VIDEO_EXTENSIONS:
                    category = "video"
            else:
                month_key = "ALL_MEDIA"
                target_dir = dest_path / file_path.parent.relative_to(Path(selected_folders[0]).parent)
                category = "standard"
                if ext in RAW_EXTENSIONS: category = "raw"
                elif ext in VIDEO_EXTENSIONS: category = "video"

            # 去除重複的警告字句並以分號連接成單一行
            plugin_msg_str = " ; ".join(dict.fromkeys(captured_warnings)) if captured_warnings else PLACEHOLDER

            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / target_name

            effective_category = category
            is_duplicate_skip = False
            skip_reason = None

            # 取得正規化後的最終目標主檔名 (例如 "2017-10-15 17.38.59")
            target_stem = target_file.stem
            
            # 在進行衝突命名與 unique_path 前，先全面檢查該群組所有序號後綴是否存在實體相同檔案
            identical_match = find_identical_in_target(file_path, target_dir, target_stem, ext)

            if identical_match:
                is_duplicate_skip = True
                skip_reason = f"[IDENTICAL] {identical_match.name}"
                target_file = identical_match

            elif target_file.exists():
                overwrite_photo_mode = overwrite and category == "standard" and ext in STANDARD_EXTENSIONS
                decision = compare_and_decide(file_path, target_file)

                if decision == "IDENTICAL":
                    is_duplicate_skip = True
                    skip_reason = f"[IDENTICAL] {target_file.name}"

                elif overwrite_photo_mode and decision == "SAME_MS":
                    src_mtime = os.path.getmtime(file_path)
                    tgt_mtime = os.path.getmtime(target_file)
                    if src_mtime > tgt_mtime:
                        archived = candidate_path_for(target_dir, target_file.stem, ext)
                        invalidate_capture_meta(target_file)
                        invalidate_capture_meta(archived)
                        target_file.rename(archived)
                        if not performance_mode:
                            q.put(('log', f"[OVERWRITE] SAME_MS: archived previous to candidate -> {archived.name}"))
                    else:
                        target_file = candidate_path_for(target_dir, target_file.stem, ext)
                        effective_category = "candidate" if category == "standard" else category

                elif overwrite_photo_mode and decision == "BURST":
                    src_meta = get_capture_meta(file_path)
                    tgt_meta = get_capture_meta(target_file)
                    base_stem = timestamp_base or target_file.stem
                    src_ms = src_meta.get('subsec_ms')
                    tgt_ms = tgt_meta.get('subsec_ms')

                    if tgt_ms and target_file.stem == base_stem:
                        existing_burst_path = unique_path(target_dir, f"{base_stem}-{tgt_ms}", ext)
                        invalidate_capture_meta(target_file)
                        invalidate_capture_meta(existing_burst_path)
                        target_file.rename(existing_burst_path)
                        if not performance_mode:
                            q.put(('log', f"[OVERWRITE] BURST: renamed existing -> {existing_burst_path.name}"))

                    if src_ms:
                        target_file = unique_path(target_dir, f"{base_stem}-{src_ms}", ext)
                    else:
                        target_file = unique_indexed_path(target_dir, base_stem, ext, start=1)

                elif overwrite_photo_mode and decision == "REPLACE":
                    archived = candidate_path_for(target_dir, target_file.stem, ext)
                    invalidate_capture_meta(target_file)
                    invalidate_capture_meta(archived)
                    target_file.rename(archived)
                    if not performance_mode:
                        q.put(('log', f"[OVERWRITE] REPLACE: archived previous to candidate -> {archived.name}"))

                elif overwrite_photo_mode and decision == "KEEP":
                    target_file = candidate_path_for(target_dir, target_file.stem, ext)
                    effective_category = "candidate" if category == "standard" else category

                else:
                    target_file = unique_path(target_dir, target_file.stem, ext)

            if target_file.parent.name == 'candidate' and effective_category == "standard":
                effective_category = "candidate"

            if is_duplicate_skip:
                skipped_count += 1
                processed_size_bytes += file_size
                report_lines.append(f"[SKIP: IDENTICAL] {full_win_path} | REASON: {skip_reason}\n")
                audit_manifest.append([file_path.name, str(file_path), str(target_file), camera_model, ext, effective_category, "SKIP", skip_reason, plugin_msg_str])
                q.put(('metrics', processed_size_bytes))  # 直接丟總大小！
                q.put(('progress', (i + 1) / total_files))
                continue

            max_retries = 5
            for attempt in range(max_retries):
                try:
                    # 嚴格守則：只有在 Target 目錄執行複製與寫入，絕對不觸碰、不污染來源資料夾
                    shutil.copy2(file_path, target_file)
                    invalidate_capture_meta(target_file)

                    log_path = target_dir / "_process_log.txt"
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    with open(log_path, 'a', encoding='utf-8') as log_f:
                        log_f.write(f"[{timestamp}] Processed: {file_path.name} -> {target_file.name}\n")

                    if organize_by_time:
                        rel_p = target_file.relative_to(dest_path).as_posix()
                        if month_key not in monthly_media_map:
                            monthly_media_map[month_key] = []

                        if effective_category != "raw":
                            monthly_media_map[month_key].append({
                                'name': target_file.name,
                                'rel_path': rel_p,
                                'size': file_size,
                                'category': effective_category,
                                'loc_name': loc_name,
                                'map_url': map_url
                            })

                    audit_manifest.append([file_path.name, str(file_path), str(target_file), camera_model, ext, effective_category, "PASS", "COPY_OK", plugin_msg_str])
                    if not performance_mode:
                        q.put(('log', f"[{timestamp}] Processed: {file_path.name} -> {target_file.name}"))

                    # 若該檔案有外掛異常訊息，同步輸出在 UI 日誌提示
                    if not performance_mode and plugin_msg_str != "-":
                        q.put(('log', f"⚠️ [PLUGIN] {file_path.name}: {plugin_msg_str}"))

                    success_count += 1
                    break
                except (PermissionError, OSError) as e:
                    if attempt < max_retries - 1: time.sleep(0.5)
                    else: raise e

        except Exception as e:
            failed_count += 1
            plugin_msg_str = " ; ".join(dict.fromkeys(captured_warnings)) if captured_warnings else "-"
            report_lines.append(f"[FAIL] {full_win_path} | REASON: processing exception ({str(e)})\n")
            audit_manifest.append([file_path.name, str(file_path), PLACEHOLDER, camera_model, ext, PLACEHOLDER, "FAIL", f"ERROR: processing exception: {str(e)}", plugin_msg_str])
            q.put(('error_log', f"ERROR while processing {file_path.name}: {e}"))

        processed_size_bytes += file_size
        display_file_path = full_win_path if len(full_win_path) <= 65 else "..." + full_win_path[-62:]
        phase_elapsed = time.time() - start_time
        rate = (i + 1) / phase_elapsed if phase_elapsed > 0 else 0
        remaining = (total_files - i - 1) / rate if rate > 0 else 0
        q.put(('progress', (i + 1) / total_files))
        overall_remaining = remaining * 1.15  # 第二輪尚未取得實際群組數，先以保守係數估算。
        q.put(('status', f"First Pass | safe collection and duplicate-skip: {i + 1} / {total_files} ({(i + 1) / total_files:.1%}) | elapsed {format_time(phase_elapsed)} | phase remaining {format_time(remaining)} | overall ETA {format_time(overall_remaining)} | {display_file_path}"))
        q.put(('metrics', processed_size_bytes))  # 直接丟總大小！

    # Second Pass：同秒連拍衝突與候選整理
    if not stop_event.is_set() and organize_by_time and overwrite:
        month_dirs = [p for p in dest_path.iterdir() if p.is_dir() and re.fullmatch(r'\d{4}_\d{2}', p.name)]
        second_start = time.time()
        for index, month_dir in enumerate(month_dirs, start=1):
            elapsed = time.time() - second_start
            rate = (index - 1) / elapsed if elapsed > 0 and index > 1 else 0
            remaining = (len(month_dirs) - index + 1) / rate if rate else 0
            q.put(('status', f"Second Pass | organizing burst sets and alternates: {index} / {len(month_dirs)} ({index / max(len(month_dirs), 1):.1%}) | elapsed {format_time(elapsed)} | overall ETA {format_time(remaining)} | {month_dir.name}"))
            second_pass_month(month_dir, stop_event)
            q.put(('progress', index / max(len(month_dirs), 1)))
            q.put(('metrics', processed_size_bytes))

    generated_html_reports = []
    index_report_path = None
    geo_stats = {'pass': 0, 'fail': 0, 'skip': 0}
    geo_fail_by_abs_path = {}
    geo_map_by_abs_path = {}
    if not stop_event.is_set():
        # 進行最終產出路徑掃描與「批量空間矩陣解析」
        monthly_media_map, geo_stats, geo_fail_by_abs_path, geo_map_by_abs_path, geo_fail_reason_counter = collect_media_records(
            dest_path, organize_by_time, enable_geo_lookup, q, stop_event, start_time, processed_size_bytes, performance_mode
        )

        # 處理完畢後：將更新後的地理空間快取字典封存回目標輸出目錄
        if enable_geo_lookup:
            save_geo_cache_to_dest(dest_dir, log_callback=lambda m: q.put(('log', m)))

        # 在生成 HTML 報表前，統計最終完成的執行時間與處理張數
        GEO_PERF_STATS['total_time'] = time.time() - start_time
        GEO_PERF_STATS['copied'] = success_count
        GEO_PERF_STATS['skipped'] = skipped_count

        q.put(('status', "Generating HTML preview reports from final file state..."))
        for m_key, records in monthly_media_map.items():
            generate_html_report(dest_path, m_key, records)
            generated_html_reports.append((m_key, dest_path / f"{m_key}_media_report.html"))

    if audit_manifest:
        try:
            if enable_geo_lookup:
                q.put(('log', f"🧭 GEO stats | PASS: {geo_stats.get('pass', 0)} | FAIL: {geo_stats.get('fail', 0)} | SKIP: {geo_stats.get('skip', 0)}"))
                if performance_mode and geo_fail_reason_counter:
                    summary_parts = [f"{reason} x{count}" for reason, count in geo_fail_reason_counter.most_common(5)]
                    q.put(('log', f"[GEO] FAIL summary: {' | '.join(summary_parts)}"))
                for row in audit_manifest:
                    if len(row) < 10:
                        row.append(PLACEHOLDER)
                    target_path = row[2]
                    if target_path == PLACEHOLDER:
                        continue
                    geo_key = os.path.normcase(os.path.abspath(str(target_path)))
                    geo_reason = geo_fail_by_abs_path.get(geo_key)
                    if not geo_reason:
                        geo_url = geo_map_by_abs_path.get(geo_key)
                        if geo_url:
                            row[9] = geo_url
                        continue
                    geo_msg = f"[GEO] {geo_reason}"
                    row[8] = geo_msg if row[8] == PLACEHOLDER else f"{row[8]} ; {geo_msg}"
                    geo_url = geo_map_by_abs_path.get(geo_key)
                    if geo_url:
                        row[9] = geo_url

            manifest_path = dest_path / "_manifest_audit.csv"
            with open(manifest_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                # 新增「相機型號」,「插件訊息」欄位；地理解析啟用時加上「地圖」
                has_geo_column = any(len(row) > 9 for row in audit_manifest)
                header = ['檔案名稱', '來源完整路徑', '輸出目標路徑', '相機型號', '副檔名', '處理類別', '最終狀態', '詳細說明/略過原因', '插件訊息']
                if has_geo_column:
                    header.append('地圖')
                writer.writerow(header)
                writer.writerows([
                    [
                        row[0],
                        format_display_path(row[1]) if row[1] != PLACEHOLDER else PLACEHOLDER,
                        format_display_path(row[2]) if row[2] != PLACEHOLDER else PLACEHOLDER,
                        *(row[3:] if has_geo_column else row[3:9])
                    ]
                    for row in audit_manifest
                ])
            q.put(('log', f"📋 CSV report exported: {manifest_path.name}"))

            generate_file_type_summary(dest_path, audit_manifest)
            # 同步產出 HTML 總報表
            generate_manifest_html(dest_path, audit_manifest)
            index_report_path = dest_path / "_index.html"
            q.put(('log', f"🌐 HTML report exported: _index.html"))

        except Exception as e:
            q.put(('error_log', f"ERROR: failed to export CSV audit report: {e}"))

    report_msg_append = ""
    if report_lines:
        try:
            report_file_path = dest_path / "_manifest_skiplist.txt"
            with open(report_file_path, "w", encoding="utf-8") as f:
                f.write(f"=== 媒體處理例外報告 (產生時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===\n")
                f.write(f"TOTAL SKIP: {skipped_count} | TOTAL FAIL: {failed_count}\n")
                f.write("="*80 + "\n")
                f.writelines(report_lines)
            report_msg_append = f"\n\n📄 報表已輸出至output根目錄:\n_manifest_skiplist.txt\n_manifest_audit.csv\n_index.html"
        except Exception: pass

    if stop_event.is_set():
        msg = f"中斷前已處理數量統計\n\n✅ PASS: {success_count}\n⏭️ SKIP: {skipped_count}\n❌ FAIL: {failed_count}{report_msg_append}"
        q.put(('msgbox', ("中斷", msg), 'warning', None, index_report_path))
    else:
        msg = f"本次處理檔案數量統計\n\n✅ PASS: {success_count}\n⏭️ SKIP: {skipped_count}\n❌ FAIL: {failed_count}{report_msg_append}"
        q.put(('msgbox', ("完成", msg), 'info', generated_html_reports, index_report_path))

    q.put(('reset', None))

# --- 智慧瀏覽資料夾 ---
# Stage 12 (non-behavioral extraction): bind threaded pipeline to core module.
try:
    from .core.pipeline import threaded_process_images as _core_threaded_process_images
except ImportError:
    from core.pipeline import threaded_process_images as _core_threaded_process_images

threaded_process_images = _core_threaded_process_images

def open_folder(path_var, selected_paths=None):
    # 1. 取得目前的所有路徑清單
    paths = []
    if selected_paths and len(selected_paths) > 0:
        paths = list(selected_paths)
    else:
        raw_str = path_var.get().strip(' "\'')
        if raw_str.startswith('[') and '] ' in raw_str:
            raw_str = raw_str.split('] ', 1)[1]
        paths = [p.strip(' "\'') for p in raw_str.split(';') if p.strip(' "\'')]

    if not paths:
        return

    # 2. 依照路徑數量與結構進行邏輯判斷
    if len(paths) == 1:
        # 邏輯一：若只有一個資料夾，直接打開它本人
        target_path = paths[0]
        if os.path.isfile(target_path):
            target_path = os.path.dirname(target_path)
    else:
        # 邏輯二與三：包含多個資料夾，先取得各自的「絕對路徑母目錄」
        parents = [os.path.abspath(os.path.dirname(p)) for p in paths]

        # 利用 normcase 處理 Windows 磁碟機與路徑大小寫問題，進行實體比對
        if os.name == 'nt':
            unique_parents = set(os.path.normcase(p) for p in parents)
        else:
            unique_parents = set(parents)

        if len(unique_parents) == 1:
            # 邏輯二：屬於同一個 parent，打開這個共通的 parent
            target_path = parents[0]
        else:
            # 邏輯三：不屬於同一個 parent (可能人為修改過 .ini)，彈窗提示衝突
            messagebox.showwarning(
                "❌ 路徑衝突",
                "偵測到目前的來源包含多個資料夾，且「不屬於」同一個母目錄！\n\n"
                "設定檔 (.ini) 可能曾經被手動編輯過，或是輸入了跨路徑的子目錄，系統無法判定欲開啟哪一個外層目錄。"
            )
            return

    # 3. 執行開啟動作
    if os.path.exists(target_path):
        try:
            if sys.platform == "win32":
                os.startfile(target_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", target_path])
            else:
                subprocess.Popen(["xdg-open", target_path])
        except Exception as e:
            messagebox.showerror("錯誤", f"❌ 無法開啟資料夾: {e}")
    else:
        messagebox.showwarning("警告", f"⚠️ 資料夾不存在: {target_path}")

# --- 精巧統計對話框 ---
# Stage 11 (non-behavioral extraction): bind folder opener helper to ui module.
try:
    from .ui.app import open_folder as _ui_open_folder
except ImportError:
    from ui.app import open_folder as _ui_open_folder

open_folder = _ui_open_folder

class ModernMessageBox(ctk.CTkToplevel):
    def __init__(self, parent, title, message, level="info", theme_colors=None, html_reports=None, index_report_path=None):
        super().__init__(parent)
        self.title(title)
        self.index_report_path = Path(index_report_path) if index_report_path else None

        num_reports = len(html_reports) if html_reports else 0
        base_height = UI_DIALOG_MSGBOX_BASE_HEIGHT
        row_height = UI_DIALOG_MSGBOX_ROW_HEIGHT
        dialog_height = min(base_height + ((num_reports + 1) * row_height), UI_DIALOG_MSGBOX_DYNAMIC_MAX_HEIGHT)

        self.geometry(f"{UI_DIALOG_MSGBOX_WIDTH}x{dialog_height}")
        self.minsize(UI_DIALOG_MSGBOX_MIN_WIDTH, UI_DIALOG_MSGBOX_MIN_HEIGHT)
        self.maxsize(UI_DIALOG_MSGBOX_MAX_WIDTH, UI_DIALOG_MSGBOX_MAX_HEIGHT)
        self.transient(parent)
        self.grab_set()

        apply_window_icon(self, inherit_from=parent)

        bg_color = theme_colors["BG"] if theme_colors else "#F4F6F7"
        main_color = theme_colors["MAIN"] if theme_colors else "#7D8C94"
        hover_color = theme_colors["HOVER"] if theme_colors else "#66747A"
        text_color = theme_colors["TEXT"] if theme_colors else "#4A4F54"
        self.configure(fg_color=bg_color)
        apply_windows_titlebar_theme(self, main_color)

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(15, 5))

        icon_str = "ℹ️"
        if level == "warning": icon_str = "⚠️"
        elif level == "error": icon_str = "❌"

        ctk.CTkLabel(header_frame, text=icon_str, font=ctk.CTkFont(size=UI_FONT_SIZE_MSGBOX_ICON)).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(header_frame, text=title, font=ctk.CTkFont(size=UI_FONT_SIZE_MSGBOX_TITLE, weight="bold"), text_color=text_color).pack(side="left")

        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=5)
        lbl_msg = ctk.CTkLabel(content_frame, text=message, font=ctk.CTkFont(size=UI_FONT_SIZE_MSGBOX_BODY), justify="left", text_color=text_color, wraplength=UI_MSGBOX_WRAP_LENGTH)
        lbl_msg.pack(anchor="w")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="both", expand=True, padx=20, pady=(5, 15))

        ctk.CTkButton(btn_frame, text="確定並打開總報表", height=UI_MSGBOX_MAIN_BTN_HEIGHT, font=ctk.CTkFont(size=UI_FONT_SIZE_MSGBOX_MAIN_BTN, weight="bold"),
                      fg_color=main_color, hover_color=hover_color, command=self.open_index_and_close).pack(side="top", fill="x", pady=5)

        if html_reports:
            if num_reports <= 3:
                for m_key, h_path in html_reports:
                    ctk.CTkButton(btn_frame, text=f"🌐 開啟 {m_key} 報告", height=UI_MSGBOX_REPORT_BTN_HEIGHT, font=ctk.CTkFont(size=UI_FONT_SIZE_MSGBOX_REPORT_BTN, weight="bold"),
                                  fg_color="#2980B9", hover_color="#1F618D",
                                  command=lambda p=h_path: webbrowser.open(p.as_uri())).pack(side="top", fill="x", pady=4)
            else:
                scroll_reports = ctk.CTkScrollableFrame(btn_frame, height=UI_MSGBOX_REPORT_SCROLL_HEIGHT, fg_color="transparent")
                scroll_reports.pack(side="top", fill="both", expand=True, pady=2)
                for m_key, h_path in html_reports:
                    ctk.CTkButton(scroll_reports, text=f"🌐 開啟 {m_key} 報告", height=UI_MSGBOX_REPORT_BTN_HEIGHT, font=ctk.CTkFont(size=UI_FONT_SIZE_MSGBOX_REPORT_BTN, weight="bold"),
                                  fg_color="#2980B9", hover_color="#1F618D",
                                  command=lambda p=h_path: webbrowser.open(p.as_uri())).pack(side="top", fill="x", pady=4, padx=2)

    # --- 完成彈窗動作 ---
    def open_index_and_close(self):
        try:
            if self.index_report_path and self.index_report_path.exists():
                webbrowser.open(self.index_report_path.as_uri())
                target_folder = self.index_report_path.parent
                if sys.platform == "win32":
                    os.startfile(str(target_folder))
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(target_folder)])
                else:
                    subprocess.Popen(["xdg-open", str(target_folder)])
        except Exception:
            pass
        self.destroy()

# --- 彈窗勾選子目錄介面 ---
class FolderSelectDialog(ctk.CTkToplevel):
    def __init__(self, parent, initial_dir, callback, theme_colors=None, allow_multiple=True):
        super().__init__(parent)
        self.title("多資料夾選取器 - 請勾選欲處理的目錄")
        self.geometry(UI_DIALOG_FOLDER_GEOMETRY)
        self.minsize(UI_DIALOG_FOLDER_MIN_WIDTH, UI_DIALOG_FOLDER_MIN_HEIGHT)
        self.callback = callback
        self.selected_paths = []
        self.allow_multiple = allow_multiple

        self.transient(parent)
        self.grab_set()

        apply_window_icon(self, inherit_from=parent)

        bg_color = theme_colors["BG"] if theme_colors else "#F4F6F7"
        main_color = theme_colors["MAIN"] if theme_colors else "#7D8C94"
        hover_color = theme_colors["HOVER"] if theme_colors else "#66747A"
        stop_color = theme_colors["STOP"] if theme_colors else "#A88B87"
        text_color = theme_colors["TEXT"] if theme_colors else "#4A4F54"
        self.configure(fg_color=bg_color)
        apply_windows_titlebar_theme(self, main_color)

        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=(15, 5))
        ctk.CTkLabel(top_frame, text=f"📂 目前位置: {format_display_path(initial_dir)}", font=ctk.CTkFont(size=UI_FONT_SIZE_FOLDER_TITLE, weight="bold"), text_color=text_color).pack(side="left")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=8)
        if self.allow_multiple:
            ctk.CTkButton(btn_frame, text="✅ 全選", width=UI_FOLDER_ACTION_BTN_WIDTH, height=UI_FOLDER_ACTION_BTN_HEIGHT, font=ctk.CTkFont(size=UI_FONT_SIZE_FOLDER_ACTION, weight="bold"), fg_color=main_color, hover_color=hover_color, command=self.select_all).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="⬜ 全不選", width=UI_FOLDER_ACTION_BTN_WIDTH, height=UI_FOLDER_ACTION_BTN_HEIGHT, font=ctk.CTkFont(size=UI_FONT_SIZE_FOLDER_ACTION, weight="bold"), fg_color=main_color, hover_color=hover_color, command=self.deselect_all).pack(side="left")

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#FFFFFF" if bg_color=="#F4F6F7" else "#FAFAFA")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.check_vars = []
        self.folder_paths = []

        try:
            subdirs = sorted([os.path.join(initial_dir, d) for d in os.listdir(initial_dir)
                              if os.path.isdir(os.path.join(initial_dir, d)) and not any(k in d.lower() for k in EXCLUDE_DIR_KEYWORDS)])
            if not subdirs:
                ctk.CTkLabel(self.scroll_frame, text="此目錄底下沒有子資料夾！\n將直接處理本目錄。", font=ctk.CTkFont(size=UI_FONT_SIZE_FOLDER_TITLE), text_color=text_color).pack(pady=40)
                self.folder_paths = [initial_dir]
                var = tk.BooleanVar(value=True)
                self.check_vars.append(var)
            else:
                for index, path in enumerate(subdirs):
                    var = tk.BooleanVar(value=self.allow_multiple or index == 0)
                    command = None if self.allow_multiple else lambda selected_var=var: self.select_one(selected_var)
                    chk = ctk.CTkCheckBox(self.scroll_frame, text=f"📁 {os.path.basename(path)}", variable=var, command=command,
                                          font=ctk.CTkFont(family=UI_FONT_FAMILY, size=UI_FONT_SIZE_FOLDER_CHECK), fg_color=main_color, hover_color=hover_color, text_color=text_color)
                    chk.pack(anchor="w", pady=8, padx=12)
                    self.check_vars.append(var)
                    self.folder_paths.append(path)
        except Exception as e:
            ctk.CTkLabel(self.scroll_frame, text=f"無法讀取目錄內容: {e}", text_color=text_color).pack(pady=20)

        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=20, pady=(10, 18))
        ctk.CTkButton(bottom_frame, text="確認載入選取目錄", height=UI_FOLDER_BOTTOM_BTN_HEIGHT, font=ctk.CTkFont(size=UI_FONT_SIZE_FOLDER_BOTTOM_BTN, weight="bold"), fg_color=main_color, hover_color=hover_color, command=self.on_confirm).pack(side="right", padx=(10, 0))
        ctk.CTkButton(bottom_frame, text="取消", height=UI_FOLDER_BOTTOM_BTN_HEIGHT, font=ctk.CTkFont(size=UI_FONT_SIZE_FOLDER_BOTTOM_BTN, weight="bold"), fg_color=stop_color, hover_color="#917774", command=self.destroy).pack(side="right")

    def select_all(self):
        if not self.allow_multiple:
            return
        for var in self.check_vars: var.set(True)

    def select_one(self, selected_var):
        if selected_var.get():
            for var in self.check_vars:
                if var is not selected_var:
                    var.set(False)

    def deselect_all(self):
        for var in self.check_vars: var.set(False)

    def on_confirm(self):
        selected = [self.folder_paths[i] for i, var in enumerate(self.check_vars) if var.get()]
        if not selected:
            messagebox.showwarning("提示", "請至少勾選一個資料夾！", parent=self)
            return
        if not self.allow_multiple and len(selected) != 1:
            messagebox.showwarning("提示", "未啟用依年月整理時，來源與目的資料夾為 1:1，請只選擇一個來源資料夾。", parent=self)
            return
        self.callback(selected)
        self.destroy()

# --- UI 主介面類別 ---
# Stage 13 (non-behavioral extraction): bind dialog classes to ui module.
try:
    from .ui.dialogs import (
        FolderSelectDialog as _ui_FolderSelectDialog,
        ModernMessageBox as _ui_ModernMessageBox,
    )
except ImportError:
    from ui.dialogs import (
        FolderSelectDialog as _ui_FolderSelectDialog,
        ModernMessageBox as _ui_ModernMessageBox,
    )

ModernMessageBox = _ui_ModernMessageBox
FolderSelectDialog = _ui_FolderSelectDialog

class ImageOrganizerAppModern:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Kairos - Media Organizer Pro")
        self.root.geometry(UI_MAIN_WINDOW_GEOMETRY)
        self.root.minsize(UI_MAIN_WINDOW_MIN_WIDTH, UI_MAIN_WINDOW_MIN_HEIGHT)
        if UI_START_MAXIMIZED:
            self.root.after(0, self._maximize_on_startup)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.queue = queue.Queue()
        self.processing = False
        self.stop_event = threading.Event()
        self.selected_src_folders = []
        self.start_time = 0
        self.processed_bytes = 0

        title_font = ctk.CTkFont(family=UI_FONT_FAMILY, size=UI_TITLE_FONT_SIZE, weight="bold")
        app_font = ctk.CTkFont(family=UI_FONT_FAMILY, size=UI_APP_FONT_SIZE)
        btn_font = ctk.CTkFont(family=UI_FONT_FAMILY, size=UI_BUTTON_FONT_SIZE, weight="bold")

        self.src_var = tk.StringVar()
        self.dest_var = tk.StringVar()
        self.organize_by_time_var = tk.BooleanVar(value=True)    # ☑ 依照時間分資料夾
        self.normalize_name_var = tk.BooleanVar(value=True)      # ☑ 檔名正規化
        self.enable_geo_lookup_var = tk.BooleanVar(value=False)  # ☐ 預設關閉地理位置解析以提升速度
        self.copy_video_var = tk.BooleanVar(value=True)          # ☑ 掃描包含 VIDEO 檔
        self.copy_raw_var = tk.BooleanVar(value=False)           # ☐ 掃描包含 RAW 檔
        self.overwrite_var = tk.BooleanVar(value=False)          # ☐ 強制覆蓋 (連拍保護 & 留新不留舊)
        self.performance_mode_var = tk.BooleanVar(value=False)   # ☐ 效能模式：精簡 LOG / 快速掃描 / GEO 失敗摘要
        self.theme_var = tk.StringVar(value=DEFAULT_THEME_NAME)

        self.load_config()

        # === 標題區 ===
        title_frame = ctk.CTkFrame(root, fg_color="transparent")
        title_frame.pack(pady=(20, 8))
        ctk.CTkLabel(title_frame, text="Kairos - Media Organizer Pro", font=title_font).pack(side="top")
        subtitle_font = ctk.CTkFont(family=UI_FONT_FAMILY, size=UI_SUBTITLE_FONT_SIZE)
        self.lbl_build = ctk.CTkLabel(title_frame, text=f"Build {VERSION}", font=subtitle_font, height=UI_SUBTITLE_BUILD_HEIGHT)
        self.lbl_build.pack(side="top", pady=(0, 0))
        self.lbl_subtitle = ctk.CTkLabel(
            title_frame,
            text=f"exifread 圖片解析: {'啟用' if EXIFREAD_AVAILABLE else '未安裝'}  |  PIL/Pillow 圖片解析: {'啟用' if PIL_AVAILABLE else '未安裝'}  |  pillow-heif 圖片解析: {'啟用' if PILLOW_HEIF_AVAILABLE else '未安裝'}",
            font=subtitle_font,
            height=UI_SUBTITLE_LINE_HEIGHT
        )
        self.lbl_subtitle.pack(side="top", pady=(0, 0))
        self.lbl_subtitle2 = ctk.CTkLabel(
            title_frame,
            text=f"Hachoir 影片解析: {'啟用' if HACHOIR_AVAILABLE else '未安裝'}  |  reverse_geocoder 地理解析: {'啟用' if RG_AVAILABLE else '未安裝'}  |  exiftool 圖片解析: {'啟用' if EXIFTOOL_AVAILABLE else '未安裝'}",
            font=subtitle_font,
            height=UI_SUBTITLE_LINE_HEIGHT
        )
        self.lbl_subtitle2.pack(side="top", pady=(0, 0))

        # === 主要輸入區塊 ===
        frame_top = ctk.CTkFrame(root, corner_radius=10)
        frame_top.pack(pady=10, padx=25, fill="x")
        frame_top.grid_columnconfigure(0, weight=0, minsize=170)
        frame_top.grid_columnconfigure(1, weight=1)
        frame_top.grid_columnconfigure(2, weight=0)

        row_height = UI_ROW_HEIGHT

        # === 來源 ===
        self.lbl_src = ctk.CTkLabel(frame_top, text="來源目錄 (Source Dir):", font=app_font)
        self.lbl_src.grid(row=0, column=0, padx=(20, 10), pady=(20, 7), sticky="e")
        self.entry_src = ctk.CTkEntry(frame_top, textvariable=self.src_var, font=app_font, height=row_height)
        self.entry_src.grid(row=0, column=1, padx=(0, 10), pady=(20, 7), sticky="ew")
        btn_frame_src = ctk.CTkFrame(frame_top, fg_color="transparent")
        btn_frame_src.grid(row=0, column=2, padx=(0, 15), pady=(20, 7), sticky="w")
        self.btn_browse_src = ctk.CTkButton(btn_frame_src, text="🔍 瀏覽", width=UI_SMALL_BTN_WIDTH, height=row_height, font=app_font, command=self.browse_src)
        self.btn_browse_src.pack(side="left", padx=(0, 10))
        self.btn_view_src = ctk.CTkButton(btn_frame_src, text="📂 檢視", width=UI_SMALL_BTN_WIDTH, height=row_height, font=app_font, command=lambda: open_folder(self.src_var, self.selected_src_folders))
        self.btn_view_src.pack(side="left")

        # === 輸出 ===
        self.lbl_dest = ctk.CTkLabel(frame_top, text="輸出目錄 (Output Dir):", font=app_font)
        self.lbl_dest.grid(row=1, column=0, padx=(20, 10), pady=(7, 10), sticky="e")
        ctk.CTkEntry(frame_top, textvariable=self.dest_var, font=app_font, height=row_height).grid(row=1, column=1, padx=(0, 10), pady=(7, 10), sticky="ew")
        btn_frame_dest = ctk.CTkFrame(frame_top, fg_color="transparent")
        btn_frame_dest.grid(row=1, column=2, padx=(0, 15), pady=(7, 10), sticky="w")
        self.btn_browse_dest = ctk.CTkButton(btn_frame_dest, text="🔍 瀏覽", width=UI_SMALL_BTN_WIDTH, height=row_height, font=app_font, command=self.browse_dest)
        self.btn_browse_dest.pack(side="left", padx=(0, 10))
        self.btn_view_dest = ctk.CTkButton(btn_frame_dest, text="📂 檢視", width=UI_SMALL_BTN_WIDTH, height=row_height, font=app_font, command=lambda: open_folder(self.dest_var))
        self.btn_view_dest.pack(side="left")

        # === 進階 ===
        self.lbl_mode = ctk.CTkLabel(frame_top, text="處理模式 (Mode):", font=app_font)
        self.lbl_mode.grid(row=2, column=0, padx=(20, 10), pady=(10, 5), sticky="e")
        mode_frame = ctk.CTkFrame(frame_top, fg_color="transparent")
        mode_frame.grid(row=2, column=1, columnspan=2, padx=(0, 20), pady=(10, 5), sticky="w")

        self.norm_chk = ctk.CTkCheckBox(mode_frame, text="檔名正規化 (YYYY-MM-DD HH.MM.SS)", variable=self.normalize_name_var, font=app_font)
        self.norm_chk.pack(side="left", padx=(0, 20))
        self.time_chk = ctk.CTkCheckBox(mode_frame, text="依照年月區分資料夾 (YYYY_MM)", variable=self.organize_by_time_var, font=app_font)
        self.time_chk.pack(side="left", padx=(0, 20))

        self.geo_checkbox = ctk.CTkCheckBox(mode_frame, text="解析地理位置與地圖 (會耗費較多時間)", variable=self.enable_geo_lookup_var, font=app_font)
        self.geo_checkbox.pack(side="left", padx=(0, 20))

        self.lbl_opt = ctk.CTkLabel(frame_top, text="動作選項 (Options):", font=app_font)
        self.lbl_opt.grid(row=3, column=0, padx=(20, 10), pady=(5, 20), sticky="e")
        options_frame = ctk.CTkFrame(frame_top, fg_color="transparent")
        options_frame.grid(row=3, column=1, columnspan=2, padx=(0, 20), pady=(5, 20), sticky="ew")

        self.vid_checkbox = ctk.CTkCheckBox(options_frame, text="掃描包含 VIDEO 檔", variable=self.copy_video_var, font=app_font)
        self.vid_checkbox.pack(side="left", padx=(0, 15))
        self.raw_checkbox = ctk.CTkCheckBox(options_frame, text="掃描包含 RAW 檔", variable=self.copy_raw_var, font=app_font)
        self.raw_checkbox.pack(side="left", padx=(0, 15))
        self.overwrite_checkbox = ctk.CTkCheckBox(options_frame, text="強制覆蓋時間戳相同的照片 (連拍保護 & 留新不留舊)", variable=self.overwrite_var, font=app_font)
        self.overwrite_checkbox.pack(side="left", padx=(0, 15))
        self.performance_checkbox = ctk.CTkCheckBox(options_frame, text="效能模式 (精簡 LOG / 快速掃描 / GEO 失敗摘要)", variable=self.performance_mode_var, font=app_font)
        self.performance_checkbox.pack(side="left", padx=(0, 15))

        # === 主題選擇 ===
        self.theme_menu = ctk.CTkOptionMenu(
            options_frame,
            values=list(THEMES.keys()),
            variable=self.theme_var,
            command=self.change_theme,
            font=app_font,
            width=UI_THEME_MENU_WIDTH
        )
        self.theme_menu.pack(side="right", padx=(0, 0))
        self.lbl_theme = ctk.CTkLabel(options_frame, text="主題配色", font=app_font)
        self.lbl_theme.pack(side="right", padx=(0, 5))

        # === 狀態與進度 ===
        self.status_frame = ctk.CTkFrame(root, fg_color="transparent")
        self.status_frame.pack(pady=(10, 0), padx=30, fill="x")

        self.status_top_frame = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        self.status_top_frame.pack(side='top', fill='x', pady=(0, 8))

        self.status_label = ctk.CTkLabel(self.status_top_frame, text="準備就緒", font=ctk.CTkFont(family=UI_FONT_FAMILY, size=UI_APP_FONT_SIZE), anchor='w')
        self.status_label.pack(side='left', fill='x', expand=True)

        self.metrics_label = ctk.CTkLabel(self.status_top_frame, text="時間: 00:00 | 大小: 0 B | 速度: 0 B/s", font=ctk.CTkFont(family=UI_FONT_FAMILY, size=UI_STATUS_FONT_SIZE, weight="bold"), anchor='e')
        self.metrics_label.pack(side='right')

        self.progress_container = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        self.progress_container.pack(side='top', fill='x')

        self.progress_bar = ctk.CTkProgressBar(self.progress_container, height=UI_PROGRESS_HEIGHT)
        self.progress_bar.set(0)
        self.progress_bar.pack(side='left', fill='x', expand=True, padx=(0, 10))

        self.progress_pct_label = ctk.CTkLabel(self.progress_container, text="0%", font=ctk.CTkFont(family=UI_FONT_FAMILY, size=UI_STATUS_FONT_SIZE, weight="bold"))
        self.progress_pct_label.pack(side='right')

        # === 即時文字日誌區 ===
        self.log_textbox = ctk.CTkTextbox(root, height=UI_LOGBOX_HEIGHT, font=(UI_LOG_FONT_FAMILY, UI_LOG_FONT_SIZE), border_width=1)
        self.log_textbox.pack(pady=(15, 5), padx=25, fill="both", expand=True)
        self.log_textbox.insert("0.0", "等待執行...\n")
        self.log_textbox.configure(state="disabled")

        # === 執行按鈕 ===
        frame_btn = ctk.CTkFrame(root, fg_color="transparent")
        frame_btn.pack(pady=(10, 20), padx=25, fill="x")
        self.start_btn = ctk.CTkButton(frame_btn, text="▶ 開始執行", font=btn_font, height=UI_START_BTN_HEIGHT, corner_radius=8, command=self.toggle_processing)
        self.start_btn.pack(expand=True, fill="x")

        # 套用初始主題顏色
        self.apply_theme_colors(self.theme_var.get())

        # 在初始化最後，呼叫圖示設定函式
        self.set_app_icon()

    def _maximize_on_startup(self):
        try:
            if sys.platform == "win32":
                self.root.state("zoomed")
            else:
                self.root.attributes("-zoomed", True)
        except Exception:
            pass

    def set_app_icon(self):
        if not apply_window_icon(self.root):
            print("未找到圖示檔案，使用系統預設圖示。")

    def apply_theme_colors(self, theme_name):
        if theme_name not in THEMES:
            theme_name = DEFAULT_THEME_NAME
            self.theme_var.set(theme_name)

        t = THEMES[theme_name]

        # === 背景與文字 ===
        self.root.configure(fg_color=t["BG"])
        apply_windows_titlebar_theme(self.root, t["MAIN"])
        self.lbl_build.configure(text_color=t["TEXT"])
        self.lbl_subtitle.configure(text_color=t["TEXT"])
        self.lbl_subtitle2.configure(text_color=t["TEXT"])
        self.lbl_src.configure(text_color=t["TEXT"])
        self.lbl_dest.configure(text_color=t["TEXT"])
        self.lbl_mode.configure(text_color=t["TEXT"])
        self.lbl_opt.configure(text_color=t["TEXT"])
        self.lbl_theme.configure(text_color=t["LABEL"])
        self.status_label.configure(text_color=t["TEXT"])
        self.metrics_label.configure(text_color=t["TEXT"])
        self.progress_pct_label.configure(text_color=t["TEXT"])

        # === 按鈕與選單 ===
        self.btn_browse_src.configure(fg_color=t["MAIN"], hover_color=t["HOVER"])
        self.btn_browse_dest.configure(fg_color=t["MAIN"], hover_color=t["HOVER"])
        self.btn_view_src.configure(fg_color=t["SUB"], hover_color=t["HOVER"])
        self.btn_view_dest.configure(fg_color=t["SUB"], hover_color=t["HOVER"])
        self.theme_menu.configure(fg_color=t["MAIN"], button_color=t["MAIN"], button_hover_color=t["HOVER"])

        for chk in [self.norm_chk, self.time_chk, self.geo_checkbox, self.vid_checkbox, self.raw_checkbox, self.overwrite_checkbox, self.performance_checkbox]:
            chk.configure(fg_color=t["MAIN"], hover_color=t["HOVER"], text_color=t["TEXT"])

        # === 執行按鈕 (需判斷是否在執行中) ===
        if self.processing:
            self.start_btn.configure(fg_color=t["STOP"], hover_color=t["HOVER"])
        else:
            self.start_btn.configure(fg_color=t["MAIN"], hover_color=t["HOVER"])

        # === 進度條與日誌 ===
        self.progress_bar.configure(fg_color=t["BORDER"], progress_color=t["PROGRESS"])

        # === 日誌區塊稍微淺色處理以適配莫蘭迪色背景 ===
        log_bg = "#FFFFFF" if t["BG"] == "#F4F6F7" else "#FAFAFA"
        self.log_textbox.configure(fg_color=log_bg, border_color=t["BORDER"], text_color=t["TEXT"])

    def change_theme(self, new_theme):
        self.apply_theme_colors(new_theme)
        self.save_config()

    def load_config(self):
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            try:
                config.read(CONFIG_FILE, encoding='utf-8')
                if 'Settings' in config:
                    saved_src = config.get('Settings', 'Source', fallback='')
                    if saved_src:
                        self.selected_src_folders = parse_saved_source_paths(saved_src)
                        if not self.selected_src_folders and os.path.exists(saved_src):
                            self.selected_src_folders = [saved_src]
                    if self.selected_src_folders:
                        self.src_var.set(" ; ".join(format_display_path(path) for path in self.selected_src_folders))
                    else:
                        self.src_var.set(format_display_path(saved_src))
                    self.dest_var.set(format_display_path(config.get('Settings', 'Destination', fallback='')))
                    self.organize_by_time_var.set(config.getboolean('Settings', 'OrganizeByTime', fallback=True))
                    if not self.organize_by_time_var.get() and len(self.selected_src_folders) > 1:
                        self.selected_src_folders = self.selected_src_folders[:1]
                        self.src_var.set(format_display_path(self.selected_src_folders[0]))
                    self.normalize_name_var.set(config.getboolean('Settings', 'NormalizeName', fallback=True))
                    self.enable_geo_lookup_var.set(config.getboolean('Settings', 'EnableGeoLookup', fallback=False))
                    self.performance_mode_var.set(config.getboolean('Settings', 'PerformanceMode', fallback=False))
                    self.copy_video_var.set(config.getboolean('Settings', 'CopyVideo', fallback=True))
                    self.copy_raw_var.set(config.getboolean('Settings', 'CopyRAW', fallback=False))
                    self.overwrite_var.set(config.getboolean('Settings', 'Overwrite', fallback=False))
                    saved_theme = config.get('Settings', 'Theme', fallback=DEFAULT_THEME_NAME)
                    if saved_theme in THEMES: self.theme_var.set(saved_theme)
            except Exception: pass

    def save_config(self):
        config = configparser.ConfigParser()
        config['Settings'] = {
            'Source': ";".join(self.selected_src_folders) if self.selected_src_folders else self.src_var.get().strip(' "\''),
            'Destination': self.dest_var.get().strip(' "\''),
            'OrganizeByTime': str(self.organize_by_time_var.get()),
            'NormalizeName': str(self.normalize_name_var.get()),
            'EnableGeoLookup': str(self.enable_geo_lookup_var.get()),
            'PerformanceMode': str(self.performance_mode_var.get()),
            'CopyVideo': str(self.copy_video_var.get()),
            'CopyRAW': str(self.copy_raw_var.get()),
            'Overwrite': str(self.overwrite_var.get()),
            'Theme': str(self.theme_var.get())
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f: config.write(f)
        except Exception: pass

    def browse_src(self):
        if self.selected_src_folders:
            current_path = os.path.dirname(self.selected_src_folders[0])
        else:
            current_path = self.src_var.get().strip(' "\'')
            if current_path.startswith('[') and '] ' in current_path:
                current_path = current_path.split('] ', 1)[1]
            if ";" in current_path: current_path = current_path.split(";")[0].strip()
        if not current_path or not os.path.isdir(current_path):
            current_path = os.path.expanduser("~")

        parent_dir = filedialog.askdirectory(initialdir=current_path, title="請先選擇「母目錄」以掃描其子資料夾")
        if parent_dir:
            t = THEMES[self.theme_var.get()]
            FolderSelectDialog(
                self.root, parent_dir, self.on_folders_selected, theme_colors=t,
                allow_multiple=self.organize_by_time_var.get()
            )

    def on_folders_selected(self, selected_paths):
        if not self.organize_by_time_var.get() and len(selected_paths) != 1:
            messagebox.showwarning("提示", "未啟用依年月整理時，來源與目的資料夾為 1:1，請只選擇一個來源資料夾。")
            return
        self.selected_src_folders = selected_paths
        displayed_paths = [format_display_path(path) for path in selected_paths]
        if len(selected_paths) == 1:
            self.src_var.set(displayed_paths[0])
        else:
            self.src_var.set(f"[已勾選 {len(selected_paths)} 個資料夾] " + " ; ".join(displayed_paths))

    def browse_dest(self):
        current_path = self.dest_var.get().strip(' "\'')
        if not current_path or not os.path.isdir(current_path): current_path = os.path.expanduser("~")
        folder = filedialog.askdirectory(initialdir=current_path)
        if folder: self.dest_var.set(format_display_path(folder))

    def check_queue(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                msg_type = msg[0]
                data = msg[1]
                if msg_type == 'status': self.status_label.configure(text=data)
                elif msg_type == 'log':
                    self.log_textbox.configure(state="normal")
                    self.log_textbox.insert("end", data + "\n")
                    if int(self.log_textbox.index("end-1c").split('.')[0]) > 1000: self.log_textbox.delete("1.0", "2.0")
                    self.log_textbox.see("end")
                    self.log_textbox.configure(state="disabled")
                elif msg_type == 'error_log':
                    self.log_textbox.configure(state="normal")
                    self.log_textbox.insert("end", f"[ERROR] {data}\n")
                    self.log_textbox.see("end")
                    self.log_textbox.configure(state="disabled")
                elif msg_type == 'progress':
                    self.progress_bar.set(data)
                    self.progress_pct_label.configure(text=f"{int(data * 100)}%")
                elif msg_type == 'metrics':
                    if isinstance(data, tuple):
                        self.processed_bytes = data[1]
                    else:
                        self.processed_bytes = data
                elif msg_type == 'reset':
                    self.reset_ui()
                    return
                elif msg_type == 'msgbox':
                    title, content = data
                    level = msg[2] if len(msg) > 2 else 'info'
                    reports = msg[3] if len(msg) > 3 else None
                    index_report_path = msg[4] if len(msg) > 4 else None
                    t = THEMES[self.theme_var.get()]
                    ModernMessageBox(self.root, title, content, level, t, html_reports=reports, index_report_path=index_report_path)
        except queue.Empty: pass
        if self.processing: self.root.after(100, self.check_queue)

    def update_timer(self):
        """GUI 獨立計時迴圈：不受背景運算卡頓影響，每 0.5 秒直接讀取系統時鐘刷新介面"""
        if self.processing and self.start_time > 0:
            elapsed = time.time() - self.start_time
            speed = self.processed_bytes / elapsed if elapsed > 0 else 0
            self.metrics_label.configure(
                text=f"時間: {format_time(elapsed)} | 大小: {format_size(self.processed_bytes)} | 速度: {format_size(speed)}/s"
            )
            # 讓 Tkinter 主介面每 500 毫秒 (0.5秒) 自動呼叫自己一次
            self.root.after(500, self.update_timer)

    def reset_ui(self):
        self.processing = False

        # 1. 在停止計時前，計算並「定格」最後的總耗時與平均速度在畫面上
        if self.start_time > 0:
            final_elapsed = time.time() - self.start_time
            speed = self.processed_bytes / final_elapsed if final_elapsed > 0 else 0
            self.metrics_label.configure(
                text=f"時間: {format_time(final_elapsed)} | 大小: {format_size(self.processed_bytes)} | 平均速度: {format_size(speed)}/s"
            )
        self.start_time = 0  # 讓 update_timer 停止循環

        # 2. 判斷是順利完成還是被中斷，呈現對應的最終狀態
        if self.stop_event.is_set():
            self.status_label.configure(text="🛑 處理已中斷")
        else:
            self.status_label.configure(text="✅ 處理完畢！可於下方日誌檢視細節或點擊彈窗開啟報告")
            self.progress_bar.set(1.0)
            self.progress_pct_label.configure(text="100%")

        self.stop_event.clear()

        # 3. 恢復介面按鈕與核取方塊的互動功能 (維持原樣)
        t = THEMES[self.theme_var.get()]
        self.start_btn.configure(state='normal', text="▶ 開始執行", fg_color=t["MAIN"], hover_color=t["HOVER"])
        for chk in [self.time_chk, self.norm_chk, self.geo_checkbox, self.vid_checkbox, self.raw_checkbox, self.overwrite_checkbox, self.performance_checkbox]:
            chk.configure(state='normal')
        self.theme_menu.configure(state='normal')
        self.btn_browse_src.configure(state='normal')

    def toggle_processing(self):
        if self.processing:
            self.stop_event.set()
            self.start_btn.configure(text="⏳ 正在中斷並等待當前檔案完成...", state='disabled')
            return

        dest = self.dest_var.get().strip(' "\'')
        if not self.selected_src_folders:
            messagebox.showwarning("警告", "請先使用瀏覽按鈕選取來源目錄！")
            return

        if not self.organize_by_time_var.get() and len(self.selected_src_folders) != 1:
            messagebox.showwarning("警告", "未啟用依年月整理時，來源與目的資料夾為 1:1，請只保留一個來源資料夾。")
            return

        if not dest:
            messagebox.showwarning("警告", "請先使用瀏覽按鈕指定輸出目錄！")
            return

        if not os.path.isdir(dest):
            messagebox.showerror("錯誤", "指定的輸出路徑不存在，請重新檢查。")
            return

        try:
            # 檢查目標目錄是否包含任何檔案
            if any(Path(dest).iterdir()):
                # 直接開啟目錄並跳出提示，不需詢問使用者
                messagebox.showwarning(
                    "目錄存在其他檔案，可能有覆蓋風險！",
                    "指定的輸出目錄不為空，建議使用空的資料夾以確保報告完整性。\n\n程式將為您開啟該目錄以利檢查。"
                )

                # 直接執行開啟目錄的動作
                if os.path.exists(dest):
                    if sys.platform == "win32": os.startfile(dest)
                    elif sys.platform == "darwin": subprocess.Popen(["open", dest])
                    else: subprocess.Popen(["xdg-open", dest])

                return # 終止本次處理啟動
        except OSError as e:
            messagebox.showerror("Destination error", f"Cannot read destination folder: {e}")
            return

        try:
            dest_res = os.path.abspath(dest)
            for src_f in self.selected_src_folders:
                src_res = os.path.abspath(src_f)
                if os.path.commonpath([src_res, dest_res]) in (src_res, dest_res):
                    messagebox.showerror("嚴重錯誤", f"「輸出目錄」不能位於「來源目錄 ({format_display_path(src_f)})」裡面！\n\n這會導致無限迴圈複製，請重新設定。")
                    return
        except Exception: pass

        self.save_config()
        self.processing = True
        self.stop_event.clear()

        t = THEMES[self.theme_var.get()]
        self.start_btn.configure(text="🛑 停止處理", fg_color=t["STOP"], hover_color=t["HOVER"])
        for chk in [self.time_chk, self.norm_chk, self.geo_checkbox, self.vid_checkbox, self.raw_checkbox, self.overwrite_checkbox, self.performance_checkbox]:
            chk.configure(state='disabled')
        self.theme_menu.configure(state='disabled')
        self.btn_browse_src.configure(state='disabled')

        self.status_label.configure(text="準備掃描檔案...")
        self.metrics_label.configure(text="時間: 00:00 | 大小: 0 B | 速度: 0 B/s")
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.progress_pct_label.configure(text="0%")
        self.start_time = time.time()
        self.processed_bytes = 0
        self.update_timer()

        self.thread = threading.Thread(
            target=threaded_process_images,
            args=(self.selected_src_folders, dest, self.organize_by_time_var.get(), self.normalize_name_var.get(), self.enable_geo_lookup_var.get(), self.copy_video_var.get(), self.copy_raw_var.get(), self.overwrite_var.get(), self.performance_mode_var.get(), self.queue, self.stop_event),
            daemon=True
        )
        self.thread.start()
        self.root.after(100, self.check_queue)

    def on_closing(self):
        if self.processing:
            if messagebox.askokcancel("強制退出", "目前正在處理媒體中，強制退出可能導致當前檔案不完整。\n\n確定要強制退出嗎？"):
                self.stop_event.set()
                self.root.destroy()
        else:
            self.save_config()
            self.root.destroy()

# Stage 14 (non-behavioral extraction): bind app class to ui module.
try:
    from .ui.app import ImageOrganizerAppModern as _ui_ImageOrganizerAppModern
except ImportError:
    from ui.app import ImageOrganizerAppModern as _ui_ImageOrganizerAppModern

ImageOrganizerAppModern = _ui_ImageOrganizerAppModern

def sigint_handler(sig, frame):
    print("\n[系統] 接收到 Ctrl+C 中斷指令，正在安全停止背景執行緒並離開程式...")
    try:
        if 'app' in globals() and app.processing:
            app.stop_event.set()
    except Exception:
        pass
    try:
        if 'root' in globals():
            root.quit()
            root.destroy()
    except Exception:
        pass
    sys.exit(0)

# Stage 16 (non-behavioral extraction): bind SIGINT handler to ui module.
try:
    from .ui.app import sigint_handler as _ui_sigint_handler
except ImportError:
    from ui.app import sigint_handler as _ui_sigint_handler

sigint_handler = _ui_sigint_handler

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigint_handler)

    # 強制設定為淺色模式，讓莫蘭迪色背景不受系統深色影響
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    app = ImageOrganizerAppModern(root)

    def check_sigint():
        root.after(200, check_sigint)
    root.after(200, check_sigint)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        sigint_handler(signal.SIGINT, None)
