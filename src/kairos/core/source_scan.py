"""Source folder scan and candidate collection helpers."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from ..config.constants import EXCLUDE_DIR_KEYWORDS, IGNORED_EXTENSIONS
    from ..utils.sys_helpers import format_display_path
except ImportError:  # pragma: no cover - direct script execution fallback
    from config.constants import EXCLUDE_DIR_KEYWORDS, IGNORED_EXTENSIONS
    from utils.sys_helpers import format_display_path


def collect_source_files(
    selected_folders,
    valid_extensions,
    report_lines,
    audit_manifest,
    q,
    stop_event,
    performance_mode,
    is_kairos_self_file,
):
    """Walk selected folders and collect files matching allowed extensions."""
    files = []
    for folder in selected_folders:
        if stop_event.is_set():
            break
        for dirpath, dirnames, filenames in os.walk(folder):
            if stop_event.is_set():
                break

            removed_dirs = [d for d in dirnames if any(keyword in d.lower() for keyword in EXCLUDE_DIR_KEYWORDS)]
            for d in removed_dirs:
                skip_path = format_display_path(os.path.join(dirpath, d))
                skip_msg = f"[SKIP_DIR] {skip_path} | REASON: ignored directory ({d})"
                report_lines.append(skip_msg + "\n")
                if not performance_mode:
                    q.put(("log", skip_msg))
            dirnames[:] = [d for d in dirnames if d not in removed_dirs]

            display_path = format_display_path(dirpath)
            display_path = display_path if len(display_path) <= 65 else "..." + display_path[-62:]
            q.put(("status", f"Scanning directory: {display_path}"))

            for filename in filenames:
                if is_kairos_self_file(filename):
                    continue

                ext = os.path.splitext(filename)[1].lower()
                full_src_p = os.path.join(dirpath, filename)
                full_src_win_p = format_display_path(full_src_p)

                if ext in IGNORED_EXTENSIONS:
                    report_lines.append(f"[SKIP_FILE] {full_src_win_p} | REASON: ignored extension ({ext})\n")
                    audit_manifest.append(
                        [filename, full_src_win_p, "-", "-", ext, "ignored", "SKIP", f"ignored extension ({ext})", "-"]
                    )
                    continue

                if ext in valid_extensions:
                    files.append(Path(dirpath) / filename)
                else:
                    report_lines.append(f"[SKIP] {full_src_win_p} | REASON: unsupported extension ({ext})\n")
                    audit_manifest.append(
                        [
                            filename,
                            full_src_win_p,
                            "-",
                            "-",
                            ext,
                            "ignored",
                            "SKIP",
                            f"unsupported extension ({ext})",
                            "-",
                        ]
                    )
    return files


__all__ = ["collect_source_files"]
