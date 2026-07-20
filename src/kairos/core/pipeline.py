"""Main workflow orchestration helpers."""

from __future__ import annotations

import csv
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

try:
    from ..database.auditor import emit_completion_dialog
    from ..database.manifest_db import (
        build_skiplist_append_message,
        export_audit_bundle,
    )
    from .source_scan import collect_source_files
    from .second_pass import run_second_pass
    from .preflight import (
        build_valid_extensions,
        classify_scan_outcome,
        requires_single_source_without_time_grouping,
    )
    from ..config.constants import (
        PLACEHOLDER,
        RAW_EXTENSIONS,
        STANDARD_EXTENSIONS,
        VIDEO_EXTENSIONS,
    )
    from ..config.rules import is_kairos_self_file as _rule_is_kairos_self_file
    from ..metadata.arbiter import (
        CAPTURE_META_CACHE,
        compare_and_decide,
        get_capture_meta,
        invalidate_capture_meta,
    )
    from ..metadata.exif_parser import get_camera_model, get_media_date
    from ..metadata.geo_engine import (
        finalize_geo_perf_stats,
        GEO_PERF_STATS,
        collect_media_records,
        load_and_merge_geo_caches,
        prepare_geo_runtime,
        reset_geo_perf_stats,
        save_geo_cache_to_dest,
    )
    from ..reporting.html_builder import generate_html_report
    from ..reporting.index_builder import generate_file_type_summary, generate_manifest_html
    from ..utils.file_ops import (
        candidate_path_for,
        find_identical_in_target,
        timestamp_parts,
        unique_indexed_path,
        unique_path,
    )
    from ..utils.logger import PluginWarningCapturer
    from ..utils.sys_helpers import format_display_path, format_time
except ImportError:  # pragma: no cover - direct script execution fallback
    from database.auditor import emit_completion_dialog
    from database.manifest_db import (
        build_skiplist_append_message,
        export_audit_bundle,
    )
    from core.source_scan import collect_source_files
    from core.second_pass import run_second_pass
    from core.preflight import (
        build_valid_extensions,
        classify_scan_outcome,
        requires_single_source_without_time_grouping,
    )
    from config.constants import (
        PLACEHOLDER,
        RAW_EXTENSIONS,
        STANDARD_EXTENSIONS,
        VIDEO_EXTENSIONS,
    )
    from config.rules import is_kairos_self_file as _rule_is_kairos_self_file
    from metadata.arbiter import (
        CAPTURE_META_CACHE,
        compare_and_decide,
        get_capture_meta,
        invalidate_capture_meta,
    )
    from metadata.exif_parser import get_camera_model, get_media_date
    from metadata.geo_engine import (
        finalize_geo_perf_stats,
        GEO_PERF_STATS,
        collect_media_records,
        load_and_merge_geo_caches,
        prepare_geo_runtime,
        reset_geo_perf_stats,
        save_geo_cache_to_dest,
    )
    from reporting.html_builder import generate_html_report
    from reporting.index_builder import generate_file_type_summary, generate_manifest_html
    from utils.file_ops import (
        candidate_path_for,
        find_identical_in_target,
        timestamp_parts,
        unique_indexed_path,
        unique_path,
    )
    from utils.logger import PluginWarningCapturer
    from utils.sys_helpers import format_display_path, format_time

def is_kairos_self_file(filename):
    # 1. 報表檔案 (如 _index.html, 2026_04_media_report.html)
    if filename.endswith('_media_report.html') or filename == '_index.html':
        return True
    # 2. 清單與日誌檔案 (如 _manifest_geo.json, _manifest_audit.csv, _manifest_skiplist.txt, _process_log.txt)
    system_prefixes = ('_manifest_', '_process_log.txt', '_kairos_')

    if filename.startswith(system_prefixes):
        return True
    return False

# Bind to centralized rule implementation.
is_kairos_self_file = _rule_is_kairos_self_file

