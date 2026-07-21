"""Consistency verification workflow for manifest vs physical files."""

from __future__ import annotations

import json
import os
import time
import csv
from datetime import datetime
from pathlib import Path

try:
    from ..config.constants import RAW_EXTENSIONS, STANDARD_EXTENSIONS, VIDEO_EXTENSIONS
    from ..database.manifest_db import (
        MANIFEST_FILE_NAME,
        MANIFEST_TXN_LOG_FILE,
        write_manifest_audit_csv,
    )
    from ..reporting.index_builder import generate_file_type_summary, generate_manifest_html
    from ..utils.file_ops import file_sha256
    from ..utils.sys_helpers import format_display_path, format_time
except ImportError:  # pragma: no cover - direct script execution fallback
    from config.constants import RAW_EXTENSIONS, STANDARD_EXTENSIONS, VIDEO_EXTENSIONS
    from database.manifest_db import (
        MANIFEST_FILE_NAME,
        MANIFEST_TXN_LOG_FILE,
        write_manifest_audit_csv,
    )
    from reporting.index_builder import generate_file_type_summary, generate_manifest_html
    from utils.file_ops import file_sha256
    from utils.sys_helpers import format_display_path, format_time


SUPPORTED_MEDIA_EXTENSIONS = STANDARD_EXTENSIONS | RAW_EXTENSIONS | VIDEO_EXTENSIONS

ISSUE_TO_REASON_CODE = {
    "invalid_json": "REASON_INVALID_JSON",
    "invalid_lineages": "REASON_INVALID_LINEAGES",
    "duplicate_relative_paths": "REASON_DUPLICATE_RELATIVE_PATH",
    "malformed_records": "REASON_MALFORMED_RECORD",
    "missing_files": "REASON_MISSING_FILE",
    "extra_files": "REASON_EXTRA_FILE",
    "hash_mismatch": "REASON_HASH_MISMATCH",
    "stale_path_index": "REASON_STALE_PATH_INDEX",
    "stale_hash_index": "REASON_STALE_HASH_INDEX",
    "pending_transactions": "REASON_TXN_PENDING",
}

REASON_CODE_LABELS_ZH = {
    "REASON_INVALID_JSON": "manifest JSON 無法解析",
    "REASON_INVALID_LINEAGES": "lineages 結構異常",
    "REASON_DUPLICATE_RELATIVE_PATH": "relative_path 重複",
    "REASON_MALFORMED_RECORD": "record 欄位缺失或格式錯誤",
    "REASON_MISSING_FILE": "manifest 有記錄但實體檔不存在",
    "REASON_EXTRA_FILE": "實體檔存在但 manifest 未記錄",
    "REASON_HASH_MISMATCH": "SHA-256 不一致",
    "REASON_STALE_PATH_INDEX": "path_to_record 索引陳舊",
    "REASON_STALE_HASH_INDEX": "hash_to_record 索引陳舊",
    "REASON_TXN_PENDING": "交易紀錄有未完成交易",
}


def _norm_abs(path_value):
    return os.path.normcase(os.path.abspath(str(path_value)))


def _norm_rel(path_value):
    return str(path_value).replace("\\", "/").lower()


