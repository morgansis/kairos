"""Platform integration helpers."""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path


def format_display_path(path_value):
    """Format a path for display without changing the path used for file I/O."""
    path_str = str(path_value)
    if os.name == "nt":
        return path_str.replace("/", "\\")
    return path_str.replace("\\", "/")


def parse_saved_source_paths(saved_value):
    """Read new and legacy multi-folder settings without treating UI text as a path."""
    paths = [path.strip() for path in saved_value.split(";") if path.strip()]
    if paths and paths[0].startswith("[") and "] " in paths[0]:
        paths[0] = paths[0].split("] ", 1)[1].strip()
    return [path for path in paths if os.path.exists(path)]


def resource_path(relative_path):
    """Get resource absolute path for dev mode and PyInstaller frozen mode."""
    try:
        base_path = os.path.join(sys._MEIPASS, "resources")
    except Exception:
        base_path = str(Path(__file__).resolve().parent.parent / "resources")
    return os.path.join(base_path, relative_path)


def format_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
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
    color = str(hex_color).lstrip("#")
    if len(color) != 6:
        return None
    r = int(color[0:2], 16)
    g = int(color[2:4], 16)
    b = int(color[4:6], 16)
    return (b << 16) | (g << 8) | r


def _titlebar_text_hex_for_bg(hex_color):
    color = str(hex_color).lstrip("#")
    if len(color) != 6:
        return "#FFFFFF"
    r = int(color[0:2], 16)
    g = int(color[2:4], 16)
    b = int(color[4:6], 16)
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
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(value_caption), ctypes.sizeof(value_caption)
        )
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_TEXT_COLOR, ctypes.byref(value_text), ctypes.sizeof(value_text)
        )
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_BORDER_COLOR, ctypes.byref(value_border), ctypes.sizeof(value_border)
        )
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
