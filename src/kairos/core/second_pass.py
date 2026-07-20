"""Second-pass month directory orchestration helpers."""

from __future__ import annotations

import re
import time

try:
    from ..metadata.arbiter import second_pass_month
    from ..utils.sys_helpers import format_time
except ImportError:  # pragma: no cover - direct script execution fallback
    from metadata.arbiter import second_pass_month
    from utils.sys_helpers import format_time


def run_second_pass(dest_path, organize_by_time, overwrite, stop_event, q, processed_size_bytes):
    """Run second-pass month-level burst/candidate organization."""
    if stop_event.is_set() or not organize_by_time or not overwrite:
        return

    month_dirs = [p for p in dest_path.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}_\d{2}", p.name)]
    second_start = time.time()
    for index, month_dir in enumerate(month_dirs, start=1):
        elapsed = time.time() - second_start
        rate = (index - 1) / elapsed if elapsed > 0 and index > 1 else 0
        remaining = (len(month_dirs) - index + 1) / rate if rate else 0
        q.put(
            (
                "status",
                f"Second Pass | organizing burst sets and alternates: {index} / {len(month_dirs)} "
                f"({index / max(len(month_dirs), 1):.1%}) | elapsed {format_time(elapsed)} | "
                f"overall ETA {format_time(remaining)} | {month_dir.name}",
            )
        )
        second_pass_month(month_dir, stop_event)
        q.put(("progress", index / max(len(month_dirs), 1)))
        q.put(("metrics", processed_size_bytes))


__all__ = ["run_second_pass"]