def threaded_process_images(selected_folders, dest_dir, organize_by_time, normalize_name, enable_geo_lookup, copy_video, copy_raw, overwrite, performance_mode, q, stop_event):
    dest_path = Path(dest_dir)
    report_lines = []
    audit_manifest = []
    CAPTURE_META_CACHE.clear()

    # 歸零全域戰情數據
    reset_geo_perf_stats(GEO_PERF_STATS)

    if performance_mode:
        q.put(('log', "[PERF] Performance mode enabled: less log / fast scan / GEO fail summary"))

    if requires_single_source_without_time_grouping(organize_by_time, selected_folders):
        q.put(('msgbox', ("設定錯誤", "未啟用依年月整理時，來源與目的資料夾為 1:1，無法處理多個來源資料夾。"), 'warning', None))
        q.put(('reset', None))
        return

    # 🚀 執行前：搜尋原本來源目錄 (及父目錄) 與目的目錄，聯集載入歷史 _manifest_geo.json
    if enable_geo_lookup:
        load_and_merge_geo_caches(selected_folders, dest_dir, log_callback=lambda m: q.put(('log', m)))

    enable_geo_lookup = prepare_geo_runtime(enable_geo_lookup, q)

    valid_extensions = build_valid_extensions(
        copy_raw=copy_raw,
        copy_video=copy_video,
        standard_extensions=STANDARD_EXTENSIONS,
        raw_extensions=RAW_EXTENSIONS,
        video_extensions=VIDEO_EXTENSIONS,
    )
    files = collect_source_files(
        selected_folders=selected_folders,
        valid_extensions=valid_extensions,
        report_lines=report_lines,
        audit_manifest=audit_manifest,
        q=q,
        stop_event=stop_event,
        performance_mode=performance_mode,
        is_kairos_self_file=is_kairos_self_file,
    )

    scan_outcome = classify_scan_outcome(stop_event, files)
    if scan_outcome == "interrupted":
        q.put(('status', "🛑 Processing interrupted"))
        q.put(('reset', None))
        return

    total_files = len(files)
    if scan_outcome == "empty":
        q.put(('msgbox', ("提示", "所選目錄中找不到符合的媒體檔。"), 'info', None))
        q.put(('reset', None))
        return

    success_count = 0
    skipped_count = 0
    failed_count = 0
    start_time = time.time()
    processed_size_bytes = 0
    q.put(('status', f"First Pass | safe collection and dup-skip: 0 / {total_files} (0.0%)"))

    monthly_media_map = {}

    for i, file_path in enumerate(files):
        if stop_event.is_set(): break

        full_win_path = format_display_path(file_path)

        try: file_size = os.path.getsize(file_path)
        except OSError: file_size = 0

        # 用於記錄該檔案處理過程中的外掛異常訊息
        captured_warnings = []
        camera_model = "-"
        loc_name, map_url = "-", "-"

        try:
            ext = file_path.suffix.lower()
            stem = file_path.stem

            # 讀取相機型號同時攔截插件訊息
            if not performance_mode:
                with PluginWarningCapturer() as capturer:
                    camera_model = get_camera_model(file_path)
                captured_warnings.extend(capturer.get_messages())

            timestamp_base, _ = timestamp_parts(stem)
            clean_stem = timestamp_base or stem

            if timestamp_base:
                year, month = timestamp_base[:4], timestamp_base[5:7]
                target_name = f"{clean_stem}{ext}"
            else:
                if organize_by_time or normalize_name:
                    # 使用攔截器包覆 get_media_date
                    if performance_mode:
                        media_date = get_media_date(file_path)
                    else:
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
                    category = "video"
            else:
                month_key = "ALL_MEDIA"
                target_dir = dest_path / file_path.parent.relative_to(Path(selected_folders[0]).parent)
                category = "standard"
                if ext in RAW_EXTENSIONS: category = "raw"
                elif ext in VIDEO_EXTENSIONS: category = "video"

            # 去除重複的警告字句並以分號連接成單一行
            plugin_msg_str = " ; ".join(dict.fromkeys(captured_warnings)) if captured_warnings else PLACEHOLDER

            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / target_name

            effective_category = category
            is_duplicate_skip = False
            skip_reason = None

            # 取得正規化後的最終目標主檔名 (例如 "2017-10-15 17.38.59")
            target_stem = target_file.stem
            
            # 在進行衝突命名與 unique_path 前，先全面檢查該群組所有序號後綴是否存在實體相同檔案
            identical_match = find_identical_in_target(file_path, target_dir, target_stem, ext)

            if identical_match:
                is_duplicate_skip = True
                skip_reason = f"[Target existed] {identical_match.name}"
                target_file = identical_match

            elif target_file.exists():
                overwrite_photo_mode = overwrite and category == "standard" and ext in STANDARD_EXTENSIONS
                decision = compare_and_decide(file_path, target_file)

                if decision == "IDENTICAL":
                    is_duplicate_skip = True
                    skip_reason = f"[Target existed] {target_file.name}"

                elif overwrite_photo_mode and decision == "SAME_MS":
                    src_mtime = os.path.getmtime(file_path)
                    tgt_mtime = os.path.getmtime(target_file)
                    if src_mtime > tgt_mtime:
                        archived = candidate_path_for(target_dir, target_file.stem, ext)
                        invalidate_capture_meta(target_file)
                        invalidate_capture_meta(archived)
                        target_file.rename(archived)
                        if not performance_mode:
                            q.put(('log', f"[OVERWRITE] SAME_MS: archived previous to candidate -> {archived.name}"))
                    else:
                        target_file = candidate_path_for(target_dir, target_file.stem, ext)
                        effective_category = "candidate" if category == "standard" else category

                elif overwrite_photo_mode and decision == "BURST":
                    src_meta = get_capture_meta(file_path)
                    tgt_meta = get_capture_meta(target_file)
                    base_stem = timestamp_base or target_file.stem
                    src_ms = src_meta.get('subsec_ms')
                    tgt_ms = tgt_meta.get('subsec_ms')

                    if tgt_ms and target_file.stem == base_stem:
                        existing_burst_path = unique_path(target_dir, f"{base_stem}-{tgt_ms}", ext)
                        invalidate_capture_meta(target_file)
                        invalidate_capture_meta(existing_burst_path)
                        target_file.rename(existing_burst_path)
                        if not performance_mode:
                            q.put(('log', f"[OVERWRITE] BURST: renamed existing -> {existing_burst_path.name}"))

                    if src_ms:
                        target_file = unique_path(target_dir, f"{base_stem}-{src_ms}", ext)
                    else:
                        target_file = unique_indexed_path(target_dir, base_stem, ext, start=1)

                elif overwrite_photo_mode and decision == "REPLACE":
                    archived = candidate_path_for(target_dir, target_file.stem, ext)
                    invalidate_capture_meta(target_file)
                    invalidate_capture_meta(archived)
                    target_file.rename(archived)
                    if not performance_mode:
                        q.put(('log', f"[OVERWRITE] REPLACE: archived previous to candidate -> {archived.name}"))

                elif overwrite_photo_mode and decision == "KEEP":
                    target_file = candidate_path_for(target_dir, target_file.stem, ext)
                    effective_category = "candidate" if category == "standard" else category

                else:
                    target_file = unique_path(target_dir, target_file.stem, ext)

            if target_file.parent.name == 'candidate' and effective_category == "standard":
                effective_category = "candidate"

            if is_duplicate_skip:
                skipped_count += 1
                processed_size_bytes += file_size
                report_lines.append(f"[SKIP: IDENTICAL] {full_win_path} | REASON: {skip_reason}\n")
                audit_manifest.append([file_path.name, str(file_path), str(target_file), camera_model, ext, effective_category, "SKIP", skip_reason, plugin_msg_str])
                q.put(('metrics', processed_size_bytes))  # 直接丟總大小！
                q.put(('progress', (i + 1) / total_files))
                continue

            max_retries = 5
            for attempt in range(max_retries):
                try:
                    # 嚴格守則：只有在 Target 目錄執行複製與寫入，絕對不觸碰、不污染來源資料夾
                    shutil.copy2(file_path, target_file)
                    invalidate_capture_meta(target_file)

                    log_path = target_dir / "_process_log.txt"
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    with open(log_path, 'a', encoding='utf-8') as log_f:
                        log_f.write(f"[{timestamp}] Processed: {file_path.name} -> {target_file.name}\n")

                    if organize_by_time:
                        rel_p = target_file.relative_to(dest_path).as_posix()
                        if month_key not in monthly_media_map:
                            monthly_media_map[month_key] = []

                        if effective_category != "raw":
                            monthly_media_map[month_key].append({
                                'name': target_file.name,
                                'rel_path': rel_p,
                                'size': file_size,
                                'category': effective_category,
                                'loc_name': loc_name,
                                'map_url': map_url
                            })

                    audit_manifest.append([file_path.name, str(file_path), str(target_file), camera_model, ext, effective_category, "PASS", "COPY_OK", plugin_msg_str])
                    if not performance_mode:
                        q.put(('log', f"[{timestamp}] Processed: {file_path.name} -> {target_file.name}"))

                    # 若該檔案有外掛異常訊息，同步輸出在 UI 日誌提示
                    if not performance_mode and plugin_msg_str != "-":
                        q.put(('log', f"⚠️ [PLUGIN] {file_path.name}: {plugin_msg_str}"))

                    success_count += 1
                    break
                except (PermissionError, OSError) as e:
                    if attempt < max_retries - 1: time.sleep(0.5)
                    else: raise e

        except Exception as e:
            failed_count += 1
            plugin_msg_str = " ; ".join(dict.fromkeys(captured_warnings)) if captured_warnings else "-"
            report_lines.append(f"[FAIL] {full_win_path} | REASON: processing exception ({str(e)})\n")
            audit_manifest.append([file_path.name, str(file_path), PLACEHOLDER, camera_model, ext, PLACEHOLDER, "FAIL", f"ERROR: processing exception: {str(e)}", plugin_msg_str])
            q.put(('error_log', f"ERROR while processing {file_path.name}: {e}"))

        processed_size_bytes += file_size
        display_file_path = full_win_path if len(full_win_path) <= 65 else "..." + full_win_path[-62:]
        phase_elapsed = time.time() - start_time
        rate = (i + 1) / phase_elapsed if phase_elapsed > 0 else 0
        remaining = (total_files - i - 1) / rate if rate > 0 else 0
        q.put(('progress', (i + 1) / total_files))
        overall_remaining = remaining * 1.15  # 第二輪尚未取得實際群組數，先以保守係數估算。
        q.put(('status', f"First Pass | safe collection and duplicate-skip: {i + 1} / {total_files} ({(i + 1) / total_files:.1%}) | elapsed {format_time(phase_elapsed)} | phase remaining {format_time(remaining)} | overall ETA {format_time(overall_remaining)} | {display_file_path}"))
        q.put(('metrics', processed_size_bytes))  # 直接丟總大小！

    run_second_pass(
        dest_path=dest_path,
        organize_by_time=organize_by_time,
        overwrite=overwrite,
        stop_event=stop_event,
        q=q,
        processed_size_bytes=processed_size_bytes,
    )

    generated_html_reports = []
    index_report_path = None
    geo_stats = {'pass': 0, 'fail': 0, 'skip': 0}
    geo_fail_by_abs_path = {}
    geo_map_by_abs_path = {}
    if not stop_event.is_set():
        # 進行最終產出路徑掃描與「批量空間矩陣解析」
        monthly_media_map, geo_stats, geo_fail_by_abs_path, geo_map_by_abs_path, geo_fail_reason_counter = collect_media_records(
            dest_path, organize_by_time, enable_geo_lookup, q, stop_event, start_time, processed_size_bytes, performance_mode
        )

        # 處理完畢後：將更新後的地理空間快取字典封存回目標輸出目錄
        if enable_geo_lookup:
            save_geo_cache_to_dest(dest_dir, log_callback=lambda m: q.put(('log', m)))

        # 在生成 HTML 報表前，統計最終完成的執行時間與處理張數
        finalize_geo_perf_stats(start_time=start_time, copied=success_count, skipped=skipped_count, stats=GEO_PERF_STATS)

        q.put(('status', "Generating HTML preview reports from final file state..."))
        for m_key, records in monthly_media_map.items():
            generate_html_report(dest_path, m_key, records)
            generated_html_reports.append((m_key, dest_path / f"{m_key}_media_report.html"))

    index_report_path = export_audit_bundle(
        dest_path=dest_path,
        audit_manifest=audit_manifest,
        enable_geo_lookup=enable_geo_lookup,
        performance_mode=performance_mode,
        q=q,
        geo_stats=geo_stats,
        geo_fail_reason_counter=geo_fail_reason_counter,
        geo_fail_by_abs_path=geo_fail_by_abs_path,
        geo_map_by_abs_path=geo_map_by_abs_path,
    )

    report_msg_append = build_skiplist_append_message(dest_path, report_lines, skipped_count, failed_count)

    emit_completion_dialog(
        q=q,
        interrupted=stop_event.is_set(),
        success_count=success_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
        report_msg_append=report_msg_append,
        generated_html_reports=generated_html_reports,
        index_report_path=index_report_path,
    )

    q.put(('reset', None))

__all__ = ["is_kairos_self_file", "threaded_process_images"]
