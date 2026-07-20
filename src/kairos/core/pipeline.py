"""Main workflow orchestration helpers."""

from __future__ import annotations

from pathlib import Path

try:
    from ..database.auditor import emit_completion_dialog
    from ..database.manifest_db import (
        build_skiplist_append_message,
        export_audit_bundle,
    )
    from .source_scan import collect_source_files
    from .first_pass import run_first_pass
    from .second_pass import run_second_pass
    from .final_phase import build_final_phase_outputs
    from .preflight import (
        build_valid_extensions,
        classify_scan_outcome,
        requires_single_source_without_time_grouping,
    )
    from ..config.constants import (
        RAW_EXTENSIONS,
        STANDARD_EXTENSIONS,
        VIDEO_EXTENSIONS,
    )
    from ..config.rules import is_kairos_self_file as _rule_is_kairos_self_file
    from ..metadata.arbiter import CAPTURE_META_CACHE
    from ..metadata.geo_engine import (
        GEO_PERF_STATS,
        load_and_merge_geo_caches,
        prepare_geo_runtime,
        reset_geo_perf_stats,
    )
except ImportError:  # pragma: no cover - direct script execution fallback
    from database.auditor import emit_completion_dialog
    from database.manifest_db import (
        build_skiplist_append_message,
        export_audit_bundle,
    )
    from core.source_scan import collect_source_files
    from core.first_pass import run_first_pass
    from core.second_pass import run_second_pass
    from core.final_phase import build_final_phase_outputs
    from core.preflight import (
        build_valid_extensions,
        classify_scan_outcome,
        requires_single_source_without_time_grouping,
    )
    from config.constants import (
        RAW_EXTENSIONS,
        STANDARD_EXTENSIONS,
        VIDEO_EXTENSIONS,
    )
    from config.rules import is_kairos_self_file as _rule_is_kairos_self_file
    from metadata.arbiter import CAPTURE_META_CACHE
    from metadata.geo_engine import (
        GEO_PERF_STATS,
        load_and_merge_geo_caches,
        prepare_geo_runtime,
        reset_geo_perf_stats,
    )

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

    (
        success_count,
        skipped_count,
        failed_count,
        start_time,
        processed_size_bytes,
        monthly_media_map,
    ) = run_first_pass(
        files=files,
        selected_folders=selected_folders,
        dest_path=dest_path,
        organize_by_time=organize_by_time,
        normalize_name=normalize_name,
        overwrite=overwrite,
        performance_mode=performance_mode,
        q=q,
        stop_event=stop_event,
        report_lines=report_lines,
        audit_manifest=audit_manifest,
    )

    run_second_pass(
        dest_path=dest_path,
        organize_by_time=organize_by_time,
        overwrite=overwrite,
        stop_event=stop_event,
        q=q,
        processed_size_bytes=processed_size_bytes,
    )

    (
        generated_html_reports,
        geo_stats,
        geo_fail_by_abs_path,
        geo_map_by_abs_path,
        geo_fail_reason_counter,
    ) = build_final_phase_outputs(
        dest_path=dest_path,
        dest_dir=dest_dir,
        organize_by_time=organize_by_time,
        enable_geo_lookup=enable_geo_lookup,
        q=q,
        stop_event=stop_event,
        start_time=start_time,
        processed_size_bytes=processed_size_bytes,
        performance_mode=performance_mode,
        success_count=success_count,
        skipped_count=skipped_count,
    )
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
