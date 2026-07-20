"""Main application window helpers."""

from __future__ import annotations

import os
import subprocess
import sys
from tkinter import messagebox

try:
    from ..utils.sys_helpers import format_display_path
except ImportError:  # pragma: no cover - direct script execution fallback
    from utils.sys_helpers import format_display_path


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

__all__ = ["open_folder", "sigint_handler"]
