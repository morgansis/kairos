"""GPS coordinate extraction helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
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
    from ..config.constants import STANDARD_EXTENSIONS
except ImportError:  # pragma: no cover - direct script execution fallback
    from config.constants import STANDARD_EXTENSIONS


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


__all__ = [
    "EXIFREAD_AVAILABLE",
    "PIL_AVAILABLE",
    "_geo_ratio_to_float",
    "_geo_dms_to_decimal",
    "_geo_extract_with_exifread",
    "_geo_extract_with_exiftool",
    "_geo_extract_with_pillow_heif",
    "extract_raw_coords",
]
