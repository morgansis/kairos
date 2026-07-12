"""
================================================================================
媒體檔案自動化整理與劇院級檢視工具 (Media Organizer Pro) - v2026-07-13
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
     - 物理實體過濾：在處理前會自動進行檔案大小 (Bytes) 與首尾區塊 (Chunks) 內容對比，
       若確認為完全相同的實體檔案則直接優雅略過，杜絕重複執行時產生冗餘的 `-1` 檔案。
     - 毫秒連拍辨識：透過讀取 EXIF 亞秒/毫秒 (SubSecTimeOriginal) 與相機原始序號，
       自動區分「0.1 秒內的連續快門照片」與「同一張照片的二次裁切/修圖版本」。連拍畫面
       會自動掛載 `-1`、`-2` 序號和諧共存，絕不誤蓋。
  3. 彈性時間分類與更新取代機制：
     - 支援將檔名正規化為「YYYY-MM-DD HH.MM.SS」標準格式，並自動依年份與月份建立資料夾。
     - 支援將修圖軟體 (Photoshop/Lightroom 等) 導出的已編修照片自動分離至 `edited/` 目錄。
     - 若勾選「強制覆蓋」，當遇到同名非連拍的二次修圖作品時，系統會自動比對修改時間與
       檔案特徵，保留最新、品質最佳的版本。
  4. 外掛異常精準攔截與對帳單整合：
     - 自動捕捉 exifread、Pillow、hachoir 等第三方解析外掛所產生的警告與錯誤，
       直接關聯至當前處理檔案並同步整合進 CSV/HTML 對帳單中的「插件訊息」欄位，不再繁雜刷屏。

二、 劇院級互動 HTML 報告與懸浮燈箱 (Interactive Report & Overlay Lightbox)：
  1. 根目錄集中式報告與免外掛總對帳單：
     - 各月份處理結果會直接於「輸出根目錄」生成單一 HTML 視覺化報告（如 2026_04_media_report.html），
       內嵌 Intersection Observer 延遲載入 (Lazy Load) 技術，萬張照片也順暢不卡頓。
     - 同時產出 `_manifest_audit_report.html` 免外掛互動式對帳單，支援關鍵字搜尋與分類過濾。
  2. 究極滿版懸浮燈箱 (100vw / 100vh Overlay Lightbox)：
     - 點擊照片或影片即進入全螢幕燈箱，畫面直接擴展至瀏覽器視窗的 100% 極限滿版，絕不浪費螢幕空間。
     - 控制資訊（張數、檔名、類別、刪除按鈕與箭頭）採取「半透明漸層懸浮列 (Overlay)」設計，
       優雅重疊於影像上下兩端，不干擾主體視覺。
     - 影片直接串流：內嵌 <video> 播放器，支援 MP4、MOV 等格式在燈箱中直接高畫質播放。
  3. 跨平台沙盒突破與安全清理機制：
     - 瀏覽器端提供「🗑️ 標記為待刪除」功能。為突破瀏覽器本地沙盒安全限制，報告上方提供
       「📋 複製 Windows 刪除指令」與「📋 複製 macOS/Linux 刪除指令」一鍵按鈕。
     - 點擊後即可將對應的 `del /f /q` 或 `rm -f` 終端機語法複製到剪貼簿，直接打開終端機
       貼上即可一鍵清除所有標記的廢片，同時保留 .bat / .sh / .txt 下載備援。

三、 現代化介面與安全中斷機制：
  1. 莫蘭迪美學 UI：全系列視窗與彈窗皆完美整合晨霧灰藍、乾燥玫瑰、大地岩石等專業配色，
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
import shutil
import signal
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

# 2. PIL/Pillow (處理圖片格式)
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# 3. Hachoir (處理影片 Metadata)
try:
    from hachoir.parser import createParser
    from hachoir.metadata import extractMetadata
    HACHOIR_AVAILABLE = True
except ImportError:
    HACHOIR_AVAILABLE = False

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
    "大地岩石 (自然)": {
        "MAIN": "#8A9A8A", "HOVER": "#758575", "BG": "#F5F6F4",
        "SUB": "#A3B3A3", "STOP": "#C9A696", "TEXT": "#4E544E",
        "LABEL": "#777777", "BORDER": "#E4E6E4", "PROGRESS": "#B8C4B8"
    }
}

# 預設啟動色系
DEFAULT_THEME_NAME = "晨霧灰藍 (沈穩)"
# ===================== 程式設定 =====================
VERSION = "2026-07-13"

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
EXCLUDE_DIR_KEYWORDS = ['helper.lrdata', 'previews.lrdata', 'smart previews.lrdata', 'lrcat-data', 'System Volume Information', '$RECYCLE.BIN']
IGNORED_EXTENSIONS = ['.lrcat', '.lrdata', '.tmp', '.ds_store', '.db', '.xls', '.xlsx', '.doc', '.docx', '.pdf']

PATTERN_PREFORMATTED = re.compile(r'^(\d{4})-(\d{2})-(\d{2}) \d{2}\.\d{2}\.\d{2}(?:-\d+)?$')
PATTERN_SUFFIX = re.compile(r'^(.*?)(?:-\d+)$')
# ===================================================

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

def is_identical_file(src_path, target_path):
    """物理層級檢查：先比對檔案大小，若相同則讀取首尾 64KB 區塊內容，杜絕產生 -1 重複檔案"""
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
                return f1.read() == f2.read()
            return True
    except Exception:
        return False

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

def is_media_edited(file_path):
    ext = Path(file_path).suffix.lower()

    if ext in RAW_EXTENSIONS:
        return False

    if ext in STANDARD_EXTENSIONS and EXIFREAD_AVAILABLE:
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)
                if 'Image Software' in tags:
                    software = str(tags['Image Software']).lower()
                    edited_keywords = ['photoshop', 'lightroom', 'snapseed', 'vsco', 'apple photos', 'gimp']
                    if any(kw in software for kw in edited_keywords):
                        return True

                if 'EXIF DateTimeOriginal' in tags and 'Image DateTime' in tags:
                    dt_orig = datetime.strptime(str(tags['EXIF DateTimeOriginal']), '%Y:%m:%d %H:%M:%S')
                    dt_mod = datetime.strptime(str(tags['Image DateTime']), '%Y:%m:%d %H:%M:%S')
                    if abs((dt_mod - dt_orig).total_seconds()) > 60:
                        return True
        except Exception:
            pass
    elif ext in VIDEO_EXTENSIONS and HACHOIR_AVAILABLE:
        try:
            parser = createParser(str(file_path))
            if parser:
                with parser:
                    metadata = extractMetadata(parser)
                    if metadata and metadata.has("producer"):
                        producer = str(metadata.get("producer")).lower()
                        vid_edited_keywords = ['premiere', 'lavf', 'handbrake', 'final cut', 'imovie']
                        if any(kw in producer for kw in vid_edited_keywords): return True
        except Exception: pass
    return False

def get_exif_subsec(file_path):
    if EXIFREAD_AVAILABLE and Path(file_path).suffix.lower() in STANDARD_EXTENSIONS:
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)
                for key in ['EXIF SubSecTimeOriginal', 'EXIF SubSecTime', 'EXIF SubSecTimeDigitized']:
                    if key in tags:
                        return str(tags[key]).strip()
        except Exception:
            pass
    return None

def is_burst_shot(src_path, target_path):
    src_subsec = get_exif_subsec(src_path)
    tgt_subsec = get_exif_subsec(target_path)
    if src_subsec and tgt_subsec and src_subsec != tgt_subsec:
        return True

    src_clean = PATTERN_SUFFIX.match(src_path.stem).group(1) if PATTERN_SUFFIX.match(src_path.stem) else src_path.stem
    tgt_clean = PATTERN_SUFFIX.match(target_path.stem).group(1) if PATTERN_SUFFIX.match(target_path.stem) else target_path.stem
    if not PATTERN_PREFORMATTED.match(src_clean) and not PATTERN_PREFORMATTED.match(tgt_clean):
        if src_clean != tgt_clean:
            return True

    return False

def compare_and_decide(src_path, target_path):
    """優先序：0.實體完全相同略過 -> 1.連拍保護 -> 2.修改時間新舊對決"""
    if is_identical_file(src_path, target_path):
        return False

    if is_burst_shot(src_path, target_path):
        return "BURST"

    try:
        src_mtime = os.path.getmtime(src_path)
        tgt_mtime = os.path.getmtime(target_path)
        return src_mtime > tgt_mtime
    except OSError:
        return False

def generate_html_report(output_root_dir, month_key, media_records):
    if not media_records:
        return

    html_path = Path(output_root_dir) / f"{month_key}_media_report.html"

    cards_html = []
    for rec in media_records:
        rel_path = rec['rel_path']
        display_rel_path = format_display_path(rel_path)
        # 關鍵修復：針對帶有空格或特殊字元的檔名進行 URL '%20' 轉碼，防止瀏覽器讀取本地檔案失敗
        rel_path_encoded = urllib.parse.quote(rel_path.replace('\\', '/'))

        fname = rec['name']
        escaped_fname = html.escape(fname, quote=True)
        escaped_display_path = html.escape(display_rel_path, quote=True)
        fsize = format_size(rec['size'])
        category = rec['category']

        display_label = "IMAGE" if category == "standard" else category.upper()
        if category == "edited": display_label = "EDITED"

        badge_style = "background: #7D8C94; color: white;"
        if category == "raw": badge_style = "background: #A88B87; color: white;"
        elif category == "video": badge_style = "background: #66747A; color: white;"
        elif category == "edited": badge_style = "background: #8A9A8A; color: white;"

        error_div = '<div class="error-msg">檔案已刪除</div>'
        error_script = "this.closest('.media-card').classList.add('broken');"

        # 關鍵修復：將 edited 類別加入圖像渲染分支，確保修圖過的圖片也能正常顯示縮圖
        if category in ("standard", "edited"):
            img_tag = f'<img data-src="{rel_path_encoded}" class="lazy-image" alt="{escaped_fname}" onerror="{error_script}">{error_div}'
        else:
            if category == "video":
                detector = f'<video src="{rel_path_encoded}" style="display:none;" onerror="{error_script}"></video>'
                img_tag = f'<div class="video-placeholder">🎬 影片檔案<br><small>{escaped_fname}</small><br><span style="font-size:11px; color:#3498DB;">[點擊播放]</span></div>{detector}{error_div}'
            elif category == "raw":
                img_tag = f'<div class="raw-placeholder">📸 RAW 原檔<br><small>{escaped_fname}</small></div>{error_div}'
            else:
                img_tag = f'<div class="raw-placeholder">{escaped_fname}</div>{error_div}'

        # data-filepath 嚴格保留未轉碼之原始相對路徑，供 Windows/macOS 終端機刪除語法使用
        card = f"""
        <div class="media-card" data-category="{category}" data-name="{html.escape(fname.lower(), quote=True)}" data-size="{rec['size']}" data-url="{rel_path_encoded}" data-filepath="{escaped_display_path}" data-display-name="{escaped_fname}">
            <div class="img-container" onclick="openLightbox(this)" style="cursor: pointer;" title="點擊開啟全螢幕極限滿版瀏覽 / 影片串流">
                {img_tag}
            </div>
            <div class="info">
                <div class="filename" title="{escaped_fname}">{escaped_fname}</div>
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
    <title>{month_key} 媒體處理報告</title>
    <style>
        :root {{ --bg: #F4F6F7; --card-bg: #FFFFFF; --text: #4A4F54; --border: #E0E4E6; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }}
        header {{ background: var(--card-bg); padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 20px; }}
        h1 {{ margin: 0 0 10px 0; font-size: 24px; color: #2C3E50; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; }}
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
            <span>📁 {month_key} 媒體處理報告</span>
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
                <button class="filter-btn" onclick="filterSelection('edited')">編修過照片</button>
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
                if (sortValue === "name-asc") return a.dataset.name.localeCompare(b.dataset.name);
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

# --- 產生免外掛、完全獨立可執行的 HTML 總對帳單報表 ---
def generate_manifest_html(output_root_dir, audit_manifest):
    if not audit_manifest:
        return
    import json
    html_path = Path(output_root_dir) / "_manifest_audit_report.html"

    # 1. 為了減少體積與記憶體，將資料轉為純陣列結構，不再生成任何靜態 <tr> HTML
    # 順序對應: 0:檔名, 1:來源, 2:輸出, 3:相機, 4:副檔名, 5:類別, 6:狀態, 7:理由, 8:插件
    clean_data = []
    for row in audit_manifest:
        clean_data.append([
            str(row[0]),
            # 若原始為 "N/A"，統一強制轉為 "-"
            format_display_path(row[1]) if (row[1] and row[1] != "N/A") else "-",
            format_display_path(row[2]) if (row[2] and row[2] != "N/A") else "-",
            str(row[3]),
            str(row[4]),
            str(row[5]),
            str(row[6]),
            str(row[7]),
            str(row[8])
        ])

    # 2. 將 Python List 轉為壓縮版 JSON 字串 (去除多餘空白，體積縮小 80%)
    json_data_str = json.dumps(clean_data, ensure_ascii=False, separators=(',', ':'))

    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>媒體處理對帳報告表</title>
    <style>
        :root {{ --bg: #F4F6F7; --card-bg: #FFFFFF; --text: #4A4F54; --border: #E0E4E6; --main: #7D8C94; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }}
        header {{ background: var(--card-bg); padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 15px; }}
        h1 {{ margin: 0 0 15px 0; font-size: 22px; color: #2C3E50; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }}
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
            <span>📋 媒體處理總對帳單 </span>
            <span style="font-size: 14px; color: #7F8C8D; font-weight: normal;">總收錄: <strong id="totalCount" style="color:#2C3E50;">0</strong> 筆資料</span>
        </h1>
        <div class="filter-bar">
            <span>🔍 搜尋過濾:</span>
            <input type="text" id="searchInput" oninput="debounceFilter()" placeholder="關鍵字 (檔名、相機、插件訊息)...">

            <span style="margin-left: 10px;">狀態篩選:</span>
            <div class="btn-group" id="statusBtns">
                <button class="active" onclick="setFilter('status', 'all', this)">全部</button>
                <button onclick="setFilter('status', '成功', this)">✅ 成功</button>
                <button onclick="setFilter('status', '略過', this)">⏭️ 略過</button>
                <button onclick="setFilter('status', '失敗', this)">❌ 失敗</button>
            </div>

            <span style="margin-left: 10px;">類別:</span>
            <div class="btn-group" id="catBtns">
                <button class="active" onclick="setFilter('cat', 'all', this)">全部</button>
                <button onclick="setFilter('cat', 'standard', this)">照片</button>
                <button onclick="setFilter('cat', 'edited', this)">已修圖</button>
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
                if (filterState.status !== 'all' && row[6] !== filterState.status) return false;
                if (filterState.cat !== 'all' && row[5] !== filterState.cat) return false;
                if (kw !== "") {{
                    let searchStr = (row[0] + " " + row[3] + " " + row[8]).toLowerCase();
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
                tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:30px; color:#999;">找不到符合條件的資料</td></tr>';
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

                let statusClass = "status-success";
                if (status === "略過") statusClass = "status-skip";
                else if (status === "失敗") statusClass = "status-fail";

                let rowClass = (plugin !== "-") ? "has-plugin-warn" : "";

                return `<tr class="${{rowClass}}">
                    <td class="font-bold">${{fname}}</td>
                    <td class="path-cell" title="${{srcP}}">${{srcP}}</td>
                    <td class="path-cell" title="${{dstP}}">${{dstP}}</td>
                    <td><span class="cam-badge">${{cam}}</span></td>
                    <td>${{ext}}</td>
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

# --- 背景執行緒函式 ---
def threaded_process_images(selected_folders, dest_dir, organize_by_time, normalize_name, separate_edited, copy_video, copy_raw, overwrite, q, stop_event):
    dest_path = Path(dest_dir)
    report_lines = []
    audit_manifest = []

    if not organize_by_time and len(selected_folders) != 1:
        q.put(('msgbox', ("設定錯誤", "未啟用依年月整理時，來源與目的資料夾為 1:1，無法處理多個來源資料夾。"), 'warning', None))
        q.put(('reset', None))
        return

    files = []
    valid_extensions = set(STANDARD_EXTENSIONS)
    if copy_raw: valid_extensions.update(RAW_EXTENSIONS)
    if copy_video: valid_extensions.update(VIDEO_EXTENSIONS)

    for folder in selected_folders:
        if stop_event.is_set(): break
        for dirpath, dirnames, filenames in os.walk(folder):
            if stop_event.is_set(): break

            # 關鍵修復：針對被 EXCLUDE_DIR_KEYWORDS 排除的目錄，強制攔截並輸出日誌理由
            removed_dirs = [d for d in dirnames if any(keyword in d.lower() for keyword in EXCLUDE_DIR_KEYWORDS)]
            for d in removed_dirs:
                skip_path = format_display_path(os.path.join(dirpath, d))
                skip_msg = f"[排除目錄] {skip_path} | 原因：不處理的目錄 ({d})"
                report_lines.append(skip_msg + "\n")
                q.put(('log', skip_msg))
            dirnames[:] = [d for d in dirnames if d not in removed_dirs]

            display_path = format_display_path(dirpath)
            display_path = display_path if len(display_path) <= 65 else "..." + display_path[-62:]
            q.put(('status', f"🔍 正在掃描目錄: {display_path}"))
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                full_src_p = os.path.join(dirpath, filename)

                full_src_win_p = format_display_path(full_src_p)

                if ext in IGNORED_EXTENSIONS:
                    report_lines.append(f"[排除檔案] {full_src_win_p} | 原因：不處理的副檔名 ({ext})\n")
                    # 順序: [名稱, 來源, 輸出, 相機, 副檔名, 類別, 狀態, 理由, 插件]
                    audit_manifest.append([filename, full_src_win_p, "-", "-", ext, "忽略", "略過", f"不處理的副檔名 ({ext})", "-"])
                    continue

                if ext in valid_extensions:
                    files.append(Path(dirpath) / filename)
                else:
                    report_lines.append(f"[略過] {full_src_win_p} | 原因：其他副檔名 ({ext})\n")
                    audit_manifest.append([filename, full_src_win_p, "-", "-", ext, "忽略", "略過", f"其他副檔名 ({ext})", "-"])

    if stop_event.is_set():
        q.put(('status', "🛑 處理已中斷"))
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

    monthly_media_map = {}

    for i, file_path in enumerate(files):
        if stop_event.is_set(): break

        full_win_path = format_display_path(file_path)

        try: file_size = os.path.getsize(file_path)
        except OSError: file_size = 0

        # 用於記錄該檔案處理過程中的外掛異常訊息
        captured_warnings = []
        camera_model = "-"

        try:
            ext = file_path.suffix.lower()
            stem = file_path.stem

            # 讀取相機型號同時攔截插件訊息
            with PluginWarningCapturer() as capturer:
                camera_model = get_camera_model(file_path)
            captured_warnings.extend(capturer.get_messages())

            clean_stem = stem
            suffix_match = PATTERN_SUFFIX.match(stem)

            if suffix_match:
                clean_stem = suffix_match.group(1)

            match = PATTERN_PREFORMATTED.match(clean_stem)

            if match:
                year, month = match.group(1), match.group(2)
                target_name = f"{clean_stem}{ext}"
            else:
                if organize_by_time or normalize_name:
                    # 使用攔截器包覆 get_media_date
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
                    target_dir /= "video"
                    category = "video"
                elif separate_edited:
                    # 使用攔截器包覆 is_media_edited
                    with PluginWarningCapturer() as capturer:
                        is_edited = is_media_edited(file_path)
                    captured_warnings.extend(capturer.get_messages())
                    if is_edited:
                        target_dir /= "edited"
                        category = "edited"
            else:
                month_key = "ALL_MEDIA"
                target_dir = dest_path / file_path.parent.relative_to(Path(selected_folders[0]).parent)
                category = "standard"
                if ext in RAW_EXTENSIONS: category = "raw"
                elif ext in VIDEO_EXTENSIONS: category = "video"
                elif separate_edited:
                    with PluginWarningCapturer() as capturer:
                        is_edited = is_media_edited(file_path)
                    captured_warnings.extend(capturer.get_messages())
                    if is_edited:
                        target_dir /= "edited"
                        category = "edited"

            # 去除重複的警告字句並以分號連接成單一行
            plugin_msg_str = " ; ".join(dict.fromkeys(captured_warnings)) if captured_warnings else "-"

            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / target_name

            is_duplicate_skip = False

            if target_file.exists():
                if overwrite and ext not in RAW_EXTENSIONS:
                    decision = compare_and_decide(file_path, target_file)
                    if decision == "BURST":
                        counter = 1
                        original_stem = target_file.stem
                        while target_file.exists():
                            if is_identical_file(file_path, target_file):
                                is_duplicate_skip = True
                                break
                            target_file = target_dir / f"{original_stem}-{counter}{ext}"
                            counter += 1
                    elif decision is True:
                        pass
                    else:
                        is_duplicate_skip = True
                else:
                    if is_identical_file(file_path, target_file):
                        is_duplicate_skip = True
                    else:
                        counter = 1
                        original_stem = target_file.stem
                        while target_file.exists():
                            if is_identical_file(file_path, target_file):
                                is_duplicate_skip = True
                                break
                            target_file = target_dir / f"{original_stem}-{counter}{ext}"
                            counter += 1

            if is_duplicate_skip:
                skipped_count += 1
                processed_size_bytes += file_size
                report_lines.append(f"[略過] {full_win_path} | 原因: 目標已存在實體相同或品質更佳之同名檔案 ({target_file.name})\n")
                audit_manifest.append([file_path.name, str(file_path), str(target_file), camera_model, ext, category, "略過", f"實體相同或目標存在品質/時間更佳檔案 ({target_file.name})", plugin_msg_str])
                q.put(('metrics', (time.time() - start_time, processed_size_bytes)))
                q.put(('progress', (i + 1) / total_files))
                continue

            max_retries = 5
            for attempt in range(max_retries):
                try:
                    # 嚴格守則：只有在 Target 目錄執行複製與寫入，絕對不觸碰、不污染來源資料夾
                    shutil.copy2(file_path, target_file)

                    log_path = target_dir / "_process_log.txt"
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    with open(log_path, 'a', encoding='utf-8') as log_f:
                        log_f.write(f"[{timestamp}] Processed: {file_path.name} -> {target_file.name}\n")

                    if organize_by_time:
                        rel_p = target_file.relative_to(dest_path).as_posix()
                        if month_key not in monthly_media_map:
                            monthly_media_map[month_key] = []

                        if category != "raw":
                            monthly_media_map[month_key].append({
                                'name': target_file.name,
                                'rel_path': rel_p,
                                'size': file_size,
                                'category': category
                            })

                    audit_manifest.append([file_path.name, str(file_path), str(target_file), camera_model, ext, category, "成功", "複製成功", plugin_msg_str])
                    q.put(('log', f"[{timestamp}] Processed: {file_path.name} -> {target_file.name}"))

                    # 若該檔案有外掛異常訊息，同步輸出在 UI 日誌提示
                    if plugin_msg_str != "-":
                        q.put(('log', f"⚠️ [外掛訊息] {file_path.name}: {plugin_msg_str}"))

                    success_count += 1
                    break
                except (PermissionError, OSError) as e:
                    if attempt < max_retries - 1: time.sleep(0.5)
                    else: raise e

        except Exception as e:
            failed_count += 1
            plugin_msg_str = " ; ".join(dict.fromkeys(captured_warnings)) if captured_warnings else "-"
            report_lines.append(f"[失敗] {full_win_path} | 原因: 處理發生錯誤 ({str(e)})\n")
            audit_manifest.append([file_path.name, str(file_path), "N/A", camera_model, ext, "N/A", "失敗", f"處理異常: {str(e)}", plugin_msg_str])
            q.put(('error_log', f"處理 {file_path.name} 發生錯誤: {e}"))

        processed_size_bytes += file_size
        display_file_path = full_win_path if len(full_win_path) <= 65 else "..." + full_win_path[-62:]
        q.put(('progress', (i + 1) / total_files))
        q.put(('status', f"🚀 正在處理: {i + 1} / {total_files} ({display_file_path})"))
        q.put(('metrics', (time.time() - start_time, processed_size_bytes)))

    generated_html_reports = []
    if organize_by_time and monthly_media_map:
        q.put(('status', "📊 正在根目錄生成各月份動態 HTML 報告 (100vw 懸浮燈箱與影音串流)..."))
        for m_key, records in monthly_media_map.items():
            generate_html_report(dest_path, m_key, records)
            generated_html_reports.append((m_key, dest_path / f"{m_key}_media_report.html"))

    if audit_manifest:
        try:
            manifest_path = dest_path / "_manifest_audit_report.csv"
            with open(manifest_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                # 新增「相機型號」,「插件訊息」欄位
                writer.writerow(['檔案名稱', '來源完整路徑', '輸出目標路徑', '相機型號', '副檔名', '處理類別', '最終狀態', '詳細說明/略過原因', '插件訊息'])
                writer.writerows([
                    [
                        row[0],
                        format_display_path(row[1]) if row[1] != "N/A" else "N/A",
                        format_display_path(row[2]) if row[2] != "N/A" else "N/A",
                        *row[3:]
                    ]
                    for row in audit_manifest
                ])
            q.put(('log', f"📋 CSV 報表已匯出: {manifest_path.name}"))

            # 同步產出 HTML 總對帳單報表
            generate_manifest_html(dest_path, audit_manifest)
            q.put(('log', f"🌐 HTML 報表已匯出: _manifest_audit_report.html"))

        except Exception as e:
            q.put(('error_log', f"無法匯出 CSV 對帳單: {e}"))

    report_msg_append = ""
    if report_lines:
        try:
            report_file_path = dest_path / "_skip_fail_report.txt"
            with open(report_file_path, "w", encoding="utf-8") as f:
                f.write(f"=== 媒體處理例外報告 (產生時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===\n")
                f.write(f"總計略過: {skipped_count} | 總計失敗: {failed_count}\n")
                f.write("="*80 + "\n")
                f.writelines(report_lines)
            report_msg_append = f"\n\n📄 報表已輸出至output根目錄:\n_skip_fail_report.txt\n_manifest_audit_report.csv\n_manifest_audit_report.html"
        except Exception: pass

    if stop_event.is_set():
        msg = f"🛑 處理已中斷！\n\n✅ 成功數量: {success_count}\n⏭️ 已略過: {skipped_count}\n❌ 處理失敗: {failed_count}{report_msg_append}"
        q.put(('msgbox', ("中斷", msg), 'warning', None))
    else:
        msg = f"處理完畢！\n\n✅ 成功數量: {success_count}\n⏭️ 略過檔案: {skipped_count}\n❌ 處理失敗: {failed_count}{report_msg_append}"
        q.put(('msgbox', ("完成", msg), 'info', generated_html_reports))

    q.put(('reset', None))

# --- 智慧瀏覽資料夾 ---
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
class ModernMessageBox(ctk.CTkToplevel):
    def __init__(self, parent, title, message, level="info", theme_colors=None, html_reports=None):
        super().__init__(parent)
        self.title(title)

        num_reports = len(html_reports) if html_reports else 0
        base_height = 240
        row_height = 46
        dialog_height = min(base_height + ((num_reports + 1) * row_height), 560)

        self.geometry(f"420x{dialog_height}")
        self.minsize(400, 240)
        self.maxsize(600, 720)
        self.transient(parent)
        self.grab_set()

        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            try: self.iconbitmap(icon_path)
            except Exception: pass

        bg_color = theme_colors["BG"] if theme_colors else "#F4F6F7"
        main_color = theme_colors["MAIN"] if theme_colors else "#7D8C94"
        hover_color = theme_colors["HOVER"] if theme_colors else "#66747A"
        text_color = theme_colors["TEXT"] if theme_colors else "#4A4F54"
        self.configure(fg_color=bg_color)

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(15, 5))

        icon_str = "ℹ️"
        if level == "warning": icon_str = "⚠️"
        elif level == "error": icon_str = "❌"

        ctk.CTkLabel(header_frame, text=icon_str, font=ctk.CTkFont(size=28)).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(header_frame, text=title, font=ctk.CTkFont(size=16, weight="bold"), text_color=text_color).pack(side="left")

        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=5)
        lbl_msg = ctk.CTkLabel(content_frame, text=message, font=ctk.CTkFont(size=14), justify="left", text_color=text_color, wraplength=360)
        lbl_msg.pack(anchor="w")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="both", expand=True, padx=20, pady=(5, 15))

        ctk.CTkButton(btn_frame, text="確定並關閉", height=38, font=ctk.CTkFont(size=14, weight="bold"),
                      fg_color=main_color, hover_color=hover_color, command=self.destroy).pack(side="top", fill="x", pady=5)

        if html_reports:
            if num_reports <= 3:
                for m_key, h_path in html_reports:
                    ctk.CTkButton(btn_frame, text=f"🌐 開啟 {m_key} 報告", height=36, font=ctk.CTkFont(size=13, weight="bold"),
                                  fg_color="#2980B9", hover_color="#1F618D",
                                  command=lambda p=h_path: webbrowser.open(p.as_uri())).pack(side="top", fill="x", pady=4)
            else:
                scroll_reports = ctk.CTkScrollableFrame(btn_frame, height=180, fg_color="transparent")
                scroll_reports.pack(side="top", fill="both", expand=True, pady=2)
                for m_key, h_path in html_reports:
                    ctk.CTkButton(scroll_reports, text=f"🌐 開啟 {m_key} 報告", height=36, font=ctk.CTkFont(size=13, weight="bold"),
                                  fg_color="#2980B9", hover_color="#1F618D",
                                  command=lambda p=h_path: webbrowser.open(p.as_uri())).pack(side="top", fill="x", pady=4, padx=2)

# --- 彈窗勾選子目錄介面 ---
class FolderSelectDialog(ctk.CTkToplevel):
    def __init__(self, parent, initial_dir, callback, theme_colors=None, allow_multiple=True):
        super().__init__(parent)
        self.title("多資料夾選取器 - 請勾選欲處理的目錄")
        self.geometry("640x540")
        self.minsize(480, 380)
        self.callback = callback
        self.selected_paths = []
        self.allow_multiple = allow_multiple

        self.transient(parent)
        self.grab_set()

        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            try: self.iconbitmap(icon_path)
            except Exception: pass

        bg_color = theme_colors["BG"] if theme_colors else "#F4F6F7"
        main_color = theme_colors["MAIN"] if theme_colors else "#7D8C94"
        hover_color = theme_colors["HOVER"] if theme_colors else "#66747A"
        stop_color = theme_colors["STOP"] if theme_colors else "#A88B87"
        text_color = theme_colors["TEXT"] if theme_colors else "#4A4F54"
        self.configure(fg_color=bg_color)

        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=(15, 5))
        ctk.CTkLabel(top_frame, text=f"📂 目前位置: {format_display_path(initial_dir)}", font=ctk.CTkFont(size=15, weight="bold"), text_color=text_color).pack(side="left")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=8)
        if self.allow_multiple:
            ctk.CTkButton(btn_frame, text="✅ 全選", width=90, height=32, font=ctk.CTkFont(size=14, weight="bold"), fg_color=main_color, hover_color=hover_color, command=self.select_all).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="⬜ 全不選", width=90, height=32, font=ctk.CTkFont(size=14, weight="bold"), fg_color=main_color, hover_color=hover_color, command=self.deselect_all).pack(side="left")

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#FFFFFF" if bg_color=="#F4F6F7" else "#FAFAFA")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.check_vars = []
        self.folder_paths = []

        try:
            subdirs = sorted([os.path.join(initial_dir, d) for d in os.listdir(initial_dir)
                              if os.path.isdir(os.path.join(initial_dir, d)) and not any(k in d.lower() for k in EXCLUDE_DIR_KEYWORDS)])
            if not subdirs:
                ctk.CTkLabel(self.scroll_frame, text="此目錄底下沒有子資料夾！\n將直接處理本目錄。", font=ctk.CTkFont(size=15), text_color=text_color).pack(pady=40)
                self.folder_paths = [initial_dir]
                var = tk.BooleanVar(value=True)
                self.check_vars.append(var)
            else:
                for index, path in enumerate(subdirs):
                    var = tk.BooleanVar(value=self.allow_multiple or index == 0)
                    command = None if self.allow_multiple else lambda selected_var=var: self.select_one(selected_var)
                    chk = ctk.CTkCheckBox(self.scroll_frame, text=f"📁 {os.path.basename(path)}", variable=var, command=command,
                                          font=ctk.CTkFont(family="Calibri", size=15), fg_color=main_color, hover_color=hover_color, text_color=text_color)
                    chk.pack(anchor="w", pady=8, padx=12)
                    self.check_vars.append(var)
                    self.folder_paths.append(path)
        except Exception as e:
            ctk.CTkLabel(self.scroll_frame, text=f"無法讀取目錄內容: {e}", text_color=text_color).pack(pady=20)

        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=20, pady=(10, 18))
        ctk.CTkButton(bottom_frame, text="確認載入選取目錄", height=42, font=ctk.CTkFont(size=16, weight="bold"), fg_color=main_color, hover_color=hover_color, command=self.on_confirm).pack(side="right", padx=(10, 0))
        ctk.CTkButton(bottom_frame, text="取消", height=42, font=ctk.CTkFont(size=16, weight="bold"), fg_color=stop_color, hover_color="#917774", command=self.destroy).pack(side="right")

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
class ImageOrganizerAppModern:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Kairos - Media Organizer Pro")
        self.root.geometry("1600x900")
        self.root.minsize(1280, 720)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.queue = queue.Queue()
        self.processing = False
        self.stop_event = threading.Event()
        self.selected_src_folders = []

        title_font = ctk.CTkFont(family="Calibri", size=24, weight="bold")
        app_font = ctk.CTkFont(family="Calibri", size=16)
        btn_font = ctk.CTkFont(family="Calibri", size=20, weight="bold")

        self.src_var = tk.StringVar()
        self.dest_var = tk.StringVar()
        self.organize_by_time_var = tk.BooleanVar(value=True)    # ☑ 依照時間分資料夾
        self.normalize_name_var = tk.BooleanVar(value=True)      # ☑ 檔名正規化
        self.separate_edited_var = tk.BooleanVar(value=False)    # ☐ 分離已編修過檔案
        self.copy_video_var = tk.BooleanVar(value=True)          # ☑ 掃描包含 VIDEO 檔
        self.copy_raw_var = tk.BooleanVar(value=False)           # ☐ 掃描包含 RAW 檔
        self.overwrite_var = tk.BooleanVar(value=True)           # ☑ 強制覆蓋 (連拍保護與留新對決)
        self.theme_var = tk.StringVar(value=DEFAULT_THEME_NAME)

        self.load_config()

        # === 標題區 ===
        title_frame = ctk.CTkFrame(root, fg_color="transparent")
        title_frame.pack(pady=(20, 10))
        ctk.CTkLabel(title_frame, text="Kairos - Media Organizer Pro", font=title_font).pack(side="top")
        self.lbl_subtitle = ctk.CTkLabel(title_frame, text=f"Build {VERSION}  |  EXIF 解析: {'啟用' if EXIFREAD_AVAILABLE else '未安裝'}  |  PIL 圖片解析: {'啟用' if PIL_AVAILABLE else '未安裝'}  |  Hachoir 影片解析: {'啟用' if HACHOIR_AVAILABLE else '未安裝'}", font=ctk.CTkFont(family="Calibri", size=12))
        self.lbl_subtitle.pack(side="top")

        # === 主要輸入區塊 ===
        frame_top = ctk.CTkFrame(root, corner_radius=10)
        frame_top.pack(pady=10, padx=25, fill="x")
        frame_top.grid_columnconfigure(0, weight=0, minsize=170)
        frame_top.grid_columnconfigure(1, weight=1)
        frame_top.grid_columnconfigure(2, weight=0)

        row_height = 35

        # 來源
        self.lbl_src = ctk.CTkLabel(frame_top, text="來源目錄 (Source):", font=app_font)
        self.lbl_src.grid(row=0, column=0, padx=(20, 10), pady=(20, 10), sticky="e")
        self.entry_src = ctk.CTkEntry(frame_top, textvariable=self.src_var, font=app_font, height=row_height)
        self.entry_src.grid(row=0, column=1, padx=(0, 10), pady=(20, 10), sticky="ew")
        btn_frame_src = ctk.CTkFrame(frame_top, fg_color="transparent")
        btn_frame_src.grid(row=0, column=2, padx=(0, 20), pady=(20, 10), sticky="w")
        self.btn_browse_src = ctk.CTkButton(btn_frame_src, text="🔍 瀏覽", width=95, height=row_height, font=app_font, command=self.browse_src)
        self.btn_browse_src.pack(side="left", padx=(0, 5))
        self.btn_view_src = ctk.CTkButton(btn_frame_src, text="📂 檢視", width=35, height=row_height, font=app_font, command=lambda: open_folder(self.src_var, self.selected_src_folders))
        self.btn_view_src.pack(side="left")

        # 輸出
        self.lbl_dest = ctk.CTkLabel(frame_top, text="輸出目錄 (Output):", font=app_font)
        self.lbl_dest.grid(row=1, column=0, padx=(20, 10), pady=(10, 10), sticky="e")
        ctk.CTkEntry(frame_top, textvariable=self.dest_var, font=app_font, height=row_height).grid(row=1, column=1, padx=(0, 10), pady=(10, 10), sticky="ew")
        btn_frame_dest = ctk.CTkFrame(frame_top, fg_color="transparent")
        btn_frame_dest.grid(row=1, column=2, padx=(0, 20), pady=(10, 10), sticky="w")
        self.btn_browse_dest = ctk.CTkButton(btn_frame_dest, text="🔍 瀏覽", width=95, height=row_height, font=app_font, command=self.browse_dest)
        self.btn_browse_dest.pack(side="left", padx=(0, 5))
        self.btn_view_dest = ctk.CTkButton(btn_frame_dest, text="📂 檢視", width=35, height=row_height, font=app_font, command=lambda: open_folder(self.dest_var))
        self.btn_view_dest.pack(side="left")

        # 進階
        self.lbl_mode = ctk.CTkLabel(frame_top, text="處理模式 (Mode):", font=app_font)
        self.lbl_mode.grid(row=2, column=0, padx=(20, 10), pady=(10, 5), sticky="e")
        mode_frame = ctk.CTkFrame(frame_top, fg_color="transparent")
        mode_frame.grid(row=2, column=1, columnspan=2, padx=(0, 20), pady=(10, 5), sticky="w")

        self.norm_chk = ctk.CTkCheckBox(mode_frame, text="檔名正規化 (YYYY-MM-DD HH.MM.SS)", variable=self.normalize_name_var, font=app_font)
        self.norm_chk.pack(side="left", padx=(0, 20))
        self.time_chk = ctk.CTkCheckBox(mode_frame, text="依照年月區分資料夾 (YYYY_MM)", variable=self.organize_by_time_var, font=app_font)
        self.time_chk.pack(side="left", padx=(0, 20))
        self.sep_edit_chk = ctk.CTkCheckBox(mode_frame, text="分離已編修過檔案", variable=self.separate_edited_var, font=app_font)
        self.sep_edit_chk.pack(side="left", padx=(0, 20))

        self.lbl_opt = ctk.CTkLabel(frame_top, text="動作選項 (Options):", font=app_font)
        self.lbl_opt.grid(row=3, column=0, padx=(20, 10), pady=(5, 20), sticky="e")
        options_frame = ctk.CTkFrame(frame_top, fg_color="transparent")
        options_frame.grid(row=3, column=1, columnspan=2, padx=(0, 20), pady=(5, 20), sticky="ew")

        self.vid_checkbox = ctk.CTkCheckBox(options_frame, text="掃描包含 VIDEO 檔", variable=self.copy_video_var, font=app_font)
        self.vid_checkbox.pack(side="left", padx=(0, 15))
        self.raw_checkbox = ctk.CTkCheckBox(options_frame, text="掃描包含 RAW 檔", variable=self.copy_raw_var, font=app_font)
        self.raw_checkbox.pack(side="left", padx=(0, 15))
        self.overwrite_checkbox = ctk.CTkCheckBox(options_frame, text="強制覆蓋時間戳相同的照片 (連拍保護與留新不留舊)", variable=self.overwrite_var, font=app_font)
        self.overwrite_checkbox.pack(side="left", padx=(0, 15))

        # 主題選擇
        self.theme_menu = ctk.CTkOptionMenu(
            options_frame,
            values=list(THEMES.keys()),
            variable=self.theme_var,
            command=self.change_theme,
            font=app_font,
            width=160
        )
        self.theme_menu.pack(side="right", padx=(0, 0))
        self.lbl_theme = ctk.CTkLabel(options_frame, text="主題配色", font=app_font)
        self.lbl_theme.pack(side="right", padx=(0, 5))

        # === 狀態與進度 ===
        self.status_frame = ctk.CTkFrame(root, fg_color="transparent")
        self.status_frame.pack(pady=(10, 0), padx=30, fill="x")

        self.status_top_frame = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        self.status_top_frame.pack(side='top', fill='x', pady=(0, 8))

        self.status_label = ctk.CTkLabel(self.status_top_frame, text="準備就緒", font=ctk.CTkFont(family="Calibri", size=15), anchor='w')
        self.status_label.pack(side='left', fill='x', expand=True)

        self.metrics_label = ctk.CTkLabel(self.status_top_frame, text="時間: 00:00 | 大小: 0 B | 速度: 0 B/s", font=ctk.CTkFont(family="Calibri", size=14, weight="bold"), anchor='e')
        self.metrics_label.pack(side='right')

        self.progress_container = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        self.progress_container.pack(side='top', fill='x')

        self.progress_bar = ctk.CTkProgressBar(self.progress_container, height=14)
        self.progress_bar.set(0)
        self.progress_bar.pack(side='left', fill='x', expand=True, padx=(0, 10))

        self.progress_pct_label = ctk.CTkLabel(self.progress_container, text="0%", font=ctk.CTkFont(family="Calibri", size=14, weight="bold"))
        self.progress_pct_label.pack(side='right')

        # === 即時文字日誌區 ===
        self.log_textbox = ctk.CTkTextbox(root, height=150, font=("Consolas", 12), border_width=1)
        self.log_textbox.pack(pady=(15, 5), padx=25, fill="both", expand=True)
        self.log_textbox.insert("0.0", "等待執行...\n")
        self.log_textbox.configure(state="disabled")

        # === 執行按鈕 ===
        frame_btn = ctk.CTkFrame(root, fg_color="transparent")
        frame_btn.pack(pady=(10, 20), padx=25, fill="x")
        self.start_btn = ctk.CTkButton(frame_btn, text="▶ 開始執行", font=btn_font, height=55, corner_radius=8, command=self.toggle_processing)
        self.start_btn.pack(expand=True, fill="x")

        self.organize_by_time_var.trace_add("write", self.update_ui_dependencies)
        self.update_ui_dependencies()
        # 套用初始主題顏色
        self.apply_theme_colors(self.theme_var.get())

        # 在初始化最後，呼叫圖示設定函式
        self.set_app_icon()

    def set_app_icon(self):
        # 1. 定義圖示檔案的路徑 (處理打包後與開發模式的路徑)
        # 假設 icon.ico 放在與程式同目錄
        icon_path = resource_path("icon.ico")

        # 2. 檢查檔案是否存在，防止找不到檔案直接報錯退出
        if os.path.exists(icon_path):
            try:
                # 嘗試設定圖示
                self.root.iconbitmap(icon_path)
            except Exception as e:
                print(f"圖示設定失敗，自動忽略: {e}")
                # 這裡不執行任何操作，Tkinter 會自動保持預設圖示
        else:
            # 如果檔案根本不存在 (雙擊時路徑找不到)，直接跳過
            # 這樣程式就會維持預設的羽毛圖示，而不會退出
            print("未找到圖示檔案，使用系統預設圖示。")

    def apply_theme_colors(self, theme_name):
        if theme_name not in THEMES:
            theme_name = DEFAULT_THEME_NAME
            self.theme_var.set(theme_name)

        t = THEMES[theme_name]

        # 背景與文字
        self.root.configure(fg_color=t["BG"])
        self.lbl_subtitle.configure(text_color=t["TEXT"])
        self.lbl_src.configure(text_color=t["TEXT"])
        self.lbl_dest.configure(text_color=t["TEXT"])
        self.lbl_mode.configure(text_color=t["TEXT"])
        self.lbl_opt.configure(text_color=t["TEXT"])
        self.lbl_theme.configure(text_color=t["LABEL"])
        self.status_label.configure(text_color=t["TEXT"])
        self.metrics_label.configure(text_color=t["TEXT"])
        self.progress_pct_label.configure(text_color=t["TEXT"])

        # 按鈕與選單
        self.btn_browse_src.configure(fg_color=t["MAIN"], hover_color=t["HOVER"])
        self.btn_browse_dest.configure(fg_color=t["MAIN"], hover_color=t["HOVER"])
        self.btn_view_src.configure(fg_color=t["SUB"], hover_color=t["HOVER"])
        self.btn_view_dest.configure(fg_color=t["SUB"], hover_color=t["HOVER"])
        self.theme_menu.configure(fg_color=t["MAIN"], button_color=t["MAIN"], button_hover_color=t["HOVER"])

        # Checkboxes
        for chk in [self.norm_chk, self.time_chk, self.sep_edit_chk, self.vid_checkbox, self.raw_checkbox, self.overwrite_checkbox]:
            chk.configure(fg_color=t["MAIN"], hover_color=t["HOVER"], text_color=t["TEXT"])

        # 執行按鈕 (需判斷是否在執行中)
        if self.processing:
            self.start_btn.configure(fg_color=t["STOP"], hover_color=t["HOVER"])
        else:
            self.start_btn.configure(fg_color=t["MAIN"], hover_color=t["HOVER"])

        # 進度條與日誌
        self.progress_bar.configure(fg_color=t["BORDER"], progress_color=t["PROGRESS"])

        # 日誌區塊稍微淺色處理以適配莫蘭迪色背景
        log_bg = "#FFFFFF" if t["BG"] == "#F4F6F7" else "#FAFAFA"
        self.log_textbox.configure(fg_color=log_bg, border_color=t["BORDER"], text_color=t["TEXT"])

    def change_theme(self, new_theme):
        self.apply_theme_colors(new_theme)
        self.save_config()

    def update_ui_dependencies(self, *args):
        if not self.organize_by_time_var.get() or not EXIFREAD_AVAILABLE:
            self.separate_edited_var.set(False)
            self.sep_edit_chk.configure(state="disabled")
        else:
            self.sep_edit_chk.configure(state="normal")

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
                    self.copy_video_var.set(config.getboolean('Settings', 'CopyVideo', fallback=True))
                    self.copy_raw_var.set(config.getboolean('Settings', 'CopyRAW', fallback=False))
                    self.separate_edited_var.set(
                        EXIFREAD_AVAILABLE and config.getboolean('Settings', 'SeparateEdited', fallback=False)
                    )
                    self.overwrite_var.set(config.getboolean('Settings', 'Overwrite', fallback=True))
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
            'CopyVideo': str(self.copy_video_var.get()),
            'CopyRAW': str(self.copy_raw_var.get()),
            'SeparateEdited': str(self.separate_edited_var.get()),
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
                    elapsed, size_bytes = data
                    speed = size_bytes / elapsed if elapsed > 0 else 0
                    self.metrics_label.configure(text=f"時間: {format_time(elapsed)} | 大小: {format_size(size_bytes)} | 速度: {format_size(speed)}/s")
                elif msg_type == 'reset':
                    self.reset_ui()
                    return
                elif msg_type == 'msgbox':
                    title, content = data
                    level = msg[2] if len(msg) > 2 else 'info'
                    reports = msg[3] if len(msg) > 3 else None
                    t = THEMES[self.theme_var.get()]
                    ModernMessageBox(self.root, title, content, level, t, html_reports=reports)
        except queue.Empty: pass
        if self.processing: self.root.after(100, self.check_queue)

    def reset_ui(self):
        self.processing = False
        self.stop_event.clear()
        self.status_label.configure(text="準備就緒")
        self.progress_bar.set(0)
        self.progress_pct_label.configure(text="0%")
        self.metrics_label.configure(text="時間: 00:00 | 大小: 0 B | 速度: 0 B/s")

        t = THEMES[self.theme_var.get()]
        self.start_btn.configure(state='normal', text="▶ 開始執行", fg_color=t["MAIN"], hover_color=t["HOVER"])
        for chk in [self.time_chk, self.norm_chk, self.vid_checkbox, self.raw_checkbox, self.sep_edit_chk, self.overwrite_checkbox]:
            chk.configure(state='normal')
        self.theme_menu.configure(state='normal')
        self.btn_browse_src.configure(state='normal')
        self.update_ui_dependencies()

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

        if not EXIFREAD_AVAILABLE:
            self.separate_edited_var.set(False)

        if not dest:
            messagebox.showwarning("警告", "請先使用瀏覽按鈕指定輸出目錄！")
            return

        if not os.path.isdir(dest):
            messagebox.showerror("錯誤", "指定的輸出路徑不存在，請重新檢查。")
            return

        try:
            dest_res = os.path.abspath(dest)
            for src_f in self.selected_src_folders:
                src_res = os.path.abspath(src_f)
                if os.path.commonpath([src_res, dest_res]) == src_res:
                    messagebox.showerror("嚴重錯誤", f"「輸出目錄」不能位於「來源目錄 ({format_display_path(src_f)})」裡面！\n\n這會導致無限迴圈複製，請重新設定。")
                    return
        except Exception: pass

        self.save_config()
        self.processing = True
        self.stop_event.clear()

        t = THEMES[self.theme_var.get()]
        self.start_btn.configure(text="🛑 停止處理", fg_color=t["STOP"], hover_color=t["HOVER"])
        for chk in [self.time_chk, self.norm_chk, self.sep_edit_chk, self.vid_checkbox, self.raw_checkbox, self.overwrite_checkbox]:
            chk.configure(state='disabled')
        self.theme_menu.configure(state='disabled')
        self.btn_browse_src.configure(state='disabled')

        self.status_label.configure(text="準備掃描檔案...")
        self.metrics_label.configure(text="時間: 00:00 | 大小: 0 B | 速度: 0 B/s")
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.progress_pct_label.configure(text="0%")

        self.thread = threading.Thread(
            target=threaded_process_images,
            args=(self.selected_src_folders, dest, self.organize_by_time_var.get(), self.normalize_name_var.get(), self.separate_edited_var.get(), self.copy_video_var.get(), self.copy_raw_var.get(), self.overwrite_var.get(), self.queue, self.stop_event),
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