def _safe_json_load(path_obj):
    try:
        with open(path_obj, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _discover_scan_roots(selected_folders):
    roots = set()
    for folder in selected_folders:
        folder_path = Path(folder).resolve()
        roots.add(folder_path)
        roots.add(folder_path.parent)
    return sorted(roots, key=lambda p: str(p).lower())


def _discover_manifest_files(scan_roots):
    manifest_files = set()
    for root in scan_roots:
        if not root.exists() or not root.is_dir():
            continue
        direct = root / MANIFEST_FILE_NAME
        if direct.exists():
            manifest_files.add(direct.resolve())
        for path in root.rglob(MANIFEST_FILE_NAME):
            manifest_files.add(path.resolve())
    return sorted(manifest_files, key=lambda p: str(p).lower())


def _iter_media_files(folder_root):
    for path in folder_root.rglob("*"):
        if not path.is_file():
            continue
        if path.name.startswith("_"):
            continue
        if ".part." in path.name:
            continue
        if path.suffix.lower() not in SUPPORTED_MEDIA_EXTENSIONS:
            continue
        yield path


def _collect_manifest_records(payload):
    records_by_rel = {}
    duplicate_relative_paths = []
    malformed_records = []
    lineages = payload.get("lineages", {})
    if not isinstance(lineages, dict):
        return records_by_rel, duplicate_relative_paths, malformed_records, True

    for lineage_id, lineage_payload in lineages.items():
        if not isinstance(lineage_payload, dict):
            continue
        records = lineage_payload.get("records", {})
        if not isinstance(records, dict):
            continue
        for record_id, record in records.items():
            if not isinstance(record, dict):
                malformed_records.append(
                    {
                        "lineage_id": lineage_id,
                        "record_id": str(record_id),
                        "reason": "record payload is not object",
                    }
                )
                continue

            rel_path = record.get("relative_path") or record.get("current_name")
            if not rel_path:
                malformed_records.append(
                    {
                        "lineage_id": lineage_id,
                        "record_id": str(record_id),
                        "reason": "missing relative_path/current_name",
                    }
                )
                continue

            rel_norm = _norm_rel(rel_path)
            if rel_norm in records_by_rel:
                duplicate_relative_paths.append(
                    {
                        "relative_path": rel_path,
                        "record_id": str(record_id),
                        "existing_record_id": records_by_rel[rel_norm]["record_id"],
                    }
                )
                continue
            records_by_rel[rel_norm] = {
                "lineage_id": str(lineage_id),
                "record_id": str(record_id),
                "relative_path": str(rel_path).replace("\\", "/"),
                "sha256": str(record.get("sha256", "")).strip().lower(),
            }

    return records_by_rel, duplicate_relative_paths, malformed_records, False


def _analyze_txn_log(manifest_root):
    txn_path = manifest_root / MANIFEST_TXN_LOG_FILE
    if not txn_path.exists():
        return {"exists": False, "pending_count": 0}

    latest_by_tx = {}
    try:
        with open(txn_path, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    row = json.loads(raw)
                except Exception:
                    continue
                tx_id = str(row.get("tx_id", "")).strip()
                if not tx_id:
                    continue
                latest_by_tx[tx_id] = str(row.get("event", "")).upper()
    except Exception:
        return {"exists": True, "pending_count": 0}

    pending_count = sum(1 for event in latest_by_tx.values() if event not in {"COMMIT", "FAIL"})
    return {"exists": True, "pending_count": int(pending_count)}


def _build_audit_reason_counts(result):
    reason_counts = {}
    issues = result.get("issues", {})
    for issue_key, count in issues.items():
        count_int = int(count or 0)
        if count_int <= 0:
            continue
        reason_code = ISSUE_TO_REASON_CODE.get(issue_key, f"REASON_{str(issue_key).upper()}")
        reason_counts[reason_code] = reason_counts.get(reason_code, 0) + count_int

    pending_count = int(result.get("txn", {}).get("pending_count", 0) or 0)
    if pending_count > 0:
        reason_code = ISSUE_TO_REASON_CODE["pending_transactions"]
        reason_counts[reason_code] = reason_counts.get(reason_code, 0) + pending_count
    return reason_counts


def _attach_audit_status(result):
    reason_counts = _build_audit_reason_counts(result)
    status = "PASS" if not reason_counts else "FAIL"
    result["audit_status"] = status
    result["audit_reason_counts"] = reason_counts
    result["audit_reason_codes"] = sorted(reason_counts.keys())
    return result


def _build_audit_manifest_rows(payload):
    """Build rows aligned with `_manifest_audit.csv` schema."""
    rows = []
    manifests = payload.get("manifests", [])
    scan_roots = payload.get("scan_roots", [])
    joined_roots = " ; ".join(scan_roots) if scan_roots else "-"

    for manifest in manifests:
        manifest_path = str(manifest.get("manifest_path", "-"))
        reason_counts = manifest.get("audit_reason_counts", {})
        if reason_counts:
            reason_text = " ; ".join(
                f"{reason_code} x{count}"
                for reason_code, count in sorted(reason_counts.items(), key=lambda x: (-int(x[1]), x[0]))
            )
        else:
            reason_text = "CONSISTENT"
        counts = manifest.get("counts", {})
        pending = int(manifest.get("txn", {}).get("pending_count", 0) or 0)
        plugin_message = (
            f"records={counts.get('manifest_records', 0)}"
            f"; actual={counts.get('actual_media_files', 0)}"
            f"; hash_verified={counts.get('hash_verified', 0)}"
            f"; pending_txn={pending}"
        )
        rows.append(
            [
                Path(manifest_path).name or "_manifest_file.json",
                manifest_path,
                "-",
                "-",
                ".json",
                "consistency",
                manifest.get("audit_status", "FAIL"),
                reason_text,
                plugin_message,
            ]
        )

    audit_summary = payload.get("audit_summary", {})
    total_manifest_files = payload.get("summary", {}).get("total_manifest_files", len(manifests))
    for status_key in ("PASS", "SKIP", "FAIL"):
        count = int(audit_summary.get(status_key, 0) or 0)
        if count <= 0:
            continue
        rows.append(
            [
                f"__SUMMARY__{status_key}",
                joined_roots,
                "-",
                "-",
                ".summary",
                "consistency",
                status_key,
                f"MANIFEST_{status_key}={count}",
                f"manifest_total={total_manifest_files}",
            ]
        )

    reason_totals = audit_summary.get("reason_counts", {})
    for reason_code, count in sorted(reason_totals.items(), key=lambda x: (-int(x[1]), x[0])):
        rows.append(
            [
                f"__REASON__{reason_code}",
                joined_roots,
                "-",
                "-",
                ".summary",
                "consistency",
                "FAIL",
                f"{reason_code} x{count}",
                "consistency_reason_counter",
            ]
        )
    return rows


def _validate_manifest_file(manifest_path, stop_event):
    manifest_root = manifest_path.parent
    payload = _safe_json_load(manifest_path)
    if not isinstance(payload, dict):
        return {
            "manifest_path": str(manifest_path),
            "manifest_root": str(manifest_root),
            "valid": False,
            "issues": {"invalid_json": 1},
            "missing_files": [],
            "extra_files": [],
            "hash_mismatch": [],
            "stale_path_index": [],
            "stale_hash_index": [],
            "duplicate_relative_paths": [],
            "malformed_records": [],
            "counts": {
                "manifest_records": 0,
                "actual_media_files": 0,
                "hash_verified": 0,
            },
            "txn": _analyze_txn_log(manifest_root),
        }

    records_by_rel, duplicate_rel, malformed_records, invalid_lineages = _collect_manifest_records(payload)
    actual_by_rel = {}
    for path in _iter_media_files(manifest_root):
        if stop_event.is_set():
            break
        rel = path.relative_to(manifest_root).as_posix()
        actual_by_rel[_norm_rel(rel)] = path

    missing_files = []
    extra_files = []
    hash_mismatch = []
    hash_verified = 0

    if not stop_event.is_set():
        for rel_norm, rec in records_by_rel.items():
            actual_path = actual_by_rel.get(rel_norm)
            if actual_path is None:
                missing_files.append(rec["relative_path"])
                continue
            expected_sha = rec.get("sha256", "")
            if expected_sha:
                try:
                    actual_sha = file_sha256(actual_path).lower()
                except Exception:
                    actual_sha = ""
                if actual_sha != expected_sha:
                    hash_mismatch.append(
                        {
                            "relative_path": rec["relative_path"],
                            "expected_sha256": expected_sha,
                            "actual_sha256": actual_sha,
                        }
                    )
                hash_verified += 1

        manifest_rel_set = set(records_by_rel.keys())
        for rel_norm, actual_path in actual_by_rel.items():
            if rel_norm not in manifest_rel_set:
                extra_files.append(actual_path.relative_to(manifest_root).as_posix())

    stale_path_index = []
    stale_hash_index = []
    indexes = payload.get("indexes", {})
    if isinstance(indexes, dict):
        path_index = indexes.get("path_to_record", {})
        if isinstance(path_index, dict):
            for rel_path, ref in path_index.items():
                rel_norm = _norm_rel(rel_path)
                if rel_norm not in records_by_rel:
                    stale_path_index.append(str(rel_path))
                elif isinstance(ref, dict):
                    idx_record_id = str(ref.get("record_id", ""))
                    if idx_record_id and idx_record_id != records_by_rel[rel_norm]["record_id"]:
                        stale_path_index.append(str(rel_path))

        hash_index = indexes.get("hash_to_record", {})
        if isinstance(hash_index, dict):
            manifest_hashes = {rec["sha256"] for rec in records_by_rel.values() if rec.get("sha256")}
            for sha, ref in hash_index.items():
                sha_norm = str(sha).strip().lower()
                if sha_norm not in manifest_hashes:
                    stale_hash_index.append(sha_norm)
                elif isinstance(ref, dict):
                    idx_record_id = str(ref.get("record_id", ""))
                    if idx_record_id:
                        match = any(
                            rec.get("record_id") == idx_record_id and rec.get("sha256") == sha_norm
                            for rec in records_by_rel.values()
                        )
                        if not match:
                            stale_hash_index.append(sha_norm)

    issue_counter = {
        "invalid_lineages": 1 if invalid_lineages else 0,
        "duplicate_relative_paths": len(duplicate_rel),
        "malformed_records": len(malformed_records),
        "missing_files": len(missing_files),
        "extra_files": len(extra_files),
        "hash_mismatch": len(hash_mismatch),
        "stale_path_index": len(stale_path_index),
        "stale_hash_index": len(stale_hash_index),
    }
    valid = sum(issue_counter.values()) == 0

    return {
        "manifest_path": str(manifest_path),
        "manifest_root": str(manifest_root),
        "valid": valid,
        "issues": issue_counter,
        "missing_files": missing_files,
        "extra_files": extra_files,
        "hash_mismatch": hash_mismatch,
        "stale_path_index": stale_path_index,
        "stale_hash_index": stale_hash_index,
        "duplicate_relative_paths": duplicate_rel,
        "malformed_records": malformed_records,
        "counts": {
            "manifest_records": len(records_by_rel),
            "actual_media_files": len(actual_by_rel),
            "hash_verified": hash_verified,
        },
        "txn": _analyze_txn_log(manifest_root),
    }


def _resolve_report_dir(selected_folders):
    if not selected_folders:
        return Path.cwd()
    resolved = [str(Path(folder).resolve()) for folder in selected_folders]
    try:
        common_path = Path(os.path.commonpath(resolved))
        if common_path.exists() and common_path.is_dir():
            return common_path
    except Exception:
        pass
    first_parent = Path(selected_folders[0]).resolve().parent
    if first_parent.exists() and first_parent.is_dir():
        return first_parent
    return Path.cwd()


def _write_consistency_reports(report_dir, payload):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_json = report_dir / f"_manifest_consistency_{ts}.json"
    report_txt = report_dir / f"_manifest_consistency_{ts}.txt"
    report_csv = report_dir / f"_manifest_consistency_{ts}.csv"

    text_lines = []
    summary = payload.get("summary", {})
    audit_summary = payload.get("audit_summary", {})
    reason_totals = audit_summary.get("reason_counts", {})

    text_lines.append("Kairos 一致性驗證報告")
    text_lines.append(f"生成時間: {payload.get('generated_at', '-')}")
    text_lines.append(f"掃描根目錄數: {summary.get('scan_roots', 0)}")
    text_lines.append(f"Manifest 檔案數: {summary.get('manifest_files', 0)}")
    text_lines.append(
        f"PASS_MANIFEST: {audit_summary.get('PASS', 0)} | "
        f"SKIP_MANIFEST: {audit_summary.get('SKIP', 0)} | "
        f"FAIL_MANIFEST: {audit_summary.get('FAIL', 0)}"
    )
    text_lines.append(f"REASON_MISSING_FILE: {reason_totals.get('REASON_MISSING_FILE', 0)}")
    text_lines.append(f"REASON_EXTRA_FILE: {reason_totals.get('REASON_EXTRA_FILE', 0)}")
    text_lines.append(f"REASON_HASH_MISMATCH: {reason_totals.get('REASON_HASH_MISMATCH', 0)}")
    text_lines.append(f"REASON_STALE_PATH_INDEX: {reason_totals.get('REASON_STALE_PATH_INDEX', 0)}")
    text_lines.append(f"REASON_STALE_HASH_INDEX: {reason_totals.get('REASON_STALE_HASH_INDEX', 0)}")
    text_lines.append(f"REASON_TXN_PENDING: {reason_totals.get('REASON_TXN_PENDING', 0)}")

    if reason_totals:
        text_lines.append("")
        text_lines.append("原因詳細統計:")
        for reason_code, count in sorted(reason_totals.items(), key=lambda x: (-int(x[1]), x[0])):
            label = REASON_CODE_LABELS_ZH.get(reason_code, reason_code)
            text_lines.append(f"- {reason_code}: {count} ({label})")
    text_lines.append("")

    for manifest in payload.get("manifests", []):
        status = manifest.get("audit_status", "FAIL")
        text_lines.append(f"[{status}] {manifest.get('manifest_path')}")
        issues = manifest.get("issues", {})
        issue_total = sum(int(v) for v in issues.values())
        text_lines.append(
            f"  記錄數={manifest.get('counts', {}).get('manifest_records', 0)}"
            f" | issue_total={issue_total}"
        )
        reason_counts = manifest.get("audit_reason_counts", {})
        if reason_counts:
            for reason_code, count in sorted(reason_counts.items(), key=lambda x: (-int(x[1]), x[0])):
                label = REASON_CODE_LABELS_ZH.get(reason_code, reason_code)
                text_lines.append(f"  {reason_code}={count} ({label})")
        text_lines.append("")

    try:
        report_dir.mkdir(parents=True, exist_ok=True)
        with open(report_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        with open(report_txt, "w", encoding="utf-8") as f:
            f.write("\n".join(text_lines))
        with open(report_csv, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "manifest_path",
                    "audit_status",
                    "reason_codes",
                    "reason_total",
                    "manifest_records",
                    "actual_media_files",
                    "hash_verified",
                    "pending_transactions",
                ]
            )
            for manifest in payload.get("manifests", []):
                reason_counts = manifest.get("audit_reason_counts", {})
                reason_codes = ";".join(sorted(reason_counts.keys()))
                reason_total = sum(int(v) for v in reason_counts.values())
                counts = manifest.get("counts", {})
                writer.writerow(
                    [
                        manifest.get("manifest_path", ""),
                        manifest.get("audit_status", "FAIL"),
                        reason_codes,
                        reason_total,
                        counts.get("manifest_records", 0),
                        counts.get("actual_media_files", 0),
                        counts.get("hash_verified", 0),
                        manifest.get("txn", {}).get("pending_count", 0),
                    ]
                )
        try:
            audit_rows = _build_audit_manifest_rows(payload)
            if audit_rows:
                write_manifest_audit_csv(report_dir, audit_rows)
                generate_file_type_summary(report_dir, audit_rows)
                generate_manifest_html(report_dir, audit_rows)
        except Exception:
            # Keep consistency-report export resilient even if audit CSV projection fails.
            pass
    except Exception:
        return None
    return report_txt


def run_consistency_check(selected_folders, q, stop_event):
    """Run consistency verification in read-only mode (log only, no file output)."""
    start_time = time.time()
    roots = _discover_scan_roots(selected_folders)
    manifest_files = _discover_manifest_files(roots)
    total_manifest_count = len(manifest_files)

    q.put(("log", f"[CONSISTENCY][SCAN] roots={len(roots)} | manifests={total_manifest_count}"))

    results = []
    for idx, manifest_path in enumerate(manifest_files, start=1):
        if stop_event.is_set():
            break
        display_path = format_display_path(manifest_path)
        q.put(
            (
                "status",
                f"Consistency Check | {idx} / {max(total_manifest_count, 1)} "
                f"| {display_path}",
            )
        )
        result = _validate_manifest_file(manifest_path, stop_event)
        result = _attach_audit_status(result)
        results.append(result)
        q.put(("progress", idx / max(total_manifest_count, 1)))
        q.put(("metrics", (time.time() - start_time, 0)))

    pass_manifests = sum(1 for r in results if r.get("audit_status") == "PASS")
    fail_manifests = sum(1 for r in results if r.get("audit_status") == "FAIL")
    skip_manifests = max(total_manifest_count - len(results), 0)
    reason_totals = {}
    for result in results:
        for reason_code, count in result.get("audit_reason_counts", {}).items():
            reason_totals[reason_code] = reason_totals.get(reason_code, 0) + int(count)

    summary = {
        "scan_roots": len(roots),
        "manifest_files": len(results),
        "total_manifest_files": total_manifest_count,
        "clean_manifests": pass_manifests,  # backward compatible key
        "issue_manifests": fail_manifests,  # backward compatible key
        "pass_manifests": pass_manifests,
        "skip_manifests": skip_manifests,
        "fail_manifests": fail_manifests,
        "missing_files": sum(r.get("issues", {}).get("missing_files", 0) for r in results),
        "extra_files": sum(r.get("issues", {}).get("extra_files", 0) for r in results),
        "hash_mismatch": sum(r.get("issues", {}).get("hash_mismatch", 0) for r in results),
        "stale_path_index": sum(r.get("issues", {}).get("stale_path_index", 0) for r in results),
        "stale_hash_index": sum(r.get("issues", {}).get("stale_hash_index", 0) for r in results),
        "pending_transactions": sum(r.get("txn", {}).get("pending_count", 0) for r in results),
        "audit_reason_counts": reason_totals,
        "elapsed_seconds": round(time.time() - start_time, 2),
    }

    payload = {
        "schema": "kairos-consistency-audit-v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "selected_folders": [str(Path(p)) for p in selected_folders],
        "scan_roots": [str(p) for p in roots],
        "summary": summary,
        "audit_summary": {
            "PASS": pass_manifests,
            "SKIP": skip_manifests,
            "FAIL": fail_manifests,
            "reason_counts": reason_totals,
        },
        "manifests": results,
    }

    # Read-only consistency mode:
    # do NOT generate any report artifacts; only return payload for log summary.
    return payload, None, None


def threaded_verify_consistency(selected_folders, q, stop_event):
    """Thread worker entry: consistency mode without copy/move operations."""
    start_time = time.time()
    try:
        payload, report_path, index_report_path = run_consistency_check(selected_folders, q, stop_event)
        summary = payload.get("summary", {})
        audit_summary = payload.get("audit_summary", {})
        reason_totals = audit_summary.get("reason_counts", {})
        elapsed = format_time(time.time() - start_time)
        top_reasons = sorted(reason_totals.items(), key=lambda x: (-int(x[1]), x[0]))[:5]

        msg = (
            f"manifests={summary.get('manifest_files', 0)}/{summary.get('total_manifest_files', summary.get('manifest_files', 0))} | "
            f"pass={audit_summary.get('PASS', 0)} | "
            f"skip={audit_summary.get('SKIP', 0)} | "
            f"fail={audit_summary.get('FAIL', 0)} | "
            f"reason_missing_file={reason_totals.get('REASON_MISSING_FILE', 0)} | "
            f"reason_extra_file={reason_totals.get('REASON_EXTRA_FILE', 0)} | "
            f"reason_hash_mismatch={reason_totals.get('REASON_HASH_MISMATCH', 0)} | "
            f"elapsed={elapsed}"
        )
        if stop_event.is_set():
            q.put(("log", "[CONSISTENCY][STATUS] Interrupted"))
        else:
            q.put(("log", "[CONSISTENCY][STATUS] Completed"))
        q.put(("log", f"[CONSISTENCY][SUMMARY] {msg}"))
        if top_reasons:
            for reason_code, count in top_reasons:
                q.put(("log", f"[CONSISTENCY][TOP] {reason_code} x{count}"))
        else:
            q.put(("log", "[CONSISTENCY][TOP] none"))
        if report_path:
            q.put(("log", f"[CONSISTENCY][OUTPUT] Report: {format_display_path(report_path)}"))
        if index_report_path:
            q.put(("log", f"[CONSISTENCY][OUTPUT] Index: {format_display_path(index_report_path)}"))
    except Exception as e:
        q.put(("error_log", f"[CONSISTENCY][ERROR] {e}"))
        q.put(("log", f"[CONSISTENCY][STATUS] Failed: {e}"))
    finally:
        q.put(("reset", None))


__all__ = [
    "run_consistency_check",
    "threaded_verify_consistency",
]
