"""Dialog components for Kairos UI."""

from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

try:
    from ..config.constants import *  # noqa: F401,F403
    from ..utils.sys_helpers import apply_window_icon, apply_windows_titlebar_theme, format_display_path
except ImportError:  # pragma: no cover - direct script execution fallback
    from config.constants import *  # noqa: F401,F403
    from utils.sys_helpers import apply_window_icon, apply_windows_titlebar_theme, format_display_path

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

__all__ = ["ModernMessageBox", "FolderSelectDialog"]
