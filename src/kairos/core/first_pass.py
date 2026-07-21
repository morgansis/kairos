"""First-pass media processing orchestration."""

from __future__ import annotations

import hashlib
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

try:
    from ..config.constants import PLACEHOLDER, RAW_EXTENSIONS, STANDARD_EXTENSIONS, VIDEO_EXTENSIONS
    from ..database.manifest_db import (
        begin_manifest_transaction,
        commit_manifest_transaction,
        fail_manifest_transaction,
    )
    from ..metadata.arbiter import compare_and_decide, get_capture_meta, invalidate_capture_meta
    from ..metadata.exif_parser import get_camera_model, get_media_date_with_source
    from ..utils.file_ops import (
        candidate_path_for,
        find_identical_in_target,
        timestamp_parts,
        unique_path,
    )
    from ..utils.logger import PluginWarningCapturer
    from ..utils.sys_helpers import format_display_path, format_time
except ImportError:  # pragma: no cover - direct script execution fallback
    from config.constants import PLACEHOLDER, RAW_EXTENSIONS, STANDARD_EXTENSIONS, VIDEO_EXTENSIONS
    from database.manifest_db import (
        begin_manifest_transaction,
        commit_manifest_transaction,
        fail_manifest_transaction,
    )
    from metadata.arbiter import compare_and_decide, get_capture_meta, invalidate_capture_meta
    from metadata.exif_parser import get_camera_model, get_media_date_with_source
    from utils.file_ops import (
        candidate_path_for,
        find_identical_in_target,
        timestamp_parts,
        unique_path,
    )
    from utils.logger import PluginWarningCapturer
    from utils.sys_helpers import format_display_path, format_time


def _norm_abs(path_value):
    return os.path.normcase(os.path.abspath(str(path_value)))


def _stream_copy_with_hash(src_path, dst_path, chunk_size=1024 * 1024):
    """Copy bytes once while computing SHA-256 from the same stream."""
    digest = hashlib.sha256()
    with open(src_path, "rb") as src, open(dst_path, "wb") as dst:
        for chunk in iter(lambda: src.read(chunk_size), b""):
            dst.write(chunk)
            digest.update(chunk)
    return digest.hexdigest()


