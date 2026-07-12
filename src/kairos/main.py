"""
================================================================================
圖片與影片分類更名工具 (Media Organizer Pro) - v2026-07-05
================================================================================

【程式使用說明與行為模式】
本程式用於將雜亂的圖檔（含 RAW 檔）與影片檔自動整理、重新命名並輸出到指定目錄，絕不更動來源檔案。

[核心行為模式] (由介面上的兩個 Checkbox 控制)：
1. 標準整理模式 (兩者皆勾選，預設)：
   - 讀取圖檔 EXIF 或影片 Metadata (Creation Date)。
   - 將檔案更名為 `YYYY-MM-DD HH.MM.SS.副檔名`。
   - 放入目標目錄下的 `YYYY_MM/` 資料夾中。
   - (RAW 檔會獨立放入 `YYYY_MM/raw/`；影片會放入 `YYYY_MM/video/`；編修過的檔案會放入 `YYYY_MM/edited/`)。

2. 僅改名不分類 (取消依照時間分類，勾選檔名正規化)：
   - 讀取時間將檔案更名為 `YYYY-MM-DD HH.MM.SS`。
   - 但在目標目錄中，完美還原來源端的子資料夾樹狀結構。

3. 僅分類不改名 (勾選依照時間分類，取消檔名正規化)：
   - 讀取時間來決定存放的 `YYYY_MM/` 資料夾，但保留原始檔名直接複製。

4. XCOPY 鏡像模式 (兩者皆取消勾選)：
   - 不讀取 Metadata，不修改檔名。
   - 將來源檔案完美依照原有的子目錄結構，直接複製一份到目標目錄。

[特殊防呆與優化機制]：
- 掃描快取：只要來源目錄未變更，暫停後再次點擊「開始」不會重新掃描硬碟，直接沿用清單。
- 預先格式化辨識：若來源檔名已是 `YYYY-MM-DD HH.MM.SS` (或帶有 -1, -2 綴字)，會直接沿用名稱與時間，跳過解析以加速執行。
- 置頂紀錄：在每個輸出的資料夾內，會自動產生 `_process_log.txt` 紀錄詳細的複製軌跡。
- 智慧瀏覽：點擊「瀏覽」時，會優先開啟輸入框中的目錄位置，提升操作流暢度。
- 效能儀表板：即時顯示經過時間、累積處理容量與處理速度。
- 例外報告：產生 `_skip_fail_report.txt` 詳列略過與失敗原因。
================================================================================
"""

import os
import sys
import re
import time
import queue
import shutil
import threading
import subprocess
import configparser
import tkinter as tk
import customtkinter as ctk
from pathlib import Path
from datetime import datetime
from tkinter import filedialog, messagebox

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
VERSION = "2026-07-05"

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
RAW_EXTENSIONS = {'.dng', '.cr2', '.cr3', '.nef', '.arw', '.raf', '.orf', '.rw2'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.m4v', '.3gp'}
EXCLUDE_DIR_KEYWORDS = ['helper.lrdata', 'previews.lrdata', 'smart previews.lrdata', 'lrcat-data']

PATTERN_PREFORMATTED = re.compile(r'^(\d{4})-(\d{2})-(\d{2}) \d{2}\.\d{2}\.\d{2}(?:-\d+)?$')
# ===================================================

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

def is_media_edited(file_path):
    ext = Path(file_path).suffix.lower()

    if ext in RAW_EXTENSIONS:
        return False

    if ext in STANDARD_EXTENSIONS:
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)
                if 'Image Software' in tags:
                    software = str(tags['Image Software']).lower()
                    edited_keywords = ['photoshop', 'lightroom', 'snapseed', 'vsco', 'apple photos', 'gimp']
                    if any(kw in software for kw in edited_keywords):
                        return True

                if 'EXIF DateTimeOriginal' in tags and 'Image DateTime' in tags:
                    dt_orig_str = str(tags['EXIF DateTimeOriginal'])
                    dt_mod_str = str(tags['Image DateTime'])
                    try:
                        dt_orig = datetime.strptime(dt_orig_str, '%Y:%m:%d %H:%M:%S')
                        dt_mod = datetime.strptime(dt_mod_str, '%Y:%m:%d %H:%M:%S')
                        if abs((dt_mod - dt_orig).total_seconds()) > 60:
                            return True
                    except ValueError:
                        pass
        except Exception:
            pass

    elif ext in VIDEO_EXTENSIONS and HACHOIR_AVAILABLE:
        try:
            parser = createParser(str(file_path))
            if parser:
                with parser:
                    metadata = extractMetadata(parser)
                    if metadata:
                        if metadata.has("producer"):
                            producer = str(metadata.get("producer")).lower()
                            vid_edited_keywords = ['premiere', 'lavf', 'handbrake', 'final cut', 'imovie']
                            if any(kw in producer for kw in vid_edited_keywords):
                                return True
        except Exception:
            pass

    return False

