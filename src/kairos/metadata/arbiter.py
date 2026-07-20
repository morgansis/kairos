"""Deduplication and collision arbitration helpers."""

from __future__ import annotations

import os
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict

try:
    import exifread

    EXIFREAD_AVAILABLE = True
except ImportError:
    EXIFREAD_AVAILABLE = False

try:
    from ..config.constants import (
        EXIF_DATETIME_FORMAT,
        EXIF_DATETIME_TAG_KEYS,
        EXIF_SERIAL_TAG_KEYS,
        EXIF_SUBSEC_TAG_KEYS,
        PLACEHOLDER,
        STANDARD_EXTENSIONS,
    )
    from ..utils.file_ops import (
        is_identical_file,
        timestamp_parts,
        unique_path,
    )
except ImportError:  # pragma: no cover - direct script execution fallback
    from config.constants import (
        EXIF_DATETIME_FORMAT,
        EXIF_DATETIME_TAG_KEYS,
        EXIF_SERIAL_TAG_KEYS,
        EXIF_SUBSEC_TAG_KEYS,
        PLACEHOLDER,
        STANDARD_EXTENSIONS,
    )
    from utils.file_ops import (
        is_identical_file,
        timestamp_parts,
        unique_path,
    )

DECISIONS = ("IDENTICAL", "SAME_MS", "BURST", "REPLACE", "KEEP")
CAPTURE_META_CACHE = {}


def normalized_subsec(value):
    """Standardize EXIF sub-second value to a three-digit millisecond string."""
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return (digits + "000")[:3] if digits else None


def _read_exif_capture_fields(file_path):
    result = {
        "capture_dt": None,
        "subsec_raw": None,
        "subsec_ms": None,
        "serial": PLACEHOLDER,
        "capture_epoch": None,
        "has_precise_ms": False,
    }
    ext = Path(file_path).suffix.lower()
    if not (EXIFREAD_AVAILABLE and ext in STANDARD_EXTENSIONS):
        return result

    try:
        with open(file_path, "rb") as f:
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
            result["capture_dt"] = datetime.strptime(dt_text, EXIF_DATETIME_FORMAT)
        except Exception:
            result["capture_dt"] = None

    for key in EXIF_SUBSEC_TAG_KEYS:
        if key in tags:
            value = str(tags[key]).strip()
            if value:
                result["subsec_raw"] = value
                result["subsec_ms"] = normalized_subsec(value)
                break

    for key in EXIF_SERIAL_TAG_KEYS:
        if key in tags:
            value = str(tags[key]).strip()
            if value:
                result["serial"] = value
                break

    return result


def get_capture_meta(file_path):
    cache_key = os.path.normcase(os.path.abspath(str(file_path)))
    if cache_key in CAPTURE_META_CACHE:
        return CAPTURE_META_CACHE[cache_key]

    meta = _read_exif_capture_fields(file_path)
    if meta["capture_dt"] is None:
        try:
            meta["capture_dt"] = datetime.fromtimestamp(os.path.getmtime(file_path))
        except Exception:
            meta["capture_dt"] = None

    if meta["capture_dt"] is not None:
        epoch = meta["capture_dt"].timestamp()
        if meta["subsec_ms"] is not None:
            epoch += int(meta["subsec_ms"]) / 1000.0
            meta["has_precise_ms"] = True
        meta["capture_epoch"] = epoch

    CAPTURE_META_CACHE[cache_key] = meta
    return meta


def invalidate_capture_meta(file_path):
    cache_key = os.path.normcase(os.path.abspath(str(file_path)))
    CAPTURE_META_CACHE.pop(cache_key, None)


def get_exif_subsec(file_path):
    return get_capture_meta(file_path).get("subsec_raw")


def is_same_millisecond_capture(src_path, target_path):
    src_meta = get_capture_meta(src_path)
    tgt_meta = get_capture_meta(target_path)
    if not (src_meta.get("has_precise_ms") and tgt_meta.get("has_precise_ms")):
        return False
    src_serial = src_meta.get("serial", PLACEHOLDER)
    tgt_serial = tgt_meta.get("serial", PLACEHOLDER)
    if src_serial != PLACEHOLDER and tgt_serial != PLACEHOLDER and src_serial != tgt_serial:
        return False
    src_ms = int(round(src_meta["capture_epoch"] * 1000))
    tgt_ms = int(round(tgt_meta["capture_epoch"] * 1000))
    return src_ms == tgt_ms


def is_burst_shot(src_path, target_path):
    src_meta = get_capture_meta(src_path)
    tgt_meta = get_capture_meta(target_path)
    src_serial = src_meta.get("serial", PLACEHOLDER)
    tgt_serial = tgt_meta.get("serial", PLACEHOLDER)
    if src_serial == PLACEHOLDER or tgt_serial == PLACEHOLDER or src_serial != tgt_serial:
        return False
    src_epoch = src_meta.get("capture_epoch")
    tgt_epoch = tgt_meta.get("capture_epoch")
    if src_epoch is None or tgt_epoch is None:
        return False
    delta = abs(src_epoch - tgt_epoch)
    return 0 < delta < 1.0


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


def safe_rename_batch(rename_map):
    """Rename through staging names to avoid overwrite collisions in one batch."""
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
    """Group by second + extension to process burst/candidate arrangement."""
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
                target = unique_path(month_dir / "candidate", f"{base}-{subsec}-c{candidate_index}", ext)
                rename_map[variant] = target
                candidate_index += 1

        for index, member in enumerate(sorted(unknown, key=lambda p: p.name), start=1):
            rename_map[member] = month_dir / f"{base}-u{index}{ext}"

        safe_rename_batch(rename_map)


__all__ = [
    "DECISIONS",
    "CAPTURE_META_CACHE",
    "normalized_subsec",
    "_read_exif_capture_fields",
    "get_capture_meta",
    "invalidate_capture_meta",
    "get_exif_subsec",
    "is_same_millisecond_capture",
    "is_burst_shot",
    "compare_and_decide",
    "safe_rename_batch",
    "second_pass_month",
]