def _capture_datetime_from_timestamp_base(timestamp_base):
    if not timestamp_base:
        return ""
    try:
        dt = datetime.strptime(timestamp_base, "%Y-%m-%d %H.%M.%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def run_first_pass(
    files,
    selected_folders,
    dest_path,
    organize_by_time,
    normalize_name,
    performance_mode,
    q,
    stop_event,
    report_lines,
    audit_manifest,
):
    """Execute first-pass copy/skip/fail processing for source files."""
    total_files = len(files)
    success_count = 0
    skipped_count = 0
    failed_count = 0
    start_time = time.time()
    processed_size_bytes = 0
    monthly_media_map = {}
    manifest_seed_records = {}
    txn_seq = 0
    q.put(("status", f"First Pass | safe collection and dup-skip: 0 / {total_files}"))

    for i, file_path in enumerate(files):
        if stop_event.is_set():
            break

        full_win_path = format_display_path(file_path)
        try:
            file_size = os.path.getsize(file_path)
        except OSError:
            file_size = 0

        captured_warnings = []
        camera_model = "-"
        loc_name, map_url = "-", "-"

        try:
            ext = file_path.suffix.lower()
            stem = file_path.stem
            src_capture_meta = get_capture_meta(file_path)
            capture_subsec_ms = str(src_capture_meta.get("subsec_ms") or "000").zfill(3)[:3]
            capture_serial = src_capture_meta.get("serial", PLACEHOLDER)
            capture_datetime_original = ""
            source_meta_source = "mtime"

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
                capture_datetime_original = _capture_datetime_from_timestamp_base(timestamp_base)
                source_meta_source = "filename"
            else:
                if organize_by_time or normalize_name:
                    if performance_mode:
                        media_date, source_meta_source = get_media_date_with_source(file_path)
                    else:
                        with PluginWarningCapturer() as capturer:
                            media_date, source_meta_source = get_media_date_with_source(file_path)
                        captured_warnings.extend(capturer.get_messages())

                    year = media_date.strftime("%Y")
                    month = media_date.strftime("%m")
                    target_name = (
                        f"{media_date.strftime('%Y-%m-%d %H.%M.%S')}{ext}"
                        if normalize_name
                        else f"{clean_stem}{ext}"
                    )
                    capture_datetime_original = media_date.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    year, month = None, None
                    target_name = f"{clean_stem}{ext}"
                    source_meta_source = "mtime"
                    capture_datetime_original = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

            if not capture_datetime_original:
                capture_datetime_original = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

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
                if ext in RAW_EXTENSIONS:
                    category = "raw"
                elif ext in VIDEO_EXTENSIONS:
                    category = "video"

            plugin_msg_str = " ; ".join(dict.fromkeys(captured_warnings)) if captured_warnings else PLACEHOLDER
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / target_name

            effective_category = category
            is_duplicate_skip = False
            skip_reason = None
            target_stem = target_file.stem
            identical_match = find_identical_in_target(file_path, target_dir, target_stem, ext)
            candidate_dir = target_dir / "candidate"
            candidate_has_similar = False
            candidate_identical = None
            if category == "standard" and ext in STANDARD_EXTENSIONS and candidate_dir.exists():
                candidate_has_similar = any(candidate_dir.glob(f"{target_stem}*{ext}"))
                candidate_identical = find_identical_in_target(file_path, candidate_dir, target_stem, ext)

            if identical_match:
                is_duplicate_skip = True
                skip_reason = f"[IDENTICAL] {identical_match.name}"
                target_file = identical_match
            elif candidate_identical is not None:
                is_duplicate_skip = True
                skip_reason = f"[IDENTICAL] candidate/{candidate_identical.name}"
                target_file = candidate_identical
            elif target_file.exists():
                candidate_photo_mode = category == "standard" and ext in STANDARD_EXTENSIONS
                decision = compare_and_decide(file_path, target_file)

                if decision == "IDENTICAL":
                    is_duplicate_skip = True
                    skip_reason = f"[IDENTICAL] {target_file.name}"
                elif candidate_photo_mode:
                    base_stem = timestamp_base or target_file.stem
                    src_ms = src_capture_meta.get("subsec_ms")
                    candidate_dir = target_dir / "candidate"
                    candidate_dir.mkdir(parents=True, exist_ok=True)

                    if target_file.parent.name != "candidate":
                        if decision == "BURST":
                            tgt_meta = get_capture_meta(target_file)
                            tgt_ms = tgt_meta.get("subsec_ms")
                            if tgt_ms:
                                archived = unique_path(candidate_dir, f"{base_stem}-{tgt_ms}", ext)
                            else:
                                archived = candidate_path_for(target_dir, base_stem, ext)
                        else:
                            archived = candidate_path_for(target_dir, base_stem, ext)
                        invalidate_capture_meta(target_file)
                        invalidate_capture_meta(archived)
                        target_file.rename(archived)
                        if not performance_mode:
                            q.put(("log", f"[CANDIDATE] promoted existing -> {archived.name}"))

                    if decision == "BURST" and src_ms:
                        target_file = unique_path(candidate_dir, f"{base_stem}-{src_ms}", ext)
                    else:
                        target_file = candidate_path_for(target_dir, base_stem, ext)
                    effective_category = "candidate"
                else:
                    target_file = unique_path(target_dir, target_file.stem, ext)
            elif category == "standard" and ext in STANDARD_EXTENSIONS and candidate_has_similar:
                base_stem = timestamp_base or target_stem
                src_ms = src_capture_meta.get("subsec_ms")
                candidate_dir.mkdir(parents=True, exist_ok=True)
                if src_ms:
                    target_file = unique_path(candidate_dir, f"{base_stem}-{src_ms}", ext)
                else:
                    target_file = candidate_path_for(target_dir, base_stem, ext)
                effective_category = "candidate"

            if target_file.parent.name == "candidate" and effective_category == "standard":
                effective_category = "candidate"

            if is_duplicate_skip:
                skipped_count += 1
                processed_size_bytes += file_size
                report_lines.append(f"[SKIP: IDENTICAL] {full_win_path} | REASON: {skip_reason}\n")
                audit_manifest.append(
                    [
                        file_path.name,
                        str(file_path),
                        str(target_file),
                        camera_model,
                        ext,
                        effective_category,
                        "SKIP",
                        skip_reason,
                        plugin_msg_str,
                    ]
                )
                q.put(("metrics", processed_size_bytes))
                q.put(("progress", (i + 1) / total_files))
                continue

            max_retries = 5
            for attempt in range(max_retries):
                tx_id = None
                part_file = None
                try:
                    txn_seq += 1
                    tx_id = f"{int(time.time() * 1000)}_{txn_seq:08d}"
                    part_file = target_file.with_name(f".{target_file.name}.part.{txn_seq}")

                    begin_manifest_transaction(
                        dest_path=dest_path,
                        tx_id=tx_id,
                        src_path=file_path,
                        target_path=target_file,
                        part_path=part_file,
                    )

                    sha256_value = _stream_copy_with_hash(file_path, part_file)
                    shutil.copystat(file_path, part_file)
                    os.replace(part_file, target_file)
                    invalidate_capture_meta(target_file)

                    commit_manifest_transaction(
                        dest_path=dest_path,
                        tx_id=tx_id,
                        sha256_value=sha256_value,
                        size_bytes=file_size,
                    )
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    if organize_by_time:
                        rel_p = target_file.relative_to(dest_path).as_posix()
                        if month_key not in monthly_media_map:
                            monthly_media_map[month_key] = []

                        if effective_category != "raw":
                            monthly_media_map[month_key].append(
                                {
                                    "name": target_file.name,
                                    "rel_path": rel_p,
                                    "size": file_size,
                                    "category": effective_category,
                                    "loc_name": loc_name,
                                    "map_url": map_url,
                                }
                            )

                    audit_manifest.append(
                        [
                            file_path.name,
                            str(file_path),
                            str(target_file),
                            camera_model,
                            ext,
                            effective_category,
                            "PASS",
                            "COPY_OK",
                            plugin_msg_str,
                        ]
                    )
                    if not performance_mode:
                        q.put(("log", f"[{timestamp}] Processed: {file_path.name} -> {target_file.name}"))

                    if not performance_mode and plugin_msg_str != "-":
                        q.put(("log", f"[PLUGIN] {file_path.name}: {plugin_msg_str}"))

                    manifest_seed_records[_norm_abs(target_file)] = {
                        "sha256": sha256_value,
                        "capture_datetime_original": capture_datetime_original,
                        "capture_subsec_ms": capture_subsec_ms,
                        "orig_name_first_seen": file_path.name,
                        "camera_model": camera_model,
                        "serial": capture_serial,
                        "meta_source": source_meta_source,
                        "filesize": file_size,
                        "mtime_iso": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(timespec="seconds"),
                    }

                    success_count += 1
                    break
                except (PermissionError, OSError) as e:
                    if tx_id:
                        fail_manifest_transaction(dest_path=dest_path, tx_id=tx_id, reason=str(e))
                    if part_file and part_file.exists():
                        try:
                            part_file.unlink()
                        except Exception:
                            pass
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                    else:
                        raise e

        except Exception as e:
            failed_count += 1
            plugin_msg_str = " ; ".join(dict.fromkeys(captured_warnings)) if captured_warnings else "-"
            report_lines.append(f"[FAIL] {full_win_path} | REASON: processing exception ({str(e)})\n")
            audit_manifest.append(
                [
                    file_path.name,
                    str(file_path),
                    PLACEHOLDER,
                    camera_model,
                    ext,
                    PLACEHOLDER,
                    "FAIL",
                    f"ERROR: processing exception: {str(e)}",
                    plugin_msg_str,
                ]
            )
            q.put(("error_log", f"ERROR while processing {file_path.name}: {e}"))

        processed_size_bytes += file_size
        display_file_path = full_win_path if len(full_win_path) <= 65 else "..." + full_win_path[-62:]
        phase_elapsed = time.time() - start_time
        rate = (i + 1) / phase_elapsed if phase_elapsed > 0 else 0
        remaining = (total_files - i - 1) / rate if rate > 0 else 0
        q.put(("progress", (i + 1) / total_files))
        overall_remaining = remaining * 1.15
        q.put(
            (
                "status",
                f"First Pass | safe collection and duplicate-skip: {i + 1} / {total_files} "
                f"| elapsed {format_time(phase_elapsed)} | "
                f"phase remaining {format_time(remaining)} | overall ETA {format_time(overall_remaining)} | "
                f"{display_file_path}",
            )
        )
        q.put(("metrics", processed_size_bytes))

    return (
        success_count,
        skipped_count,
        failed_count,
        start_time,
        processed_size_bytes,
        monthly_media_map,
        manifest_seed_records,
    )


__all__ = ["run_first_pass"]