# --- 背景執行緒函式 ---
def threaded_process_images(src_dir, dest_dir, organize_by_time, normalize_name, separate_edited, copy_video, copy_raw, overwrite, cached_files, q, stop_event):
    src_path = Path(src_dir)
    dest_path = Path(dest_dir)

    # 儲存失敗與略過的紀錄
    report_lines = []

    if cached_files is not None:
        files = cached_files
    else:
        files = []
        valid_extensions = set(STANDARD_EXTENSIONS)
        if copy_raw:
            valid_extensions.update(RAW_EXTENSIONS)
        if copy_video:
            valid_extensions.update(VIDEO_EXTENSIONS)

        for dirpath, dirnames, filenames in os.walk(src_dir):
            if stop_event.is_set():
                break
            dirnames[:] = [d for d in dirnames if not any(keyword in d.lower() for keyword in EXCLUDE_DIR_KEYWORDS)]

            display_path = dirpath if len(dirpath) <= 65 else "..." + dirpath[-62:]
            q.put(('status', f"🔍 正在掃描目錄: {display_path}"))

            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in valid_extensions:
                    files.append(Path(dirpath) / filename)

        q.put(('cache_files', files))

    if stop_event.is_set():
        q.put(('status', "🛑 處理已中斷"))
        q.put(('reset', None))
        return

    total_files = len(files)
    if total_files == 0:
        q.put(('msgbox', ("提示", "來源目錄中找不到符合的媒體檔。"), 'info'))
        q.put(('reset', None))
        return

    success_count = 0
    skipped_count = 0
    failed_count = 0

    start_time = time.time()
    processed_size_bytes = 0

    # 階段 2：處理檔案
    for i, file_path in enumerate(files):
        if stop_event.is_set():
            break

        try:
            file_size = os.path.getsize(file_path)
        except OSError:
            file_size = 0

        try:
            ext = file_path.suffix.lower()
            match = PATTERN_PREFORMATTED.match(file_path.stem)

            if match:
                year, month = match.group(1), match.group(2)
                target_name = file_path.name
            else:
                if organize_by_time or normalize_name:
                    media_date = get_media_date(file_path)
                    year = media_date.strftime('%Y')
                    month = media_date.strftime('%m')
                    target_name = f"{media_date.strftime('%Y-%m-%d %H.%M.%S')}{ext}" if normalize_name else file_path.name
                else:
                    year, month = None, None
                    target_name = file_path.name

            if organize_by_time:
                target_dir = dest_path / f"{year}_{month}"
                if separate_edited and is_media_edited(file_path):
                    target_dir /= "edited"
                elif ext in RAW_EXTENSIONS:
                    target_dir /= "raw"
                elif ext in VIDEO_EXTENSIONS:
                    target_dir /= "video"
            else:
                target_dir = dest_path / file_path.parent.relative_to(src_path)

            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / target_name

            counter = 1
            is_duplicate = False
            original_stem = target_file.stem

            while target_file.exists():
                if os.path.getsize(file_path) == os.path.getsize(target_file):
                    if not overwrite:
                        is_duplicate = True
                        break
                    else:
                        break
                else:
                    target_file = target_dir / f"{original_stem}-{counter}{ext}"
                    counter += 1

            if is_duplicate:
                skipped_count += 1
                processed_size_bytes += file_size
                elapsed = time.time() - start_time
                report_lines.append(f"[略過] {file_path}\n   ↳ 原因: 目標目錄已存在完全相同的檔案 ({target_file.name})\n")

                q.put(('metrics', (elapsed, processed_size_bytes)))
                q.put(('progress', (i + 1) / total_files))
                continue

            max_retries = 5
            for attempt in range(max_retries):
                try:
                    shutil.copy2(file_path, target_file)

                    log_path = target_dir / "_process_log.txt"
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    log_entry = f"[{timestamp}] Processed: {file_path.name} -> {target_file.name}"

                    with open(log_path, 'a', encoding='utf-8') as log_f:
                        log_f.write(log_entry + "\n")

                    q.put(('log', log_entry))
                    success_count += 1
                    break
                except (PermissionError, OSError) as e:
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                    else:
                        raise e

        except Exception as e:
            failed_count += 1
            report_lines.append(f"[失敗] {file_path}\n   ↳ 原因: 處理發生例外錯誤 - {str(e)}\n")
            q.put(('error_log', f"處理檔案 {file_path.name} 時發生錯誤: {e}"))

        processed_size_bytes += file_size
        elapsed = time.time() - start_time

        display_file_path = str(file_path) if len(str(file_path)) <= 65 else "..." + str(file_path)[-62:]
        q.put(('progress', (i + 1) / total_files))
        q.put(('status', f"🚀 正在處理: {i + 1} / {total_files}  ({display_file_path})"))
        q.put(('metrics', (elapsed, processed_size_bytes)))

    # 產生失敗與略過報告
    report_msg_append = ""
    if report_lines:
        try:
            report_file_path = dest_path / "_skip_fail_report.txt"
            with open(report_file_path, "w", encoding="utf-8") as f:
                f.write(f"=== 媒體處理例外報告 ===\n")
                f.write(f"產生時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"總計略過: {skipped_count} | 總計失敗: {failed_count}\n")
                f.write("="*60 + "\n\n")
                f.writelines(report_lines)
            report_msg_append = f"\n\n📄 略過與失敗的詳細紀錄已輸出至:\n_skip_fail_report.txt"
        except Exception:
            pass

    if stop_event.is_set():
        msg = f"🛑 處理已中斷！\n\n✅ 成功數量: {success_count}\n⏭️ 已略過: {skipped_count}\n❌ 處理失敗: {failed_count}{report_msg_append}"
        q.put(('msgbox', ("中斷", msg), 'warning'))
    else:
        msg = f"處理完畢！\n\n✅ 成功數量: {success_count}\n⏭️ 略過檔案: {skipped_count}\n❌ 處理失敗: {failed_count}{report_msg_append}"
        q.put(('msgbox', ("完成", msg), 'info'))

    q.put(('reset', None))

def open_folder(path_var):
    path = path_var.get().strip(' "\'')
    if not path: return
    if os.path.isfile(path): path = os.path.dirname(path)

    if os.path.exists(path):
        try:
            if sys.platform == "win32": os.startfile(path)
            elif sys.platform == "darwin": subprocess.Popen(["open", path])
            else: subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("錯誤", f"無法開啟資料夾: {e}")
    else:
        messagebox.showwarning("警告", f"資料夾不存在: {path}")

# --- UI 介面類別 ---
class ImageOrganizerAppModern:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Kairos - Media Organizer Pro")
        self.root.geometry("1600x900")
        self.root.minsize(800, 600)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.queue = queue.Queue()
        self.processing = False
        self.stop_event = threading.Event()

        self.cached_src_dir = ""
        self.cached_files = None

        title_font = ctk.CTkFont(family="Calibri", size=24, weight="bold")
        app_font = ctk.CTkFont(family="Calibri", size=16)
        btn_font = ctk.CTkFont(family="Calibri", size=20, weight="bold")

        self.src_var = tk.StringVar()
        self.dest_var = tk.StringVar()
        self.organize_by_time_var = tk.BooleanVar(value=True)
        self.normalize_name_var = tk.BooleanVar(value=True)
        self.separate_edited_var = tk.BooleanVar(value=False)
        self.copy_video_var = tk.BooleanVar(value=True)
        self.copy_raw_var = tk.BooleanVar(value=False)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.theme_var = tk.StringVar(value=DEFAULT_THEME_NAME)

        self.load_config()

        # === 標題區 ===
        title_frame = ctk.CTkFrame(root, fg_color="transparent")
        title_frame.pack(pady=(20, 10))
        ctk.CTkLabel(title_frame, text="Kairos - Media Organizer Pro", font=title_font).pack(side="top")
        self.lbl_subtitle = ctk.CTkLabel(title_frame, text=f"Build {VERSION}  |  EXIF 解析: {'啟用' if EXIFREAD_AVAILABLE else '未安裝'}  |  PIL 圖片格式: {'啟用' if PIL_AVAILABLE else '未安裝'}  |  Hachoir 影片解析: {'啟用' if HACHOIR_AVAILABLE else '未安裝'}", font=ctk.CTkFont(family="Calibri", size=12))
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
        ctk.CTkEntry(frame_top, textvariable=self.src_var, font=app_font, height=row_height).grid(row=0, column=1, padx=(0, 10), pady=(20, 10), sticky="ew")
        btn_frame_src = ctk.CTkFrame(frame_top, fg_color="transparent")
        btn_frame_src.grid(row=0, column=2, padx=(0, 20), pady=(20, 10), sticky="w")
        self.btn_browse_src = ctk.CTkButton(btn_frame_src, text="🔍 瀏覽", width=70, height=row_height, font=app_font, command=self.browse_src)
        self.btn_browse_src.pack(side="left", padx=(0, 5))
        self.btn_view_src = ctk.CTkButton(btn_frame_src, text="📂 檢視", width=35, height=row_height, font=app_font, command=lambda: open_folder(self.src_var))
        self.btn_view_src.pack(side="left")

        # 輸出
        self.lbl_dest = ctk.CTkLabel(frame_top, text="輸出目錄 (Output):", font=app_font)
        self.lbl_dest.grid(row=1, column=0, padx=(20, 10), pady=(10, 10), sticky="e")
        ctk.CTkEntry(frame_top, textvariable=self.dest_var, font=app_font, height=row_height).grid(row=1, column=1, padx=(0, 10), pady=(10, 10), sticky="ew")
        btn_frame_dest = ctk.CTkFrame(frame_top, fg_color="transparent")
        btn_frame_dest.grid(row=1, column=2, padx=(0, 20), pady=(10, 10), sticky="w")
        self.btn_browse_dest = ctk.CTkButton(btn_frame_dest, text="🔍 瀏覽", width=70, height=row_height, font=app_font, command=self.browse_dest)
        self.btn_browse_dest.pack(side="left", padx=(0, 5))
        self.btn_view_dest = ctk.CTkButton(btn_frame_dest, text="📂 檢視", width=35, height=row_height, font=app_font, command=lambda: open_folder(self.dest_var))
        self.btn_view_dest.pack(side="left")

        # 進階
        self.lbl_mode = ctk.CTkLabel(frame_top, text="控制模式 (Mode):", font=app_font)
        self.lbl_mode.grid(row=2, column=0, padx=(20, 10), pady=(10, 5), sticky="e")
        mode_frame = ctk.CTkFrame(frame_top, fg_color="transparent")
        mode_frame.grid(row=2, column=1, columnspan=2, padx=(0, 20), pady=(10, 5), sticky="w")

        self.norm_chk = ctk.CTkCheckBox(mode_frame, text="將檔案名稱正規化 (YYYY-MM-DD HH:MM:SS)", variable=self.normalize_name_var, font=app_font)
        self.norm_chk.pack(side="left", padx=(0, 20))
        self.time_chk = ctk.CTkCheckBox(mode_frame, text="依照時間分資料夾 (YYYY_MM)", variable=self.organize_by_time_var, font=app_font)
        self.time_chk.pack(side="left", padx=(0, 20))
        self.sep_edit_chk = ctk.CTkCheckBox(mode_frame, text="分離已編修過檔案 (edited/)", variable=self.separate_edited_var, font=app_font)
        self.sep_edit_chk.pack(side="left", padx=(0, 20))

        self.lbl_opt = ctk.CTkLabel(frame_top, text="進階選項 (Options):", font=app_font)
        self.lbl_opt.grid(row=3, column=0, padx=(20, 10), pady=(5, 20), sticky="e")
        options_frame = ctk.CTkFrame(frame_top, fg_color="transparent")
        options_frame.grid(row=3, column=1, columnspan=2, padx=(0, 20), pady=(5, 20), sticky="ew")

        self.vid_checkbox = ctk.CTkCheckBox(options_frame, text="掃描包含 VIDEO 檔", variable=self.copy_video_var, font=app_font)
        self.vid_checkbox.pack(side="left", padx=(0, 15))
        self.raw_checkbox = ctk.CTkCheckBox(options_frame, text="掃描包含 RAW 檔", variable=self.copy_raw_var, font=app_font)
        self.raw_checkbox.pack(side="left", padx=(0, 15))
        self.overwrite_checkbox = ctk.CTkCheckBox(options_frame, text="強制覆蓋同大小檔案", variable=self.overwrite_var, font=app_font)
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
        if not self.organize_by_time_var.get():
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
                    self.src_var.set(config.get('Settings', 'Source', fallback=''))
                    self.dest_var.set(config.get('Settings', 'Destination', fallback=''))
                    self.organize_by_time_var.set(config.getboolean('Settings', 'OrganizeByTime', fallback=True))
                    self.normalize_name_var.set(config.getboolean('Settings', 'NormalizeName', fallback=True))
                    self.copy_video_var.set(config.getboolean('Settings', 'CopyVideo', fallback=True))
                    self.copy_raw_var.set(config.getboolean('Settings', 'CopyRAW', fallback=False))
                    self.separate_edited_var.set(config.getboolean('Settings', 'SeparateEdited', fallback=False))
                    self.overwrite_var.set(config.getboolean('Settings', 'Overwrite', fallback=False))

                    saved_theme = config.get('Settings', 'Theme', fallback=DEFAULT_THEME_NAME)
                    if saved_theme in THEMES:
                        self.theme_var.set(saved_theme)
            except Exception:
                pass

    def save_config(self):
        config = configparser.ConfigParser()
        config['Settings'] = {
            'Source': self.src_var.get().strip(' "\''),
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
            with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
                config.write(configfile)
        except Exception:
            pass

    def browse_src(self):
        current_path = self.src_var.get().strip(' "\'')
        if not current_path or not os.path.isdir(current_path):
            current_path = getattr(self, 'cached_src_dir', '')
            if not current_path or not os.path.isdir(current_path):
                current_path = os.path.expanduser("~")

        folder = filedialog.askdirectory(initialdir=current_path)
        if folder:
            self.src_var.set(folder)
            self.cached_src_dir = ""
            self.cached_files = None

    def browse_dest(self):
        current_path = self.dest_var.get().strip(' "\'')
        if not current_path or not os.path.isdir(current_path):
            current_path = os.path.expanduser("~")

        folder = filedialog.askdirectory(initialdir=current_path)
        if folder:
            self.dest_var.set(folder)

    def check_queue(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                msg_type = msg[0]
                data = msg[1]

                if msg_type == 'status':
                    self.status_label.configure(text=data)
                elif msg_type == 'cache_files':
                    self.cached_files = data
                    self.cached_src_dir = self.src_var.get()
                elif msg_type == 'log':
                    self.log_textbox.configure(state="normal")
                    self.log_textbox.insert("end", data + "\n")
                    if int(self.log_textbox.index("end-1c").split('.')[0]) > 1000:
                        self.log_textbox.delete("1.0", "2.0")
                    self.log_textbox.see("end")
                    self.log_textbox.configure(state="disabled")
                elif msg_type == 'error_log':
                    # 在日誌中顯示錯誤
                    self.log_textbox.configure(state="normal")
                    self.log_textbox.insert("end", f"[ERROR] {data}\n")
                    self.log_textbox.see("end")
                    self.log_textbox.configure(state="disabled")
                elif msg_type == 'progress':
                    self.progress_bar.set(data)
                    pct_val = int(data * 100)
                    self.progress_pct_label.configure(text=f"{pct_val}%")
                elif msg_type == 'metrics':
                    elapsed, size_bytes = data
                    speed = size_bytes / elapsed if elapsed > 0 else 0
                    time_str = format_time(elapsed)
                    size_str = format_size(size_bytes)
                    speed_str = f"{format_size(speed)}/s"
                    self.metrics_label.configure(text=f"時間: {time_str} | 大小: {size_str} | 速度: {speed_str}")
                elif msg_type == 'reset':
                    self.reset_ui()
                    return
                elif msg_type == 'msgbox':
                    title, msg_content = data
                    # 如果有第三個參數代表警告層級
                    level = msg[2] if len(msg) > 2 else 'info'
                    if level == 'warning':
                        messagebox.showwarning(title, msg_content)
                    elif level == 'info':
                        messagebox.showinfo(title, msg_content)
                    elif level == 'error':
                        messagebox.showerror(title, msg_content)
                elif msg_type == 'error':
                    messagebox.showerror("錯誤", data)
        except queue.Empty:
            pass
        if self.processing:
            self.root.after(100, self.check_queue)

    def reset_ui(self):
        self.processing = False
        self.stop_event.clear()
        self.status_label.configure(text="準備就緒")
        self.progress_bar.set(0)
        self.progress_pct_label.configure(text="0%")
        self.metrics_label.configure(text="時間: 00:00 | 大小: 0 B | 速度: 0 B/s")

        t = THEMES[self.theme_var.get()]
        self.start_btn.configure(state='normal', text="▶ 開始執行", fg_color=t["MAIN"], hover_color=t["HOVER"])

        self.time_chk.configure(state='normal')
        self.norm_chk.configure(state='normal')
        self.vid_checkbox.configure(state='normal')
        self.raw_checkbox.configure(state='normal')
        self.sep_edit_chk.configure(state='normal')
        self.overwrite_checkbox.configure(state='normal')
        self.theme_menu.configure(state='normal')

    def toggle_processing(self):
        if self.processing:
            self.stop_event.set()
            self.start_btn.configure(text="⏳ 正在中斷並等待當前檔案完成...", state='disabled')
            return

        src = self.src_var.get().strip(' "\'')
        dest = self.dest_var.get().strip(' "\'')
        organize_by_time = self.organize_by_time_var.get()
        normalize_name = self.normalize_name_var.get()
        copy_video = self.copy_video_var.get()
        copy_raw = self.copy_raw_var.get()
        separate_edited = self.separate_edited_var.get()
        overwrite = self.overwrite_var.get()

        self.src_var.set(src)
        self.dest_var.set(dest)

        if not src or not dest:
            messagebox.showwarning("警告", "請完整指定來源與輸出目錄！")
            return

        if not os.path.isdir(src) or not os.path.isdir(dest):
            messagebox.showerror("錯誤", "指定的路徑不存在，請重新檢查。")
            return

        try:
            src_res = os.path.abspath(src)
            dest_res = os.path.abspath(dest)
            if os.path.commonpath([src_res, dest_res]) == src_res:
                messagebox.showerror("嚴重錯誤", "「輸出目錄」不能位於「來源目錄」裡面！\n\n這會導致無限迴圈複製，請重新設定。")
                return
        except Exception:
            pass

        self.save_config()

        self.processing = True
        self.stop_event.clear()

        t = THEMES[self.theme_var.get()]
        self.start_btn.configure(text="🛑 停止處理", fg_color=t["STOP"], hover_color=t["HOVER"])
        self.time_chk.configure(state='disabled')
        self.norm_chk.configure(state='disabled')
        self.sep_edit_chk.configure(state='disabled')
        self.vid_checkbox.configure(state='disabled')
        self.raw_checkbox.configure(state='disabled')
        self.overwrite_checkbox.configure(state='disabled')
        self.theme_menu.configure(state='disabled')

        self.status_label.configure(text="準備掃描檔案...")
        self.metrics_label.configure(text="時間: 00:00 | 大小: 0 B | 速度: 0 B/s")
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.progress_pct_label.configure(text="0%")

        passed_cache = self.cached_files if src == getattr(self, 'cached_src_dir', '') else None

        self.thread = threading.Thread(
            target=threaded_process_images,
            args=(src, dest, organize_by_time, normalize_name, separate_edited, copy_video, copy_raw, overwrite, passed_cache, self.queue, self.stop_event),
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

if __name__ == "__main__":
    # 強制設定為淺色模式，讓莫蘭迪色背景不受系統深色影響
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    app = ImageOrganizerAppModern(root)
    root.mainloop()
