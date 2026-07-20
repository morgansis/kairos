"""Main application window helpers and class."""

from __future__ import annotations

import configparser
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

try:
    from ..config.constants import *  # noqa: F401,F403
    from ..core.pipeline import threaded_process_images
    from ..ui.dialogs import FolderSelectDialog, ModernMessageBox
    from ..utils.sys_helpers import (
        apply_window_icon,
        apply_windows_titlebar_theme,
        format_display_path,
        format_size,
        format_time,
        parse_saved_source_paths,
    )
except ImportError:  # pragma: no cover - direct script execution fallback
    from config.constants import *  # noqa: F401,F403
    from core.pipeline import threaded_process_images
    from ui.dialogs import FolderSelectDialog, ModernMessageBox
    from utils.sys_helpers import (
        apply_window_icon,
        apply_windows_titlebar_theme,
        format_display_path,
        format_size,
        format_time,
        parse_saved_source_paths,
    )

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

def sigint_handler(sig, frame):
    print("\n[系統] 接收到 Ctrl+C 中斷指令，正在安全停止背景執行緒並離開程式...")
    main_mod = sys.modules.get("__main__")
    app_obj = getattr(main_mod, "app", None) if main_mod else None
    root_obj = getattr(main_mod, "root", None) if main_mod else None
    if app_obj is None:
        app_obj = globals().get("app")
    if root_obj is None:
        root_obj = globals().get("root")
    try:
        if app_obj is not None and getattr(app_obj, "processing", False):
            app_obj.stop_event.set()
    except Exception:
        pass
    try:
        if root_obj is not None:
            root_obj.quit()
            root_obj.destroy()
    except Exception:
        pass
    sys.exit(0)

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

__all__ = ["open_folder", "sigint_handler", "ImageOrganizerAppModern"]
