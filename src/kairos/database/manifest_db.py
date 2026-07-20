"""Manifest and report export helpers."""

from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path

try:
    from ..config.constants import PLACEHOLDER
    from ..reporting.index_builder import generate_file_type_summary, generate_manifest_html
    from ..utils.sys_helpers import format_display_path
except ImportError:  # pragma: no cover - direct script execution fallback
    from config.constants import PLACEHOLDER
    from reporting.index_builder import generate_file_type_summary, generate_manifest_html
    from utils.sys_helpers import format_display_path


def merge_geo_audit_columns(
    audit_manifest,
    enable_geo_lookup,
    performance_mode,
    q,
    geo_stats,
    geo_fail_reason_counter,
    geo_fail_by_abs_path,
    geo_map_by_abs_path,
):
    """Mutate audit rows with GEO url/error metadata and emit optional logs."""
    if not enable_geo_lookup:
        return
    q.put(
        (
            "log",
            f"🛰️ GEO stats | PASS: {geo_stats.get('pass', 0)} | FAIL: {geo_stats.get('fail', 0)} | SKIP: {geo_stats.get('skip', 0)}",
        )
    )
    if performance_mode and geo_fail_reason_counter:
        summary_parts = [f"{reason} x{count}" for reason, count in geo_fail_reason_counter.most_common(5)]
        q.put(("log", f"[GEO] FAIL summary: {' | '.join(summary_parts)}"))
    for row in audit_manifest:
        if len(row) < 10:
            row.append(PLACEHOLDER)
        target_path = row[2]
        if target_path == PLACEHOLDER:
            continue
        geo_key = os.path.normcase(os.path.abspath(str(target_path)))
        geo_reason = geo_fail_by_abs_path.get(geo_key)
        if not geo_reason:
            geo_url = geo_map_by_abs_path.get(geo_key)
            if geo_url:
                row[9] = geo_url
            continue
        geo_msg = f"[GEO] {geo_reason}"
        row[8] = geo_msg if row[8] == PLACEHOLDER else f"{row[8]} ; {geo_msg}"
        geo_url = geo_map_by_abs_path.get(geo_key)
        if geo_url:
            row[9] = geo_url


def write_manifest_audit_csv(dest_path, audit_manifest):
    """Write `_manifest_audit.csv` and return the file path."""
    manifest_path = Path(dest_path) / "_manifest_audit.csv"
    with open(manifest_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        has_geo_column = any(len(row) > 9 for row in audit_manifest)
        header = [
            "檔案名稱",
            "來源檔案完整路徑",
            "目的地檔案完整路徑",
            "相機型號",
            "副檔名",
            "檔案類型",
            "處理結果",
            "跳過/失敗原因",
            "插件警告訊息",
        ]
        if has_geo_column:
            header.append("地圖")
        writer.writerow(header)
        writer.writerows(
            [
                [
                    row[0],
                    format_display_path(row[1]) if row[1] != PLACEHOLDER else PLACEHOLDER,
                    format_display_path(row[2]) if row[2] != PLACEHOLDER else PLACEHOLDER,
                    *(row[3:] if has_geo_column else row[3:9]),
                ]
                for row in audit_manifest
            ]
        )
    return manifest_path


def export_index_reports(dest_path, audit_manifest, q):
    """Export CSV + file-type summary + index HTML and return index path."""
    manifest_path = write_manifest_audit_csv(dest_path, audit_manifest)
    q.put(("log", f"✅ CSV report exported: {manifest_path.name}"))

    generate_file_type_summary(dest_path, audit_manifest)
    generate_manifest_html(dest_path, audit_manifest)
    index_report_path = Path(dest_path) / "_index.html"
    q.put(("log", "✅ HTML report exported: _index.html"))
    return index_report_path


def write_skiplist_report(dest_path, report_lines, skipped_count, failed_count):
    """Write `_manifest_skiplist.txt` and return the user-facing suffix message."""
    report_file_path = Path(dest_path) / "_manifest_skiplist.txt"
    with open(report_file_path, "w", encoding="utf-8") as f:
        f.write(f"=== 媒體整理跳過/錯誤報告 (產生時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===\n")
        f.write(f"TOTAL SKIP: {skipped_count} | TOTAL FAIL: {failed_count}\n")
        f.write("=" * 80 + "\n")
        f.writelines(report_lines)
    return "\n\n📄 報表已輸出至output根目錄:\n_manifest_skiplist.txt\n_manifest_audit.csv\n_index.html"


def build_skiplist_append_message(dest_path, report_lines, skipped_count, failed_count):
    """Return report suffix message while keeping pipeline flow resilient."""
    if not report_lines:
        return ""
    try:
        return write_skiplist_report(dest_path, report_lines, skipped_count, failed_count)
    except Exception:
        return ""


__all__ = [
    "merge_geo_audit_columns",
    "write_manifest_audit_csv",
    "export_index_reports",
    "write_skiplist_report",
    "build_skiplist_append_message",
]
