"""Root index report helpers."""

from __future__ import annotations

import html
from collections import Counter
from datetime import datetime
from pathlib import Path


def destination_extension_counts(dest_path):
    excluded = {
        "_index.html",
        "_manifest_audit.csv",
        "_manifest_skiplist.txt",
        "_manifest_filetype.html",
    }
    return Counter(
        p.suffix.lower() or "[no_ext]"
        for p in dest_path.rglob("*")
        if p.is_file()
        and p.name not in excluded
        and not p.name.startswith("_process_log")
        and not p.name.endswith("_media_report.html")
    )


def generate_file_type_summary(output_root_dir, audit_manifest):
    source = Counter(row[4].lower() or "[no_ext]" for row in audit_manifest)
    copied = Counter(row[4].lower() or "[no_ext]" for row in audit_manifest if row[6] == "PASS")
    skipped = Counter(row[4].lower() or "[no_ext]" for row in audit_manifest if row[6] == "SKIP")
    failed = Counter(row[4].lower() or "[no_ext]" for row in audit_manifest if row[6] == "FAIL")
    destination = destination_extension_counts(Path(output_root_dir))
    extensions = sorted(set(source) | set(destination))
    rows = "".join(
        f"<tr><td>{html.escape(ext)}</td><td>{source[ext]:,}</td><td>{copied[ext]:,}</td><td>{skipped[ext]:,}</td><td>{failed[ext]:,}</td><td>{destination[ext]:,}</td></tr>"
        for ext in extensions
    )
    generated_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"""<!doctype html><html lang="zh-TW"><meta charset="utf-8"><title>File Type Summary</title>
    <style>body{{font-family:Segoe UI,sans-serif;margin:24px;color:#2c3e50}}table{{border-collapse:collapse;width:100%;max-width:900px}}th,td{{padding:9px 12px;border:1px solid #dfe6e9;text-align:right}}th:first-child,td:first-child{{text-align:left}}th{{background:#eef2f3}}</style>
    <h1>File Type Summary <span style="color:#95A5A6;font-size:13px;font-weight:normal;">(Generated : {generated_ts})</span></h1><p>Compare source scan and destination counts to quickly validate file-type migration consistency.</p>
    <table><tr><th>Ext</th><th>Scanned</th><th>PASS</th><th>SKIP</th><th>FAIL</th><th>Dest Count</th></tr>{rows}</table></html>"""
    with open(Path(output_root_dir) / "_manifest_filetype.html", "w", encoding="utf-8") as f:
        f.write(content)


__all__ = ["destination_extension_counts", "generate_file_type_summary"]
