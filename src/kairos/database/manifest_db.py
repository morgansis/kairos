"""Manifest persistence and report export helpers."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    from ..config.constants import (
        PLACEHOLDER,
        RAW_EXTENSIONS,
        STANDARD_EXTENSIONS,
        VIDEO_EXTENSIONS,
    )
    from ..metadata.arbiter import get_capture_meta
    from ..metadata.exif_parser import get_camera_model, get_media_date_with_source
    from ..reporting.index_builder import generate_file_type_summary, generate_manifest_html
    from ..utils.file_ops import file_sha256, timestamp_parts
    from ..utils.sys_helpers import format_display_path
except ImportError:  # pragma: no cover - direct script execution fallback
    from config.constants import (
        PLACEHOLDER,
        RAW_EXTENSIONS,
        STANDARD_EXTENSIONS,
        VIDEO_EXTENSIONS,
    )
    from metadata.arbiter import get_capture_meta
    from metadata.exif_parser import get_camera_model, get_media_date_with_source
    from reporting.index_builder import generate_file_type_summary, generate_manifest_html
    from utils.file_ops import file_sha256, timestamp_parts
    from utils.sys_helpers import format_display_path


MANIFEST_FILE_NAME = "_manifest_file.json"
MANIFEST_VERSION = "1.0"
MANIFEST_TXN_LOG_FILE = "_manifest_txn.jsonl"
MONTH_DIR_RE = re.compile(r"\d{4}_\d{2}")
TIMESTAMP_STEM_FORMAT = "%Y-%m-%d %H.%M.%S"
TIMESTAMP_DISPLAY_FORMAT = "%Y-%m-%d %H:%M:%S"


def _norm_abs(path_value):
    return os.path.normcase(os.path.abspath(str(path_value)))


def _normalize_rel_path(path_value):
    return str(path_value).replace("\\", "/").lower()


def _slug(text, max_len=24):
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in str(text or "").strip().upper())
    cleaned = cleaned.strip("_")
    return (cleaned or "UNKNOWN")[:max_len]


def _capture_slot_key(capture_datetime_original, capture_subsec_ms, device_fingerprint):
    return (
        str(capture_datetime_original).strip(),
        str(capture_subsec_ms).zfill(3)[:3],
        str(device_fingerprint).strip(),
    )


def _safe_json_load(path_obj):
    try:
        with open(path_obj, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _is_relative_to(path_obj, root_obj):
    try:
        path_obj.resolve().relative_to(root_obj.resolve())
        return True
    except Exception:
        return False


def _append_manifest_txn_event(dest_path, event_payload):
    try:
        log_path = Path(dest_path) / MANIFEST_TXN_LOG_FILE
        event = dict(event_payload or {})
        event.setdefault("ts", datetime.now().isoformat(timespec="seconds"))
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        return


def begin_manifest_transaction(dest_path, tx_id, src_path, target_path, part_path):
    _append_manifest_txn_event(
        dest_path,
        {
            "event": "BEGIN",
            "tx_id": str(tx_id),
            "src_path": str(src_path),
            "target_path": str(target_path),
            "part_path": str(part_path),
        },
    )


def commit_manifest_transaction(dest_path, tx_id, sha256_value, size_bytes=0):
    _append_manifest_txn_event(
        dest_path,
        {
            "event": "COMMIT",
            "tx_id": str(tx_id),
            "sha256": str(sha256_value).lower(),
            "size_bytes": int(size_bytes or 0),
        },
    )


def fail_manifest_transaction(dest_path, tx_id, reason):
    _append_manifest_txn_event(
        dest_path,
        {
            "event": "FAIL",
            "tx_id": str(tx_id),
            "reason": str(reason),
        },
    )


def recover_manifest_transactions(dest_path, log_callback=None):
    """Recover unfinished copy transactions by cleaning stale part files."""
    dest_root = Path(dest_path)
    log_path = dest_root / MANIFEST_TXN_LOG_FILE
    if not log_path.exists():
        return {"pending": 0, "cleaned_part": 0, "orphan_final": 0}

    latest_event_by_tx = {}
    begin_by_tx = {}
    try:
        with open(log_path, "r", encoding="utf-8") as f:
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
                event = str(row.get("event", "")).strip().upper()
                latest_event_by_tx[tx_id] = event
                if event == "BEGIN":
                    begin_by_tx[tx_id] = row
    except Exception:
        return {"pending": 0, "cleaned_part": 0, "orphan_final": 0}

    pending = 0
    cleaned_part = 0
    orphan_final = 0
    for tx_id, event in latest_event_by_tx.items():
        if event in {"COMMIT", "FAIL"}:
            continue
        begin_row = begin_by_tx.get(tx_id, {})
        pending += 1
        part_path = Path(begin_row.get("part_path", "")) if begin_row.get("part_path") else None
        target_path = Path(begin_row.get("target_path", "")) if begin_row.get("target_path") else None

        if part_path and _is_relative_to(part_path, dest_root) and part_path.exists():
            try:
                part_path.unlink()
                cleaned_part += 1
            except Exception:
                pass
        elif target_path and _is_relative_to(target_path, dest_root) and target_path.exists():
            orphan_final += 1

    if log_callback and (pending or cleaned_part or orphan_final):
        log_callback(
            "[MANIFEST][RECOVERY] "
            f"pending={pending} | cleaned_part={cleaned_part} | orphan_final={orphan_final}"
        )

    return {"pending": pending, "cleaned_part": cleaned_part, "orphan_final": orphan_final}


def _discover_manifest_files(source_folders, dest_dir):
    roots = {Path(dest_dir)}
    for folder in source_folders:
        src = Path(folder)
        roots.add(src)
        roots.add(src.parent)

    manifests = set()
    for root in roots:
        if not root.exists():
            continue
        direct = root / MANIFEST_FILE_NAME
        if direct.exists():
            manifests.add(direct)
        for p in root.rglob(MANIFEST_FILE_NAME):
            manifests.add(p)
    return sorted(manifests)


def load_and_merge_manifest_indexes(source_folders, dest_dir, log_callback=None):
    """Load historical manifests and build lookup indexes for inheritance."""
    if log_callback:
        log_callback("[MANIFEST] Build lookup index from historical manifest files...")

    manifest_files = _discover_manifest_files(source_folders, dest_dir)
    indexes = {"hash": {}, "path": {}, "lineage": {}, "capture": {}}
    loaded = 0

    for manifest_path in manifest_files:
        payload = _safe_json_load(manifest_path)
        if not isinstance(payload, dict):
            continue
        lineages = payload.get("lineages", {})
        if not isinstance(lineages, dict):
            continue

        for lineage_id, lineage_payload in lineages.items():
            if not isinstance(lineage_payload, dict):
                continue
            records = lineage_payload.get("records", {})
            if not isinstance(records, dict):
                continue

            lineage_stub = {
                "lineage_id": lineage_id,
                "capture_datetime_original": lineage_payload.get("capture_datetime_original", ""),
                "capture_subsec_ms": lineage_payload.get("capture_subsec_ms", "000"),
                "orig_name_first_seen": lineage_payload.get("orig_name_first_seen", ""),
                "device_fingerprint": lineage_payload.get("device_fingerprint", "UNKNOWN"),
                "bundle_id": lineage_payload.get("bundle_id", ""),
                "display_meta": lineage_payload.get("display_meta", {}),
                "raw_meta": lineage_payload.get("raw_meta", {}),
            }
            indexes["lineage"].setdefault(lineage_id, lineage_stub)
            capture_key = _capture_slot_key(
                lineage_stub["capture_datetime_original"],
                lineage_stub["capture_subsec_ms"],
                lineage_stub["device_fingerprint"],
            )
            indexes["capture"].setdefault(capture_key, lineage_id)

            for record_id, record in records.items():
                if not isinstance(record, dict):
                    continue
                info = {
                    "lineage_id": lineage_id,
                    "lineage": lineage_stub,
                    "record_id": record_id,
                    "record": record,
                }

                sha = str(record.get("sha256", "")).strip().lower()
                if sha and sha not in indexes["hash"]:
                    indexes["hash"][sha] = info

                rel_path = record.get("relative_path") or record.get("current_name")
                if rel_path:
                    rel_key = _normalize_rel_path(rel_path)
                    if rel_key not in indexes["path"]:
                        indexes["path"][rel_key] = info

        loaded += 1

    if log_callback:
        hash_count = len(indexes["hash"])
        path_count = len(indexes["path"])
        capture_count = len(indexes["capture"])
        if loaded == 0:
            log_callback(
                "[MANIFEST] Build lookup index: done "
                "(no historical manifest file found; will index from current run)."
            )
        else:
            log_callback(
                "[MANIFEST] Build lookup index: done "
                f"({loaded} manifest files loaded, {hash_count} hash entries, "
                f"{path_count} path entries, {capture_count} capture slots)."
            )
    return indexes


def _iter_manifest_roots(dest_path, organize_by_time):
    if not organize_by_time:
        return [dest_path]
    return sorted([p for p in dest_path.iterdir() if p.is_dir() and MONTH_DIR_RE.fullmatch(p.name)])


def _iter_media_files(folder_root):
    supported = STANDARD_EXTENSIONS | RAW_EXTENSIONS | VIDEO_EXTENSIONS
    files = []
    for path in folder_root.rglob("*"):
        if not path.is_file():
            continue
        if path.name.startswith("_"):
            continue
        ext = path.suffix.lower()
        if ext not in supported:
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.relative_to(folder_root).as_posix().lower())


def _classify_media_category(path_obj):
    ext = path_obj.suffix.lower()
    if ext in RAW_EXTENSIONS:
        return "raw"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if "candidate" in path_obj.parts:
        return "candidate"
    return "standard"


def _capture_datetime_from_filename(path_obj):
    base, _suffix = timestamp_parts(path_obj.stem)
    if not base:
        return None
    try:
        return datetime.strptime(base, TIMESTAMP_STEM_FORMAT)
    except Exception:
        return None


def _build_record_id(sha256_value):
    return f"rec_v1_{str(sha256_value).lower()[:32]}"


def _build_lineage_id(capture_dt, subsec_ms, device_fingerprint, sequence):
    capture_compact = capture_dt.strftime("%Y%m%dT%H%M%S")
    device_short = _slug(device_fingerprint, max_len=18)
    return f"lin_v1_{capture_compact}_{subsec_ms}_{device_short}_{int(sequence):02d}"


def _build_bundle_id(capture_dt, subsec_ms, device_fingerprint, stem):
    capture_compact = capture_dt.strftime("%Y%m%dT%H%M%S")
    if str(subsec_ms) != "000":
        basis = f"{capture_compact}|{subsec_ms}|{device_fingerprint}"
    else:
        basis = f"{capture_compact}|{device_fingerprint}|{str(stem).lower()}"
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:20]
    return f"bun_v1_{digest}"


def _ensure_lineage(lineages, lineage_id, capture_dt_text, subsec_ms, orig_name, device_fingerprint, bundle_id):
    lineage = lineages.get(lineage_id)
    if lineage is None:
        lineage = {
            "lineage_id": lineage_id,
            "capture_datetime_original": capture_dt_text,
            "capture_subsec_ms": subsec_ms,
            "orig_name_first_seen": orig_name,
            "device_fingerprint": device_fingerprint,
            "bundle_id": bundle_id,
            "display_meta": {},
            "raw_meta": {},
            "records": {},
        }
        lineages[lineage_id] = lineage
        return lineage

    if not lineage.get("orig_name_first_seen"):
        lineage["orig_name_first_seen"] = orig_name
    if not lineage.get("bundle_id"):
        lineage["bundle_id"] = bundle_id
    return lineage


def _parse_capture_datetime_text(capture_text, path_obj):
    capture_text = str(capture_text or "").strip()
    if capture_text:
        try:
            capture_dt = datetime.strptime(capture_text, TIMESTAMP_DISPLAY_FORMAT)
            return capture_dt, capture_text
        except Exception:
            pass
    capture_dt = datetime.fromtimestamp(path_obj.stat().st_mtime)
    return capture_dt, capture_dt.strftime(TIMESTAMP_DISPLAY_FORMAT)


def _cached_sha_from_path_index(path_obj, path_index_info):
    """Reuse historical SHA only if mtime+size match."""
    if not path_index_info:
        return ""
    record = path_index_info.get("record", {})
    sha = str(record.get("sha256", "")).strip().lower()
    if not sha:
        return ""
    try:
        stat_info = path_obj.stat()
    except Exception:
        return ""
    raw_meta = record.get("raw_meta", {}) if isinstance(record.get("raw_meta"), dict) else {}
    cached_size = raw_meta.get("filesize")
    cached_mtime = str(raw_meta.get("mtime", ""))
    actual_mtime = datetime.fromtimestamp(stat_info.st_mtime).isoformat(timespec="seconds")
    try:
        if int(cached_size) != int(stat_info.st_size):
            return ""
    except Exception:
        return ""
    if cached_mtime != actual_mtime:
        return ""
    return sha


def _resolve_media_identity(path_obj, inherited_info=None, known_record=None):
    if inherited_info:
        lineage = inherited_info.get("lineage", {})
        capture_dt, capture_text = _parse_capture_datetime_text(
            lineage.get("capture_datetime_original", ""),
            path_obj,
        )

        return {
            "lineage_id": lineage.get("lineage_id", ""),
            "capture_dt": capture_dt,
            "capture_datetime_original": capture_text,
            "capture_subsec_ms": str(lineage.get("capture_subsec_ms", "000")).zfill(3)[:3],
            "orig_name_first_seen": lineage.get("orig_name_first_seen") or path_obj.name,
            "device_fingerprint": lineage.get("device_fingerprint") or "UNKNOWN",
            "bundle_id": lineage.get("bundle_id", ""),
            "meta_source": "inherited",
            "camera_model": lineage.get("display_meta", {}).get("camera_model", "-"),
            "serial": lineage.get("raw_meta", {}).get("serial", PLACEHOLDER),
        }

    if known_record:
        capture_dt, capture_text = _parse_capture_datetime_text(
            known_record.get("capture_datetime_original", ""),
            path_obj,
        )
        camera_model = known_record.get("camera_model", "-")
        serial = known_record.get("serial", PLACEHOLDER)
        subsec_ms = str(known_record.get("capture_subsec_ms", "000")).zfill(3)[:3]
        device_fingerprint = known_record.get("device_fingerprint") or (
            f"{_slug(camera_model, max_len=18)}|{_slug(serial, max_len=12)}"
        )
        bundle_id = known_record.get("bundle_id") or _build_bundle_id(
            capture_dt,
            subsec_ms,
            device_fingerprint,
            path_obj.stem,
        )
        return {
            "lineage_id": "",
            "capture_dt": capture_dt,
            "capture_datetime_original": capture_text,
            "capture_subsec_ms": subsec_ms,
            "orig_name_first_seen": known_record.get("orig_name_first_seen") or path_obj.name,
            "device_fingerprint": device_fingerprint,
            "bundle_id": bundle_id,
            "meta_source": known_record.get("meta_source", "mtime"),
            "camera_model": camera_model,
            "serial": serial,
        }

    filename_dt = _capture_datetime_from_filename(path_obj)
    if filename_dt is not None:
        capture_dt = filename_dt
        dt_source = "filename"
    else:
        capture_dt, dt_source = get_media_date_with_source(path_obj)

    capture_meta = get_capture_meta(path_obj)
    subsec_ms = capture_meta.get("subsec_ms") or "000"
    subsec_ms = str(subsec_ms).zfill(3)[:3]
    serial = capture_meta.get("serial", PLACEHOLDER)
    camera_model = get_camera_model(path_obj)
    device_fingerprint = f"{_slug(camera_model, max_len=18)}|{_slug(serial, max_len=12)}"
    bundle_id = _build_bundle_id(capture_dt, subsec_ms, device_fingerprint, path_obj.stem)

    return {
        "lineage_id": "",
        "capture_dt": capture_dt,
        "capture_datetime_original": capture_dt.strftime(TIMESTAMP_DISPLAY_FORMAT),
        "capture_subsec_ms": subsec_ms,
        "orig_name_first_seen": path_obj.name,
        "device_fingerprint": device_fingerprint,
        "bundle_id": bundle_id,
        "meta_source": dt_source,
        "camera_model": camera_model,
        "serial": serial,
    }


def rebuild_folder_manifests(
    dest_path,
    organize_by_time,
    inherited_indexes=None,
    known_records=None,
    log_callback=None,
):
    """Rebuild per-folder manifest files and return record lookup for reporting."""
    if log_callback:
        log_callback("[MANIFEST] Rebuild per-folder _manifest_file.json from output media...")

    if inherited_indexes is None:
        inherited_indexes = {"hash": {}, "path": {}, "lineage": {}, "capture": {}}
    if known_records is None:
        known_records = {}

    roots = _iter_manifest_roots(Path(dest_path), organize_by_time)
    record_lookup = {}
    written_count = 0

    for root in roots:
        files = _iter_media_files(root)
        lineages = {}
        slot_counts = defaultdict(int)
        capture_to_lineage = {}
        hash_to_record = {}
        path_to_record = {}
        bundle_to_raw_paths = defaultdict(list)

        for path_obj in files:
            rel_path = path_obj.relative_to(root).as_posix()
            rel_key = _normalize_rel_path(rel_path)
            abs_key = _norm_abs(path_obj)
            known_record = known_records.get(abs_key, {})
            path_inherited = inherited_indexes.get("path", {}).get(rel_key)

            sha = str(known_record.get("sha256", "")).strip().lower()
            if not sha:
                sha = _cached_sha_from_path_index(path_obj, path_inherited)
            if not sha:
                try:
                    sha = file_sha256(path_obj)
                except Exception:
                    continue
            sha = str(sha).lower()
            record_id = _build_record_id(sha)

            inherited = inherited_indexes.get("hash", {}).get(sha) or path_inherited
            identity = _resolve_media_identity(path_obj, inherited, known_record=known_record)

            lineage_id = identity.get("lineage_id", "")
            capture_key = _capture_slot_key(
                identity["capture_datetime_original"],
                identity["capture_subsec_ms"],
                identity["device_fingerprint"],
            )
            if not lineage_id:
                lineage_id = (
                    inherited_indexes.get("capture", {}).get(capture_key)
                    or capture_to_lineage.get(capture_key, "")
                )
                if not lineage_id:
                    slot_counts[capture_key] += 1
                    lineage_id = _build_lineage_id(
                        identity["capture_dt"],
                        identity["capture_subsec_ms"],
                        identity["device_fingerprint"],
                        slot_counts[capture_key],
                    )

            inherited_lineage = inherited_indexes.get("lineage", {}).get(lineage_id)
            if inherited_lineage:
                identity["capture_datetime_original"] = (
                    inherited_lineage.get("capture_datetime_original") or identity["capture_datetime_original"]
                )
                identity["capture_subsec_ms"] = (
                    str(inherited_lineage.get("capture_subsec_ms", identity["capture_subsec_ms"])).zfill(3)[:3]
                )
                identity["device_fingerprint"] = (
                    inherited_lineage.get("device_fingerprint") or identity["device_fingerprint"]
                )
                identity["orig_name_first_seen"] = (
                    inherited_lineage.get("orig_name_first_seen") or identity["orig_name_first_seen"]
                )
                identity["bundle_id"] = inherited_lineage.get("bundle_id") or identity["bundle_id"]
                if identity.get("meta_source") != "inherited":
                    identity["meta_source"] = "inherited_capture"
                capture_key = _capture_slot_key(
                    identity["capture_datetime_original"],
                    identity["capture_subsec_ms"],
                    identity["device_fingerprint"],
                )

            capture_to_lineage[capture_key] = lineage_id

            category = _classify_media_category(path_obj)
            lineage = _ensure_lineage(
                lineages=lineages,
                lineage_id=lineage_id,
                capture_dt_text=identity["capture_datetime_original"],
                subsec_ms=identity["capture_subsec_ms"],
                orig_name=identity["orig_name_first_seen"],
                device_fingerprint=identity["device_fingerprint"],
                bundle_id=identity["bundle_id"],
            )

            lineage["display_meta"] = {
                "camera_model": identity.get("camera_model", "-"),
                "capture_datetime": identity["capture_datetime_original"],
                "capture_subsec_ms": identity["capture_subsec_ms"],
            }
            lineage["raw_meta"] = {
                "serial": identity.get("serial", PLACEHOLDER),
                "meta_source": identity.get("meta_source", "mtime"),
            }
            try:
                stat_info = path_obj.stat()
                file_size = int(known_record.get("filesize", stat_info.st_size))
                file_mtime = str(
                    known_record.get(
                        "mtime_iso",
                        datetime.fromtimestamp(stat_info.st_mtime).isoformat(timespec="seconds"),
                    )
                )
            except Exception:
                file_size = int(known_record.get("filesize", 0))
                file_mtime = str(known_record.get("mtime_iso", ""))

            record_payload = {
                "record_id": record_id,
                "sha256": sha,
                "current_name": path_obj.name,
                "relative_path": rel_path,
                "ext": path_obj.suffix.lower(),
                "category": category,
                "status": "PRESENT",
                "meta_source": identity.get("meta_source", "mtime"),
                "display_meta": {
                    "camera_model": identity.get("camera_model", "-"),
                },
                "raw_meta": {
                    "orig_name": identity["orig_name_first_seen"],
                    "serial": identity.get("serial", PLACEHOLDER),
                    "filesize": file_size,
                    "mtime": file_mtime,
                },
                "geo": {
                    "coord": [],
                    "loc_name": "-",
                    "map_url": "-",
                },
            }
            lineage["records"][record_id] = record_payload

            hash_to_record[sha] = {"lineage_id": lineage_id, "record_id": record_id}
            path_to_record[rel_path] = {"lineage_id": lineage_id, "record_id": record_id}

            if category == "raw":
                bundle_to_raw_paths[lineage.get("bundle_id", "")].append(str(path_obj.resolve()))

            inherited_indexes.setdefault("hash", {}).setdefault(
                sha,
                {
                    "lineage_id": lineage_id,
                    "lineage": lineage,
                    "record_id": record_id,
                    "record": record_payload,
                },
            )
            inherited_indexes.setdefault("path", {}).setdefault(
                rel_key,
                {
                    "lineage_id": lineage_id,
                    "lineage": lineage,
                    "record_id": record_id,
                    "record": record_payload,
                },
            )
            inherited_indexes.setdefault("capture", {}).setdefault(capture_key, lineage_id)

        for lineage_id, lineage in lineages.items():
            bundle_id = lineage.get("bundle_id", "")
            raw_paths = sorted(set(bundle_to_raw_paths.get(bundle_id, [])))
            for record_id, record in lineage.get("records", {}).items():
                abs_path = _norm_abs(root / record.get("relative_path", ""))
                linked_raw = [p for p in raw_paths if _norm_abs(p) != abs_path]
                record["linked_raw_paths"] = linked_raw
                record_lookup[abs_path] = {
                    "bundle_id": bundle_id,
                    "lineage_id": lineage_id,
                    "record_id": record_id,
                    "linked_raw_paths": linked_raw,
                }

        manifest_payload = {
            "manifest_version": MANIFEST_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "folder": root.name,
            "lineages": lineages,
            "indexes": {
                "hash_to_record": hash_to_record,
                "path_to_record": path_to_record,
            },
        }

        manifest_path = root / MANIFEST_FILE_NAME
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_payload, f, ensure_ascii=False, indent=2)
            written_count += 1
        except Exception:
            continue

    if log_callback:
        record_count = len(record_lookup)
        if written_count == 0:
            log_callback("[MANIFEST] Rebuild manifest files: done (no target folder written).")
        else:
            log_callback(
                "[MANIFEST] Rebuild manifest files: done "
                f"({written_count} manifest files written, {record_count} records indexed)."
            )
    return record_lookup


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
            f"GEO stats | PASS: {geo_stats.get('pass', 0)} | "
            f"FAIL: {geo_stats.get('fail', 0)} | SKIP: {geo_stats.get('skip', 0)}",
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
        geo_key = _norm_abs(target_path)
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
    q.put(("log", f"CSV report exported: {manifest_path.name}"))

    generate_file_type_summary(dest_path, audit_manifest)
    generate_manifest_html(dest_path, audit_manifest)
    index_report_path = Path(dest_path) / "_index.html"
    q.put(("log", "HTML report exported: _index.html"))
    return index_report_path


def export_audit_bundle(
    dest_path,
    audit_manifest,
    enable_geo_lookup,
    performance_mode,
    q,
    geo_stats,
    geo_fail_reason_counter,
    geo_fail_by_abs_path,
    geo_map_by_abs_path,
):
    """Merge GEO columns and export reports; return index path or None."""
    if not audit_manifest:
        return None
    try:
        merge_geo_audit_columns(
            audit_manifest,
            enable_geo_lookup,
            performance_mode,
            q,
            geo_stats,
            geo_fail_reason_counter,
            geo_fail_by_abs_path,
            geo_map_by_abs_path,
        )
        return export_index_reports(dest_path, audit_manifest, q)
    except Exception as e:
        q.put(("error_log", f"ERROR: failed to export CSV audit report: {e}"))
        return None


def write_skiplist_report(dest_path, report_lines, skipped_count, failed_count):
    """Write `_manifest_skiplist.txt` and return the user-facing suffix message."""
    report_file_path = Path(dest_path) / "_manifest_skiplist.txt"
    with open(report_file_path, "w", encoding="utf-8") as f:
        f.write(f"=== 媒體整理跳過/錯誤報告 (產生時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===\n")
        f.write(f"TOTAL SKIP: {skipped_count} | TOTAL FAIL: {failed_count}\n")
        f.write("=" * 80 + "\n")
        f.writelines(report_lines)
    return "\n\n報表已輸出至 output 根目錄:\n_manifest_skiplist.txt\n_manifest_audit.csv\n_index.html"


def build_skiplist_append_message(dest_path, report_lines, skipped_count, failed_count):
    """Return report suffix message while keeping pipeline flow resilient."""
    if not report_lines:
        return ""
    try:
        return write_skiplist_report(dest_path, report_lines, skipped_count, failed_count)
    except Exception:
        return ""


__all__ = [
    "MANIFEST_FILE_NAME",
    "MANIFEST_TXN_LOG_FILE",
    "begin_manifest_transaction",
    "commit_manifest_transaction",
    "fail_manifest_transaction",
    "recover_manifest_transactions",
    "load_and_merge_manifest_indexes",
    "rebuild_folder_manifests",
    "merge_geo_audit_columns",
    "write_manifest_audit_csv",
    "export_index_reports",
    "export_audit_bundle",
    "write_skiplist_report",
    "build_skiplist_append_message",
]
