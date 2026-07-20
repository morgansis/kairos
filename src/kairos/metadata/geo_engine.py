"""GPS coordinate extraction helpers."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

try:
    import exifread

    EXIFREAD_AVAILABLE = True
except ImportError:
    EXIFREAD_AVAILABLE = False

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import reverse_geocoder as rg

    RG_AVAILABLE = True
except ImportError:
    RG_AVAILABLE = False

try:
    from ..config.constants import GEO_LOOKUP_EXTENSIONS, STANDARD_EXTENSIONS, VIDEO_EXTENSIONS
    from ..utils.file_ops import timestamp_parts
    from ..utils.sys_helpers import format_display_path
    from ..utils.sys_helpers import format_time
except ImportError:  # pragma: no cover - direct script execution fallback
    from config.constants import GEO_LOOKUP_EXTENSIONS, STANDARD_EXTENSIONS, VIDEO_EXTENSIONS
    from utils.file_ops import timestamp_parts
    from utils.sys_helpers import format_display_path
    from utils.sys_helpers import format_time


GEO_COORD_CACHE = {}
GEO_PERF_STATS = {
    "queries": 0,
    "cache_hits": 0,
    "new_lookups": 0,
    "copied": 0,
    "skipped": 0,
    "total_time": 0.0,
}


def load_and_merge_geo_caches(source_folders, dest_dir, log_callback=None):
    """Load and merge geo caches from destination and source parent paths."""
    cache_files_found = set()

    dest_cache = Path(dest_dir) / "_manifest_geo.json"
    if dest_cache.exists():
        cache_files_found.add(dest_cache)

    for src in source_folders:
        src_path = Path(src)
        for check_dir in [src_path, src_path.parent]:
            src_cache = check_dir / "_manifest_geo.json"
            if src_cache.exists():
                cache_files_found.add(src_cache)

    loaded_count = 0
    for cache_file in cache_files_found:
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for key_str, loc_name in data.items():
                    if "," in key_str:
                        lat_str, lon_str = key_str.split(",", 1)
                        coord_key = (round(float(lat_str), 3), round(float(lon_str), 3))
                        if coord_key not in GEO_COORD_CACHE:
                            GEO_COORD_CACHE[coord_key] = loc_name
                            loaded_count += 1
            if log_callback:
                log_callback(
                    f"[GEO_CACHE] Loaded cache file: {cache_file.name} (+{loaded_count} merged keys)"
                )
        except Exception as e:
            if log_callback:
                log_callback(f"[GEO_CACHE] Failed to load ({cache_file.name}): {e}")


def save_geo_cache_to_dest(dest_dir, log_callback=None):
    """Persist merged GEO cache into destination root."""
    if not GEO_COORD_CACHE:
        return
    dest_cache = Path(dest_dir) / "_manifest_geo.json"
    try:
        export_data = {f"{lat},{lon}": name for (lat, lon), name in GEO_COORD_CACHE.items()}
        with open(dest_cache, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        if log_callback:
            log_callback(f"[GEO_CACHE] Saved merged cache: {dest_cache.name} ({len(export_data)} keys)")
    except Exception as e:
        if log_callback:
            log_callback(f"[GEO_CACHE] Save failed: {e}")


def get_stats_banner_html():
    """Render runtime GEO statistics banner for manifest report."""
    t_time = format_time(GEO_PERF_STATS.get("total_time", 0))
    copied = GEO_PERF_STATS.get("copied", 0)
    skipped = GEO_PERF_STATS.get("skipped", 0)
    queries = GEO_PERF_STATS.get("queries", 0)
    hits = GEO_PERF_STATS.get("cache_hits", 0)
    new_l = GEO_PERF_STATS.get("new_lookups", 0)
    hit_rate = (hits / queries * 100) if queries > 0 else 0.0

    return f"""
    <div style="background: #EAF2F8; border-left: 4px solid #2980B9; padding: 12px 18px; margin: 15px 0; border-radius: 6px; font-size: 13px; display: flex; flex-wrap: wrap; gap: 20px; color: #2C3E50; box-shadow: 0 1px 3px rgba(0,0,0,0.05); line-height: 1.6;">
        <span><b>Total Time:</b> {t_time}</span>
        <span><b>Copied / Skipped:</b> {copied:,} / {skipped:,}</span>
        <span><b>Geo Queries:</b> {queries:,}</span>
        <span><b>Cache Hit:</b> {hits:,} (<span style="color:#27AE60; font-weight:bold;">{hit_rate:.1f}%</span>)</span>
        <span><b>Batch Lookups:</b> {new_l:,}</span>
    </div>
    """


def _geo_ratio_to_float(value):
    try:
        if hasattr(value, "num") and hasattr(value, "den"):
            den = float(value.den) if float(value.den) != 0 else 1.0
            return float(value.num) / den
        if isinstance(value, tuple) and len(value) == 2:
            den = float(value[1]) if float(value[1]) != 0 else 1.0
            return float(value[0]) / den
        return float(value)
    except Exception:
        return None


def _geo_dms_to_decimal(dms_values, ref_tag):
    try:
        if len(dms_values) < 3:
            return None
        d = _geo_ratio_to_float(dms_values[0])
        m = _geo_ratio_to_float(dms_values[1])
        s = _geo_ratio_to_float(dms_values[2])
        if d is None or m is None or s is None:
            return None
        dec = d + (m / 60.0) + (s / 3600.0)
        if str(ref_tag).upper() in ["S", "W"]:
            dec = -dec
        return dec
    except Exception:
        return None


def _geo_extract_with_exifread(file_path):
    if not EXIFREAD_AVAILABLE:
        return None, None, "FAIL: exifread unavailable"
    try:
        with open(file_path, "rb") as f:
            tags = exifread.process_file(f, details=False)
        if "GPS GPSLatitude" not in tags or "GPS GPSLongitude" not in tags:
            return None, None, "FAIL: missing GPS EXIF (GPSLatitude/GPSLongitude)"
        lat_ref = str(tags.get("GPS GPSLatitudeRef", "N"))
        lon_ref = str(tags.get("GPS GPSLongitudeRef", "E"))
        lat = _geo_dms_to_decimal(tags["GPS GPSLatitude"].values, lat_ref)
        lon = _geo_dms_to_decimal(tags["GPS GPSLongitude"].values, lon_ref)
        if lat is None or lon is None:
            return None, None, "FAIL: invalid GPS EXIF DMS values"
        return lat, lon, None
    except Exception as e:
        return None, None, f"ERROR: EXIF parse exception | {repr(e)}"


def _geo_extract_with_exiftool(file_path):
    exiftool_path = shutil.which("exiftool")
    if not exiftool_path:
        return None, None, "FAIL: exiftool unavailable"
    try:
        cp = subprocess.run(
            [exiftool_path, "-j", "-n", "-GPSLatitude", "-GPSLongitude", str(file_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        if cp.returncode != 0:
            return None, None, f"ERROR: exiftool failed | {cp.stderr.strip()}"
        payload = json.loads(cp.stdout or "[]")
        if not payload or not isinstance(payload, list):
            return None, None, "FAIL: exiftool returned empty payload"
        row = payload[0]
        lat = row.get("GPSLatitude")
        lon = row.get("GPSLongitude")
        if lat is None or lon is None:
            return None, None, "FAIL: exiftool returned no GPS fields"
        return float(lat), float(lon), None
    except Exception as e:
        return None, None, f"ERROR: exiftool exception | {repr(e)}"


def _geo_extract_with_pillow_heif(file_path):
    if not PIL_AVAILABLE:
        return None, None, "FAIL: Pillow unavailable"
    try:
        import pillow_heif
    except Exception:
        return None, None, "FAIL: pillow-heif unavailable"

    try:
        pillow_heif.register_heif_opener()
        with Image.open(file_path) as img:
            exif = img.getexif()
            gps_ifd = exif.get_ifd(0x8825) if hasattr(exif, "get_ifd") else None
            if gps_ifd is None:
                gps_ifd = exif.get(34853) if exif else None
            if not gps_ifd:
                return None, None, "FAIL: missing GPS EXIF in pillow-heif metadata"
            lat_values = gps_ifd.get(2)
            lon_values = gps_ifd.get(4)
            lat_ref = gps_ifd.get(1, "N")
            lon_ref = gps_ifd.get(3, "E")
            if not lat_values or not lon_values:
                return None, None, "FAIL: missing GPS EXIF (GPSLatitude/GPSLongitude)"
            lat = _geo_dms_to_decimal(lat_values, lat_ref)
            lon = _geo_dms_to_decimal(lon_values, lon_ref)
            if lat is None or lon is None:
                return None, None, "FAIL: invalid GPS EXIF DMS values"
            return lat, lon, None
    except Exception as e:
        return None, None, f"ERROR: pillow-heif parse exception | {repr(e)}"


def extract_raw_coords(file_path):
    ext = Path(file_path).suffix.lower()
    if ext not in STANDARD_EXTENSIONS:
        return None, None, "SKIP: EXIF GPS not supported for this file type"

    lat, lon, reason = _geo_extract_with_exifread(file_path)
    if (lat is None or lon is None) and ext in {".heic", ".heif"}:
        lat, lon, reason_pillow = _geo_extract_with_pillow_heif(file_path)
        if lat is None or lon is None:
            lat, lon, reason_exiftool = _geo_extract_with_exiftool(file_path)
            reason = reason_exiftool or reason_pillow or reason
        else:
            reason = None

    if lat is None or lon is None:
        reason = reason or "FAIL: missing GPS EXIF (GPSLatitude/GPSLongitude)"
        return None, None, reason

    return lat, lon, None


def collect_media_records(
    dest_path,
    organize_by_time,
    enable_geo_lookup=False,
    q=None,
    stop_event=None,
    start_time=0,
    processed_size=0,
    performance_mode=False,
):
    """Rebuild report records and optional geo metadata from destination tree."""
    records_by_group = defaultdict(list)
    geo_log_callback = (lambda message: q.put(("log", message))) if (q and not performance_mode) else None
    geo_stats = {"pass": 0, "fail": 0, "skip": 0}
    geo_fail_by_abs_path = {}
    geo_map_by_abs_path = {}
    geo_fail_reason_counter = Counter()
    roots = [p for p in dest_path.iterdir() if p.is_dir()] if organize_by_time else [dest_path]

    all_files = []
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file() and not path.name.startswith("_"):
                ext = path.suffix.lower()
                if ext in STANDARD_EXTENSIONS or ext in VIDEO_EXTENSIONS:
                    all_files.append((root.name if organize_by_time else "ALL_MEDIA", path))

    total_count = len(all_files)
    file_geo_tasks = []
    unique_keys_to_query = set()

    for idx, (month_key, path) in enumerate(all_files, start=1):
        if stop_event and stop_event.is_set():
            break

        if q and idx % 15 == 0:
            q.put(("status", f"Building HTML report and extracting GPS data... ({idx} / {total_count})"))
            q.put(("progress", idx / max(total_count, 1)))
            if start_time > 0:
                q.put(("metrics", (time.time() - start_time, processed_size)))

        ext = path.suffix.lower()
        base, _ = timestamp_parts(path.stem)
        category = "candidate" if "candidate" in path.parts else ("video" if ext in VIDEO_EXTENSIONS else "standard")

        loc_name, map_url = "-", "-"
        needs_geo_lookup = category in ("standard", "candidate") and ext in GEO_LOOKUP_EXTENSIONS

        rec_dict = {
            "name": path.name,
            "rel_path": path.relative_to(dest_path).as_posix(),
            "size": path.stat().st_size,
            "category": category,
            "group_key": base or path.stem,
            "group_order": 1 if category == "candidate" else 0,
            "loc_name": loc_name,
            "map_url": map_url,
        }
        records_by_group[month_key].append(rec_dict)

        if enable_geo_lookup and needs_geo_lookup:
            lat, lon, reason = extract_raw_coords(path)
            if lat is None or lon is None:
                geo_stats["fail"] += 1
                abs_p = os.path.normcase(os.path.abspath(str(path)))
                geo_fail_by_abs_path[abs_p] = reason or "FAIL: missing GPS EXIF"
                geo_fail_reason_counter[reason or "FAIL: missing GPS EXIF"] += 1
                if geo_log_callback:
                    geo_log_callback(f"[GEO] {format_display_path(path)} | {reason}")
            else:
                geo_stats["pass"] += 1
                map_url = f"https://www.google.com/maps?q={lat:.4f},{lon:.4f}"
                coord_key = (round(lat, 3), round(lon, 3))

                abs_p = os.path.normcase(os.path.abspath(str(path)))
                geo_map_by_abs_path[abs_p] = map_url
                rec_dict["map_url"] = map_url

                GEO_PERF_STATS["queries"] += 1
                if coord_key in GEO_COORD_CACHE:
                    GEO_PERF_STATS["cache_hits"] += 1
                    rec_dict["loc_name"] = GEO_COORD_CACHE[coord_key]
                else:
                    unique_keys_to_query.add(coord_key)
                    file_geo_tasks.append((rec_dict, coord_key))
        elif enable_geo_lookup and not needs_geo_lookup:
            geo_stats["skip"] += 1

    if unique_keys_to_query and RG_AVAILABLE:
        query_list = list(unique_keys_to_query)
        if q:
            q.put(("status", f"Running reverse_geocoder batch lookup... ({len(query_list)} coords)"))
        try:
            res_list = rg.search(query_list)
            for idx, coord_key in enumerate(query_list):
                info = res_list[idx]
                c = info.get("cc", "")
                a1 = info.get("admin1", "")
                a2 = info.get("name", "")
                parts = [p for p in [c, a1] if p]
                loc_str = " - ".join(parts)
                loc_name = f"{loc_str} ({a2})" if (loc_str and a2) else (loc_str or a2 or "-")
                GEO_COORD_CACHE[coord_key] = loc_name
            GEO_PERF_STATS["new_lookups"] += len(query_list)
            if geo_log_callback:
                geo_log_callback(f"[GEO_BATCH] Batch reverse lookup completed: {len(query_list)} keys")
        except Exception as e:
            if geo_log_callback:
                geo_log_callback(f"[GEO_ERROR] Batch reverse lookup failed: {e}")

    for rec_dict, coord_key in file_geo_tasks:
        rec_dict["loc_name"] = GEO_COORD_CACHE.get(coord_key, "-")

    if q:
        q.put(("progress", 1.0))
        if start_time > 0:
            q.put(("metrics", (time.time() - start_time, processed_size)))

    return records_by_group, geo_stats, geo_fail_by_abs_path, geo_map_by_abs_path, geo_fail_reason_counter


__all__ = [
    "EXIFREAD_AVAILABLE",
    "PIL_AVAILABLE",
    "GEO_COORD_CACHE",
    "GEO_PERF_STATS",
    "load_and_merge_geo_caches",
    "save_geo_cache_to_dest",
    "get_stats_banner_html",
    "_geo_ratio_to_float",
    "_geo_dms_to_decimal",
    "_geo_extract_with_exifread",
    "_geo_extract_with_exiftool",
    "_geo_extract_with_pillow_heif",
    "extract_raw_coords",
    "collect_media_records",
]
